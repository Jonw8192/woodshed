from __future__ import annotations
from typing import Literal, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, model_validator

Position = Literal['QB','RB','WR','TE','K','DEF']
Horizon = Literal['week','ros','season','dynasty']

class ScoringSettings(BaseModel):
    pass_yd: float=0.04; pass_td: float=4; pass_int: float=-2
    rush_yd: float=0.1; rush_td: float=6
    rec: float=1.0; rec_yd: float=0.1; rec_td: float=6
    te_rec_bonus: float=0.0; two_pt: float=2.0; fumble: float=-2.0
    pass_first_down: float=0.0; rush_first_down: float=0.0; rec_first_down: float=0.0
    bonus_pass_300: float=0.0; bonus_rush_100: float=0.0; bonus_rec_100: float=0.0
    superflex: bool=False

class ProjectionBase(BaseModel):
    model_config={'extra':'forbid'}
    player_id:str; name:str; position:Position; team:str='FA'; horizon:Horizon='ros'
    source:str='user'; source_updated_at:datetime|None=None
    quality:Literal['good','partial','stale','unknown']='unknown'

class FantasyPointsProjection(ProjectionBase):
    projection_mode: Literal['fantasy_points']='fantasy_points'
    median:float; floor:float|None=None; ceiling:float|None=None; stdev:float=0
    scoring_fingerprint:str

class RawStatProjection(ProjectionBase):
    projection_mode: Literal['raw_stats']='raw_stats'
    pass_yards:float|None=None; pass_tds:float|None=None; interceptions:float|None=None
    rush_yards:float|None=None; rush_tds:float|None=None
    receptions:float|None=None; rec_yards:float|None=None; rec_tds:float|None=None
    two_pt:float|None=None; fumbles:float|None=None
    pass_first_downs:float|None=0; rush_first_downs:float|None=0; rec_first_downs:float|None=0
    pass_300_games:float|None=0; rush_100_games:float|None=0; rec_100_games:float|None=0
    stdev:float=0

Projection = Annotated[FantasyPointsProjection|RawStatProjection, Field(discriminator='projection_mode')]

class DraftPick(BaseModel):
    season:str; manager_id:str; manager_name:str|None=None; round:int|None=None; pick_no:int|None=None
    player_id:str|None=None; player_name:str|None=None; position:str=''; nfl_team_at_event:str|None=None
    adp:float|None=None; adp_source:str|None=None; draft_purpose:str='unknown'; draft_mechanic:str='unknown'; draft_status:str='complete'
    roster_id:str|None=None; attribution_quality:Literal['verified','provider_reported','uncertain']='uncertain'

class DNARequest(BaseModel): league_id:str=Field(pattern=r'^\d{8,25}$')

class TradeAsset(BaseModel):
    id:str; name:str; kind:Literal['player','pick']='player'; position:str|None=None
    market_value:float=Field(ge=0); projection_value:float=Field(default=0,ge=0)
    replacement_value:float=Field(default=0,ge=0); starter_probability:float=Field(default=.5,ge=0,le=1)
    age:float|None=None; future_variance:float=Field(default=0,ge=0)

class TradeAnalyzeRequest(BaseModel):
    give:list[TradeAsset]=Field(min_length=1,max_length=12); receive:list[TradeAsset]=Field(min_length=1,max_length=12)
    format:Literal['redraft','dynasty','keeper']='dynasty'; scoring:ScoringSettings=Field(default_factory=ScoringSettings)
    roster_spots_open:int=Field(default=1,ge=0,le=20); lineup_slots:list[str]=Field(default_factory=list)
    league_size:int=Field(default=12,ge=4,le=32)

class StartSitCandidate(BaseModel):
    player_id:str; name:str; position:Position; projection:Projection
    active:bool=True; matchup_adjustment:float=Field(default=0,ge=-10,le=10); role_security:float=Field(default=.5,ge=0,le=1)

class StartSitRequest(BaseModel):
    week:int=Field(ge=1,le=18); slot:Literal['QB','RB','WR','TE','FLEX','SUPERFLEX']
    candidates:list[StartSitCandidate]=Field(min_length=2,max_length=20); risk_profile:Literal['floor','balanced','ceiling']='balanced'
    scoring:ScoringSettings=Field(default_factory=ScoringSettings)

class WaiverCandidate(BaseModel):
    player_id:str; name:str; position:Position; median:float; floor:float; ceiling:float
    replacement_median:float=0; usable_weeks:int=Field(default=6,ge=0,le=20); start_probability:float=Field(default=.5,ge=0,le=1)
    scarcity:float=Field(default=.5,ge=0,le=1); drop_cost:float=Field(default=0,ge=0); drop_player_id:str|None=None

class WaiverRequest(BaseModel):
    candidates:list[WaiverCandidate]=Field(min_length=1,max_length=100); faab_left:int=Field(ge=0)
    teams_remaining:int=Field(default=12,ge=2,le=32); weeks_remaining:int=Field(default=10,ge=1,le=20)
    survival_risk:float=Field(default=.2,ge=0,le=1); scoring:ScoringSettings=Field(default_factory=ScoringSettings)

class RankingsRequest(BaseModel):
    projections:list[Projection]=Field(min_length=1,max_length=1000); scoring:ScoringSettings=Field(default_factory=ScoringSettings)
    limit:int=Field(default=100,ge=1,le=500)
    @model_validator(mode='after')
    def ros_only(self):
        bad=[p.player_id for p in self.projections if p.horizon!='ros']
        if bad: raise ValueError('ROS rankings require horizon=ros for every projection')
        return self

class InsightRequest(BaseModel):
    player:Projection; context:str=Field(default='fantasy football decision support',max_length=500); include_ai:bool=False

class GuillotineTeam(BaseModel):
    roster_id:str; name:str; current_points:float=0; projected_remaining:float=0; volatility:float=Field(default=8,ge=0,le=100); faab_left:int=Field(default=100,ge=0)
class GuillotineRequest(BaseModel):
    teams:list[GuillotineTeam]=Field(min_length=2,max_length=32); simulations:int=Field(default=5000,ge=500,le=20000); seed:int=Field(default=42,ge=0,le=2_147_483_647)
