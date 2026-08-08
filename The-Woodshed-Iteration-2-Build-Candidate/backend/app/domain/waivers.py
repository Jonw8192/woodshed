from app.schemas.fantasy import WaiverRequest
from app.domain.scoring import scoring_fingerprint

def optimize_waivers(req:WaiverRequest)->list[dict]:
    scarcity_pressure=max(.7,min(1.4,12/req.teams_remaining));reserve=max(.35,min(1.0,req.weeks_remaining/10));out=[]
    for p in req.candidates:
        # floor/ceiling participate so accepted uncertainty inputs are not silently ignored.
        risk_weight=max(0,min(1,req.survival_risk));effective=(.55*p.median+.30*p.floor+.15*p.ceiling) if risk_weight>=.5 else (.70*p.median+.15*p.floor+.15*p.ceiling)
        increment=max(0,effective-p.replacement_median)
        pos_context=1.0
        if p.position=='TE' and req.scoring.te_rec_bonus>0:pos_context+=min(.2,.08*req.scoring.te_rec_bonus)
        if p.position=='QB' and req.scoring.superflex:pos_context+=.18
        utility=increment*p.usable_weeks*p.start_probability*(.7+.6*p.scarcity)*pos_context*(1+.8*req.survival_risk)-p.drop_cost
        bid_pct=min(.9,max(0,(utility/120)*scarcity_pressure/reserve));bid=min(req.faab_left,round(req.faab_left*bid_pct))
        out.append({'player_id':p.player_id,'name':p.name,'position':p.position,'incremental_utility':round(utility,2),'suggested_bid':bid,'bid_pct':round(bid_pct*100,1),
                    'drop_player_id':p.drop_player_id,'reason':f'+{increment:.1f} median vs replacement; {p.usable_weeks} usable weeks; {p.start_probability:.0%} start probability',
                    'scoring_fingerprint':scoring_fingerprint(req.scoring)})
    return sorted(out,key=lambda x:(x['incremental_utility'],x['suggested_bid']),reverse=True)
