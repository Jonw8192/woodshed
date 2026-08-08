from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

SCHEMA_VERSION='2.0'

class SourceStamp(BaseModel):
    provider:str; source_record_id:str|None=None; observed_at:datetime; effective_at:datetime|None=None; ingested_at:datetime; schema_version:str=SCHEMA_VERSION
class CanonicalUser(BaseModel): id:str; account_id:str; display_name:str|None=None
class CanonicalAccount(BaseModel): id:str; status:Literal['active','disabled']='active'
class ProviderConnection(BaseModel): id:str; account_id:str; provider:str; provider_user_id:str|None=None; status:str='active'
class CanonicalLeague(BaseModel): id:str; account_id:str; provider:str; provider_league_id:str; name:str; season:str; source:SourceStamp
class LeagueSettings(BaseModel): league_id:str; roster_positions:list[str]=Field(default_factory=list); scoring:dict[str,float]=Field(default_factory=dict); waiver_budget:int|None=None; source:SourceStamp
class ManagerIdentity(BaseModel): id:str; account_id:str; provider_user_id:str|None=None; display_name:str|None=None
class ManagerSeasonIdentity(BaseModel): manager_id:str; league_id:str; season:str; roster_id:str|None=None; attribution_quality:str='uncertain'
class CanonicalRoster(BaseModel): id:str; league_id:str; manager_season_id:str|None=None; roster_id:str; players:list[str]=Field(default_factory=list); starters:list[str]=Field(default_factory=list); faab_left:int|None=None; source:SourceStamp
class CanonicalPlayer(BaseModel): id:str; provider:str; provider_player_id:str; name:str; position:str; team:str|None=None; source:SourceStamp
class DraftMeta(BaseModel): provider_draft_id:str; league_id:str; season:str; purpose:str='unknown'; mechanic:str='unknown'; status:str; source:SourceStamp
class CanonicalDraftPick(BaseModel): provider_draft_id:str; pick_no:int; round:int|None=None; player_id:str|None=None; manager_id:str|None=None; roster_id:str|None=None; attribution_quality:str='uncertain'; source:SourceStamp
class ModelRun(BaseModel): id:str; account_id:str; league_id:str|None=None; model_name:str; model_version:str; input_hash:str; scoring_fingerprint:str|None=None; seed:int|None=None; created_at:datetime
class DataLineage(BaseModel): model_run_id:str; source_kind:str; source_id:str; observed_at:datetime|None=None
class Recommendation(BaseModel): id:str; model_run_id:str; kind:str; output:dict; evidence_strength:str; created_at:datetime
