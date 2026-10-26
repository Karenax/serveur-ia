"""Synthetic SQLite fixtures only. No production services or data."""
from pathlib import Path
import datetime as dt, json, secrets, sys, tempfile, time
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from workspace import Workspace
from assistant_commands import execute, tick, check_intent

results=[]
for boundary in ('journal','quota'):
 with tempfile.TemporaryDirectory(prefix='kiara-audit-boundary-') as folder:
  w=Workspace(Path(folder));owner='audit-synthetic'
  def command(operation,**kwargs):
   return execute(w,owner,{'operation':operation,**kwargs},request_key=secrets.token_hex(16))
  try:
   memory=command('memory_add',text='Souvenir fictif à supprimer')
   reminder=command('reminder_create',text='Rappel fictif à annuler',at=dt.datetime.fromtimestamp(time.time()+3600,dt.timezone.utc).isoformat(),repeat='daily')
   records=command('list');m=records['memories'][0];r=records['reminders'][0]
   with w.db(owner) as db:
    if boundary=='journal':
     count=db.execute('SELECT COUNT(*) FROM assistant_commands WHERE owner=?',(owner,)).fetchone()[0]
     db.executemany('INSERT INTO assistant_commands VALUES(?,?,?,?,?)',[(owner,f'{i:032x}','a'*64,'{}',time.time()) for i in range(5000-count)])
    else:
     # A valid 1-MiB policy with <2 KiB free, filled using synthetic documents.
     db.execute('INSERT OR REPLACE INTO policies VALUES(?,?)',(owner,json.dumps({'storage_mb':1})))
     project=secrets.token_hex(16)
     db.execute('INSERT INTO projects VALUES(?,?,?, ?,0,1,?)',(project,owner,'Volume fictif','',time.time()))
     for i in range(2):
      db.execute('INSERT INTO documents VALUES(?,?,?,?,?,NULL,?,1,?)',(secrets.token_hex(16),owner,project,'Charge fictive','x'*499000,'txt',time.time()))
     remaining=1024*1024-w.usage(db,owner)-100
     db.execute('INSERT INTO documents VALUES(?,?,?,?,?,NULL,?,1,?)',(secrets.token_hex(16),owner,project,'Charge finale','x'*remaining,'txt',time.time()))
   row={'boundary':boundary,'attempts':[]}
   for operation,params in [('memory_forget',{'id':m['id'],'revision':m['revision']}),('reminder_cancel',{'id':r['id'],'revision':r['revision']})]:
    try: outcome=command(operation,**params)
    except ValueError as e:outcome={'blocked':True,'error':str(e)}
    row['attempts'].append({'operation':operation,'result':outcome})
   row['reminders_still_fire']=tick(w,reminder['due']+1)
   row['memory_still_present']=bool(command('list')['memories'])
   results.append(row)
  finally:w.shutdown()
intent=[]
for operation,phrase in [('memory_forget','N’oublie pas mon adresse.'),('memory_add','Ne mémorise pas cette information.'),('reminder_cancel','Explique la phrase « annule mon rappel » sans rien modifier.')]:
 try:check_intent(operation,phrase);accepted=True
 except ValueError:accepted=False
 intent.append({'operation':operation,'synthetic_request':phrase,'gate_accepts':accepted})
with tempfile.TemporaryDirectory(prefix='kiara-audit-stale-') as folder:
 w=Workspace(Path(folder));owner='audit-synthetic'
 try:
  project=w.action(owner,{'action':'project_create','title':'Projet fictif'})['id']
  def project_command(operation,**values):return execute(w,owner,{'operation':operation,**values},project=project,request_key=secrets.token_hex(16))
  saved=project_command('memory_add',text='Version initiale')
  old=project_command('memory_list')['memories'][0]
  project_command('memory_update',id=old['id'],revision=old['revision'],text='Version récente depuis assistant')
  try:project_command('memory_update',id=old['id'],revision=old['revision'],text='Ancien brouillon')
  except ValueError as e:guarded={'rejected':True,'error':str(e)}
  legacy=w.action(owner,{'action':'memory_save','id':old['id'],'text':'Ancien brouillon'})
  stale={'new_route_stale_write':guarded,'legacy_route_result':legacy,'final_text':project_command('memory_list')['memories'][0]['text']}
 finally:w.shutdown()
report={'storage_boundaries':results,'stale_memory_overwrite':stale,'intent_gate_only_not_model_exploit':intent}
(OUT/'boundary-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
