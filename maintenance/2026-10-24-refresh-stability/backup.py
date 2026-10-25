import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'lanceur'))
from validate_live_lots6_8 import post
value=post('/api/backups/create',{'kind':'manual'})
print(json.dumps({'state':value['job']['state'],'phase':value['job']['phase']}))
