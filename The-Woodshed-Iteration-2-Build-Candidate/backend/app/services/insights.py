from __future__ import annotations
from app.schemas.fantasy import InsightRequest, FantasyPointsProjection
from app.core.config import Settings

class InsightService:
    def __init__(self, settings: Settings):self.settings=settings
    def _baseline(self,req:InsightRequest)->str:
        p=req.player
        if not isinstance(p,FantasyPointsProjection):
            return f'{p.name} has a raw-stat projection. A scoring-compatible fantasy-point distribution is required before a decision insight can be generated.'
        floor=p.floor if p.floor is not None else max(0,p.median-p.stdev);ceiling=p.ceiling if p.ceiling is not None else p.median+p.stdev
        spread=ceiling-floor;profile='stable' if spread<p.median*.6 else 'volatile'
        return (f'{p.name} profiles as a {profile} {p.position} option: median {p.median:.1f}, floor {floor:.1f}, ceiling {ceiling:.1f}. '
                'The decision should be driven by league scoring, lineup need, and risk tolerance rather than name value.')
    async def generate(self,req:InsightRequest)->dict:
        baseline=self._baseline(req)
        if not req.include_ai or not self.settings.ai_enabled or not self.settings.openai_api_key:
            return {'insight':baseline,'mode':'deterministic','model':None,'evidence':['projection_payload']}
        try:
            from openai import AsyncOpenAI
            client=AsyncOpenAI(api_key=self.settings.openai_api_key)
            prompt=('Use only the structured projection below. Do not invent injuries, news, usage, rankings, statistics, or matchups. '
                    'Separate fact from inference and give one concise fantasy action.\n'+req.player.model_dump_json())
            r=await client.responses.create(model=self.settings.openai_model,input=prompt,max_output_tokens=220)
            text=getattr(r,'output_text','') or baseline
            return {'insight':text,'mode':'ai','model':self.settings.openai_model,'evidence':['projection_payload']}
        except Exception:
            return {'insight':baseline,'mode':'deterministic_fallback','model':None,'evidence':['projection_payload']}
