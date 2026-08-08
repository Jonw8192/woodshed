import pytest
from pydantic import ValidationError
from app.schemas.fantasy import *
from app.domain.trades import analyze_trade
from app.domain.start_sit import start_sit
from app.domain.waivers import optimize_waivers
from app.domain.rankings import rank_ros
from app.domain.league_dna import analyze_dna
from app.domain.guillotine import chop_probabilities
from app.domain.scoring import scoring_fingerprint

def fp(scoring=None):return scoring_fingerprint(scoring or ScoringSettings())
def pts(pid,name,pos,median,**kw):return FantasyPointsProjection(player_id=pid,name=name,position=pos,horizon=kw.pop('horizon','ros'),median=median,scoring_fingerprint=kw.pop('scoring_fingerprint',fp()),**kw)
def raw(pid,name,pos,**kw):return RawStatProjection(player_id=pid,name=name,position=pos,horizon=kw.pop('horizon','ros'),**kw)

def test_trade_accept():
 r=TradeAnalyzeRequest(give=[TradeAsset(id='a',name='A',market_value=40,projection_value=20,replacement_value=8)],receive=[TradeAsset(id='b',name='B',market_value=50,projection_value=26,replacement_value=9)])
 assert analyze_trade(r)['verdict'] in {'accept','strong_accept'}
def test_trade_roster_overflow_penalized():
 r=TradeAnalyzeRequest(give=[TradeAsset(id='a',name='A',market_value=50)],receive=[TradeAsset(id='b',name='B',market_value=25),TradeAsset(id='c',name='C',market_value=25)],roster_spots_open=0)
 assert analyze_trade(r)['roster_overflow']==1
def test_start_sit_floor_prefers_safe():
 r=StartSitRequest(week=1,slot='FLEX',risk_profile='floor',candidates=[StartSitCandidate(player_id='1',name='Safe',position='WR',projection=pts('1','Safe','WR',14,floor=11,ceiling=18)),StartSitCandidate(player_id='2',name='Boom',position='WR',projection=pts('2','Boom','WR',15,floor=4,ceiling=27))])
 assert start_sit(r)['start']['name']=='Safe'
def test_start_sit_rejects_ineligible():
 r=StartSitRequest(week=1,slot='QB',candidates=[StartSitCandidate(player_id='1',name='WR1',position='WR',projection=pts('1','WR1','WR',14)),StartSitCandidate(player_id='2',name='WR2',position='WR',projection=pts('2','WR2','WR',13))])
 with pytest.raises(ValueError):start_sit(r)
def test_waiver_budget_cap():
 r=WaiverRequest(faab_left=40,candidates=[WaiverCandidate(player_id='1',name='P',position='RB',median=18,floor=12,ceiling=24,replacement_median=9)])
 assert optimize_waivers(r)[0]['suggested_bid']<=40
def test_waiver_incremental_value_matters():
 r=WaiverRequest(faab_left=100,candidates=[WaiverCandidate(player_id='a',name='Upgrade',position='RB',median=15,floor=10,ceiling=20,replacement_median=5),WaiverCandidate(player_id='b',name='Small',position='QB',median=22,floor=18,ceiling=26,replacement_median=21)])
 assert optimize_waivers(r)[0]['name']=='Upgrade'
def test_rankings_ppr_changes_order():
 base=dict(pass_yards=0,pass_tds=0,interceptions=0,rush_yards=0,rush_tds=0,two_pt=0,fumbles=0)
 ps=[raw('w','WR','WR',receptions=90,rec_yards=900,rec_tds=5,stdev=10,**base),raw('r','RB','RB',receptions=15,rec_yards=300,rec_tds=2,rush_yards=900,rush_tds=7,stdev=10,pass_yards=0,pass_tds=0,interceptions=0,two_pt=0,fumbles=0)]
 standard=rank_ros(RankingsRequest(scoring=ScoringSettings(rec=0),projections=ps));ppr=rank_ros(RankingsRequest(scoring=ScoringSettings(rec=1),projections=ps))
 assert standard[0]['name']=='RB' and ppr[0]['name']=='WR'
def test_rankings_custom_pass_td_scoring_changes_qb_points():
 p=raw('q','QB','QB',pass_yards=4000,pass_tds=30,interceptions=10,rush_yards=0,rush_tds=0,receptions=0,rec_yards=0,rec_tds=0,two_pt=0,fumbles=0)
 four=rank_ros(RankingsRequest(scoring=ScoringSettings(pass_td=4),projections=[p]))[0]['median'];six=rank_ros(RankingsRequest(scoring=ScoringSettings(pass_td=6),projections=[p]))[0]['median']
 assert six-four==60
def test_rankings_ros_horizon_enforced():
 with pytest.raises(ValidationError):RankingsRequest(projections=[pts('x','X','WR',10,horizon='week')])
def test_dna_same_window_baseline_and_segment():
 picks=[]
 for y in ['2023','2024','2025']:
  picks += [DraftPick(season=y,manager_id='m',round=1,pick_no=1,position='QB',draft_purpose='startup'),DraftPick(season=y,manager_id='m',round=2,pick_no=2,position='QB',draft_purpose='startup'),DraftPick(season=y,manager_id='o',round=1,pick_no=3,position='RB',draft_purpose='startup'),DraftPick(season=y,manager_id='o',round=2,pick_no=4,position='WR',draft_purpose='startup')]
 m=next(x for x in analyze_dna(picks) if x['manager_id']=='m')
 assert m['dominant_early_position']=='QB' and m['room_relative_signal']>0 and m['favorite_nfl_team'] is None and m['draft_purpose']=='startup'
def test_dna_excludes_drafting():
 picks=[DraftPick(season='2025',manager_id='m',round=1,pick_no=1,position='QB',draft_status='drafting')]
 assert analyze_dna(picks)==[]
def test_dna_adp_unavailable_without_source():
 x=analyze_dna([DraftPick(season='2025',manager_id='m',round=1,pick_no=1,position='QB',adp=5)])[0]
 assert x['market_style']=='unavailable'
def test_guillotine_deterministic_and_bounded():
 r=GuillotineRequest(teams=[GuillotineTeam(roster_id='1',name='Low',current_points=10,projected_remaining=50),GuillotineTeam(roster_id='2',name='High',current_points=50,projected_remaining=60)],simulations=500,seed=7)
 a=chop_probabilities(r);b=chop_probabilities(r);assert a==b and a['chop_watch'][0]['name']=='Low' and a['seed']==7
