"""The Woodshed research core. No third-party dependencies. Editorial review is mandatory."""
from __future__ import annotations
import csv, json, sqlite3, math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

POSITIONS={'RB','WR','TE','QB'}
REQUIRED={'player_id','name','team','position','season','week'}
METRICS={'snap_share','route_share','target_share','targets','routes','carries','rush_share','redzone_touches','goal_line_touches','tprr','wopr','qb_rushes','two_minute_share','third_down_share'}

def parse_float(x):
    if x is None or str(x).strip()=='': return None
    try:
        v=float(x)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError):return None

def normalize(row):
    missing=REQUIRED-set(row)
    if missing: raise ValueError(f'Required columns missing: {sorted(missing)}')
    d={k:row.get(k) for k in row}
    for k in ('season','week'):
        try:d[k]=int(d[k])
        except (TypeError,ValueError):raise ValueError(f'Invalid {k}')
    if d['week']<1 or d['week']>22:raise ValueError('Invalid NFL week')
    if d['position'] not in POSITIONS:raise ValueError('Unsupported position')
    if not str(d['player_id']).strip():raise ValueError('Missing player ID')
    for k in METRICS:
        d[k]=parse_float(d.get(k))
        if k.endswith('_share') and d[k] is not None and not 0<=d[k]<=1:
            raise ValueError(f'{k} must be between 0 and 1')
        if d[k] is not None and d[k]<0:raise ValueError(f'{k} cannot be negative')
    d['rostered_pct']=parse_float(d.get('rostered_pct'))
    if d['rostered_pct'] is not None and not 0<=d['rostered_pct']<=100:raise ValueError('Invalid rostered_pct')
    d['source']=str(d.get('source') or '')
    d['source_url']=str(d.get('source_url') or '')
    d['source_date']=str(d.get('source_date') or '')
    d['retrieved_at']=str(d.get('retrieved_at') or '')
    d['roster_source']=str(d.get('roster_source') or '')
    d['injury_status']=str(d.get('injury_status') or '')
    return d

def connect(path):
    conn=sqlite3.connect(str(path));conn.row_factory=sqlite3.Row
    conn.executescript('''CREATE TABLE IF NOT EXISTS player_weeks (
    player_id TEXT NOT NULL, season INTEGER NOT NULL, week INTEGER NOT NULL,
    name TEXT NOT NULL, team TEXT NOT NULL, position TEXT NOT NULL,
    payload TEXT NOT NULL, PRIMARY KEY(player_id,season,week));
    CREATE TABLE IF NOT EXISTS decisions (
    player_id TEXT NOT NULL,season INTEGER NOT NULL,week INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',thesis TEXT NOT NULL DEFAULT '',
    approved_bid INTEGER,updated_at TEXT NOT NULL,
    PRIMARY KEY(player_id,season,week));
    CREATE TABLE IF NOT EXISTS faab_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT, season INTEGER NOT NULL, week INTEGER NOT NULL,
    player TEXT NOT NULL, amount INTEGER NOT NULL CHECK(amount>=0), note TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, logged_at TEXT NOT NULL, event TEXT NOT NULL,detail TEXT NOT NULL);''')
    return conn

def audit(conn,event,detail):
    conn.execute('INSERT INTO audit_log(logged_at,event,detail) VALUES(?,?,?)',(datetime.now(timezone.utc).isoformat(),event,detail))

