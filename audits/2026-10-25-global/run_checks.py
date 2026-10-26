"""Run existing checks, preserving historical UI screenshots byte for byte."""
from pathlib import Path
import json, os, subprocess, sys, time
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
PY=ROOT/'Strata-src/.venv/Scripts/python.exe'
group=sys.argv[1]
commands={
 'server':[[str(PY),'-m','unittest','discover','-s','lanceur','-v']],
 'clients':[[str(PY),'-m','unittest','discover','-s',folder,'-v'] for folder in ('client-qwen','client-voice','client-android/tests')],
 'static':[[str(PY),'maintenance/check_sources.py'],[str(PY),'client-android/scripts/Prepare-Assets.py','--check'],[str(PY),'maintenance/verrous_runtime.py','check'],['npm.cmd','--prefix','client-qwen','run','ux:check:all']],
 'ui':[['npm.cmd','--prefix','client-qwen','test']],
}[group]
env={**os.environ,'PYTHONIOENCODING':'utf-8','PYTHON_EXE':str(PY),'UI_PROOF_DIRECTORY':str(OUT/'ui-tests')}
historical=[ROOT/'maintenance/2026-10-23-fluidite-vocale/windows-interruptions-desactivees.png']+[ROOT/f'maintenance/2026-10-23-listes-correcteur/{p}-{v}.png' for p in ('windows','android') for v in ('correcteur','conversations')]
historical += [ROOT/f'maintenance/2026-10-24-vocal-workspace/ui/{p}-{v}.png' for p in ('windows','android') for v in ('kiara','microphone')]
historical += [ROOT/f'maintenance/2026-10-25-assistant-integration/ui/{p}-{v}.png' for p in ('windows','android') for v in ('desktop','phone','tablet')]
before={p:p.read_bytes() if p.exists() else None for p in historical} if group=='ui' else {}
results=[]
try:
 for i,command in enumerate(commands):
  log=OUT/f'{group}-{i+1}.txt'; start=time.monotonic()
  with log.open('w',encoding='utf-8') as stream:
   stream.write('COMMAND: '+subprocess.list2cmdline(command)+'\n');stream.flush()
   try:
    result=subprocess.run(command,cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=2400)
    rc=result.returncode
   except subprocess.TimeoutExpired: rc=124
  record={'command':command,'returncode':rc,'seconds':round(time.monotonic()-start,2),'log':log.name}
  results.append(record);print(json.dumps(record),flush=True)
finally:
 for p,content in before.items():
  if p.exists() and (content is None or p.read_bytes()!=content):
   target=OUT/'ui-tests'/p.name;target.parent.mkdir(exist_ok=True);target.write_bytes(p.read_bytes())
   if content is not None:p.write_bytes(content)
   else:p.unlink()
 (OUT/f'{group}-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
