from __future__ import annotations
import uuid,httpx,ipaddress,asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.rate_limit import RateLimiter
from app.core.cache import Cache
from app.integrations.sleeper import SleeperClient
from app.data.database import Database
from app.api.routes.health import router as health_router
from app.api.routes.league import router as league_router
from app.api.routes.tools import router as tools_router
configure_logging();s=get_settings()
@asynccontextmanager
async def lifespan(app:FastAPI):
    cache=Cache(s.redis_url,s.cache_ttl_seconds)
    client=httpx.AsyncClient(headers={'User-Agent':'TheWoodshed/2.0-candidate'},limits=httpx.Limits(max_connections=20,max_keepalive_connections=10))
    db=Database(s);app.state.settings=s;app.state.db=db;app.state.cache=cache;app.state.http=client
    app.state.sleeper=SleeperClient(s.sleeper_base_url,cache,client,s.sleeper_timeout_seconds,s.sleeper_max_concurrency)
    app.state.limiter=RateLimiter(s.rate_limit_per_minute,cache.redis_client if s.redis_url else None)
    app.state.simulation_semaphore=asyncio.Semaphore(s.simulation_concurrency)
    yield
    await client.aclose();await cache.close();await db.close()
app=FastAPI(title=s.app_name,version='2.0.0-candidate',lifespan=lifespan,docs_url='/docs' if (s.app_env or s.environment)!='production' else None,redoc_url=None)
app.add_middleware(CORSMiddleware,allow_origins=s.cors_origins,allow_credentials=False,allow_methods=['GET','POST'],allow_headers=['Content-Type','Authorization','X-Request-ID','X-Woodshed-Account-Key'])
def client_ip(request):
    direct=request.client.host if request.client else 'unknown';xff=request.headers.get('x-forwarded-for');trusted=False
    try:
        addr=ipaddress.ip_address(direct);trusted=any(addr in ipaddress.ip_network(net,strict=False) for net in s.proxies)
    except ValueError:pass
    if xff and trusted:return xff.split(',')[0].strip()
    return direct
@app.middleware('http')
async def security(request:Request,call_next):
    limiter=getattr(request.app.state,'limiter',None)
    if limiter and not await limiter.allowed(client_ip(request)):return JSONResponse({'error':{'code':'rate_limited','message':'rate limit exceeded'}},429)
    raw=request.headers.get('content-length')
    if raw:
        try:
            if int(raw)>s.body_limit_bytes:return JSONResponse({'error':{'code':'request_too_large','message':'request too large'}},413)
        except ValueError:return JSONResponse({'error':{'code':'bad_content_length','message':'invalid content-length'}},400)
    rid=request.headers.get('x-request-id') or str(uuid.uuid4())
    try:resp=await call_next(request)
    except ValueError as e:return JSONResponse({'error':{'code':'invalid_request','message':str(e)}},422,headers={'X-Request-ID':rid})
    resp.headers.update({'X-Request-ID':rid,'X-Content-Type-Options':'nosniff','X-Frame-Options':'DENY','Referrer-Policy':'same-origin','Permissions-Policy':'camera=(), microphone=(), geolocation=()','Content-Security-Policy':"default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"})
    return resp
app.include_router(health_router);app.include_router(league_router,prefix=s.api_prefix);app.include_router(tools_router,prefix=s.api_prefix)
