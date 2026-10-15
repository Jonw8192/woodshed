"""Original newsletter preparation, approval gates and business ledger."""
from datetime import datetime,timezone

def init(conn):
    conn.executescript('''CREATE TABLE IF NOT EXISTS newsletter_issues(id INTEGER PRIMARY KEY,title TEXT NOT NULL,issue_date TEXT NOT NULL,free_body TEXT NOT NULL DEFAULT '',paid_body TEXT NOT NULL DEFAULT '',source_notes TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'draft' CHECK(status IN ('draft','reviewed','approved','published')),UNIQUE(title,issue_date));
    CREATE TABLE IF NOT EXISTS business_events(id INTEGER PRIMARY KEY,occurred_on TEXT NOT NULL,kind TEXT NOT NULL,description TEXT NOT NULL,amount REAL NOT NULL,currency TEXT NOT NULL DEFAULT 'USD',confirmed INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS audience_metrics(id INTEGER PRIMARY KEY,observed_on TEXT NOT NULL,channel TEXT NOT NULL,followers INTEGER,subscribers INTEGER,paid_subscribers INTEGER,notes TEXT DEFAULT '');''')

def save_issue(conn,title,issue_date,free_body,paid_body='',source_notes='',status='draft'):
    if status not in ('draft','reviewed','approved','published'):raise ValueError('Unknown status')
    if status in ('approved','published') and (not free_body.strip() or not source_notes.strip()):raise ValueError('Approved issues require content and source review notes')
    with conn:conn.execute('''INSERT INTO newsletter_issues(title,issue_date,free_body,paid_body,source_notes,status) VALUES(?,?,?,?,?,?) ON CONFLICT(title,issue_date) DO UPDATE SET free_body=excluded.free_body,paid_body=excluded.paid_body,source_notes=excluded.source_notes,status=excluded.status''',(title,issue_date,free_body,paid_body,source_notes,status))

def issue_markdown(row,include_paid=False):
    result=f'# {row["title"]}\n\n{row["free_body"]}\n\n'
    if include_paid and row['paid_body']:result+='## Woodshed Pro\n\n'+row['paid_body']+'\n\n'
    return result+'\n\n[Editorial status: '+row['status']+']\n'

def record_business(conn,day,kind,description,amount,confirmed=False):
    if not kind.strip() or not description.strip():raise ValueError('Missing event details')
    with conn:conn.execute('INSERT INTO business_events(occurred_on,kind,description,amount,confirmed) VALUES(?,?,?,?,?)',(day,kind,description,float(amount),int(confirmed)))

def summary(conn):
    rows=[dict(x) for x in conn.execute('SELECT kind,amount,confirmed FROM business_events')]
    actual=sum(x['amount'] for x in rows if x['confirmed'])
    pending=sum(x['amount'] for x in rows if not x['confirmed'])
    return {'confirmed_net_cashflow':round(actual,2),'unconfirmed_pipeline':round(pending,2),'events':len(rows)}

def create_issue_outline(week):
    return f'''# The Edge Report — Week {week}\n\nDRAFT: Independent original analysis only. Do not republish commissioned FFToday text.\n\n## Where the opportunity changed\n[Select confirmed research findings and provide original analysis.]\n\n## Waiver watch\n[Only verified eligibility and Jon-approved recommendations.]\n\n## Rankings disagreements\n[Jon's independent positions and evidence.]\n\n## VERSUS: DFS Showdown\n[Slate-specific research; no unverified salary claims.]\n\n## What I'm watching next\n[News and research questions to monitor.]\n'''
