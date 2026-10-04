"""Configuration and process ownership for the local Qwen control panel."""
from __future__ import annotations
import copy
import ipaddress
import json
import os
import tempfile
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
from urllib.parse import urlsplit
import psutil

ROOT = Path(__file__).resolve().parent.parent
HOME = ROOT / 'lanceur'
BASE_PATH = ROOT / 'strata-iq4-p100-hybride.json'
PYTHON = ROOT / 'Strata-src/.venv/Scripts/python.exe'
HIDDEN = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

def read_json(path, fallback=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return copy.deepcopy(fallback)

def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=path.name+'.', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        deadline=time.monotonic()+2
        while True:
            try:os.replace(name,path);break
            except PermissionError:
                if time.monotonic()>=deadline:raise
                time.sleep(.05)
    finally:
        if os.path.exists(name): os.unlink(name)

def arg(config, flag, default=''):
    args = config.get('args', [])
    return args[args.index(flag) + 1] if flag in args else default

def defaults_from_config(config):
    return {
        'model_name': config.get('model_name', 'qwen3.8-flash-next'),
        'pack': arg(config, '--pack'), 'native': arg(config, '--native'),
        'tokenizer': config.get('tokenizer', ''), 'exe': config.get('exe', ''),
        'mtp_path': arg(config, '--mtp'), 'expert_profile': arg(config, '--expert-profile'),
        'context': int(arg(config, '--max-context', 262144)),
        'workers': int(arg(config, '--pool-workers', 15)),
        'prefill': int(arg(config, '--prefill', 256)),
        'vram_reserve': int(arg(config, '--vram-reserve-mib', 2048)),
        'expert_cache': str(arg(config, '--expert-cache', 'auto')),
        'layer_split': int(arg(config, '--layer-split', 24)),
        'gpus': config.get('env', {}).get('CUDA_VISIBLE_DEVICES', ''),
        'mtp_enabled': '--mtp' in config.get('args', []),
        'spec': int(arg(config, '--spec', 3)),
        'spec_min_p': float(arg(config, '--spec-min-p', .5)),
        'history_enabled': int(arg(config, '--prompt-cache', 6)) > 0,
        'history_slots': max(1, int(arg(config, '--prompt-cache', 6))),
        'history_every': int(arg(config, '--prompt-cache-every', 16384)),
        'short_read': int(arg(config, '--short-read', 0)),
        'host': config.get('host', '127.0.0.1'), 'port': int(config.get('port', 8080)),
        'api_key': config.get('api_key', ''),
        'cors_origins': '\n'.join(config.get('cors_origins', [])),
        'trusted_origins': '\n'.join(config.get('trusted_origins', [])),
        'fit_max_tokens': bool(config.get('fit_max_tokens', False)),
        'min_free_ram_gib': 6,
    }

def origins(value, wildcard=False):
    if not isinstance(value, str):
        raise ValueError('Les origines réseau doivent être du texte.')
    result = []
    for line in value.replace(',', '\n').splitlines():
        line = line.strip().rstrip('/')
        if not line:
            continue
        if line == '*' and wildcard:
            result.append(line)
            continue
        parsed = urlsplit(line)
        if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.path or parsed.query or parsed.fragment or parsed.username:
            raise ValueError('Origine invalide : utiliser une adresse telle que http://192.168.1.20:3000.')
        try:
            parsed.port
        except ValueError:
            raise ValueError('Port invalide dans une origine réseau.')
        result.append(line)
    return list(dict.fromkeys(result))

def validate(settings, check_paths=False):
    if not isinstance(settings, dict):
        raise ValueError('Réglages invalides.')
    s = copy.deepcopy(settings)
    limits = {'context': (512, 262144), 'workers': (1, 31), 'prefill': (256, 8192),
              'vram_reserve': (512, 8192), 'layer_split': (1, 47), 'spec': (2, 8),
              'history_slots': (1, 24), 'history_every': (0, 262144),
              'short_read': (0, 256), 'port': (1, 65535)}
    for name, (lo, hi) in limits.items():
        try:
            number = float(s[name])
            if not number.is_integer():
                raise ValueError()
            value = int(number)
        except (KeyError, TypeError, ValueError, OverflowError):
            raise ValueError(f'Valeur entière attendue : {name}.')
        if not lo <= value <= hi:
            raise ValueError(f'{name} doit être compris entre {lo} et {hi}.')
        s[name] = value
    for name, lo, hi in [('spec_min_p', 0, 1), ('min_free_ram_gib', 2, 32)]:
        try:
            s[name] = float(s[name])
            if not lo <= s[name] <= hi:
                raise ValueError()
        except (KeyError, TypeError, ValueError):
            raise ValueError(f'{name} doit être compris entre {lo} et {hi}.')
    for name in ['mtp_enabled', 'history_enabled', 'fit_max_tokens']:
        if not isinstance(s.get(name), bool):
            raise ValueError(f'Valeur oui/non attendue : {name}.')
    for name in ['model_name', 'pack', 'native', 'tokenizer', 'exe', 'mtp_path', 'expert_profile', 'gpus', 'host', 'api_key', 'expert_cache']:
        if not isinstance(s.get(name), str):
            raise ValueError(f'Texte attendu : {name}.')
        if '\x00' in s[name] or len(s[name]) > 4096:
            raise ValueError(f'Valeur invalide : {name}.')
        s[name] = s[name].strip()
    if not s['model_name']:
        raise ValueError('Le nom du modèle est obligatoire.')
    try:
        host = ipaddress.ip_address(s['host'])
        if host.version != 4:
            raise ValueError()
    except ValueError:
        raise ValueError("L'adresse d'écoute doit être une IPv4 : 127.0.0.1, 0.0.0.0 ou une adresse de ce PC.")
    if not host.is_loopback and len(s['api_key']) < 24:
        raise ValueError('Pour le réseau, générer une clé API d’au moins 24 caractères.')
    gpus = [part.strip() for part in s['gpus'].split(',')]
    if len(gpus) != 2 or len(set(gpus)) != 2 or not all(part and (part.isdecimal() or part.startswith('GPU-')) for part in gpus):
        raise ValueError('Ce profil P100 nécessite exactement deux GPU distincts, dans leur ordre de calcul.')
    s['gpus'] = ','.join(gpus)
    if s['expert_cache'] != 'auto':
        try:
            if not 0 <= int(s['expert_cache']) <= 24576:
                raise ValueError()
        except ValueError:
            raise ValueError('Le cache GPU doit être auto ou un nombre de 0 à 24576.')
    if s['prefill'] > s['context']:
        raise ValueError('Le bloc de prompt ne peut pas dépasser le contexte.')
    cors = origins(s.get('cors_origins', ''), True)
    origins(s.get('trusted_origins', ''))
    if '*' in cors and len(s['api_key']) < 24:
        raise ValueError('Une clé API est obligatoire avec une origine CORS *.')
    if check_paths:
        paths = [('Moteur', s['exe'], False), ('Pack', s['pack'], True),
                 ('GGUF', s['native'], False), ('Tokenizer', s['tokenizer'], True),
                 ('Profil experts', s['expert_profile'], False)]
        if s['mtp_enabled']:
            paths.append(('Pack MTP', s['mtp_path'], True))
        for label, path, directory in paths:
            target = Path(path)
            if not target.is_absolute() or not (target.is_dir() if directory else target.is_file()):
                raise ValueError(f'{label} introuvable : {path}')
        if not (Path(s['pack']) / 'native_experts.txt').is_file():
            raise ValueError('Le pack ne contient pas native_experts.txt.')
        if not (Path(s['tokenizer']) / 'vocab.json').is_file():
            raise ValueError('Le tokenizer ne contient pas vocab.json.')
        if not PYTHON.is_file():
            raise ValueError('Le Python de Strata est introuvable.')
    return s

def build_config(base, settings, log_path=None):
    s = validate(settings)
    cfg = copy.deepcopy(base)
    args = list(cfg['args'])
    def set_arg(flag, value):
        if flag in args:
            i = args.index(flag)
            args[i + 1] = str(value)
        else:
            args.extend([flag, str(value)])
    for flag, name in [('--pack', 'pack'), ('--native', 'native'), ('--expert-profile', 'expert_profile'),
                       ('--max-context', 'context'), ('--pool-workers', 'workers'), ('--prefill', 'prefill'),
                       ('--vram-reserve-mib', 'vram_reserve'), ('--expert-cache', 'expert_cache'),
                       ('--layer-split', 'layer_split'), ('--short-read', 'short_read'),
                       ('--prompt-cache-every', 'history_every'), ('--spec-min-p', 'spec_min_p')]:
        set_arg(flag, s[name])
    set_arg('--prompt-cache', s['history_slots'] if s['history_enabled'] else 0)
    set_arg('--spec', s['spec'] if s['mtp_enabled'] else 1)
    if s['mtp_enabled']:
        set_arg('--mtp', s['mtp_path'])
    elif '--mtp' in args:
        i = args.index('--mtp')
        del args[i:i + 2]
    cfg.update(args=args, exe=s['exe'], tokenizer=s['tokenizer'], model_name=s['model_name'],
               host=s['host'], port=s['port'], api_key=s['api_key'],
               cors_origins=origins(s['cors_origins'], True), trusted_origins=origins(s['trusted_origins']),
               fit_max_tokens=s['fit_max_tokens'])
    cfg.setdefault('env', {})['CUDA_VISIBLE_DEVICES'] = s['gpus']
    if log_path:
        cfg['log'] = str(log_path).replace('\\', '/')
    return cfg

def health(host='127.0.0.1', port=8080, timeout=1):
    if host == '0.0.0.0':
        host = '127.0.0.1'
    try:
        # Local health checks must not inherit an HTTP proxy.
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(f'http://{host}:{port}/health', timeout=timeout) as response:
            return json.load(response)
    except (OSError, ValueError):
        return {}

def process_identity(process):
    return {'pid': process.pid, 'created': process.create_time()}

def same_process(identity):
    try:
        process = psutil.Process(int(identity['pid']))
        return process if abs(process.create_time() - float(identity['created'])) < .01 and process.is_running() else None
    except (KeyError, ValueError, psutil.Error):
        return None

def matching_servers(config_paths):
    paths = {os.path.normcase(str(Path(path).resolve())) for path in config_paths}
    found = []
    for process in psutil.process_iter(['pid', 'name']):
        try:
            if (process.info['name'] or '').lower() not in ('python.exe','pythonw.exe'):continue
            cmd = process.cmdline()
            if 'serve.server' not in cmd or '--config' not in cmd:continue
            config_path = cmd[cmd.index('--config') + 1]
            if os.path.normcase(str(Path(config_path).resolve())) in paths:
                found.append(process)
        except (psutil.Error, ValueError, IndexError):
            pass
    return found

def stop_processes(processes):
    """Only explicit identities and their descendants; never kill by executable name."""
    victims = {}
    for process in processes:
        try:
            for child in process.children(recursive=True):
                victims[child.pid] = child
            victims[process.pid] = process
        except psutil.Error:
            pass
    identities = [process_identity(p) for p in victims.values() if p.pid != os.getpid()]
    alive = []
    for identity in reversed(identities):
        process = same_process(identity)
        if process:
            try:
                process.terminate()
                alive.append(process)
            except psutil.NoSuchProcess:
                pass
    _, still_alive = psutil.wait_procs(alive, timeout=12)
    if still_alive:
        raise RuntimeError('Windows libère encore les processus du modèle. Attendre avant de relancer.')

def available_port(host, port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        if os.name == 'nt':
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        probe.bind((host, port))

def tail(path, limit=18000):
    try:
        with open(path, 'rb') as stream:
            stream.seek(0, 2)
            length = stream.tell()
            stream.seek(max(0, length - limit))
            return stream.read().decode('utf-8', errors='replace')
    except OSError:
        return ''
