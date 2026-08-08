from app.schemas.fantasy import StartSitRequest, FantasyPointsProjection, RawStatProjection
from app.domain.scoring import score_raw_projection, scoring_fingerprint

def _eligible(pos,slot): return slot==pos or slot=='FLEX' and pos in {'RB','WR','TE'} or slot=='SUPERFLEX' and pos in {'QB','RB','WR','TE'}
def _dist(p,scoring):
    pr=p.projection; fp=scoring_fingerprint(scoring)
    if isinstance(pr,FantasyPointsProjection):
        if pr.scoring_fingerprint!=fp: raise ValueError(f'{p.name} projection scoring fingerprint is incompatible with league scoring')
        med=pr.median; floor=pr.floor if pr.floor is not None else max(0,med-pr.stdev); ceil=pr.ceiling if pr.ceiling is not None else med+pr.stdev
        return floor,med,ceil
    if isinstance(pr,RawStatProjection):
        med=score_raw_projection(pr,scoring); return max(0,med-pr.stdev),med,med+pr.stdev
    raise ValueError('unsupported projection mode')
def start_sit(req:StartSitRequest)->dict:
    weights={'floor':(.55,.35,.10),'balanced':(.30,.50,.20),'ceiling':(.15,.45,.40)}[req.risk_profile]; rows=[]
    for p in req.candidates:
        if not p.active or not _eligible(p.position,req.slot): continue
        floor,median,ceiling=_dist(p,req.scoring); wf,wm,wc=weights
        score=wf*floor+wm*median+wc*ceiling+p.matchup_adjustment*.18+p.role_security*1.5
        rows.append({'player_id':p.player_id,'name':p.name,'position':p.position,'score':round(score,2),'floor':round(floor,2),'median':round(median,2),'ceiling':round(ceiling,2),
                     'reason':f'eligible for {req.slot}; {req.risk_profile} profile; role security {p.role_security:.0%}'})
    if not rows: raise ValueError('no active candidates eligible for decision slot')
    rows.sort(key=lambda x:x['score'],reverse=True); delta=rows[0]['score']-rows[1]['score'] if len(rows)>1 else rows[0]['score']
    return {'start':rows[0],'alternatives':rows[1:],'expected_edge':round(delta,2),'slot':req.slot,'week':req.week,'risk_profile':req.risk_profile,'scoring_fingerprint':scoring_fingerprint(req.scoring)}
