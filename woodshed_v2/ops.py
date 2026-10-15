"""Batch operations; external publishing is deliberately unsupported."""
import argparse,json
from woodshed.automation import run_local
p=argparse.ArgumentParser(description='THE WOODSHED local safe batch jobs')
p.add_argument('--db',default='woodshed.db');p.add_argument('--season',type=int,default=2026);p.add_argument('--week',type=int,required=True);p.add_argument('--out',default='output')
a=p.parse_args();print(json.dumps(run_local(a.db,a.season,a.week,a.out),indent=2))
