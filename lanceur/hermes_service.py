"""Supervise only the Fred Hermes gateway and adapt its native, profile-scoped API."""
from __future__ import annotations

import atexit
import hashlib
import http.client
import json
import os
from pathlib import Path
import socket
import subprocess
import threading
import time
from urllib.parse import quote, urlsplit

import psutil

from core import HIDDEN, read_json, write_json
from hermes_accounts import CONFIG_VERSION
from hermes_codex_compat import PATCH_SOURCE as CODEX_PATCH
from hermes_web import gateway_bootstrap

GATEWAY_BOOTSTRAP = gateway_bootstrap(CODEX_PATCH)


def installation(source=None):
    directory = Path(source) if source else Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'hermes/hermes-agent'
    # Resolve the installed committed dependency generation without importing PM
    # under Fred's different home (which would otherwise try to install it anew).
    install_home = directory.parent
    install_key = hashlib.sha256(str(directory.resolve()).encode()).hexdigest()[:16]
    state = install_home / 'installs' / install_key
    facts = json.loads((state / 'facts.json').read_text(encoding='utf-8-sig'))
    environment = Path(facts['packages']['venv']['environment']).resolve()
    if not environment.is_relative_to((state / 'environments').resolve()):
        raise ValueError('Le runtime Hermes installé est incohérent.')
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.is_file() or not (directory / 'hermes_cli/main.py').is_file():
        raise ValueError('Installation Hermes utilisable introuvable.')
    version = subprocess.run(['git', '-C', str(directory), 'rev-parse', 'HEAD'], capture_output=True,
                             text=True, timeout=10, creationflags=HIDDEN)
    commit = version.stdout.strip() if version.returncode == 0 else ''
    return {'source': directory, 'python': python, 'commit': commit,
            'dependencies': install_home / 'installs', 'tools': install_home / 'tools'}


def prepare_runtime(root, runtime):
    """Reuse package state, not personal agent state; the junction is excluded from backups."""
    link = root / 'installs'
    target = runtime['dependencies'].resolve()
    if link.exists():
        if link.resolve() != target:
            raise ValueError('Le répertoire de dépendances Hermes Fred est incohérent.')
        return
    if os.name == 'nt':
        env = os.environ.copy()
        env.update(FRED_HERMES_LINK=str(link), FRED_HERMES_TARGET=str(target))
        result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                "New-Item -ItemType Junction -Path $env:FRED_HERMES_LINK -Target $env:FRED_HERMES_TARGET -ErrorAction Stop | Out-Null"],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15, creationflags=HIDDEN)
        if result.returncode:
            raise ValueError('Impossible de réutiliser le runtime Hermes installé.')
    else:
        link.symlink_to(target, target_is_directory=True)


def child_environment(root, runtime=None):
    # Keep OS/tool discovery variables, never shell credentials, personal Hermes selectors or proxies.
    allowed = {'SYSTEMROOT', 'WINDIR', 'COMSPEC', 'PATHEXT', 'PATH', 'TEMP', 'TMP', 'LOCALAPPDATA',
               'APPDATA', 'USERPROFILE', 'HOME', 'HOMEDRIVE', 'HOMEPATH', 'PROGRAMFILES', 'PROGRAMFILES(X86)',
               'PROGRAMDATA', 'NUMBER_OF_PROCESSORS', 'PROCESSOR_ARCHITECTURE'}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    env.update(HERMES_HOME=str(root), PYTHONUTF8='1', PYTHONIOENCODING='utf-8',
               HERMES_DISABLE_LAZY_INSTALLS='1',
               NO_PROXY='127.0.0.1,localhost,::1', no_proxy='127.0.0.1,localhost,::1')
    if runtime:
        env['HERMES_RUNTIME_DIR'] = str(runtime['tools'])
    return env


_CREATE_PROFILE = '''
import json, os, sys, tempfile
from pathlib import Path
from hermes_cli import profiles
from hermes_cli.config import atomic_config_replace
data=json.load(sys.stdin)
notify=profiles._notify_multiplexer
profiles._notify_multiplexer=lambda *a,**k: None
directory=profiles.get_profile_dir(data['profile'])
expected=Path(data['root']).resolve()/'profiles'
if directory.parent.exists() and directory.parent.resolve()!=expected:
    raise ValueError('invalid profiles directory')
if not directory.exists():
    directory=profiles.create_profile(data['profile'], no_alias=True, no_skills=True)
elif directory.is_symlink() or directory.resolve().parent!=expected:
    raise ValueError('invalid profile directory')
atomic_config_replace(directory/'config.yaml',data['config'])
descriptor,name=tempfile.mkstemp(prefix='.fred-env-',suffix='.tmp',dir=directory)
tmp=Path(name)
try:
    with os.fdopen(descriptor,'w',encoding='utf-8',newline='\\n') as stream:
        stream.write(data['env'])
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(directory/'.env')
finally:
    tmp.unlink(missing_ok=True)
notify(data['profile'])
'''


