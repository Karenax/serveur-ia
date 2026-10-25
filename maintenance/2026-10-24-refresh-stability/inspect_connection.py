"""Read-only, reduced connection evidence; no credentials or conversation text output."""
import json
from pathlib import Path
import urllib.request
import datetime
ROOT=Path(__file__).resolve().parents[2]
out=Path(__file__).resolve().parent
def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8765'+path,timeout=20) as response:return json.load(response)
state=get('/api/state')
audit=get('/api/audit')
logs=state.get('logs','')
terms=('disconnect','connection','broken pipe','reset by peer','timed out','timeout','cancel','error','exception')
lines=[line for line in logs.splitlines() if any(term in line.lower() for term in terms)]
# Keep categorical evidence, not free-form prompts, tracebacks or private URLs.
result={'time':datetime.datetime.now().astimezone().isoformat(),'server':{key:state.get(key) for key in ('status','running','managed','error')},
    'log_lines':len(logs.splitlines()),'matching_categories':{term:sum(term in line.lower() for line in logs.splitlines()) for term in terms},
    'audit_recent':[{'time':row.get('epoch',row.get('time',row.get('at'))),'event':row.get('event')} for row in audit[-20:]],
    'local_client_journal_available':False,'note':'No local Windows client API is listening; Android journal is not available from this workspace.'}
path=ROOT/'lanceur/inference-errors.json'
if path.is_file():
    failures=json.loads(path.read_text(encoding='utf-8-sig'))
    result['inference_errors']=[{key:row.get(key) for key in ('time','status','route')} for row in failures[-12:]]
(out/'connection-evidence.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
