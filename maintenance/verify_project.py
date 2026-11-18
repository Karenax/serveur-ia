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


def definitions(output, business_python=None, npm_cli=None):
    spec=json.loads((ROOT/'client-qwen/wireguard-toolchain.json').read_text(encoding='utf-8'))
    go=ROOT/'client-qwen/wireguard-tools/versions'/spec['version']/'go/bin/go.exe'
    shell=['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-Command']
    business_python = str(business_python or PYTHON)
    npm = ['node', str(npm_cli.resolve(strict=True))] if npm_cli else ['npm.cmd']
    web = ROOT / 'agent/web'
    windows_tests = [path.stem for path in sorted((ROOT/'client-qwen').glob('test_*.py'))
                     if path.name != 'test_linux_support.py']
    windows_server_tests = [path.stem for path in sorted((ROOT/'lanceur').glob('test_*.py'))
                            if path.name != 'test_android_updates.py']
    return {
        # This profile intentionally exercises only desktop sizes. Browser
        # simulations are useful regression checks, not native OS qualification.
        'desktop-server': [[business_python, '-m', 'pytest',
                            'tests/test_workspace.py::test_jobs_keep_global_mail_jobs_out_of_project_scope',
                            '-p', 'no:cacheprovider']],
        'desktop-portal': [['node', str(ROOT/'agent/scripts/ux-quality-check.mjs')],
                           ['node', '--test', str(ROOT/'agent/scripts/ux-quality-check.test.mjs')],
                           ['node', str(web/'node_modules/typescript/bin/tsc'), '--noEmit', '--incremental', 'false'],
                           ['node', str(web/'node_modules/vite/bin/vite.js'), 'build', '--outDir', str(output/'desktop-web')]],
        'desktop-windows-browser': [['node', 'client-qwen/test_ux_recovery_ui.cjs', '--windows-only', '--desktop-audit']],
        'desktop-linux-browser': [['node', 'client-qwen/test_ux_recovery_ui.cjs', '--linux-only', '--desktop-audit']],
        'business': [[business_python, '-m', 'pytest', 'tests', '-p', 'no:cacheprovider']],
        'business-restore': [[business_python, '-m', 'pytest', 'tests/test_project_note_backup.py',
                              '-p', 'no:cacheprovider']],
        'business-web': [['node', str(ROOT/'agent/scripts/ux-quality-check.mjs')],
                         ['node', '--test', str(ROOT/'agent/scripts/ux-quality-check.test.mjs')],
                         ['node', str(web/'node_modules/typescript/bin/tsc'), '--noEmit', '--incremental', 'false'],
                         ['node', str(web/'node_modules/vitest/vitest.mjs'), 'run', '--maxWorkers=4'],
                         ['node', str(web/'node_modules/vite/bin/vite.js'), 'build', '--outDir', str(output/'web')]],
        'package-server': [['node', str(web/'node_modules/vite/bin/vite.js'), 'build', '--outDir', str(output/'package-web')],
                           [str(PYTHON), 'maintenance/package_server.py', '--output', str(output/'package-server'),
                            '--web-dist', str(output/'package-web')]],
        'tauri': [shell + [". './maintenance/tauri-dev-env.ps1'; "
                          "cargo test -j 2 --locked --manifest-path client-tauri/Cargo.toml; exit $LASTEXITCODE"]],
        'transport': [[str(PYTHON), '-m', 'unittest', 'test_agent_access', 'test_agent_gateway',
                       'test_agent_web', 'test_agent_transport']],
        'sources':[[str(PYTHON),'maintenance/check_sources.py']],
        'runtimes':[[str(PYTHON),'maintenance/verrous_runtime.py','check']],
        'server':[[str(PYTHON),'-m','unittest','discover','-s','lanceur','-v']],
        'server-windows':[[str(PYTHON),'-m','unittest','-v',*windows_server_tests]],
        'windows':[[str(PYTHON),'-m','unittest','discover','-s','client-qwen','-v']],
        'windows-client':[[str(PYTHON),'-m','unittest','-v',*windows_tests]],
        'voice':[[str(PYTHON),'-m','unittest','discover','-s','client-voice','-v']],
        'android':[[str(PYTHON),'-m','unittest','discover','-s','client-android/tests','-v'],
                   [str(PYTHON),'client-android/scripts/Prepare-Assets.py','--check']],
        'ui':[npm+['--prefix','client-qwen','test'],npm+['--prefix','client-qwen','run','ux:check:all']],
        'ui-windows':[['node','client-qwen/test_ux_recovery_ui.cjs','--windows-only'],
                      ['node','client-qwen/test_conversation_ui.cjs','--voice-workspace'],
                      ['node','client-qwen/test_conversation_ui.cjs','--assistant-integration']],
        'android-lint':[shell+["$ErrorActionPreference='Stop'\n. '.\\client-qwen\\android-outils\\Environnement-Android.ps1'\n& '.\\toolchain\\gradle-8.13\\bin\\gradle.bat' --offline --no-daemon --console=plain -p client-android lintDebug\nexit $LASTEXITCODE"]],
        'go':[[str(go),'test','-count=1','-v','.']],
        'go-security':[[str(go),'run','golang.org/x/vuln/cmd/govulncheck@v1.9.0','-json','.'],
                       [str(PYTHON),str(ROOT/'maintenance/summarize_go_security.py'),str(output/'go-security-1.txt'),'--output',str(output/'go-security.json')]],
        'maintenance':[[str(PYTHON),'-m','unittest','discover','-s','maintenance/tests','-v']],
        'dependencies':[[str(PYTHON),'maintenance/check_dependencies.py','--output',str(output/'python-security.json')],
                        npm+['--prefix','client-qwen','audit','--json']],
    }