def create_native_profile(accounts, owner, port=8643, source=None):
    runtime = installation(source)
    prepare_runtime(accounts.root, runtime)
    credentials = accounts.credentials(owner)
    payload = {'profile': credentials['profile'], 'root': str(accounts.root.resolve()),
               'config': accounts.config(owner, port),
               'env': ''.join(f'{key}={value}\n' for key, value in {
                   'API_SERVER_KEY': credentials['api_key'], 'FRED_INFERENCE_KEY': credentials['inference_key'],
                   'FRED_TOOL_KEY': credentials['tool_key'], 'FRED_WEB_URL': accounts.mcp_url}.items())}
    result = subprocess.run([str(runtime['python']), '-c', _CREATE_PROFILE], input=json.dumps(payload).encode(),
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, cwd=runtime['source'],
                            env=child_environment(accounts.root, runtime), timeout=60, creationflags=HIDDEN)
    if result.returncode:
        raise ValueError('Hermes ne peut pas créer ce profil isolé.')


class _Response:
    def __init__(self, response, connection):
        self._response, self._connection = response, connection
    def __getattr__(self, name):
        return getattr(self._response, name)
    def close(self):
        self._response.close()
        self._connection.close()
    def __enter__(self):
        return self
    def __exit__(self, *args):
        self.close()


