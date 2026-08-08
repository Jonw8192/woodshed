import asyncio
from datetime import datetime, timezone, timedelta
import pytest
from pydantic import ValidationError
from app.schemas.fantasy import *
from app.domain.scoring import score_raw_projection, scoring_fingerprint
from app.domain.rankings import rank_ros
from app.domain.start_sit import start_sit
from app.domain.trades import analyze_trade
from app.domain.waivers import optimize_waivers
from app.domain.league_dna import analyze_dna
from app.core.config import Settings
from app.core.cache import Cache
from app.core.rate_limit import RateLimiter
from app.integrations.sleeper import _retry_after, _draft_purpose, _draft_mechanic

BASE_RAW=dict(pass_yards=0,pass_tds=0,interceptions=0,rush_yards=0,rush_tds=0,receptions=0,rec_yards=0,rec_tds=0,two_pt=0,fumbles=0)
def raw(pid='p',name='P',pos='WR',**kw):
 d=BASE_RAW.copy();d.update(kw);return RawStatProjection(player_id=pid,name=name,position=pos,horizon='ros',**d)
def fp(s=None):return scoring_fingerprint(s or ScoringSettings())
def fpp(pid='p',name='P',pos='WR',median=10,scoring=None,**kw):return FantasyPointsProjection(player_id=pid,name=name,position=pos,horizon='ros',median=median,scoring_fingerprint=fp(scoring),**kw)

# scoring semantics (1-10)
def test_i2_01_scoring_fingerprint_stable(): assert fp()==fp()
def test_i2_02_scoring_fingerprint_changes_with_ppr(): assert fp(ScoringSettings(rec=0))!=fp(ScoringSettings(rec=1))
def test_i2_03_raw_ppr_scoring(): assert score_raw_projection(raw(receptions=10),ScoringSettings(rec=1))==10
def test_i2_04_raw_half_ppr_scoring(): assert score_raw_projection(raw(receptions=10),ScoringSettings(rec=.5))==5
def test_i2_05_te_premium_scoring(): assert score_raw_projection(raw(pos='TE',receptions=10),ScoringSettings(rec=1,te_rec_bonus=.5))==15
def test_i2_06_pass_td_scoring(): assert score_raw_projection(raw(pos='QB',pass_tds=5),ScoringSettings(pass_td=6))==30
def test_i2_07_first_down_scoring(): assert score_raw_projection(raw(rush_first_downs=10),ScoringSettings(rush_first_down=.5))==5
def test_i2_08_bonus_scoring(): assert score_raw_projection(raw(rush_100_games=3),ScoringSettings(bonus_rush_100=2))==6
def test_i2_09_missing_required_raw_stats_rejected():
 p=RawStatProjection(player_id='p',name='P',position='WR',horizon='ros',receptions=10)
 with pytest.raises(ValueError):score_raw_projection(p,ScoringSettings())
def test_i2_10_explicit_zero_raw_stats_valid(): assert score_raw_projection(raw(),ScoringSettings())==0

# projection/rankings contracts (11-16)
def test_i2_11_fantasy_points_preserved_exactly():
 s=ScoringSettings();r=rank_ros(RankingsRequest(scoring=s,projections=[fpp(median=180,scoring=s)]))[0];assert r['median']==180
def test_i2_12_qa_partial_projection_cannot_be_silently_rebuilt():
 with pytest.raises(ValidationError):
  RankingsRequest(projections=[{'projection_mode':'fantasy_points','player_id':'w','name':'WR','position':'WR','horizon':'ros','median':180,'receptions':80,'scoring_fingerprint':fp()}])
def test_i2_13_incompatible_fantasy_points_fingerprint_rejected_at_engine():
 with pytest.raises(ValueError):rank_ros(RankingsRequest(scoring=ScoringSettings(rec=0),projections=[fpp(median=10,scoring=ScoringSettings(rec=1))]))
