import io,csv
import pytest
from woodshed.core import connect
from woodshed import editorial,versus,publishing

def newdb(tmp_path):
 c=connect(tmp_path/'new.db');editorial.init(c);versus.init(c);publishing.init(c);return c

def test_favorites_format_and_approval(tmp_path):
 c=newdb(tmp_path);gid=editorial.add_game(c,2026,6,'BUF','TB','TB -3','47.5')
 editorial.upsert_pick(c,gid,'TB','Bucky Irving','Favorites','Useful analysis','source://check',True,True)
 txt=editorial.export_favorites(c,2026,6)
 assert 'Opponent FPts Allowed vs. RBs:' in txt and 'Bucky Irving [APPROVED]' in txt
 assert 'Prediction:' in txt
 with pytest.raises(ValueError):editorial.upsert_pick(c,gid,'TB','Player','Fade','No sources','',False,True)

def test_dfs_valid_and_overcap(tmp_path):
 c=newdb(tmp_path);sid=versus.create_slate(c,'Demo','DraftKings',50000,3,1.5)
 pool=io.StringIO('player_id,name,salary,team\na,A,10000,TB\nb,B,11000,TB\nc,C,12000,BUF\n')
 assert versus.import_players(c,sid,pool)==3
 entries=[{'player_id':'a','slot':'CAPTAIN'},{'player_id':'b','slot':'FLEX'},{'player_id':'c','slot':'FLEX'}]
 assert versus.validate_lineup(c,sid,entries)['salary']==38000
 assert versus.save_lineup(c,sid,'Jon',entries)['valid']
 assert 'Jon' in versus.showdown_notes(c,sid)
 assert not versus.validate_lineup(c,sid,[entries[0],entries[0],entries[2]])['valid']
 sid2=versus.create_slate(c,'Low cap','DraftKings',25000,3,1.5)
 versus.import_players(c,sid2,io.StringIO('player_id,name,salary,team\na,A,10000,TB\nb,B,11000,TB\nc,C,12000,BUF\n'))
 assert not versus.validate_lineup(c,sid2,entries)['valid']

def test_newsletter_and_accounting(tmp_path):
 c=newdb(tmp_path)
 with pytest.raises(ValueError):publishing.save_issue(c,'Issue','2026-10-15','','','','approved')
 publishing.save_issue(c,'Issue','2026-10-15','Original research','','source reviewed','approved')
 assert 'Original research' in publishing.issue_markdown(dict(c.execute('SELECT * FROM newsletter_issues').fetchone()))
 publishing.record_business(c,'2026-10-15','service','Consultation',35,True)
 publishing.record_business(c,'2026-10-15','subscription','Potential subscriber',7,False)
 assert publishing.summary(c)['confirmed_net_cashflow']==35
 assert publishing.summary(c)['unconfirmed_pipeline']==7
