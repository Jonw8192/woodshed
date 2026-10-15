"""Contest-scoped DFS pricing and lineup validation, not a lineup optimizer or betting bot."""
import csv, json

def init(conn):
    conn.executescript('''CREATE TABLE IF NOT EXISTS dfs_slates(id INTEGER PRIMARY KEY, name TEXT NOT NULL, provider TEXT NOT NULL, salary_cap INTEGER NOT NULL, roster_slots INTEGER NOT NULL, captain_multiplier REAL NOT NULL, UNIQUE(name,provider));
    CREATE TABLE IF NOT EXISTS dfs_players(slate_id INTEGER NOT NULL,player_id TEXT NOT NULL,name TEXT NOT NULL,salary INTEGER NOT NULL,team TEXT DEFAULT '',PRIMARY KEY(slate_id,player_id));
    CREATE TABLE IF NOT EXISTS dfs_lineups(id INTEGER PRIMARY KEY, slate_id INTEGER NOT NULL,label TEXT NOT NULL, entries TEXT NOT NULL, result_points REAL, notes TEXT DEFAULT '', UNIQUE(slate_id,label));''')

def create_slate(conn,name,provider,salary_cap,roster_slots=6,captain_multiplier=1.5):
    if salary_cap<=0 or roster_slots<=0 or captain_multiplier<=0:raise ValueError('Invalid contest rules')
    with conn:
        conn.execute('INSERT INTO dfs_slates(name,provider,salary_cap,roster_slots,captain_multiplier) VALUES(?,?,?,?,?) ON CONFLICT(name,provider) DO UPDATE SET salary_cap=excluded.salary_cap,roster_slots=excluded.roster_slots,captain_multiplier=excluded.captain_multiplier',(name,provider,salary_cap,roster_slots,captain_multiplier))
    return conn.execute('SELECT id FROM dfs_slates WHERE name=? AND provider=?',(name,provider)).fetchone()[0]

def import_players(conn,slate_id,file):
    rows=list(csv.DictReader(file))
    if not rows:raise ValueError('Empty player pool')
    prepared=[]
    for r in rows:
        pid=str(r['player_id']).strip();salary=int(r['salary']);name=str(r['name']).strip()
        if not pid or not name or salary<0:raise ValueError('Invalid salary row')
        prepared.append((slate_id,pid,name,salary,r.get('team','')))
    if len({r[1] for r in prepared})!=len(prepared):raise ValueError('Duplicate player ID in salary pool')
    with conn:
        conn.execute('DELETE FROM dfs_players WHERE slate_id=?',(slate_id,))
        conn.executemany('INSERT INTO dfs_players VALUES(?,?,?,?,?)',prepared)
    return len(prepared)

def validate_lineup(conn,slate_id,entries):
    """entries: [{player_id,slot:CAPTAIN|FLEX}], captain salary multiplier is provider-configured."""
    slate=conn.execute('SELECT * FROM dfs_slates WHERE id=?',(slate_id,)).fetchone()
    if not slate:raise ValueError('Unknown slate')
    flags=[];total=0
    if len(entries)!=slate['roster_slots']:flags.append(f'Expected {slate["roster_slots"]} slots, got {len(entries)}')
    if len({str(e.get('player_id')) for e in entries})!=len(entries):flags.append('Duplicate player selected')
    if sum(e.get('slot')=='CAPTAIN' for e in entries)!=1:flags.append('Exactly one CAPTAIN required')
    for e in entries:
        if e.get('slot') not in ('CAPTAIN','FLEX'):flags.append('Invalid slot: '+str(e.get('slot')))
        r=conn.execute('SELECT salary FROM dfs_players WHERE slate_id=? AND player_id=?',(slate_id,str(e.get('player_id')))).fetchone()
        if r is None:flags.append('Missing player salary: '+str(e.get('player_id')));continue
        total+=round(r['salary']*(slate['captain_multiplier'] if e.get('slot')=='CAPTAIN' else 1))
    if total>slate['salary_cap']:flags.append(f'Over cap by ${total-slate["salary_cap"]}')
    return {'valid':not flags,'salary':total,'cap':slate['salary_cap'],'remaining':slate['salary_cap']-total,'flags':flags,'provider':slate['provider']}

def save_lineup(conn,slate_id,label,entries,notes=''):
    result=validate_lineup(conn,slate_id,entries)
    if not result['valid']:raise ValueError('; '.join(result['flags']))
    with conn:conn.execute('INSERT INTO dfs_lineups(slate_id,label,entries,notes) VALUES(?,?,?,?) ON CONFLICT(slate_id,label) DO UPDATE SET entries=excluded.entries,notes=excluded.notes',(slate_id,label,json.dumps(entries),notes))
    return result

def record_result(conn,lineup_id,points):
    with conn:conn.execute('UPDATE dfs_lineups SET result_points=? WHERE id=?',(float(points),lineup_id))

def showdown_notes(conn,slate_id):
    slate=conn.execute('SELECT * FROM dfs_slates WHERE id=?',(slate_id,)).fetchone()
    if not slate:raise ValueError('Unknown slate')
    lines=[f'# VERSUS: DFS Showdown — {slate["name"]}',f'Provider: {slate["provider"]}','DRAFT — requires Jon approval','']
    for r in conn.execute('SELECT * FROM dfs_lineups WHERE slate_id=? ORDER BY label',(slate_id,)):
        entries=json.loads(r['entries']);check=validate_lineup(conn,slate_id,entries)
        lines += [f'## {r["label"]}',f'Salary: ${check["salary"]:,} / ${check["cap"]:,} | Valid: {check["valid"]}',f'Construction thesis: {r["notes"] or "[add research]"}']
        for e in entries:
            p=conn.execute('SELECT name FROM dfs_players WHERE slate_id=? AND player_id=?',(slate_id,e['player_id'])).fetchone()
            lines.append(f'- {e["slot"]}: {p["name"] if p else e["player_id"]}')
        lines.append(f'Result: {r["result_points"] if r["result_points"] is not None else "Not recorded"}')
    lines += ['','Research and final lineup choices must be verified. No contest entry occurs here.']
    return '\n'.join(lines)
