"""Optional live nflreadpy adapter. Requires network; missing fields remain unknown."""
from datetime import datetime,timezone
from .core import normalize

def fetch(season,week):
    import nflreadpy as nfl
    stats=nfl.load_player_stats([season])
    rows=stats.to_dicts() if hasattr(stats,'to_dicts') else stats.to_dict('records')
    filtered=[r for r in rows if int(r.get('week') or 0)==week]
    if not filtered:raise RuntimeError('No stats for requested week; aborting import')
    output=[]
    now=datetime.now(timezone.utc).isoformat()
    for r in filtered:
        pos=r.get('position')
        if pos not in ('QB','RB','WR','TE'):continue
        pid=r.get('player_id')
        if not pid:continue
        d={'player_id':pid,'name':r.get('player_display_name') or r.get('player_name') or pid,
           'team':r.get('recent_team') or r.get('team') or 'UNK', 'position':pos,'season':season,'week':week,
           'targets':r.get('targets'),'carries':r.get('carries'),'target_share':r.get('target_share'),
           'wopr':r.get('wopr'),'source':'nflverse weekly player statistics',
           'source_url':'https://github.com/nflverse/nflverse-data','source_date':f'{season} week {week}',
           'retrieved_at':now}
        output.append(normalize(d))
    return output

def fetch_to_csv(season,week,path):
    import csv
    from pathlib import Path
    rows=fetch(season,week)
    if not rows:raise RuntimeError('No skill-position rows')
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    with open(path,'w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),extrasaction='ignore');w.writeheader();w.writerows(rows)
    return len(rows)
