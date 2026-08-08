from app.schemas.fantasy import RankingsRequest, FantasyPointsProjection, RawStatProjection
from app.domain.scoring import score_raw_projection, scoring_fingerprint

def _projection_points(p, scoring):
    fp = scoring_fingerprint(scoring)
    if isinstance(p, FantasyPointsProjection):
        if p.scoring_fingerprint != fp:
            raise ValueError('fantasy_points projection scoring fingerprint is incompatible with requested scoring')
        return p.median, p.floor, p.ceiling, False
    if isinstance(p, RawStatProjection):
        median = score_raw_projection(p, scoring)
        floor = max(0, median-p.stdev) if p.stdev else median
        ceiling = median+p.stdev if p.stdev else median
        return median, floor, ceiling, True
    raise ValueError('unsupported projection mode')

def rank_ros(req:RankingsRequest)->list[dict]:
    rows=[]
    fp=scoring_fingerprint(req.scoring)
    for p in req.projections:
        median,floor,ceil,component_scored=_projection_points(p,req.scoring)
        if floor is None: floor=max(0,median-getattr(p,'stdev',0))
        if ceil is None: ceil=median+getattr(p,'stdev',0)
        uncertainty=(ceil-floor)/max(abs(median),1);adj=median*(1-min(.12,uncertainty*.04))
        rows.append({'player_id':p.player_id,'name':p.name,'position':p.position,'team':p.team,'score':round(adj,2),'median':round(median,2),
            'floor':round(floor,2),'ceiling':round(ceil,2),'source':p.source,'source_updated_at':p.source_updated_at.isoformat() if p.source_updated_at else None,
            'horizon':'ros','quality':p.quality,'scoring_fingerprint':fp,'component_scored':component_scored,'projection_mode':p.projection_mode})
    rows.sort(key=lambda x:(x['score'],x['name']),reverse=True)
    for i,row in enumerate(rows[:req.limit],1):row['rank']=i
    return rows[:req.limit]