DESKTOP_AUDIT_CHECKS = ('desktop-server', 'desktop-portal', 'desktop-windows-browser', 'desktop-linux-browser')


def coverage(checks, results):
    """Describe evidence actually recorded, without promoting it to OS qualification."""
    recorded = {result['check'] for result in results}
    categories = {
        'serveur': {'business', 'business-restore', 'server', 'server-windows', 'desktop-server'},
        'portail': {'business-web', 'desktop-portal'},
        'client_windows': {'windows', 'windows-client', 'ui', 'ui-windows', 'desktop-windows-browser'},
        'client_linux': {'ui', 'desktop-linux-browser'},
        'android': {'ui', 'android', 'android-lint'},
    }
    dimensions = {}
    for category, members in categories.items():
        matching = [result for result in results if result['check'] in members]
        dimensions[category] = {
            'recorded_checks': sorted({result['check'] for result in matching}),
            'recorded_commands_passed': all(result['passed'] for result in matching) if matching else None,
        }
    return {
        'recorded_checks': sorted(recorded),
        'not_recorded_checks': sorted(set(checks) - recorded),
        'dimensions': dimensions,
        'passed_applies_to': 'recorded commands only',
        'native_windows_qualification': 'not established by this report',
        'native_linux_qualification': 'not established by this report',
        'desktop_browser_checks': 'Chromium simulations, not Tauri or native system tests',
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--checks',nargs='+')
    parser.add_argument('--desktop-audit', action='store_true',
                        help='Run isolated desktop-oriented checks; browser simulations are not native qualification')
    parser.add_argument('--business-python', type=Path, help='Python environment with the project-service dependencies')
    parser.add_argument('--npm-cli', type=Path, help='Path to npm-cli.js when npm.cmd is unavailable')
    parser.add_argument('--reuse-server-log',type=Path,help='Explicitly reuse a completed full server suite; recorded as reused evidence')
    parser.add_argument('--server-recheck-logs',type=Path,nargs='+',default=[],help='Successful verbose reruns covering every failure in the complete server log')
    parser.add_argument('--client-executable',type=Path,help='Use an isolated built client in server packaging tests')
    parser.add_argument('--append',action='store_true',help='Keep previous check results except the selected groups')
    args=parser.parse_args()
    evidence_root=Path(os.environ.get('KIARA_EVIDENCE_DIR',str(ROOT/'toolchain/test-results'))).expanduser()
    output=(args.output or evidence_root/datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')).resolve()
    output.mkdir(parents=True,exist_ok=True)
    checks=definitions(output,args.business_python,args.npm_cli)
    if args.desktop_audit and args.checks:
        parser.error('--desktop-audit and --checks cannot be combined')
    selected=list(DESKTOP_AUDIT_CHECKS) if args.desktop_audit else args.checks or [name for name in checks if name not in {'server-windows', 'ui-windows', 'windows-client', *DESKTOP_AUDIT_CHECKS}]
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
                    cwd = {'business': ROOT/'agent', 'business-restore': ROOT/'agent', 'business-web': ROOT/'agent/web',
                           'desktop-server': ROOT/'agent', 'desktop-portal': ROOT/'agent/web',
                           'windows-client': ROOT/'client-qwen'}.get(name, ROOT)
                    if name == 'package-server' and number == 1:
                        cwd = ROOT/'agent/web'
                    if name in ('go','go-security') and number == 1:
                        cwd = ROOT/'client-qwen/wireguard-bridge'
                    check_env = env
                    if name.startswith('desktop-'):
                        temporary = output/'tmp'
                        temporary.mkdir(exist_ok=True)
                        check_env = {**env, 'TEMP': str(temporary), 'TMP': str(temporary), 'TMPDIR': str(temporary)}
                    if name in ('desktop-windows-browser', 'desktop-linux-browser'):
                        # Do not silently substitute an externally configured Windows
                        # executable for the requested browser simulation.
                        check_env = {key: value for key, value in check_env.items() if key != 'KIARA_UX_WINDOWS_EXE'}
                    if name in ('business', 'business-restore', 'desktop-server', 'transport'):
                        modules = ('agent', 'shared') if name != 'transport' else ('lanceur', 'client-qwen', 'shared')
                        check_env = {**check_env, 'PYTHONPATH': os.pathsep.join(str(ROOT/module) for module in modules)}
                    if name == 'windows-client':
                        check_env = {**env, 'PYTHONPATH': str(ROOT/'shared')}
                    if name == 'server-windows':
                        check_env = {**env, 'PYTHONPATH': os.pathsep.join(
                            value for value in (str(ROOT/'lanceur'), env.get('PYTHONPATH')) if value
                        )}
                    timeout = 3600 if name in ('server', 'server-windows', 'business', 'tauri') else 1200 if name == 'android-lint' else 600
                    code=execute(command,cwd=cwd,env=check_env,stream=stream,timeout=timeout)
                except OSError as error:stream.write(type(error).__name__+': '+str(error));code=127
            results.append({'check':name,'command':command,'returncode':code,'passed':code==0,
                            'seconds':round(time.monotonic()-started,3),'log':str(log),
                            'sha256':hashlib.sha256(log.read_bytes()).hexdigest()})
            print(json.dumps(results[-1],ensure_ascii=False),flush=True)
    report={'format':1,'created_at':datetime.now(timezone.utc).isoformat(),
            'passed':all(value['passed'] for value in results),'results':results,
            'coverage':coverage(checks, results)}
    if previous_hash:report['previous_validation_sha256']=previous_hash
    (output/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    for category, summary in report['coverage']['dimensions'].items():
        status = 'aucun contrôle dédié enregistré' if summary['recorded_commands_passed'] is None else ('commandes enregistrées réussies' if summary['recorded_commands_passed'] else 'échec enregistré')
        print(f"{category}: {status} ({', '.join(summary['recorded_checks']) or 'aucune commande enregistrée'})")
    print('Les résultats navigateur ne constituent pas une qualification Tauri native.')
    print('Validation:',output/'validation.json')
    if not report['passed']:raise SystemExit(1)


if __name__=='__main__':main()