def import_csv(conn,path):
    with open(path,newline='',encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    if not rows: raise ValueError('Empty CSV')
    cleaned=[normalize(x) for x in rows]
    keys=[(x['player_id'],x['season'],x['week']) for x in cleaned]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate player-week rows in upload')
    with conn:
        for x in cleaned:
            conn.execute('''INSERT INTO player_weeks VALUES(?,?,?,?,?,?,?) ON CONFLICT(player_id,season,week)
             DO UPDATE SET name=excluded.name,team=excluded.team,position=excluded.position,payload=excluded.payload''',
             (x['player_id'],x['season'],x['week'],x['name'],x['team'],x['position'],json.dumps(x)))
        audit(conn,'import',f'{len(cleaned)} rows from {Path(path).name}')
    return len(cleaned)

def week_rows(conn,season,week):
    return [json.loads(r['payload']) for r in conn.execute('SELECT payload FROM player_weeks WHERE season=? AND week=?',(season,week))]

def compare(current,previous):
    p=previous or {};delta={}
    for k in METRICS:
        a,b=current.get(k),p.get(k)
        delta[k]=round(a-b,4) if a is not None and b is not None else None
    return delta

def classify(current,delta):
    p=current['position']
    keys={'RB':['rush_share','carries','snap_share','goal_line_touches','target_share'],
          'WR':['route_share','target_share','targets','tprr','snap_share'],
          'TE':['route_share','target_share','targets','tprr','snap_share'],
          'QB':['snap_share','qb_rushes']}[p]
    present=[k for k in keys if current.get(k) is not None]
    evidence=[(k,v) for k,v in delta.items() if k in keys and v is not None]
    # changes are expressed in shares, except counting metrics
    rise=[(k,v) for k,v in evidence if v >= (2 if k in {'carries','targets','goal_line_touches','qb_rushes'} else .07)]
    fall=[(k,v) for k,v in evidence if v <= (-2 if k in {'carries','targets','goal_line_touches','qb_rushes'} else -.07)]
    confidence='medium' if len(evidence)>=2 else 'low'
    if not evidence:return 'insufficient evidence','low',[]
    if rise: return 'expanding role', confidence, rise
    if fall:return 'declining role',confidence,fall
    return 'stable/unclear',confidence,evidence[:3]

def ownership(current,threshold=65):
    pct=current.get('rostered_pct')
    if pct is None or not current.get('roster_source') or not current.get('source_date'):
        return 'unverified'
    return 'eligible' if pct<threshold else 'ineligible'

def research(conn,season,week):
    rows=week_rows(conn,season,week);previous={x['player_id']:x for x in week_rows(conn,season,week-1)}
    result=[]
    for x in rows:
        d=compare(x,previous.get(x['player_id']));role,confidence,signals=classify(x,d)
        qual=ownership(x)
        missing=[k for k in ({'RB':['rush_share','carries','snap_share'], 'WR':['route_share','target_share'], 'TE':['route_share','target_share'], 'QB':['snap_share','qb_rushes']}[x['position']]) if x.get(k) is None]
        flags=[]
        if missing:flags.append('Missing key usage: '+', '.join(missing))
        if not x.get('source'):flags.append('No named statistical source')
        if not x.get('source_date'):flags.append('No source observation date')
        if not x.get('source_url'):flags.append('No source URL or identifier')
        if qual=='unverified':flags.append('Roster eligibility unverified')
        if not previous.get(x['player_id']):flags.append('No prior-week comparison')
        # Explicitly do not equate source-date with freshness without checking game schedule.
        if x.get('injury_status'):flags.append('Injury needs current official verification: '+x['injury_status'])
        result.append({'player_id':x['player_id'],'name':x['name'],'team':x['team'],'position':x['position'],
                       'season':season,'week':week,'metrics':{k:x.get(k) for k in sorted(METRICS)},
                       'delta':d,'role_signal':role,'confidence':confidence,'signals':[{'metric':k,'delta':v} for k,v in signals],
                       'ownership_pct':x['rostered_pct'],'eligibility':qual,'flags':flags,
                       'source':x['source'],'source_url':x['source_url'],'source_date':x['source_date'],'retrieved_at':x['retrieved_at'],
                       'editorial_status':'pending','faab_suggestion':None})
    # Favor role change, not absolute usage; keep ineligible listed as context only.
    result.sort(key=lambda r:(r['eligibility']!='eligible',r['role_signal']!='expanding role',-len(r['signals']),r['name']))
    return result

def faab_range(remaining,role_signal,confidence,role_certainty='uncertain',weeks_left=10):
    if not isinstance(remaining,int) or remaining<0 or remaining>200:raise ValueError('Remaining budget must be 0..200')
    if remaining==0:return (0,0,'No FAAB remaining')
    if role_signal=='expanding role' and confidence=='medium' and role_certainty=='high':low,high=14,32
    elif role_signal=='expanding role':low,high=5,16
    elif role_signal=='stable/unclear':low,high=1,6
    else:low,high=0,3
    # Conservative deterministic baseline; not an editorial bid.
    factor=0.7 if weeks_left>8 else 1.0
    return (min(remaining,round(low*factor)),min(remaining,round(high*factor)), 'Illustrative model range; requires Jon approval')

def ledger_remaining(conn,season,budget=200):
    spent=conn.execute('SELECT COALESCE(SUM(amount),0) FROM faab_ledger WHERE season=?',(season,)).fetchone()[0]
    return budget-spent

def add_spend(conn,season,week,player,amount):
    if not isinstance(amount,int) or amount<0:raise ValueError('Spend must be nonnegative integer')
    with conn:
        if amount>ledger_remaining(conn,season):raise ValueError('FAAB exceeds remaining budget')
        conn.execute('INSERT INTO faab_ledger(season,week,player,amount) VALUES(?,?,?,?)',(season,week,player,amount))
        audit(conn,'faab_spend',f'{player}: ${amount}')

def save_decision(conn,player_id,season,week,status,thesis='',bid=None):
    if status not in {'pending','reviewed','approved','rejected'}:raise ValueError('Invalid status')
    if bid is not None and (not isinstance(bid,int) or bid<0 or bid>ledger_remaining(conn,season)):
        raise ValueError('Invalid bid')
    with conn:
        conn.execute('''INSERT INTO decisions VALUES(?,?,?,?,?,?,?) ON CONFLICT(player_id,season,week)
        DO UPDATE SET status=excluded.status,thesis=excluded.thesis,approved_bid=excluded.approved_bid,updated_at=excluded.updated_at''',
        (player_id,season,week,status,thesis,bid,datetime.now(timezone.utc).isoformat()))
        audit(conn,'decision',f'{season}w{week} {player_id}: {status}')

def export_packet(conn,season,week,destination):
    candidates=research(conn,season,week)
    decisions={(r['player_id']):dict(r) for r in conn.execute('SELECT * FROM decisions WHERE season=? AND week=?',(season,week))}
    for c in candidates:
        d=decisions.get(c['player_id'])
        if d:c['editorial_status']=d['status'];c['jon_thesis']=d['thesis'];c['approved_bid']=d['approved_bid']
    payload={'product':'FFToday Touch Transfer','season':season,'week':week,'generated_at':datetime.now(timezone.utc).isoformat(),
             'remaining_faab':ledger_remaining(conn,season),'publication_status':'NOT APPROVED FOR PUBLICATION', 'candidates':candidates}
    Path(destination).parent.mkdir(parents=True,exist_ok=True)
    Path(destination).write_text(json.dumps(payload,indent=2),encoding='utf-8')
    return payload

def article_draft(packet):
    week=packet['week'];parts=[f'# Touch Transfer — Week {week}','By Jon Woods','DRAFT — NOT FOR SUBMISSION',
      '## Introduction','[Jon: identify the week’s most important role change.]',
      '## $200 FAAB Tracker',f"Remaining budget: ${packet['remaining_faab']} (based on entered ledger only).",
      '## Priority Adds']
    approved=[x for x in packet['candidates'] if x['editorial_status']=='approved' and x['eligibility']=='eligible']
    if not approved:parts.append('[No eligible, Jon-approved priority adds yet.]')
    for x in approved:
        parts += [f"### {x['position']} {x['name']}, {x['team']}",f"Approved thesis: {x.get('jon_thesis') or '[Jon to supply]'}",f"FAAB: ${x.get('approved_bid')}" if x.get('approved_bid') is not None else 'FAAB: [requires review]','Evidence: ' + (', '.join('{} {:+g}'.format(sig['metric'], sig['delta']) for sig in x['signals']) or 'Insufficient trend evidence'),f"Source: {x['source']} ({x['source_date']}) {x['source_url']}", '']
    parts+=['## Also Worth a Bid','[Jon to select additional eligible candidates.]','## Panic Meter','[Requires Jon-approved judgment.]',
            '## Monday Night Waiver Watch','[Update after MNF; verify news and usage.]','## How I’m Spending','[Jon to finalize budget strategy.]',
            '','Prepared for manual Tuta email submission only.']
    return '\n\n'.join(parts)
