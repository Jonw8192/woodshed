from fastapi import Request,Header,HTTPException
from app.services.league import LeagueService
from app.services.insights import InsightService
from app.core.config import get_settings

def sleeper(request:Request):return request.app.state.sleeper
def league_service(request:Request):return LeagueService(request.app.state.sleeper,getattr(request.app.state,'db',None))
def insight_service():return InsightService(get_settings())
async def current_account(x_woodshed_account_key:str|None=Header(default=None)):
    s=get_settings();accounts=s.accounts
    if not accounts:raise HTTPException(503,'account authentication is not configured')
    account=accounts.get(x_woodshed_account_key or '')
    if not account:raise HTTPException(401,'invalid account credentials')
    return account
async def require_ai_entitlement(account:str=__import__('fastapi').Depends(current_account)):
    s=get_settings()
    if not s.ai_enabled:raise HTTPException(503,'AI insights are disabled')
    return account
