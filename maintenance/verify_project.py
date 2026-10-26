"""One entrypoint for non-production checks, with isolated output and aggregated results."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import psutil

ROOT=Path(__file__).resolve().parents[1]
PYTHON=ROOT/'Strata-src/.venv/Scripts/python.exe'


def execute(command, *, cwd, env, stream, timeout):
    process=subprocess.Popen(command,cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT)
    try:return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Windows launchers can outlive a terminated cmd/venv wrapper. Close
        # only descendants of this verification, preserving unrelated services.
        try:
            parent=psutil.Process(process.pid)
            for child in reversed(parent.children(recursive=True)):
                try:child.kill()
                except psutil.NoSuchProcess:pass
            parent.kill()
        except psutil.NoSuchProcess:pass
        process.wait(timeout=10)
        return 124


def definitions(output):
    spec=json.loads((ROOT/'client-qwen/wireguard-toolchain.json').read_text(encoding='utf-8'))
    go=ROOT/'client-qwen/wireguard-tools/versions'/spec['version']/'go/bin/go.exe'
    shell=['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command']
    return {
        'sources':[[str(PYTHON),'maintenance/check_sources.py']],
        'runtimes':[[str(PYTHON),'maintenance/verrous_runtime.py','check']],
        'server':[[str(PYTHON),'-m','unittest','discover','-s','lanceur','-v']],
        'windows':[[str(PYTHON),'-m','unittest','discover','-s','client-qwen','-v']],
        'voice':[[str(PYTHON),'-m','unittest','discover','-s','client-voice','-v']],
        'android':[[str(PYTHON),'-m','unittest','discover','-s','client-android/tests','-v'],
                   [str(PYTHON),'client-android/scripts/Prepare-Assets.py','--check']],
        'ui':[['npm.cmd','--prefix','client-qwen','test'],['npm.cmd','--prefix','client-qwen','run','ux:check:all']],
        'android-lint':[shell+["$ErrorActionPreference='Stop'\n. '.\\client-qwen\\android-outils\\Environnement-Android.ps1'\n& '.\\toolchain\\gradle-8.13\\bin\\gradle.bat' --offline --no-daemon --console=plain -p client-android lintDebug\nexit $LASTEXITCODE"]],
        'go':[[str(go),'test','-count=1','-v','.']],
        'go-security':[[str(go),'run','golang.org/x/vuln/cmd/govulncheck@v1.9.0','-json','.'],
                       [str(PYTHON),str(ROOT/'maintenance/summarize_go_security.py'),str(output/'go-security-1.txt'),'--output',str(output/'go-security.json')]],
        'maintenance':[[str(PYTHON),'-m','unittest','discover','-s','maintenance/tests','-v']],
        'dependencies':[[str(PYTHON),'maintenance/check_dependencies.py','--output',str(output/'python-security.json')],
                        ['npm.cmd','--prefix','client-qwen','audit','--json']],
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--checks',nargs='+')
    parser.add_argument('--reuse-server-log',type=Path,help='Explicitly reuse a completed full server suite; recorded as reused evidence')
    parser.add_argument('--server-recheck-logs',type=Path,nargs='+',default=[],help='Successful verbose reruns covering every failure in the complete server log')
    parser.add_argument('--client-executable',type=Path,help='Use an isolated built client in server packaging tests')
    parser.add_argument('--append',action='store_true',help='Keep previous check results except the selected groups')
    args=parser.parse_args()
    output=(args.output or ROOT/'toolchain/test-results'/datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')).resolve()
    output.mkdir(parents=True,exist_ok=True)
    checks=definitions(output);selected=args.checks or list(checks)
    if set(selected)-set(checks):parser.error('Unknown check: '+','.join(sorted(set(selected)-set(checks))))
    env={**os.environ,'PYTHON_EXE':str(PYTHON),'PYTHONIOENCODING':'utf-8','UI_PROOF_DIRECTORY':str(output/'ui'),
         'GOPATH':str(ROOT/'client-qwen/wireguard-tools/workspace'),'GOCACHE':str(ROOT/'client-qwen/wireguard-tools/cache'),
         'GOTOOLCHAIN':'local','GOMAXPROCS':'2'}
    client=args.client_executable or ROOT/'toolchain/releases-staging/windows/Accès serveur Fred.exe'
    if client.is_file():env['FRED_TEST_CLIENT_EXE']=str(client.resolve())
    results=[];previous_hash=None
    previous=output/'validation.json'
    if args.append and previous.is_file():
        previous_hash=hashlib.sha256(previous.read_bytes()).hexdigest()
        results=[value for value in json.loads(previous.read_text(encoding='utf-8'))['results'] if value['check'] not in selected]
    for name in selected:
        if name=='server' and args.reuse_server_log:
            from server_evidence import evidence
            results.append(evidence(args.reuse_server_log,args.server_recheck_logs))
            continue
        for number,command in enumerate(checks[name],1):
            log=output/f'{name}-{number}.txt';started=time.monotonic()
            with log.open('w',encoding='utf-8') as stream:
                try:
                    code=execute(command,cwd=ROOT/'client-qwen/wireguard-bridge' if name in ('go','go-security') and number==1 else ROOT,
                        env=env,stream=stream,timeout=3600 if name=='server' else 1200 if name=='android-lint' else 600)
                except OSError as error:stream.write(type(error).__name__+': '+str(error));code=127
            results.append({'check':name,'command':command,'returncode':code,'passed':code==0,
                            'seconds':round(time.monotonic()-started,3),'log':str(log),
                            'sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
            print(json.dumps(results[-1],ensure_ascii=False),flush=True)
    report={'format':1,'created_at':datetime.now(timezone.utc).isoformat(),
            'passed':all(value['passed'] for value in results),'results':results}
    if previous_hash:report['previous_validation_sha256']=previous_hash
    (output/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Validation:',output/'validation.json')
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
