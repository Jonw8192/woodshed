from fastapi import APIRouter,Request
router=APIRouter(tags=['system'])
@router.get('/live')
async def live():return {'ok':True,'service':'woodshed-api','version':'2.0.0-candidate'}
@router.get('/health')
async def health():return await live()
@router.get('/ready')
async def ready(request:Request):
    s=request.app.state.settings
    cache_ok=await request.app.state.cache.ping()
    db_configured=bool(request.app.state.db.url); db_ok=await request.app.state.db.ping() if db_configured else None
    provider_ok=None
    if s.sleeper_required:
        try:provider_ok=await request.app.state.sleeper.ping()
        except Exception:provider_ok=False
    required_checks=[]
    if s.redis_required:required_checks.append(bool(s.redis_url) and cache_ok)
    if s.database_required:required_checks.append(db_configured and db_ok is True)
    if s.sleeper_required:required_checks.append(provider_ok is True)
    ok=all(required_checks) if required_checks else True
    return {'ok':ok,'process':{'ok':True},
      'cache':{'required':s.redis_required,'configured':bool(s.redis_url),'ok':cache_ok,'degraded':request.app.state.cache.degraded},
      'database':{'required':s.database_required,'configured':db_configured,'ok':db_ok},
      'provider':{'name':'sleeper','required':s.sleeper_required,'ok':provider_ok},
      'ai':{'enabled':s.ai_enabled,'configured':bool(s.openai_api_key)}}
