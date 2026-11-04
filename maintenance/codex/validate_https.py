"""Qualify the installed Codex profile against the deployed HTTPS gateway.

Read one existing active personal executable in memory. Never persist its token.
The API is stateless; the only file read by Codex is a disposable local fixture.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'lanceur'))
from core import HOME,HIDDEN
from releases import profile


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    records=json.loads((HOME/'acces-distants.json').read_text(encoding='utf-8'))['clients']
    active={r['id'] for r in records if not r.get('revoked') and not r.get('suspended') and not r.get('hermes_pending') and (not r.get('expires_epoch') or r['expires_epoch']>time.time())}
    access=next(profile(p) for p in (HOME/'clients').glob('*.exe') if p.stem in active)
    started=time.monotonic()
    with tempfile.TemporaryDirectory(prefix='kiara-https-qualification-') as folder:
        expected='KIARA-'+secrets.token_hex(6)
        (Path(folder)/'preuve.txt').write_text(expected,encoding='utf-8')
        command=[shutil.which('codex'),'exec','--profile','kiara','--ephemeral','--skip-git-repo-check','--ignore-rules','-C',folder,
                 '-c','approval_policy="never"','-s','danger-full-access','-c','agents.enabled=false','--json',
                 'Lis preuve.txt avec un outil du PC et réponds uniquement avec son contenu exact.']
        result=subprocess.run(command,env=dict(os.environ,KIARA_API_KEY=access['token']),stdin=subprocess.DEVNULL,
                              capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180,creationflags=HIDDEN)
        events=[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
        answers=[v['item']['text'] for v in events if v.get('type')=='item.completed' and v.get('item',{}).get('type')=='agent_message']
        executed=any(v.get('type')=='item.completed' and v.get('item',{}).get('type')=='command_execution' and v['item'].get('exit_code')==0 for v in events)
        report={'passed':result.returncode==0 and executed and bool(answers) and answers[-1].strip()==expected,
                'endpoint':'https://ia.karenax.net/v1','model':'fred-qwen','seconds':round(time.monotonic()-started,2),
                'expected':expected,'answer':answers[-1] if answers else '', 'client_tool_executed':executed,
                'returncode':result.returncode,'stdout':result.stdout.replace(access['token'],'[REDACTED]'),
                'stderr':result.stderr.replace(access['token'],'[REDACTED]')}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('stdout','stderr')},ensure_ascii=True))
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
