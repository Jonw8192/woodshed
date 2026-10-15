import argparse,json
from woodshed.core import connect,import_csv,export_packet,article_draft,add_spend
from woodshed.nflverse import fetch_to_csv
p=argparse.ArgumentParser(description='Woodshed Research Engine')
p.add_argument('--db',default='woodshed.db');s=p.add_subparsers(dest='command',required=True)
a=s.add_parser('import');a.add_argument('csv')
a=s.add_parser('fetch');a.add_argument('--season',type=int,required=True);a.add_argument('--week',type=int,required=True);a.add_argument('--csv',default='data/nflverse.csv')
a=s.add_parser('packet');a.add_argument('--season',type=int,required=True);a.add_argument('--week',type=int,required=True);a.add_argument('--out',default='output/research.json');a.add_argument('--draft',default='output/touch_transfer.md')
a=s.add_parser('spend');a.add_argument('--season',type=int,required=True);a.add_argument('--week',type=int,required=True);a.add_argument('--player',required=True);a.add_argument('--amount',type=int,required=True)
x=p.parse_args();c=connect(x.db)
if x.command=='import':print('Imported',import_csv(c,x.csv),'player-week records')
elif x.command=='fetch':print('Fetched',fetch_to_csv(x.season,x.week,x.csv),'rows to',x.csv,'; inspect before import')
elif x.command=='packet':
 from pathlib import Path
 packet=export_packet(c,x.season,x.week,x.out);Path(x.draft).parent.mkdir(parents=True,exist_ok=True);Path(x.draft).write_text(article_draft(packet));print('Saved',x.out,x.draft)
elif x.command=='spend':add_spend(c,x.season,x.week,x.player,x.amount);print('Ledger updated')
