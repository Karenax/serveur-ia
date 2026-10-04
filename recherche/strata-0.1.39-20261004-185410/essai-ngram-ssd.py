"""Essai isole du profil normal, seule la table PLE passe de RAM a SSD direct."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import psutil

ROOT = Path(__file__).resolve().parent
PROD = ROOT.parent.parent
RUN = ROOT / 'normal-ngram-ssd-262144'
PYTHON = PROD / 'Strata-src/.venv/Scripts/python.exe'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def environment(config=None):
    env = os.environ.copy()
    for key in list(env):
        if key.startswith('STRATA_'):
            del env[key]
    env.update(PYTHONDONTWRITEBYTECODE='1', TEMP=r'D:\Temp\strata-recherche', TMP=r'D:\Temp\strata-recherche')
    if config is not None:
        env.update(config['env'])
        env['PATH'] = os.pathsep.join(config['lib_dirs']+[env.get('PATH','')])
    return env

def check_free(port):
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',port))

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=['prepare','stop-production','start','stop','restore'])
args = parser.parse_args()

if args.action == 'prepare':
    RUN.mkdir(exist_ok=True)
    if (RUN/'config.json').exists() or (RUN/'processus.json').exists():
        raise RuntimeError('Cet essai est deja prepare; ne pas le remplacer')
    pointer = read(PROD/'lanceur/session.json')
    session = Path(pointer['directory'])
    active = read(session/'strata.json')
    expected = read(ROOT/'production-sauvegarde/configuration-active.json')
    if active != expected:
        raise RuntimeError('Le profil actif a change depuis la reference RAM : comparaison a reevaluer')
    backup = RUN/'production-sauvegarde'
    backup.mkdir(exist_ok=True)
    files = [PROD/'lanceur/session.json', PROD/'lanceur/reglages.json',
             PROD/'lanceur/reglages-par-defaut.json', PROD/'lanceur/base-strata.json',
             PROD/'lanceur/exploitation.json', session/'strata.json', session/'state.json']
    stamps = []
    for path in files:
        if path.exists():
            shutil.copy2(path, backup/path.name)
            stamps.append(dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    stamps.append(dict(path=active['exe'],sha256=hashlib.sha256(Path(active['exe']).read_bytes()).hexdigest()))
    save(backup/'empreintes.json',stamps)
    config = read(ROOT/'reference-production-262144/config.json')
    config['args'][config['args'].index('--native')+1] = active['args'][active['args'].index('--native')+1]
    config['args'][config['args'].index('--ple-io')+1] = 'direct'
    copied_table=read(RUN/'copie-ngram.json')
    if copied_table['status']!='verifie' or copied_table['source_sha256']!=copied_table['copied_sha256']:
        raise RuntimeError('La copie SSD de la table ngram n\'est pas verifiee')
    config['args']+=['--ple-gguf',copied_table['path']]
    config.update(log=str(RUN/'engine.log'),
                  research_ngram_mode='SSD C, unbuffered direct I/O; bounded default row cache')
    native = Path(config['args'][config['args'].index('--native')+1])
    if not native.is_file() or not Path(copied_table['path']).is_file():
        raise RuntimeError('Les fichiers du modele ou de la table sont absents')
    save(RUN/'config.json',config)
    save(RUN/'origine.json',dict(created=dt.datetime.now(dt.timezone.utc).isoformat(),
        reference=str(ROOT/'reference-production-262144'),production_session=str(session),
        engine=config['exe'],native=str(native),context=262144,
        sole_inference_change={'--ple-io':['ram','direct'],'--ple-gguf':copied_table['path']},
        native_loading_note='Original model on D; all expert bytes resident in RAM/VRAM before measurement. Prior RAM reference loaded equivalent SSD copies, now absent.',
        note='Identical benchmark settings: prompt history disabled, 2 repetitions after 1 warmup; production files unchanged. Separate PLE GGUF contains exact original tensor bytes.',
        table_bytes=28800138240, row_cache_capacity=1048576, row_cache_bytes=98697216))
    print(json.dumps(dict(status='prepare',run=str(RUN),config=str(RUN/'config.json')),ensure_ascii=False))

elif args.action == 'stop-production':
    sys.path.insert(0,str(PROD/'lanceur'))
    from core import matching_servers, same_process, stop_processes
    session=Path(read(RUN/'production-sauvegarde/session.json')['directory'])
    if read(PROD/'lanceur/session.json')['directory']!=str(session):
        raise RuntimeError('La session active a change')
    state=read(session/'state.json')
    supervisor=same_process(state.get('supervisor',{}))
    if not supervisor or str(session/'strata.json').lower() not in ' '.join(supervisor.cmdline()).lower():
        raise RuntimeError('Superviseur de production non identifie')
    servers=matching_servers([str(session/'strata.json')])
    if not servers:
        raise RuntimeError('Serveur de production introuvable')
    # Keep the original launcher/watch preferences and its desired flag intact.
    # An alive, suspended supervisor prevents automatic reload during the trial.
    metadata=dict(pid=supervisor.pid,created=supervisor.create_time(),status='suspendu',
                  config_path=str(session/'strata.json'),server_pids=[p.pid for p in servers])
    supervisor.suspend()
    save(RUN/'production-superviseur-suspendu.json',metadata)
    try:
        stop_processes(servers)
        check_free(8080)
    except Exception:
        supervisor.resume()
        metadata['status']='repris_apres_erreur'
        save(RUN/'production-superviseur-suspendu.json',metadata)
        raise
    print(json.dumps({**metadata,'status':'production_arretee_pour_essai'}))

elif args.action == 'start':
    if (RUN/'processus.json').exists():
        raise RuntimeError('Cet essai a deja ete lance')
    config = read(RUN/'config.json')
    for port in (8080,8088):
        check_free(port)
    for process in psutil.process_iter(['exe','pid']):
        if process.info['exe'] and Path(process.info['exe']).resolve()==Path(config['exe']).resolve():
            raise RuntimeError(f'Moteur deja actif : {process.pid}')
    command=[str(PYTHON),'-u','-m','serve.server','--engine','strata','--config',str(RUN/'config.json'),
             '--host','127.0.0.1','--port','8088']
    with (RUN/'server.stdout.log').open('ab') as out,(RUN/'server.stderr.log').open('ab') as err:
        process=subprocess.Popen(command,cwd=config['cwd'],env=environment(config),stdout=out,stderr=err,
            stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)
    save(RUN/'processus.json',dict(pid=process.pid,created=psutil.Process(process.pid).create_time(),
        command=command,started=dt.datetime.now(dt.timezone.utc).isoformat()))
    print(json.dumps(dict(status='demarre',pid=process.pid,run=str(RUN)),ensure_ascii=False))

elif args.action == 'stop':
    metadata=read(RUN/'processus.json')
    try:
        parent=psutil.Process(metadata['pid'])
    except psutil.NoSuchProcess:
        print('Serveur de recherche deja arrete')
        raise SystemExit(0)
    if abs(parent.create_time()-metadata['created'])>0.01 or str(RUN).lower() not in ' '.join(parent.cmdline()).lower():
        raise RuntimeError('Identite du serveur de recherche non confirmee')
    processes=parent.children(recursive=True)+[parent]
    for process in reversed(processes):
        try: process.terminate()
        except psutil.NoSuchProcess: pass
    _,alive=psutil.wait_procs(processes,timeout=10)
    for process in alive:
        process.kill()
    print(json.dumps(dict(status='arrete',pids=[p.pid for p in processes])))

elif args.action == 'restore':
    backup=RUN/'production-sauvegarde'
    pointer=read(PROD/'lanceur/session.json')
    if pointer['directory']!=read(backup/'session.json')['directory']:
        raise RuntimeError('Autre session selectionnee; restauration interrompue')
    session=Path(pointer['directory'])
    config_path=session/'strata.json'
    config=read(config_path)
    if config!=read(backup/'strata.json'):
        raise RuntimeError('Profil modifie; restauration interrompue')
    engine_stamp=next(x for x in read(backup/'empreintes.json') if Path(x['path'])==Path(config['exe']))
    if hashlib.sha256(Path(config['exe']).read_bytes()).hexdigest()!=engine_stamp['sha256']:
        raise RuntimeError('Le binaire de production a change')
    for port in (8080,8088):
        check_free(port)
    command=[str(PYTHON),'-u',str(PROD/'lanceur/runtime.py'),'--config',str(config_path),
             '--run-dir',str(session),'--floor','6']
    with (RUN/'retablissement-production.log').open('ab') as log:
        process=subprocess.Popen(command,cwd=PROD,env=environment(),stdout=log,stderr=log,
            stdin=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
    save(RUN/'retablissement-production.json',dict(pid=process.pid,run_dir=str(session),config_path=str(config_path),
        exe=config['exe'],port=config['port'],context=262144,history_slots=6,settings_rewritten=False,
        started=dt.datetime.now(dt.timezone.utc).isoformat()))
    held=read(RUN/'production-superviseur-suspendu.json')
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        state=read(session/'state.json')
        identity=state.get('supervisor',{})
        if identity.get('pid') and identity['pid']!=held['pid']:
            replacement=psutil.Process(identity['pid'])
            if abs(replacement.create_time()-identity['created'])<0.01 and str(config_path).lower() in ' '.join(replacement.cmdline()).lower():
                break
        time.sleep(.2)
    else:
        raise RuntimeError('Le nouveau superviseur ne s\'est pas declare; ancien superviseur maintenu suspendu')
    try:
        old=psutil.Process(held['pid'])
    except psutil.NoSuchProcess:
        old=None
    if old is not None:
        if abs(old.create_time()-held['created'])>0.01:
            raise RuntimeError('Identite de l\'ancien superviseur perdue')
        old.kill()
    held.update(status='remplace',replacement=identity)
    save(RUN/'production-superviseur-suspendu.json',held)
    print(json.dumps(dict(status='restauration_demarre',pid=process.pid,run_dir=str(session)),ensure_ascii=False))
