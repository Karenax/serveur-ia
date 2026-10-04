"""Pilotage des essais isoles; aucun fichier de production n'est modifie."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request
import psutil

ROOT = Path(__file__).resolve().parent
PROD = ROOT.parent.parent
PYTHON = PROD / 'Strata-src/.venv/Scripts/python.exe'

def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def arg_value(args, flag, value):
    if flag in args:
        args[args.index(flag) + 1] = str(value)
    else:
        args.extend([flag, str(value)])

def prepare(variant, context):
    if variant == 'reference-production':
        raise RuntimeError('Utiliser reference-production.py pour lancer le moteur precedent')
    adapted = variant == 'adapte'
    label = f'{variant}-{context}'
    run = ROOT / label
    run.mkdir(exist_ok=True)
    config = read(ROOT / 'production-sauvegarde/configuration-active.json')
    source = ROOT / ('source-adaptee' if adapted else 'source-officielle')
    build = ROOT / ('build-adapte' if adapted else 'build-officiel')
    config.update(exe=str(build / 'strata.exe'), cwd=str(source), log=str(run / 'engine.log'),
                  host='127.0.0.1', port=8088, api_key='', cors_origins=[], trusted_origins=[])
    arg_value(config['args'], '--max-context', context)
    arg_value(config['args'], '--prompt-cache', 0)
    if '--prompt-cache-every' in config['args']:
        i = config['args'].index('--prompt-cache-every')
        del config['args'][i:i+2]
    if not adapted:
        previous=config['args']
        def value(flag):
            return previous[previous.index(flag)+1]
        config['args']=['--pack',value('--pack'),'--native',value('--native'),
            '--mmap-experts','--expert-profile',value('--expert-profile'),'--expert-cache','auto',
            '--layer-split','24','--split-device','1','--prefill','auto',
            '--mtp',value('--mtp'),'--spec','3','--max-context',str(context),'--prompt-cache','0',
            '--ple-io','mmap']
        config['env'] = {k: v for k, v in config['env'].items() if not k.startswith('STRATA_')}
        config['engine_silence_s']=1800
        if variant.startswith('officiel-ram'):
            config['args'].remove('--mmap-experts')
        if variant=='officiel-ram-reserve2048':
            arg_value(config['args'], '--vram-reserve-mib', 2048)
    else:
        config['env'].pop('STRATA_P100_DIAGNOSTIC_SYNC_FILE', None)
    if (ROOT/'modele-ssd.json').exists():
        model=read(ROOT/'modele-ssd.json')
        arg_value(config['args'],'--native',model['native'])
    if not adapted:
        ram=read(ROOT/'ngram-ram.json')
        if ram['status']!='verrouille' or ram['verified_locked_pages']<=0 or not psutil.pid_exists(ram['pid']):
            raise RuntimeError('La table ngram doit etre completement verrouillee en RAM avant cet essai')
        if Path(ram['path']).resolve()!=Path(config['args'][config['args'].index('--native')+1]).resolve():
            raise RuntimeError('La table verrouillee doit provenir de la meme copie GGUF que le moteur')
        config['research_ngram_lock_state']=str(ROOT/'ngram-ram.json')
    save(run / 'config.json', config)
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=source, text=True)
    if not adapted and status:
        raise RuntimeError('Le code officiel doit rester intact: ' + status)
    save(run / 'origine.json', dict(tag='v0.1.39', revision=revision, source_status=status,
         adaptations=adapted, context=context, prompt_cache=0,
         difference='Official code and stock automatic tuning. The standard --ple-io mmap option plus an external read-only lock keeps the entire PLE table physically in RAM on Windows. No local STRATA environment switches.' if not adapted else 'Local P100 resident hybrid adaptations'))
    save(build / 'BUILD.json', dict(version='0.1.39', revision=revision, research=True, adaptations=adapted))
    return run

def start(run):
    config_path = run / 'config.json'
    config = read(config_path)
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('STRATA_'):
            del env[key]
    env.update(config['env'])
    env.update(PYTHONDONTWRITEBYTECODE='1', TEMP=r'D:\Temp\strata-recherche', TMP=r'D:\Temp\strata-recherche')
    env['PATH'] = os.pathsep.join(config['lib_dirs'] + [env.get('PATH', '')])
    command = [str(PYTHON), '-u', '-m', 'serve.server', '--engine', 'strata', '--config',
               str(config_path), '--host', '127.0.0.1', '--port', str(config['port'])]
    with (run / 'server.stdout.log').open('ab') as out, (run / 'server.stderr.log').open('ab') as err:
        proc = subprocess.Popen(command, cwd=config['cwd'], env=env, stdout=out, stderr=err,
                                stdin=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
    save(run / 'processus.json', dict(pid=proc.pid, command=command, started=dt.datetime.now(dt.timezone.utc).isoformat()))
    print(json.dumps(dict(run=str(run), pid=proc.pid, port=config['port']), ensure_ascii=False), flush=True)

def status(run):
    info = read(run / 'processus.json')
    children = []
    try:
        parent = psutil.Process(info['pid'])
        for p in [parent, *parent.children(recursive=True)]:
            with p.oneshot():
                children.append(dict(pid=p.pid, name=p.name(), ram_gib=p.memory_info().rss / 2**30,
                                     cpu_seconds=sum(p.cpu_times()[:2])))
    except psutil.NoSuchProcess:
        pass
    result = dict(processes=children)
    try:
        with urllib.request.urlopen('http://127.0.0.1:8088/health', timeout=3) as response:
            result['health'] = json.load(response)
    except Exception as e:
        result['health'] = str(e)
    print(json.dumps(result, ensure_ascii=False), flush=True)

def stop(run):
    info = read(run / 'processus.json')
    try:
        parent = psutil.Process(info['pid'])
        if str(run).lower() not in ' '.join(parent.cmdline()).lower():
            raise RuntimeError('PID reutilise: arret refuse')
        processes = parent.children(recursive=True) + [parent]
        for p in processes:
            try:
                p.terminate()
            except psutil.NoSuchProcess:
                pass
        gone, alive = psutil.wait_procs(processes, timeout=10)
        for p in alive:
            p.kill()
        print(json.dumps(dict(stopped=[p.pid for p in processes])), flush=True)
    except psutil.NoSuchProcess:
        print('already stopped', flush=True)

def checksums():
    results = []
    for item in read(ROOT / 'production-sauvegarde/empreintes.json'):
        actual = hashlib.sha256(Path(item['path']).read_bytes()).hexdigest().upper()
        results.append(dict(path=item['path'], unchanged=actual == item['sha256'], current_sha256=actual))
    save(ROOT / 'verification-production.json', results)
    print(json.dumps(results, ensure_ascii=False), flush=True)

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['start', 'status', 'stop', 'checksums'])
parser.add_argument('--variant', choices=['officiel', 'officiel-ram', 'officiel-ram-reserve2048', 'adapte', 'reference-production'], default='officiel')
parser.add_argument('--context', type=int, default=262144)
args = parser.parse_args()
if args.action == 'checksums':
    checksums()
elif args.action == 'start':
    start(prepare(args.variant, args.context))
else:
    globals()[args.action](ROOT / f'{args.variant}-{args.context}')
