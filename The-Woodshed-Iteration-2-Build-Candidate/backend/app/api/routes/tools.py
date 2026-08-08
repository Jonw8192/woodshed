import asyncio
from fastapi import APIRouter,Depends,Request
from app.schemas.fantasy import TradeAnalyzeRequest,StartSitRequest,WaiverRequest,RankingsRequest,InsightRequest,GuillotineRequest
from app.domain.trades import analyze_trade
from app.domain.start_sit import start_sit
from app.domain.waivers import optimize_waivers
from app.domain.rankings import rank_ros
from app.domain.guillotine import chop_probabilities
from app.services.insights import InsightService
from app.api.deps import insight_service,require_ai_entitlement
router=APIRouter(prefix='/tools',tags=['tools'])
@router.post('/trade')
async def trade(req:TradeAnalyzeRequest):return analyze_trade(req)
@router.post('/start-sit')
async def start(req:StartSitRequest):return start_sit(req)
@router.post('/waivers')
async def waivers(req:WaiverRequest):return {'targets':optimize_waivers(req)}
@router.post('/rankings/ros')
async def rankings(req:RankingsRequest):return {'rankings':rank_ros(req)}
@router.post('/guillotine/chop')
async def guillotine(req:GuillotineRequest,request:Request):
    sem=request.app.state.simulation_semaphore
    async with sem:return await asyncio.to_thread(chop_probabilities,req)
@router.post('/insights/player/deterministic')
async def deterministic_insight(req:InsightRequest,svc:InsightService=Depends(insight_service)):
    req.include_ai=False;return await svc.generate(req)
@router.post('/insights/player/ai')
async def ai_insight(req:InsightRequest,account:str=Depends(require_ai_entitlement),svc:InsightService=Depends(insight_service)):
    req.include_ai=True;return await svc.generate(req)
