import csv,tempfile
from pathlib import Path
import pytest
from woodshed.core import *

def record(pid,week,**kw):
 d={'player_id':pid,'name':'Test Player','team':'TB','position':'RB','season':2026,'week':week,'source':'sample fixture','source_date':'2026-10-11','source_url':'fixture://local','roster_source':'sample league','rostered_pct':24,'rush_share':.2,'carries':4,'snap_share':.25}
 d.update(kw);return d

def test_null_not_zero():
 x=normalize(record('a',5,target_share=''));assert x['target_share'] is None
 assert compare(x,{})['target_share'] is None

def test_score_role_changes():
 prev=normalize(record('a',4));now=normalize(record('a',5,rush_share=.6,carries=13,snap_share=.65))
 assert classify(now,compare(now,prev))[0]=='expanding role'

def test_roster_gate():
 x=normalize(record('a',5));assert ownership(x)=='eligible'
 x['rostered_pct']=80;assert ownership(x)=='ineligible'
 x['rostered_pct']=None;assert ownership(x)=='unverified'

def test_faab_bounds():
 assert faab_range(2,'expanding role','medium','high')[1]<=2
 assert faab_range(0,'expanding role','medium')[1]==0

def test_duplicate_rejected(tmp_path):
 c=connect(tmp_path/'db.sqlite');p=tmp_path/'a.csv'
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(record('a',5)));w.writeheader();w.writerows([record('a',5),record('a',5)])
 with pytest.raises(ValueError):import_csv(c,p)

def test_faab_ledger(tmp_path):
 c=connect(tmp_path/'db.sqlite');add_spend(c,2026,5,'A',190)
 with pytest.raises(ValueError):add_spend(c,2026,5,'B',11)
 assert ledger_remaining(c,2026)==10

def test_approval_gate(tmp_path):
 c=connect(tmp_path/'db.sqlite');p=tmp_path/'r.csv';rs=[record('a',4),record('a',5,rush_share=.7,carries=15)]
 with p.open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rs[0]));w.writeheader();w.writerows(rs)
 import_csv(c,p);pkt=export_packet(c,2026,5,tmp_path/'pkt.json');assert 'No eligible, Jon-approved' in article_draft(pkt)
 save_decision(c,'a',2026,5,'approved','Role changed, but check competition',12)
 pkt=export_packet(c,2026,5,tmp_path/'pkt.json');assert 'Role changed' in article_draft(pkt)

def test_invalid_share():
 with pytest.raises(ValueError):normalize(record('a',5,rush_share=1.3))
