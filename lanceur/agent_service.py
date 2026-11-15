"""Own the local Agent process and expose it through the Kiara gateway."""

import http.client
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
from tempfile import TemporaryDirectory
from pathlib import Path
from zipfile import BadZipFile

import psutil

from agent_access import AgentAccess
from agent_gateway import AgentBridge
from core import HIDDEN, ROOT, stop_processes, write_json
from kiara_shared.agent_auth import issue
from kiara_shared.agent_workers import validate_groups
from wg_crypto import private_directory

WEB_FIELDS = {'web_origin', 'web_port'}
DOCUMENT_FIELDS = {
    'document_roots': ('AGENT_DOCUMENT_ROOTS', list),
    'document_write_roots': ('AGENT_DOCUMENT_WRITE_ROOTS', list),
    'document_drive_mappings': ('AGENT_DOCUMENT_DRIVE_MAPPINGS', dict),
    'document_project_root': ('AGENT_DOCUMENT_PROJECT_ROOT', str),
}


def _read_configuration(home):
    try:
        with (home / 'agent-service.json').open(encoding='utf-8-sig') as stream:
            values = json.load(stream)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as error:
        raise ValueError('Le fichier agent-service.json est illisible.') from error
    if not isinstance(values, dict):
        raise ValueError('Vérifiez les champs de agent-service.json.')
    return values


def service_configuration(home):
    variables = {'data': 'KIARA_AGENT_DATA_DIR', 'python': 'KIARA_AGENT_PYTHON',
                 'speech_python': 'KIARA_AGENT_SPEECH_PYTHON',
                 'speech_models': 'KIARA_AGENT_SPEECH_MODELS_DIR',
                 'thunderbird_device': 'KIARA_AGENT_THUNDERBIRD_DEVICE',
                 'start_workers': 'KIARA_AGENT_START_WORKERS'}
    values = _read_configuration(home)
    if values is not None and values.keys() - variables.keys() - WEB_FIELDS - DOCUMENT_FIELDS.keys() - {'worker_groups'}:
        raise ValueError('Vérifiez les champs de agent-service.json.')
    file_settings = values or {}
    settings = {key: os.environ.get(variable) or file_settings.get(key) for key, variable in variables.items()}
    workers = settings['start_workers']
    if workers in ('0', '1'):
        settings['start_workers'] = workers == '1'
    elif workers is not None and type(workers) is not bool:
        raise ValueError('start_workers doit être un booléen dans agent-service.json ou 0/1 dans KIARA_AGENT_START_WORKERS.')
    document_settings = {}
    for key, (variable, kind) in DOCUMENT_FIELDS.items():
        override = os.environ.get(variable)
        if override is None and key not in file_settings:
            continue
        try:
            value = json.loads(override) if override is not None else file_settings[key]
            if not isinstance(value, kind):
                raise ValueError
            if key == 'document_project_root' and value and not Path(value).is_absolute():
                raise ValueError
        except ValueError as error:
            raise ValueError(f'Configuration documentaire Agent invalide pour {key} ({variable}).') from error
        document_settings[variable] = json.dumps(value)
    if values is None and not document_settings and all(value is None for value in settings.values()):
        return None
    for key, value in settings.items():
        if key in ('start_workers', 'thunderbird_device'):
            continue
        if value is None and key not in ('data', 'python'):
            continue
        if not isinstance(value, str) or not Path(value).is_absolute():
            raise ValueError(f'Indiquez un chemin absolu pour {key} dans agent-service.json ou {variables[key]}.')
    if document_settings:
        settings['document_settings'] = document_settings
    if 'worker_groups' in file_settings:
        settings['worker_groups'] = validate_groups(file_settings['worker_groups'])
    return settings


def web_configuration(home):
    values = _read_configuration(home) or {}
    origin = os.environ.get('KIARA_AGENT_WEB_ORIGIN', values.get('web_origin'))
    if origin is None or origin == '':
        return None
    if not isinstance(origin, str):
        raise ValueError('Origine HTTPS Agent invalide.')
    from agent_web import validate_origin
    validate_origin(origin)
    port = os.environ.get('KIARA_AGENT_WEB_PORT', values.get('web_port', 8767))
    if isinstance(port, str) and port.isascii() and port.isdecimal():
        port = int(port)
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError('Port local du web Agent invalide.')
    return origin, port


