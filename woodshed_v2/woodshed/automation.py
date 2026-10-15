"""Safe recurring local research export. Publishing remains manual."""
import json
from pathlib import Path
from datetime import datetime,timezone
from .core import connect, export_packet, article_draft
from .editorial import init as init_ff,export_favorites
from .publishing import init as init_pub,create_issue_outline

def run_local(db,season,week,out):
    conn=connect(db);init_ff(conn);init_pub(conn)
    root=Path(out);root.mkdir(parents=True,exist_ok=True)
    packet=export_packet(conn,season,week,root/f'touch_transfer_research_w{week}.json')
    (root/f'touch_transfer_draft_w{week}.md').write_text(article_draft(packet),encoding='utf-8')
    (root/f'favorites_fades_draft_w{week}.md').write_text(export_favorites(conn,season,week),encoding='utf-8')
    (root/f'edge_report_outline_w{week}.md').write_text(create_issue_outline(week),encoding='utf-8')
    status={'at':datetime.now(timezone.utc).isoformat(),'season':season,'week':week,'records':len(packet['candidates']),'note':'No automatic data acquisition, emails or publication; imports must be independently verified.'}
    (root/'job_status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
    return status
