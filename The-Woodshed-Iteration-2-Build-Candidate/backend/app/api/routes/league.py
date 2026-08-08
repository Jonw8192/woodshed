from fastapi import APIRouter,Depends,HTTPException
from app.schemas.fantasy import DNARequest
from app.services.league import LeagueService
from app.services.importer import normalize_sleeper_league,persist_import
from app.api.deps import league_service,current_account
from app.integrations.sleeper import SleeperError,SleeperNotFound,SleeperRateLimited
router=APIRouter(prefix='/league',tags=['league'])
def _raise(e):
    if isinstance(e,SleeperNotFound):raise HTTPException(404,str(e))
    if isinstance(e,SleeperRateLimited):raise HTTPException(503,str(e),headers={'Retry-After':'30'})
    raise HTTPException(502,str(e))
@router.get('/{league_id}')
async def overview(league_id:str,svc:LeagueService=Depends(league_service)):
    if not league_id.isdigit() or not 8<=len(league_id)<=25:raise HTTPException(422,'league_id must be an 8-25 digit Sleeper league id')
    try:return await svc.overview(league_id)
    except SleeperError as e:_raise(e)
@router.post('/dna')
async def dna(req:DNARequest,svc:LeagueService=Depends(league_service)):
    try:
        out=await svc.dna(req.league_id)
        if not out['sample_size']:raise HTTPException(404,'No completed draft history found')
        return out
    except SleeperError as e:_raise(e)
@router.post('/{league_id}/import')
async def import_league(league_id:str,account_id:str=Depends(current_account),svc:LeagueService=Depends(league_service)):
    if not league_id.isdigit() or not 8<=len(league_id)<=25:raise HTTPException(422,'invalid Sleeper league id')
    if not svc.db or not svc.db.sessions:raise HTTPException(503,'durable league import requires configured Postgres')
    try:raw=await svc.overview(league_id)
    except SleeperError as e:_raise(e)
    league,settings,rosters=normalize_sleeper_league(account_id=account_id,league=raw['league'],rosters=raw['rosters'])
    async with svc.db.sessions() as session:db_id=await persist_import(session,account_id=account_id,league=league,settings=settings,rosters=rosters)
    return {'status':'imported','league_id':league_id,'canonical_league_id':league.id,'database_id':db_id,'rosters':len(rosters),'schema_version':'2.0'}
