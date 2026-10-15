"""Favorites & Fades research and editorial workflow; no autonomous picks."""
import json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES=('No Brainers','Favorites','On the Fence','Fade')
DIVISIONS={'AFC South':{'HOU','IND','JAX','TEN'},'NFC South':{'ATL','CAR','NO','TB'}}

def init(conn):
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS ff_games (id INTEGER PRIMARY KEY,season INTEGER NOT NULL,week INTEGER NOT NULL,away TEXT NOT NULL,home TEXT NOT NULL,line TEXT DEFAULT '',total TEXT DEFAULT '',prediction TEXT DEFAULT '', UNIQUE(season,week,away,home));
    CREATE TABLE IF NOT EXISTS ff_offenses (game_id INTEGER NOT NULL,team TEXT NOT NULL,qb_allowed TEXT DEFAULT '',rb_allowed TEXT DEFAULT '',wr_allowed TEXT DEFAULT '',te_allowed TEXT DEFAULT '',PRIMARY KEY(game_id,team),FOREIGN KEY(game_id) REFERENCES ff_games(id));
    CREATE TABLE IF NOT EXISTS ff_picks (id INTEGER PRIMARY KEY,game_id INTEGER NOT NULL,team TEXT NOT NULL,player TEXT NOT NULL,category TEXT NOT NULL,analysis TEXT DEFAULT '',sources TEXT DEFAULT '',verified INTEGER DEFAULT 0,approved INTEGER DEFAULT 0,UNIQUE(game_id,team,player),FOREIGN KEY(game_id) REFERENCES ff_games(id));
    ''')

def add_game(conn,season,week,away,home,line='',total=''):
    if not all(str(x).strip() for x in (away,home)) or away==home: raise ValueError('Invalid matchup')
    with conn:
        conn.execute('INSERT INTO ff_games(season,week,away,home,line,total) VALUES(?,?,?,?,?,?) ON CONFLICT(season,week,away,home) DO UPDATE SET line=excluded.line,total=excluded.total',(season,week,away.strip(),home.strip(),line,total))
        game=conn.execute('SELECT id FROM ff_games WHERE season=? AND week=? AND away=? AND home=?',(season,week,away,home)).fetchone()[0]
        for team in (away,home):conn.execute('INSERT OR IGNORE INTO ff_offenses(game_id,team) VALUES(?,?)',(game,team))
    return game

def update_opponent_allowed(conn,game_id,team,values):
    with conn:
        if not conn.execute('SELECT 1 FROM ff_offenses WHERE game_id=? AND team=?',(game_id,team)).fetchone():raise ValueError('Team not in game')
        conn.execute('UPDATE ff_offenses SET qb_allowed=?,rb_allowed=?,wr_allowed=?,te_allowed=? WHERE game_id=? AND team=?',tuple(values.get(k,'') for k in ('QB','RB','WR','TE'))+(game_id,team))

def upsert_pick(conn,game_id,team,player,category,analysis='',sources='',verified=False,approved=False):
    if category not in CATEGORIES:raise ValueError('Invalid category')
    game=conn.execute('SELECT away,home FROM ff_games WHERE id=?',(game_id,)).fetchone()
    if not game or team not in game:raise ValueError('Team not in matchup')
    if approved and (not verified or not analysis.strip() and category!='No Brainers'):raise ValueError('Verify and analyze before approving')
    with conn:conn.execute('''INSERT INTO ff_picks(game_id,team,player,category,analysis,sources,verified,approved) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(game_id,team,player) DO UPDATE SET category=excluded.category,analysis=excluded.analysis,sources=excluded.sources,verified=excluded.verified,approved=excluded.approved''',(game_id,team,player,category,analysis,sources,int(verified),int(approved)))

def export_favorites(conn,season,week):
    games=conn.execute('SELECT * FROM ff_games WHERE season=? AND week=? ORDER BY id',(season,week)).fetchall()
    lines=[f'# Favorites & Fades — Week {week}','By Jon Woods','DRAFT — VERIFY BEFORE SUBMISSION','']
    for g in games:
        lines += [f'## {g["away"]} @ {g["home"]}',f'Line: {g["line"] or "[verify]"}',f'Total: {g["total"] or "[verify]"}','']
        for team in (g['away'],g['home']):
            lines.append(f'### {team} offense')
            o=conn.execute('SELECT * FROM ff_offenses WHERE game_id=? AND team=?',(g['id'],team)).fetchone()
            for p,k in [('QBs','qb_allowed'),('RBs','rb_allowed'),('WRs','wr_allowed'),('TEs','te_allowed')]:lines.append(f'Opponent FPts Allowed vs. {p}: {o[k] if o and o[k] else "[verify]"}')
            picks=[dict(x) for x in conn.execute('SELECT * FROM ff_picks WHERE game_id=? AND team=?',(g['id'],team))]
            for cat in CATEGORIES:
                lines.append(f'**{cat}:**')
                selected=[x for x in picks if x['category']==cat]
                if not selected:lines.append('N/A')
                for x in selected:
                    status='APPROVED' if x['approved'] else 'PENDING REVIEW'
                    lines.append(f'{x["player"]} [{status}]')
                    if cat!='No Brainers':lines.append(x['analysis'] or '[Jon: analysis needed]')
                    if x['sources']:lines.append('Research sources: '+x['sources'])
                lines.append('')
        lines.append(f'**Prediction:** {g["prediction"] or "[Jon: final score prediction]"}')
        lines.append('')
    if not games:lines.append('[No matchups selected for this week.]')
    lines += ['---','NOT APPROVED FOR SUBMISSION. Confirm lines, defense data, player claims, and final predictions.']
    return '\n'.join(lines)