def test_i2_14_raw_stats_rank_responds_to_scoring():
 a=raw('te','TE','TE',receptions=80,rec_yards=800,rec_tds=5);b=raw('rb','RB','RB',rush_yards=900,rush_tds=7,receptions=20,rec_yards=200)
 base=rank_ros(RankingsRequest(scoring=ScoringSettings(rec=.5),projections=[a,b]));tep=rank_ros(RankingsRequest(scoring=ScoringSettings(rec=.5,te_rec_bonus=1),projections=[a,b]));assert base[0]['name']!=tep[0]['name']
def test_i2_15_ros_horizon_required_for_raw():
 with pytest.raises(ValidationError):RankingsRequest(projections=[RawStatProjection(player_id='x',name='X',position='WR',horizon='week',**BASE_RAW)])
def test_i2_16_ranking_output_has_scoring_fingerprint(): assert rank_ros(RankingsRequest(projections=[fpp()]))[0]['scoring_fingerprint']==fp()

# start/sit context (17-20)
def test_i2_17_start_sit_te_premium_can_flip():
 base=BASE_RAW.copy();te=raw('te','TE','TE',receptions=5,rec_yards=60);wr=raw('wr','WR','WR',receptions=5,rec_yards=70)
 def cand(p):return StartSitCandidate(player_id=p.player_id,name=p.name,position=p.position,projection=p)
 no=start_sit(StartSitRequest(week=1,slot='FLEX',scoring=ScoringSettings(rec=1),candidates=[cand(te),cand(wr)]))['start']['name']
 yes=start_sit(StartSitRequest(week=1,slot='FLEX',scoring=ScoringSettings(rec=1,te_rec_bonus=1),candidates=[cand(te),cand(wr)]))['start']['name']
 assert no=='WR' and yes=='TE'
def test_i2_18_start_sit_inactive_filtered():
 a=StartSitCandidate(player_id='a',name='A',position='WR',projection=fpp('a','A','WR',20),active=False);b=StartSitCandidate(player_id='b',name='B',position='WR',projection=fpp('b','B','WR',10));assert start_sit(StartSitRequest(week=1,slot='WR',candidates=[a,b]))['start']['name']=='B'
def test_i2_19_superflex_accepts_qb():
 a=StartSitCandidate(player_id='q',name='Q',position='QB',projection=fpp('q','Q','QB',20));b=StartSitCandidate(player_id='w',name='W',position='WR',projection=fpp('w','W','WR',10));assert start_sit(StartSitRequest(week=1,slot='SUPERFLEX',candidates=[a,b]))['start']['name']=='Q'
def test_i2_20_start_sit_returns_expected_edge():
 a=StartSitCandidate(player_id='a',name='A',position='WR',projection=fpp('a','A','WR',12));b=StartSitCandidate(player_id='b',name='B',position='WR',projection=fpp('b','B','WR',10));assert start_sit(StartSitRequest(week=1,slot='WR',candidates=[a,b]))['expected_edge']>0

# trade/waiver context (21-27)
def test_i2_21_trade_superflex_changes_qb_value():
 qb=TradeAsset(id='q',name='Q',position='QB',market_value=40,projection_value=30,replacement_value=15,starter_probability=1);wr=TradeAsset(id='w',name='W',position='WR',market_value=40,projection_value=30,replacement_value=15,starter_probability=1)
 one=analyze_trade(TradeAnalyzeRequest(give=[wr],receive=[qb],scoring=ScoringSettings(superflex=False)));sf=analyze_trade(TradeAnalyzeRequest(give=[wr],receive=[qb],scoring=ScoringSettings(superflex=True)));assert sf['receive_value']>one['receive_value']
def test_i2_22_trade_te_premium_changes_te_value():
 te=TradeAsset(id='t',name='T',position='TE',market_value=30,projection_value=25,replacement_value=10,starter_probability=1);wr=TradeAsset(id='w',name='W',position='WR',market_value=30,projection_value=25,replacement_value=10,starter_probability=1)
 a=analyze_trade(TradeAnalyzeRequest(give=[wr],receive=[te],scoring=ScoringSettings(te_rec_bonus=0)));b=analyze_trade(TradeAnalyzeRequest(give=[wr],receive=[te],scoring=ScoringSettings(te_rec_bonus=1)));assert b['receive_value']>a['receive_value']
