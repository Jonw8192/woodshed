from __future__ import annotations
from datetime import datetime,timezone
from app.data.models import RecommendationRecord
class RecommendationRepository:
    def __init__(self,session):self.session=session
    async def save(self,*,kind,input_hash,output,model_version='1.1.0',data_version='user-input',league_id=None,seed=None,quality_state='partial'):
        x=RecommendationRecord(kind=kind,input_hash=input_hash,output=output,model_version=model_version,data_version=data_version,league_id=league_id,seed=seed,quality_state=quality_state,created_at=datetime.now(timezone.utc));self.session.add(x);await self.session.commit();await self.session.refresh(x);return x