class HermesService:
    def __init__(self, accounts, port=8643, *, source=None, startup_timeout=60, supervise=True):
        self.accounts = accounts
        self.root = accounts.root
        if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
            raise ValueError('Port Hermes invalide.')
        if port == 0:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
        self.port = port
        self.source = source
        self.startup_timeout = startup_timeout
        self.supervise = supervise
        self.process = None
        self.runtime = None
        self.lock = threading.RLock()
        self.stopping = threading.Event()
        self.watcher = None
        self.error = ''
        self.restarts = 0
        self.ready = False
        self.owned = []
        atexit.register(self.close)

    @property
    def url(self):
        return f'http://127.0.0.1:{self.port}'

    def _prepare(self):
        self.runtime = installation(self.source)
        prepare_runtime(self.root, self.runtime)
        write_json(self.root / 'config.yaml', self.accounts.config(port=self.port))
        self.accounts._write_env(self.root, {'API_SERVER_KEY': self.accounts.gateway_key()})
        for owner in self.accounts.owners(ready_only=True):
            self.accounts.materialize(owner, self.port)
        write_json(self.root / 'fred-runtime.json', {'source_commit': self.runtime['commit'],
                   'config_version': CONFIG_VERSION, 'port': self.port, 'validated': False})

    def _launch(self):
        self._prepare()
        log_dir = self.root / 'logs'
        log_dir.mkdir(exist_ok=True)
        with (log_dir / 'fred-gateway.log').open('ab') as log:
            self.process = subprocess.Popen([str(self.runtime['python']), '-c', GATEWAY_BOOTSTRAP,
                    'gateway', 'run', '--external-supervisor'], cwd=self.runtime['source'],
                    stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                    env=child_environment(self.root, self.runtime), creationflags=HIDDEN)
        identity = psutil.Process(self.process.pid)
        self.owned = [{'pid': self.process.pid, 'created': identity.create_time()}]
        self._record_owned()
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline and not self.stopping.is_set():
            if self.process.poll() is not None:
                raise ValueError('La passerelle Hermes ne démarre pas ; consulter son diagnostic local.')
            try:
                result = self._json(None, 'GET', '/v1/capabilities', timeout=2)
                features = result.get('features', {})
                required = ('run_submission', 'run_status', 'run_events_sse', 'run_stop', 'session_resources')
                if any(features.get(name) is not True for name in required):
                    raise ValueError('La version Hermes ne fournit pas les API de runs requises.')
                self.ready = True
                self.error = ''
                self.owned.extend({'pid': child.pid, 'created': child.create_time()}
                                  for child in identity.children(recursive=True))
                self._record_owned()
                write_json(self.root / 'fred-runtime.json', {'source_commit': self.runtime['commit'],
                           'config_version': CONFIG_VERSION, 'port': self.port, 'validated': True})
                return
            except (OSError, http.client.HTTPException, ValueError):
                self.stopping.wait(.2)
        raise ValueError('La passerelle Hermes ne répond pas dans le délai de démarrage.')

    def start(self):
        with self.lock:
            if self.process and self.process.poll() is None and self.ready:
                return self.status()
            self.stopping.clear()
            try:
                self._recover_owned()
                self._launch()
            except Exception:
                self.error = 'Hermes indisponible ; consulter le diagnostic local.'
                self._stop_owned()
                self.accounts.clear_runtime_secrets()
                raise
            if self.supervise and (not self.watcher or not self.watcher.is_alive()):
                self.watcher = threading.Thread(target=self._watch, name='Fred Hermes', daemon=True)
                self.watcher.start()
            return self.status()

    def _watch(self):
        failures = 0
        while not self.stopping.wait(1):
            if self.process and self.process.poll() is None:
                continue
            self.ready = False
            self.error = 'Hermes redémarre après une interruption.'
            if self.stopping.wait(min(30, 2 ** min(failures, 5))):
                return
            with self.lock:
                if self.stopping.is_set():
                    return
                try:
                    self._stop_owned()
                    self._launch()
                    self.restarts += 1
                    failures = 0
                except Exception:
                    failures += 1
                    self._stop_owned()
                    self.error = 'Hermes indisponible ; reprise automatique temporisée.'

    def _record_owned(self):
        write_json(self.root / 'fred-gateway.pid.json', {'home': str(self.root.resolve()),
                   'source_commit': self.runtime['commit'], 'processes': self.owned})

    def _tracked(self, record):
        try:
            process = psutil.Process(record['pid'])
            if process.create_time() != record['created']:
                return None
            home = process.environ().get('HERMES_HOME', '')
            if not home or Path(home).resolve() != self.root.resolve():
                raise ValueError('Identité du processus Hermes Fred incohérente.')
            return process
        except psutil.NoSuchProcess:
            return None

    def _recover_owned(self):
        """A console crash may leave only a native launcher child; never scan unrelated processes."""
        record = read_json(self.root / 'fred-gateway.pid.json', {})
        if not record:
            return
        if record.get('home') != str(self.root.resolve()):
            raise ValueError('Identité de supervision Hermes Fred incohérente.')
        self.owned = record.get('processes', [])
        self._stop_owned()

    def _stop_owned(self):
        self.ready = False
        # Snapshot descendants before terminating a launcher; Windows reparents
        # its interpreter worker immediately when the launcher dies.
        known = list(self.owned)
        for record in list(known):
            process = self._tracked(record)
            if process:
                known.extend({'pid': child.pid, 'created': child.create_time()}
                             for child in process.children(recursive=True))
        records = {record['pid']: record for record in known}
        processes = [process for record in records.values() if (process := self._tracked(record))]
        for process in processes:
            try:
                process.terminate()
            except psutil.NoSuchProcess:
                pass
        alive = psutil.wait_procs(processes, timeout=5)[1]
        for process in alive:
            record = records[process.pid]
            if self._tracked(record):
                try:
                    process.kill()
                except psutil.NoSuchProcess:
                    pass
        psutil.wait_procs(alive, timeout=3)
        if self.process:
            self.process.wait(timeout=3)
        self.process = None
        self.owned = []
        (self.root / 'fred-gateway.pid.json').unlink(missing_ok=True)

    def close(self):
        self.stopping.set()
        with self.lock:
            self._stop_owned()
            self.accounts.clear_runtime_secrets()
        if self.watcher and self.watcher is not threading.current_thread():
            self.watcher.join(timeout=2)

    def status(self):
        available = bool(self.ready and self.process and self.process.poll() is None)
        return {'ready': available, 'available': available,
                'state': 'ready' if available else ('error' if self.error else 'stopped'),
                'error': self.error, 'port': self.port, 'restarts': self.restarts,
                'source_commit': self.runtime['commit'] if self.runtime else '',
                'profiles': len(self.accounts.owners(ready_only=True))}

    def _open(self, owner, method, path, body=None, headers=None, timeout=30):
        parsed = urlsplit(path)
        if parsed.scheme or parsed.netloc or not path.startswith('/') or path.startswith('//') or '\\' in path:
            raise ValueError('Chemin API Hermes invalide.')
        if '/..' in path or '%2e' in path.lower() or '%2f' in path.lower() or '%5c' in path.lower():
            raise ValueError('Chemin API Hermes invalide.')
        if owner is None:
            key = self.accounts.gateway_key()
        else:
            if not self.accounts.enabled(owner):
                raise ValueError('Accès Hermes désactivé ou non provisionné.')
            credentials = self.accounts.credentials(owner)
            path = '/p/' + quote(credentials['profile'], safe='') + path
            key = credentials['api_key']
        allowed_headers = {'Content-Type', 'Accept', 'Idempotency-Key', 'X-Request-ID', 'Last-Event-ID', 'X-Hermes-Session-Key'}
        outgoing = {name: value for name, value in (headers or {}).items() if name in allowed_headers}
        outgoing['Authorization'] = 'Bearer ' + key
        if body is not None:
            body = json.dumps(body).encode('utf-8')
            outgoing['Content-Type'] = 'application/json'
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=timeout)
        try:
            connection.request(method, path, body=body, headers=outgoing)
            return _Response(connection.getresponse(), connection)
        except Exception:
            connection.close()
            raise

    def open(self, owner, method, path, body=None, headers=None, timeout=30):
        return self._open(owner, method, path, body, headers, timeout)

    def _json(self, owner, method, path, body=None, headers=None, timeout=30):
        with self._open(owner, method, path, body, headers, timeout) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
            if response.status >= 400:
                # Never forward an upstream exception which may include provider keys or user content.
                raise ValueError(f'API Hermes indisponible (HTTP {response.status}).')
            if len(raw) > 8 * 1024 * 1024:
                raise ValueError('Réponse API Hermes trop volumineuse.')
            return json.loads(raw) if raw else {}

    def request(self, owner, method, path, body=None, headers=None, timeout=30):
        return self._json(owner, method, path, body, headers, timeout)

    def capabilities(self, owner=None):
        return self._json(owner, 'GET', '/v1/capabilities')