def test_i2_23_trade_redraft_differs_from_dynasty():
 old=TradeAsset(id='o',name='Old',position='WR',market_value=50,projection_value=35,replacement_value=10,starter_probability=1,age=31)
 young=TradeAsset(id='y',name='Young',position='WR',market_value=48,projection_value=28,replacement_value=10,starter_probability=1,age=23)
 assert analyze_trade(TradeAnalyzeRequest(give=[young],receive=[old],format='redraft'))['net_value']!=analyze_trade(TradeAnalyzeRequest(give=[young],receive=[old],format='dynasty'))['net_value']
def test_i2_24_redraft_pick_market_ignored():
 pick=TradeAsset(id='p',name='2027 1st',kind='pick',market_value=50);x=analyze_trade(TradeAnalyzeRequest(give=[TradeAsset(id='x',name='X',market_value=1)],receive=[pick],format='redraft'));assert x['receive_value']==0
def test_i2_25_waiver_superflex_increases_qb_utility():
 c=WaiverCandidate(player_id='q',name='Q',position='QB',median=20,floor=15,ceiling=25,replacement_median=15);a=optimize_waivers(WaiverRequest(faab_left=100,candidates=[c],scoring=ScoringSettings(superflex=False)))[0];b=optimize_waivers(WaiverRequest(faab_left=100,candidates=[c],scoring=ScoringSettings(superflex=True)))[0];assert b['incremental_utility']>a['incremental_utility']
def test_i2_26_waiver_te_premium_increases_te_utility():
 c=WaiverCandidate(player_id='t',name='T',position='TE',median=15,floor=10,ceiling=20,replacement_median=10);a=optimize_waivers(WaiverRequest(faab_left=100,candidates=[c],scoring=ScoringSettings(te_rec_bonus=0)))[0];b=optimize_waivers(WaiverRequest(faab_left=100,candidates=[c],scoring=ScoringSettings(te_rec_bonus=1)))[0];assert b['incremental_utility']>a['incremental_utility']
def test_i2_27_waiver_preserves_drop_candidate():
 c=WaiverCandidate(player_id='t',name='T',position='TE',median=15,floor=10,ceiling=20,replacement_median=10,drop_player_id='drop');assert optimize_waivers(WaiverRequest(faab_left=10,candidates=[c]))[0]['drop_player_id']=='drop'

# DNA and provider mapping (28-31)
def test_i2_28_dna_separates_purpose_from_mechanic():
 picks=[DraftPick(season='2025',manager_id='m',round=1,pick_no=1,position='QB',draft_purpose='startup',draft_mechanic='snake'),DraftPick(season='2025',manager_id='m',round=1,pick_no=1,position='RB',draft_purpose='rookie',draft_mechanic='snake')];out=analyze_dna(picks);assert {x['draft_purpose'] for x in out}=={'startup','rookie'}
def test_i2_29_draft_purpose_mapping(): assert _draft_purpose({'metadata':{'name':'2026 Rookie Draft'},'type':'snake'})=='rookie'
def test_i2_30_draft_mechanic_mapping(): assert _draft_mechanic({'type':'snake','metadata':{'name':'Rookie'}})=='snake'
def test_i2_31_dna_uses_evidence_strength_name(): assert 'evidence_strength' in analyze_dna([DraftPick(season='2025',manager_id='m',round=1,pick_no=1,position='QB')])[0]

# environment and controls (32-36)
def test_i2_32_production_requires_database_when_flagged():
 with pytest.raises(ValidationError):Settings(app_env='production',database_required=True,database_url=None)
def test_i2_33_production_requires_redis_when_flagged():
 with pytest.raises(ValidationError):Settings(app_env='production',redis_required=True,redis_url=None)
def test_i2_34_retry_after_seconds(): assert _retry_after('1.5')==1.5
def test_i2_35_retry_after_http_date_nonnegative():
 value=(datetime.now(timezone.utc)+timedelta(seconds=2)).strftime('%a, %d %b %Y %H:%M:%S GMT');assert _retry_after(value)>=0
@pytest.mark.asyncio
async def test_i2_36_cache_key_lock_cleanup():
 c=Cache(None)
 async with c.key_lock('a'): assert 'a' in c._key_locks
 assert 'a' not in c._key_locks
