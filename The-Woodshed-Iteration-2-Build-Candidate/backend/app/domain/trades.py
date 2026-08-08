from app.schemas.fantasy import TradeAnalyzeRequest,TradeAsset
from app.domain.scoring import scoring_fingerprint

def _asset_value(a:TradeAsset, req:TradeAnalyzeRequest):
    vor=max(0,a.projection_value-a.replacement_value)*a.starter_probability
    format_factor=1.0
    # Format effects operate through lineup demand / horizon rather than hidden arbitrary output multipliers.
    if a.position=='QB' and (req.scoring.superflex or 'SUPERFLEX' in req.lineup_slots or req.lineup_slots.count('QB')>=2):
        demand=min(1.35,1.10+0.02*req.league_size); vor*=demand
    if a.position=='TE' and req.scoring.te_rec_bonus>0:
        vor*=1+min(.25,req.scoring.te_rec_bonus*.12)
    if req.format=='redraft':
        market_weight=.45; projection_weight=.55
    elif req.format=='keeper':
        market_weight=.55; projection_weight=.45
    else:
        market_weight=.65; projection_weight=.35
    if a.kind=='pick' and req.format=='redraft':
        market=0.0
    else: market=a.market_value
    age_penalty=0.0
    if req.format=='dynasty' and a.age is not None and a.kind=='player' and a.age>28:
        age_penalty=min(market*.18,(a.age-28)*market*.025)
    return market_weight*market+projection_weight*vor-age_penalty

def analyze_trade(req:TradeAnalyzeRequest)->dict:
    give=sum(_asset_value(a,req) for a in req.give);receive=sum(_asset_value(a,req) for a in req.receive)
    overflow=max(0,len(req.receive)-len(req.give)-req.roster_spots_open); roster_penalty=overflow*2.0
    delta=receive-give-roster_penalty;pct=delta/max(give,1)*100
    verdict='strong_accept' if pct>=12 else 'accept' if pct>=3 else 'fair' if pct>-3 else 'decline' if pct>-12 else 'strong_decline'
    return {'give_value':round(give,2),'receive_value':round(receive,2),'net_value':round(delta,2),'edge_pct':round(pct,1),'verdict':verdict,'roster_overflow':overflow,
            'uncertainty':round(sum(a.future_variance for a in req.give+req.receive),2),'format':req.format,'league_size':req.league_size,
            'scoring_fingerprint':scoring_fingerprint(req.scoring),'note':'League-format context affects replacement demand and horizon; market and projection inputs remain sourced externally.'}
