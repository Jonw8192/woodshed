from app.schemas.fantasy import *
from app.domain.trades import analyze_trade
from app.domain.guillotine import chop_probabilities
from app.domain.rankings import rank_ros
from app.domain.scoring import scoring_fingerprint

def fp():return scoring_fingerprint(ScoringSettings())
def test_trade_accounting_symmetry_near_inverse():
 a=TradeAsset(id='a',name='A',market_value=50,projection_value=20,replacement_value=10);b=TradeAsset(id='b',name='B',market_value=45,projection_value=20,replacement_value=10)
 x=analyze_trade(TradeAnalyzeRequest(give=[a],receive=[b]));y=analyze_trade(TradeAnalyzeRequest(give=[b],receive=[a]));assert x['net_value']==-y['net_value']
def test_guillotine_probabilities_sum_to_one():
 req=GuillotineRequest(teams=[GuillotineTeam(roster_id=str(i),name=str(i),current_points=i*2,projected_remaining=50,volatility=10) for i in range(6)],simulations=5000)
 out=chop_probabilities(req);assert abs(sum(x['chop_probability'] for x in out['chop_watch'])-1)<.002
def test_rankings_tie_is_deterministic():
 ps=[FantasyPointsProjection(player_id='a',name='A',position='WR',horizon='ros',median=10,scoring_fingerprint=fp()),FantasyPointsProjection(player_id='b',name='B',position='WR',horizon='ros',median=10,scoring_fingerprint=fp())]
 assert rank_ros(RankingsRequest(projections=ps))==rank_ros(RankingsRequest(projections=ps))