class AgentService:
    def __init__(self, store, data, python, *, inference_port=None, speech_python=None, speech_models=None,
                 start_workers=None, thunderbird_device=None,
                 document_settings=None, worker_groups=None):
        self.store = store
        self.data = Path(data).resolve()
        self.python = Path(python).resolve()
        if inference_port is not None and (type(inference_port) is not int or not 1 <= inference_port <= 65535):
            raise ValueError('Port d’inférence Agent invalide')
        self.inference_port = inference_port
        self.speech_python = speech_python or os.environ.get('KIARA_AGENT_SPEECH_PYTHON')
        self.speech_models = speech_models or os.environ.get('KIARA_AGENT_SPEECH_MODELS_DIR')
        self.start_workers = start_workers is not False
        self.worker_groups = None if worker_groups is None else tuple(validate_groups(worker_groups))
        self.document_settings = document_settings or {}
        self.thunderbird_device = thunderbird_device or os.environ.get('KIARA_AGENT_THUNDERBIRD_DEVICE') or None
        if self.thunderbird_device is not None and (
                not isinstance(self.thunderbird_device, str) or not re.fullmatch('[0-9a-f]{16}', self.thunderbird_device)):
            raise ValueError('Identifiant du poste Thunderbird invalide dans la configuration Agent.')
        self.inference_token = None
        self.access = AgentAccess(store)
        self.lock = threading.RLock()
        self.process = None
        self.startup_error = ''

    def running(self):
        with self.lock:
            return self.process is not None and self.process.poll() is None and self.store.agent_bridge is not None

    @property
    def document_project_root(self):
        return json.loads(self.document_settings.get('AGENT_DOCUMENT_PROJECT_ROOT', '""'))

    def _archive_tool(self, script, *paths):
        env = {name: value for name, value in os.environ.items() if not name.startswith(('PB_', 'AGENT_'))}
        env['PYTHONPATH'] = os.pathsep.join((str(ROOT / 'agent'), str(ROOT / 'shared')))
        try:
            subprocess.run([str(self.python), '-B', '-c', script, *(str(path) for path in paths)], cwd=ROOT / 'agent',
                           env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, creationflags=HIDDEN)
        except subprocess.CalledProcessError as error:
            raise ValueError('La sauvegarde ou restauration native Agent a échoué.') from error

    def backup_archive(self, target, password):
        from agent_archive import extract_archive, write_archive
        target = Path(target).resolve()
        if target.is_relative_to(self.data) or target.exists():
            raise ValueError('Choisissez une nouvelle archive hors du dossier de données Agent.')
        with TemporaryDirectory(prefix='agent-backup-', dir=self.data.parent) as folder:
            stage = Path(folder)
            private_directory(stage)
            snapshot = stage / 'snapshot'
            with self.lock:
                client_root = self.document_project_root
                restart = self.running()
                if restart:
                    self.stop()
                try:
                    self._archive_tool(
                        'from pathlib import Path; import sys; from app.services.backup import create_backup; '
                        'out, data, *roots = map(Path, sys.argv[1:]); '
                        'create_backup(out, data / "brain/project_brain.db", data / "erp", data / "storage", '
                        'client_root=roots[0] if roots else None)',
                        snapshot, self.data, *([client_root] if client_root else []))
                finally:
                    if restart:
                        self.start()
            with TemporaryDirectory(prefix='.agent-verification-', dir=target.parent) as folder:
                pending = Path(folder) / 'archive'
                write_archive(snapshot, pending, password)
                check = stage / 'verified'
                check.mkdir()
                extract_archive(pending, check, password)
                self._archive_tool('from pathlib import Path; import sys; from app.services.backup import verify_backup; '
                                   'verify_backup(Path(sys.argv[1]))', check)
                pending.rename(target)
        return target

    def restore_archive(self, source, parent, password):
        from agent_archive import extract_archive
        parent = Path(parent).resolve(strict=True)
        if parent.is_relative_to(self.data):
            raise ValueError('Choisissez un dossier hors des données Agent actives.')
        with TemporaryDirectory(prefix='agent-restore-', dir=parent) as folder:
            stage = Path(folder)
            private_directory(stage)
            snapshot = stage / 'snapshot'
            snapshot.mkdir()
            try:
                extract_archive(source, snapshot, password)
            except BadZipFile as error:
                raise ValueError('Le contenu de la sauvegarde Agent est illisible.') from error
            recovery = parent / ('agent-restaure-' + secrets.token_hex(8))
            recovery.mkdir()
            destination = recovery / 'data'
            try:
                private_directory(recovery)
                # The native restore records the final absolute path in SQLite.
                self._archive_tool('from pathlib import Path; import sys; from app.services.backup import restore_backup; '
                                   'restore_backup(*map(Path, sys.argv[1:]))', snapshot, destination)
            except Exception:
                if recovery.resolve() == recovery and recovery.parent == parent:
                    shutil.rmtree(recovery)
                raise
        return destination

    def set_thunderbird_device(self, identity):
        if identity is not None and (not isinstance(identity, str) or not re.fullmatch('[0-9a-f]{16}', identity)):
            raise ValueError('Choisissez un poste Kiara actif.')
        with self.lock, self.store.lock:
            if os.environ.get('KIARA_AGENT_THUNDERBIRD_DEVICE'):
                raise ValueError('Le poste Thunderbird est défini dans la configuration de démarrage.')
            if identity is not None:
                operator = self.access.operator_for(identity)
                if not operator or operator['role'] == 'reader':
                    raise ValueError('Ce poste doit avoir un accès Agent avec droit de modification.')
            home = self.store.home
            settings = _read_configuration(home) or {}
            if identity is None:
                settings.pop('thunderbird_device', None)
            else:
                settings['thunderbird_device'] = identity
            write_json(home / 'agent-service.json', settings)
            self.thunderbird_device = identity
            if self.store.agent_bridge is not None:
                self.store.agent_bridge.thunderbird_device = identity

    def enable_meetings(self):
        """Enable the meeting workspace from the local launcher administration."""
        with self.lock:
            if not self.running():
                raise ValueError('Démarrez Agent avant d’activer les réunions.')
            bridge = self.store.agent_bridge
            operator = {'id': 'kiara-service', 'role': 'owner', 'project_ids': None, 'person_id': None}
            path = '/api/v1/workspace/fusion-settings'
            current = self._admin_request(bridge, operator, path, 'GET')
            if current.get('enabled') is True:
                return
            keys = ('live_transcription_enabled', 'proactive_enabled', 'auto_enhancement_enabled',
                    'mode', 'onboarding_complete')
            if any(key not in current for key in keys):
                raise ValueError('Les réglages Réunions reçus sont incomplets.')
            body = {'enabled': True, **{key: current[key] for key in keys}}
            result = self._admin_request(bridge, operator, path, 'PUT', body)
            if result.get('enabled') is not True:
                raise ValueError('Agent n’a pas activé les réunions. Vérifiez la configuration du service.')

    def link_project_knowledge(self, project_id):
        if not isinstance(project_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', project_id):
            raise ValueError('Choisissez un projet Agent.')
        with self.lock:
            if not self.running():
                raise ValueError('Demarrez Agent avant de relier un projet.')
            bridge = self.store.agent_bridge
            operator = {'id': 'kiara-service', 'role': 'owner', 'project_ids': None, 'person_id': None}
            path = f'/api/v1/projects/{project_id}/brain/ensure'
            result = self._admin_request(bridge, operator, path, 'POST')
            if result.get('linked') is not True or not result.get('brain_project_id'):
                raise ValueError('Agent ne confirme pas la liaison du projet.')

    def _admin_request(self, bridge, operator, path, method, body=None):
        connection = http.client.HTTPConnection('127.0.0.1', bridge.port, timeout=20)
        try:
            headers = {'X-Kiara-Agent-Context': issue(bridge.key, method, path, operator)}
            if body is not None:
                headers['Content-Type'] = 'application/json'
                body = json.dumps(body).encode()
            connection.request(method, path, body, headers)
            response = connection.getresponse()
            limit = 128 * 1024
            raw = response.read(limit + 1)
            if len(raw) > limit:
                raise ValueError('La réponse d’Agent est trop volumineuse.')
            payload = json.loads(raw)
            if not isinstance(payload, dict):
                raise ValueError('La réponse d’Agent est invalide.')
            if response.status != 200:
                detail = payload.get('detail')
                raise ValueError(detail if isinstance(detail, str) else 'Agent a refusé la commande.')
            return payload
        except (OSError, http.client.HTTPException, json.JSONDecodeError) as error:
            raise ValueError('Agent ne répond pas correctement.') from error
        finally:
            connection.close()

    def management_data(self):
        with self.lock:
            if not self.running():
                raise ValueError('Le service Agent est indisponible.')
            bridge = self.store.agent_bridge
            operator = {'id': 'kiara-service', 'role': 'owner', 'project_ids': None, 'person_id': None}
            results = []
            for path in ('/api/v1/project-catalogue', '/internal/kiara/personal-sessions'):
                connection = http.client.HTTPConnection('127.0.0.1', bridge.port, timeout=10)
                try:
                    connection.request('GET', path, headers={'X-Kiara-Agent-Context': issue(bridge.key, 'GET', path, operator)})
                    response = connection.getresponse()
                    payload = response.read(4 * 1024 * 1024 + 1)
                    if response.status != 200 or len(payload) > 4 * 1024 * 1024:
                        raise ValueError('Lecture du catalogue Agent impossible.')
                    results.append(json.loads(payload))
                except (OSError, http.client.HTTPException, json.JSONDecodeError) as error:
                    raise ValueError('Lecture du catalogue Agent impossible.') from error
                finally:
                    connection.close()
            projects, sessions = results
            if not isinstance(projects, list) or not isinstance(sessions, dict) or not isinstance(sessions.get('sessions'), list):
                raise ValueError('Réponse du catalogue Agent invalide.')
            return {'projects': [{'id': row['id'], 'code': row['code'], 'title': row['title'], 'status': row['status'],
                                  'knowledge_linked': bool(row.get('brain_project_id'))}
                                 for row in projects], 'sessions': sessions['sessions'],
                    'sessions_truncated': bool(sessions.get('sessions_truncated'))}

    def start(self):
        with self.lock:
            try:
                self._start()
            except (OSError, ValueError, RuntimeError) as error:
                self.startup_error = (str(error) if isinstance(error, (ValueError, RuntimeError))
                                      else 'Agent ne peut pas démarrer. Vérifiez les droits du dossier de données et du runtime.')
                raise
            self.startup_error = ''

    def preflight(self):
        """Validate the configured service files without starting Agent."""
        for path, label in ((self.python, 'Python d’Agent'),
                            (self.data / 'brain/project_brain.db', 'base Brain'),
                            (self.data / 'erp/minipilot.db', 'base MiniPilot')):
            if not path.is_file():
                raise ValueError(f'Agent ne trouve pas {label}. Vérifiez agent-service.json.')
        if not (self.data / 'storage').is_dir():
            raise ValueError('Stockage Agent introuvable')
        if self.document_project_root:
            root = Path(self.document_project_root)
            try:
                if not root.is_dir() or root.resolve(strict=True) != root:
                    raise ValueError('Le dossier client Agent est introuvable ou redirigé.')
            except (OSError, RuntimeError) as error:
                raise ValueError('Le dossier client Agent est inaccessible.') from error
            for setting in ('AGENT_DOCUMENT_ROOTS', 'AGENT_DOCUMENT_WRITE_ROOTS'):
                for value in json.loads(self.document_settings.get(setting, '[]')):
                    shared = Path(value).resolve()
                    if root.is_relative_to(shared) or shared.is_relative_to(root):
                        raise ValueError('Les racines partagées doivent être distinctes du dossier client Agent.')
        env = {}
        speech = self.speech_python
        if speech:
            speech_python = Path(speech).resolve()
            if not speech_python.is_file():
                raise ValueError('Runtime audio Agent introuvable')
            env['PB_SPEECH_PYTHON'] = str(speech_python)
        if self.speech_models:
            models = Path(self.speech_models).resolve()
            if not (models / 'models.json').is_file():
                raise ValueError('Configuration des modèles audio Agent introuvable.')
            env['PB_SPEECH_MODELS_DIR'] = str(models)
        return env

    def _start(self):
        with self.lock:
            if self.process is not None and self.process.poll() is None:
                return
            runtime_env = self.preflight()
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
            key = secrets.token_bytes(32)
            env = {name: value for name, value in os.environ.items()
                   if not name.startswith(('PB_', 'AGENT_'))}
            env.update(self.document_settings)
            env.update(PB_STORAGE_DIR=str(self.data / 'storage'),
                       MINIPILOT_HOME=str(self.data / 'erp'),
                       PB_DATABASE_URL='sqlite:///' + (self.data / 'brain/project_brain.db').as_posix(),
                       AGENT_KIARA_KEY=key.hex(),
                       AGENT_KIARA_PARENT_PIPE='1',
                       PYTHONPATH=os.pathsep.join((str(ROOT / 'agent'), str(ROOT / 'shared'))))
            env['AGENT_DOCUMENT_JOBS_ENABLED'] = '1'
            if not self.start_workers:
                env['AGENT_START_WORKERS'] = '0'
            if self.worker_groups is not None:
                env['AGENT_WORKER_GROUPS'] = json.dumps(self.worker_groups)
            inference_token = None
            if self.inference_port is not None:
                inference_token = 'kiara-agent-' + secrets.token_urlsafe(32)
                env['PB_API_KEY'] = inference_token
                env['AGENT_KIARA_INFERENCE_URL'] = f'http://127.0.0.1:{self.inference_port}'
            env.update(runtime_env)
            directory = self.data / 'logs'
            private_directory(directory)
            log = directory / 'service.log'
            if log.exists() and log.stat().st_size >= 4 * 1024 * 1024:
                log.replace(directory / 'service-previous.log')
            with log.open('ab') as stream:
                process = subprocess.Popen([str(self.python), '-m', 'uvicorn', 'app.main:app',
                                            '--host', '127.0.0.1', '--port', str(port), '--no-access-log'],
                                           cwd=ROOT / 'agent', env=env, stdin=subprocess.PIPE,
                                           stdout=stream, stderr=subprocess.STDOUT, creationflags=HIDDEN)
            self.process = process
            if inference_token:
                with self.store.lock:
                    self.store.agent_inference_token = inference_token
                    self.inference_token = inference_token
            operator = {'id': 'kiara-service', 'role': 'owner', 'project_ids': None, 'person_id': None}
            # Imports and migrations can take longer on a busy server; do not
            # kill a healthy process just as its health endpoint becomes ready.
            deadline = time.monotonic() + 60
            while time.monotonic() < deadline and process.poll() is None:
                connection = http.client.HTTPConnection('127.0.0.1', port, timeout=1)
                try:
                    token = issue(key, 'GET', '/health', operator)
                    connection.request('GET', '/health', headers={'X-Kiara-Agent-Context': token})
                    response = connection.getresponse()
                    data = json.loads(response.read())
                    if response.status == 200 and data.get('service') == 'agent' and data.get('status') == 'ok':
                        self.store.agent_bridge = AgentBridge(port, key, self.access.operator_for, self.thunderbird_device)
                        threading.Thread(target=self._watch, args=(process,), daemon=True,
                                         name='kiara-agent-watch').start()
                        return
                except (OSError, ValueError, http.client.HTTPException):
                    pass
                finally:
                    connection.close()
                time.sleep(.2)
            self.stop()
            raise RuntimeError('Le service Agent ne répond pas au contrôle de santé')

    def _watch(self, process):
        """Remove the bridge and inference credential when this child exits."""
        process.wait()
        with self.lock:
            if getattr(process, 'stdin', None) is not None:
                process.stdin.close()
            if self.process is not process:
                return
            self.store.agent_bridge = None
            with self.store.lock:
                if self.inference_token and self.store.agent_inference_token == self.inference_token:
                    self.store.agent_inference_token = None
                self.inference_token = None
            self.process = None

    def stop(self):
        with self.lock:
            self.store.agent_bridge = None
            with self.store.lock:
                if self.inference_token and self.store.agent_inference_token == self.inference_token:
                    self.store.agent_inference_token = None
                self.inference_token = None
            if self.process is None:
                return
            if self.process.poll() is None:
                # A Windows venv may start the interpreter as a child of
                # python.exe. Stop that child before taking the snapshot.
                try:
                    stop_processes([psutil.Process(self.process.pid)])
                except psutil.NoSuchProcess:
                    pass
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=10)
            if self.process.stdin is not None:
                self.process.stdin.close()
            self.process = None
