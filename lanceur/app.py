"""Local browser control panel. Does not load or change the running model on startup."""
from __future__ import annotations
import argparse
import datetime as dt
import hmac
from http.server import BaseHTTPRequestHandler
import json
from pathlib import Path
import secrets
import socket
import subprocess
import threading
import time
from urllib.parse import urlsplit, quote, parse_qs
import psutil
from core import ROOT, HOME, BASE_PATH, PYTHON, HIDDEN, read_json, write_json, defaults_from_config, validate, build_config, health, matching_servers, process_identity, same_process, stop_processes, available_port, tail, arg
from operations import Operations, VERSION as VERSION
from releases import status as release_status, repackage, rollback, download_name
from remote import AccessStore, GATEWAY_PORT, serve_gateway
from wireguard_access import WireGuardAccess,firewall
from http_boundary import json_body
from local_access import LocalUserHTTPServer

class Controller:
    def __init__(self, home=HOME, include_legacy=True):
        self.home = Path(home)
        self.include_legacy = include_legacy
        self.home.mkdir(parents=True, exist_ok=True)
        from restoration import recover
        recover(self.home)
        self.base_path = self.home / 'base-strata.json'
        if not self.base_path.exists():
            write_json(self.base_path, read_json(BASE_PATH))
        self.base = read_json(self.base_path)
        self.defaults_path = self.home / 'reglages-par-defaut.json'
        if not self.defaults_path.exists():
            write_json(self.defaults_path, defaults_from_config(self.base))
        self.settings_path = self.home / 'reglages.json'
        if not self.settings_path.exists():
            write_json(self.settings_path, self.defaults())
        self.pointer = self.home / 'session.json'
        self.lock = threading.RLock()
        self.gpu_cache = (0, [])
        self.process_cache = (0, [])
        self.disk_before = (time.monotonic(), psutil.disk_io_counters(perdisk=True))
        self.last_error = ''
        self.remote = AccessStore(self.home)
        self.voice = self.remote.voice
        from embeddings import EmbeddingService
        from knowledge import Knowledge
        self.embeddings = EmbeddingService(self.remote.workspace)
        self.remote.workspace.knowledge = Knowledge(self.remote.workspace,self.embeddings)
        from client_storage import ClientStorage
        self.client_storage = ClientStorage(self.remote)
        self.remote.storage = self.client_storage
        self.wireguard = WireGuardAccess(self.remote,self.home)
        self.gateway = None
        self.operations = Operations(self)
        self.hermes = None
        from hermes_fred import configured
        agent_config = configured(self.home)
        if agent_config:
            from hermes_fred import HermesFred
            self.hermes=HermesFred(self.remote,self.remote_backend,port=agent_config.get('port',8643),private_port=agent_config.get('private_port',8768))
            self.remote.hermes=self.hermes
            self.remote.workspace.hermes=self.hermes

    def remote_backend(self):
        run = self.current_run()
        cfg = read_json(run.get('config_path', ''), {}) or read_json(BASE_PATH, self.base)
        for process in self.processes(cached=True):
            try:
                cmd=process.cmdline()
                live=read_json(cmd[cmd.index('--config')+1],{})
                if live:
                    cfg=live;break
            except (psutil.Error,ValueError,IndexError):pass
        return int(cfg.get('port', 8080)), cfg.get('model_name', 'qwen3.8-flash-next'), cfg.get('api_key', '')

    def remote_state(self):
        values = self.remote.metadata()
        values.update(gateway_port=GATEWAY_PORT,
                      gateway_available=self.gateway is not None,
                      client_compiled=(ROOT / 'client-qwen/dist/Accès serveur Fred.exe').is_file())
        values['connection'] = self.wireguard.status()
        values['online_clients'] = sum(time.time()-epoch < 45 for epoch in values['last_connections'].values())
        return values

    def settings(self):
        return read_json(self.settings_path, self.defaults())

    def defaults(self):
        return read_json(self.defaults_path, defaults_from_config(self.base))

    def save(self, settings, as_default=False):
        settings = validate(settings)
        with self.lock:
            write_json(self.settings_path, settings)
            if as_default:
                write_json(self.defaults_path, settings)
        return settings

    def current_run(self):
        pointer = read_json(self.pointer, {})
        directory = pointer.get('directory')
        return read_json(Path(directory) / 'state.json', {}) if directory else {}

    def supervisor(self, run):
        # The child may not have written state.json yet. The pointer is recorded
        # before releasing the start lock, so a second request cannot load twice.
        worker = read_json(self.pointer, {}).get('worker', {})
        return same_process(run.get('supervisor', {})) or same_process(worker)

    def processes(self,cached=False):
        if cached and time.monotonic()-self.process_cache[0]<5:return list(self.process_cache[1])
        run = self.current_run()
        paths = [BASE_PATH] if self.include_legacy else []
        if self.include_legacy:
            # Recognize another Strata profile on this console's port, without
            # claiming servers on other ports or changing the next-load profile.
            port=self.settings()['port']
            paths.extend(path for path in ROOT.glob('strata-*.json') if read_json(path,{}).get('port')==port)
        if run.get('config_path'):
            paths.append(run['config_path'])
        values=matching_servers(paths)
        self.process_cache=(time.monotonic(),values)
        return values

    def start(self, settings):
        with self.lock:
            if self.remote.maintenance:raise ValueError('Serveur en maintenance : lancement suspendu.')
            s = validate(settings, check_paths=True)
            run = self.current_run()
            if self.processes() or self.supervisor(run):
                raise ValueError('Un serveur Qwen est déjà lancé. Arrêtez-le avant un nouveau chargement.')
            available_port(s['host'], s['port'])
            free = psutil.virtual_memory().available / 2**30
            if free < s['min_free_ram_gib']:
                raise ValueError('La RAM disponible est inférieure à la marge de lancement.')
            directory = self.home / 'sessions' / dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            directory.mkdir(parents=True)
            cfg = build_config(self.base, s, directory / 'engine.log')
            config_path = directory / 'strata.json'
            write_json(config_path, cfg)
            self.save(s)
            write_json(directory / 'state.json', {'status': 'chargement', 'started_epoch': time.time(),
                       'config_path': str(config_path), 'host': s['host'], 'port': s['port']})
            write_json(self.pointer, {'directory': str(directory)})
            with (directory / 'supervisor.log').open('wb') as stream:
                worker = subprocess.Popen([str(PYTHON), '-u', str(HOME / 'runtime.py'),
                         '--config', str(config_path), '--run-dir', str(directory),
                         '--floor', str(s['min_free_ram_gib'])], cwd=ROOT,
                         stdout=stream, stderr=stream,
                         creationflags=HIDDEN | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
            write_json(self.pointer, {'directory': str(directory), 'worker': process_identity(psutil.Process(worker.pid))})
            self.last_error = ''
            self.operations.desired = True
            return {'status': 'chargement', 'worker_pid': worker.pid}

    def stop(self):
        self.operations.desired = False
        with self.lock:
            run = self.current_run()
            processes = self.processes()
            supervisor = self.supervisor(run)
            if supervisor:
                processes.append(supervisor)
            # The previous PowerShell launcher can still be waiting for health.
            try:
                warmup_pid = int((ROOT / 'strata-warmup.pid').read_text().strip())
                warmup = psutil.Process(warmup_pid)
                if self.include_legacy and any('Warmup-Strata-P100.ps1' in part for part in warmup.cmdline()):
                    processes.append(warmup)
            except (OSError, ValueError, psutil.Error):
                pass
            if processes:
                stop_processes(processes)
            if run.get('config_path'):
                run.update(status='arrete', stopped_epoch=time.time())
                write_json(Path(run['config_path']).parent / 'state.json', run)
            self.last_error = ''
            return {'status': 'arrete'}

    def gpu_stats(self):
        if time.monotonic() - self.gpu_cache[0] < 12:
            return self.gpu_cache[1]
        values = []
        try:
            output = subprocess.run(['nvidia-smi', '--query-gpu=name,uuid,memory.used,memory.total,utilization.gpu,temperature.gpu',
                                     '--format=csv,noheader,nounits'], capture_output=True, text=True,
                                     timeout=4, creationflags=HIDDEN)
            for line in output.stdout.splitlines():
                name, uuid, used, total, utilization, temperature = [part.strip() for part in line.split(',')]
                values.append({'name': name, 'uuid': uuid, 'used_mib': int(used), 'total_mib': int(total),
                               'utilization': int(utilization), 'temperature': int(temperature), 'selected_by_default': 'P100' in name})
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        self.gpu_cache = (time.monotonic(), values)
        return values

    def state(self):
        run = self.current_run()
        servers = self.processes(cached=True)
        active_config = None
        if servers:
            for server in servers:
                try:
                    cmd = server.cmdline()
                    active_config = read_json(cmd[cmd.index('--config') + 1])
                    for child in server.children(recursive=True):
                        if child.name().lower() == 'strata.exe':
                            active_config['args'] = child.cmdline()[1:]
                            break
                    break
                except (psutil.Error, ValueError, IndexError):
                    pass
        cfg = active_config or read_json(run.get('config_path', ''), {}) or self.base
        live = health(cfg.get('host', '127.0.0.1'), cfg.get('port', 8080)) if servers else {}
        status = run.get('status', 'arrete')
        if servers:
            if live.get('loaded') and status not in ('validation_cuda',):
                status = 'pret'
            elif status not in ('chargement', 'validation_cuda'):
                status = 'chargement'
        elif status not in ('erreur',) and not self.supervisor(run):
            status = 'arrete'
        now = time.monotonic()
        current = psutil.disk_io_counters(perdisk=True)
        seconds = max(now - self.disk_before[0], .01)
        disks = []
        for disk, label in [('PhysicalDrive0', 'C:'), ('PhysicalDrive1', 'D:')]:
            if disk in current and disk in self.disk_before[1]:
                before = self.disk_before[1][disk]
                disks.append({'name': label, 'read_mib_s': round((current[disk].read_bytes - before.read_bytes) / seconds / 2**20, 2),
                              'write_mib_s': round((current[disk].write_bytes - before.write_bytes) / seconds / 2**20, 2)})
        self.disk_before = (now, current)
        memory = psutil.virtual_memory()
        ips = []
        for addresses in psutil.net_if_addrs().values():
            for address in addresses:
                if address.family == socket.AF_INET and not address.address.startswith(('127.', '169.254.')):
                    ips.append(address.address)
        config_host = cfg.get('host', '127.0.0.1')
        local_host = '127.0.0.1' if config_host == '0.0.0.0' else config_host
        directory = Path(run['config_path']).parent if run.get('config_path') else None
        log = cfg.get('log', str(ROOT / 'strata-engine-p100.log'))
        logs = tail(log)
        errors = tail(directory / 'server.stderr.log', 4000) if directory else tail(ROOT / 'strata-server.stderr.log', 4000)
        if errors:
            logs += '\n--- Serveur ---\n' + errors
        elapsed = time.time() - run['started_epoch'] if run.get('started_epoch') and status in ('chargement', 'validation_cuda') else run.get('ready_seconds')
        return {'status': status, 'error': run.get('error', '') if status == 'erreur' else self.last_error,
                'running': bool(servers) or bool(self.supervisor(run)),
                'managed': bool(directory) and bool(servers) and bool(self.supervisor(run)),
                'health': live, 'elapsed_seconds': elapsed,
                'ram': {'total_gib': round(memory.total / 2**30, 1), 'available_gib': round(memory.available / 2**30, 1), 'percent': memory.percent},
                'gpus': self.gpu_stats(), 'disks': disks, 'lan_ips': list(dict.fromkeys(ips)),
                'chat_url': f'http://{local_host}:{cfg.get("port", 8080)}/',
                'api_url': f'http://{local_host}:{cfg.get("port", 8080)}/v1',
                'active': {'context': int(arg(cfg, '--max-context', 4096)), 'workers': int(arg(cfg, '--pool-workers', 15)),
                           'history': int(arg(cfg, '--prompt-cache', 0)), 'mtp': '--mtp' in cfg.get('args', []),
                           'host': config_host, 'port': cfg.get('port', 8080)},
                'logs': logs, 'queue': self.remote.scheduler.snapshot(), 'operations': self.operations.status()}

def serve(port=8765, controller=None):
    controller = controller or Controller()
    token = secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def own_host(self):
            port = self.server.server_address[1]
            return self.headers.get('Host', '') in (f'127.0.0.1:{port}', f'localhost:{port}')

        def respond(self, status, content, content_type='application/json; charset=utf-8'):
            data = json.dumps(content, ensure_ascii=False).encode() if 'application/json' in content_type else content
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self.own_host():
                return self.respond(403, {'error': 'Interface locale uniquement.'})
            path = urlsplit(self.path).path
            if path == '/health':
                return self.respond(200, {'service': 'qwen-launcher'})
            if path == '/api/operations':
                return self.respond(200, controller.operations.status())
            if path == '/api/backups':
                return self.respond(200, controller.operations.backups.status())
            if path == '/api/maintenance':
                return self.respond(200, controller.operations.restorations.status())
            if path == '/api/inventory':
                from server_state import inventory
                return self.respond(200, inventory(controller))
            if path == '/api/devices':
                return self.respond(200, controller.remote.metadata())
            if path == '/api/hermes/models':
                if not hmac.compare_digest(self.headers.get('X-Launcher-Token', ''), token):
                    return self.respond(403, {'error': 'Accès administrateur requis.'})
                if not controller.hermes:
                    return self.respond(200, {'enabled': False, 'providers': [], 'share_all': False, 'shared_accounts': []})
                try:
                    models = controller.hermes.models
                    if parse_qs(urlsplit(self.path).query).get('refresh') == ['1']:
                        models.refresh(force=True)
                    return self.respond(200, {'enabled': True, **models.admin()})
                except (OSError, ValueError, RuntimeError):
                    return self.respond(503, {'error': 'Liste des fournisseurs Hermes indisponible.'})
            if path == '/api/client-storage':
                return self.respond(200, controller.client_storage.status())
            if path.startswith('/api/remote/profile/'):
                if not hmac.compare_digest(self.headers.get('X-Launcher-Token',''),token):
                    return self.respond(403, {'error':'Accès administrateur requis.'})
                identity=path.removeprefix('/api/remote/profile/')
                try:raw=controller.wireguard.android_profile(identity)
                except (ValueError,OSError):return self.respond(404, {'error':'Profil absent, suspendu ou révoqué.'})
                self.send_response(200)
                self.send_header('Content-Type','application/octet-stream')
                self.send_header('Content-Length',str(len(raw)))
                self.send_header('Cache-Control','no-store')
                self.send_header('X-Content-Type-Options','nosniff')
                self.send_header('Content-Disposition','attachment; filename="profil-'+identity+'.fred-android"')
                self.end_headers();self.wfile.write(raw);return
            if path=='/api/workspace':
                return self.respond(200,controller.remote.workspace.admin())
            if path=='/api/knowledge':
                return self.respond(200,{'engine':controller.embeddings.status(),'index':controller.remote.workspace.knowledge.status()})
            if path=='/api/voice':
                return self.respond(200,controller.voice.status())
            if path == '/api/notifications':
                with controller.lock:
                    if controller.remote.maintenance:
                        return self.respond(503, {'error': 'Notifications suspendues pendant la restauration.'})
                    result = controller.remote.notifications.admin()
                return self.respond(200, result)
            if path == '/api/releases':
                return self.respond(200, release_status(controller.home))
            if path == '/api/diagnostic':
                return self.respond(200, controller.operations.diagnostic())
            if path == '/api/audit':
                return self.respond(200, read_json(controller.home / 'audit.json', []))
            if path == '/api/settings':
                return self.respond(200, controller.settings())
            if path == '/api/defaults':
                return self.respond(200, controller.defaults())
            if path == '/api/remote':
                return self.respond(200, controller.remote_state())
            if path.startswith('/api/remote/client/'):
                identity = path.removeprefix('/api/remote/client/')
                if len(identity) != 16 or any(c not in '0123456789abcdef' for c in identity):
                    return self.respond(404, {'error': 'Client inconnu.'})
                record = next((client for client in controller.remote.metadata()['clients'] if client['id'] == identity and not client['revoked']), None)
                target = controller.home / 'clients' / (identity + '.exe')
                if not record or not target.is_file():
                    return self.respond(404, {'error': 'Client absent ou révoqué.'})
                filename=download_name(target,record['name'])
                import unicodedata
                fallback=unicodedata.normalize('NFKD',filename).encode('ascii','ignore').decode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', f'attachment; filename="{fallback}"; filename*=UTF-8\'\'{quote(filename,safe="")}')
                self.send_header('Content-Length', str(target.stat().st_size))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.end_headers()
                with target.open('rb') as stream:
                    while block := stream.read(65536):
                        self.wfile.write(block)
                return
            if path == '/api/state':
                try:
                    return self.respond(200, controller.state())
                except Exception as error:
                    return self.respond(500, {'error': str(error)})
            if path in ('/', '/app.css', '/app.js','/workspace.js','/interface.css','/interface.js','/maintenance.js','/maintenance.css','/notifications.js','/notifications.css','/voice.js'):
                filename = 'index.html' if path == '/' else path[1:]
                data = (HOME / 'web' / filename).read_bytes()
                if filename == 'index.html':
                    data = data.replace(b'__TOKEN__', token.encode())
                content_type = 'text/html; charset=utf-8' if filename=='index.html' else 'text/css; charset=utf-8' if filename.endswith('.css') else 'application/javascript; charset=utf-8'
                return self.respond(200, data, content_type)
            self.respond(404, {'error': 'Page introuvable.'})

        def do_POST(self):
            port = self.server.server_address[1]
            path = urlsplit(self.path).path
            origin = self.headers.get('Origin', '')
            if not self.own_host() or (origin and origin not in (f'http://127.0.0.1:{port}', f'http://localhost:{port}')):
                return self.respond(403, {'error': 'Commande refusée depuis une autre page.'})
            if not hmac.compare_digest(self.headers.get('X-Launcher-Token', ''), token):
                return self.respond(403, {'error': 'Rechargez la page du lanceur.'})
            if not self.headers.get('Content-Type', '').startswith('application/json'):
                return self.respond(415, {'error': 'JSON attendu.'})
            try:
                if getattr(controller.remote,'maintenance',False) and path not in ('/api/backups/verify','/api/backups/recover'):
                    raise ValueError('Serveur en maintenance ; action suspendue.')
                data = json_body(self, 65536, allow_empty=True)
                # Restoration coordinates its own locks and may wait for an
                # active agent to release the provider. Keep the controller
                # available while that worker shuts down.
                if path == '/api/restore':
                    return self.respond(200, controller.operations.restore(data))
                with controller.lock:
                    if getattr(controller.remote,'maintenance',False) and path not in ('/api/backups/verify','/api/backups/recover'):
                        raise ValueError('Serveur en maintenance ; action suspendue.')
                    path = urlsplit(self.path).path
                    if path == '/api/voice':
                        result=controller.voice.configure(data.get('enabled'))
                    elif path == '/api/operations':
                        result = controller.operations.configure(data)
                    elif path == '/api/client-storage':
                        if data.get('action')!='sync':raise ValueError('Commande des dossiers clients inconnue.')
                        result = controller.client_storage.synchronize()
                    elif path == '/api/notifications/action':
                        result = controller.remote.notifications.admin_action(data)
                    elif path=='/api/workspace':
                        with controller.remote.lock:
                            result=controller.remote.workspace.admin_action(data,{c['id'] for c in controller.remote.metadata()['clients']})
                    elif path=='/api/knowledge':
                        action=data.get('action')
                        if action in ('start','stop'):
                            result=controller.embeddings.configure(action=='start')
                            if action=='start':controller.remote.workspace.knowledge.start()
                        elif action=='reindex':
                            controller.remote.workspace.knowledge.reset();result={'saved':True}
                        else:raise ValueError('Commande EG2 inconnue.')
                    elif path=='/api/knowledge/memory':
                        with controller.remote.lock:
                            owner=data.pop('owner',None)
                            if owner not in {c['id'] for c in controller.remote.metadata()['clients'] if not c.get('revoked')}:raise ValueError('Accès personnel inconnu.')
                            if data.get('action')=='list':
                                snapshot=controller.remote.workspace.snapshot(owner)
                                result={'memories':snapshot['personal_memories'],'projects':[{'id':p['id'],'title':p['title']} for p in snapshot['projects'] if not p['archived']]}
                            else:
                                if data.get('action') not in ('personal_memory_create','personal_memory_save','personal_memory_delete','knowledge_search'):raise ValueError('Commande mémoire inconnue.')
                                result=controller.remote.workspace.action(owner,data)
                    elif path == '/api/releases/prepare':
                        with controller.lock,controller.wireguard.lock,controller.remote.lock:result = repackage(controller.home)
                    elif path == '/api/releases/rollback':
                        with controller.lock,controller.wireguard.lock,controller.remote.lock:result = rollback(controller.home)
                    elif path == '/api/startup':
                        result = controller.operations.startup(data.get('enabled'))
                    elif path == '/api/backup':
                        result = controller.operations.backup(data.get('password'))
                    elif path == '/api/backups/configure':
                        result = controller.operations.backups.configure(data)
                    elif path == '/api/backups/create':
                        result = controller.operations.backups.start(data)
                    elif path == '/api/backups/verify':
                        result = controller.operations.restorations.preview(data)
                    elif path == '/api/backups/restore':
                        result = controller.operations.restorations.start(data)
                    elif path == '/api/backups/recover':
                        if data.get('confirm') is not True:raise ValueError('Confirmer le retour à l’état précédent.')
                        result = controller.operations.restorations.recover_now()
                    elif path == '/api/remote/policy':
                        result = controller.wireguard.policy(data)
                    elif path == '/api/devices/configure':
                        result = controller.remote.device(data)
                    elif path == '/api/devices/create':
                        if data.get('platform','android')=='android':
                            result=controller.wireguard.create_android(data.get('name'),controller.remote_backend()[1],data.get('owner',''),data.get('kind','phone'))
                        elif data.get('platform')=='windows':
                            result=controller.wireguard.create_client(data.get('name'),controller.remote_backend()[1])
                            controller.remote.device({'id':result['id'],'kind':'pc','owner':data.get('owner','')})
                        else:raise ValueError('Plateforme attendue : Android ou Windows.')
                    elif path == '/api/devices/replace':
                        result=controller.wireguard.replace(data.get('id'),controller.remote_backend()[1],data.get('platform','android'),data.get('name'),data.get('owner'),data.get('kind'))
                    elif path == '/api/save':
                        result = controller.save(data)
                    elif path == '/api/set-default':
                        result = controller.save(data, True)
                    elif path == '/api/start':
                        result = controller.start(data)
                    elif path == '/api/stop':
                        result = controller.stop()
                    elif path == '/api/key':
                        result = {'api_key': secrets.token_urlsafe(36)}
                    elif path == '/api/remote/configure':
                        result = controller.wireguard.configure(data)
                    elif path == '/api/remote/create-client':
                        result = controller.wireguard.create_client(data.get('name'), controller.remote_backend()[1])
                    elif path == '/api/remote/hermes-retry':
                        if not controller.hermes:raise ValueError('Hermes n’est pas activé.')
                        client=next((c for c in controller.remote.metadata()['clients'] if c['id']==data.get('id')),None)
                        if not client:raise ValueError('Accès inconnu.')
                        if client.get('hermes_pending'):
                            if client.get('creation_platform')=='android':
                                result=controller.wireguard.create_android(client['name'],controller.remote_backend()[1],client.get('device_owner',''),client.get('device_kind') if client.get('device_kind') in ('phone','tablet') else 'phone',resume=client['id'])
                            else:result=controller.wireguard.create_client(client['name'],controller.remote_backend()[1],resume=client['id'])
                        else:
                            controller.hermes.ensure(client['id'],client['name'])
                            result={'message':'Assistant Hermes prêt.'}
                    elif path == '/api/hermes/models/configure':
                        if not controller.hermes:raise ValueError('Hermes n’est pas activé.')
                        result = controller.hermes.models.configure(data)
                    elif path == '/api/remote/revoke':
                        result = controller.wireguard.revoke(data.get('id'))
                    elif path == '/api/remote/rename':
                        result = controller.remote.rename(data.get('id'),data.get('name'))
                    elif path == '/api/remote/delete':
                        result = controller.wireguard.delete(data.get('id'))
                    elif path == '/api/remote/firewall':
                        result = firewall(controller.home)
                    elif path == '/api/remote/activate':
                        result = controller.wireguard.activate(controller.gateway is not None)
                    elif path == '/api/remote/deactivate':
                        result = controller.wireguard.deactivate()
                    else:
                        return self.respond(404, {'error': 'Commande inconnue.'})
                self.respond(200, result)
            except (ValueError, OSError, RuntimeError, psutil.Error) as error:
                self.respond(400, {'error': str(error)})
    httpd = LocalUserHTTPServer(('127.0.0.1', port), Handler, capacity=24)
    httpd.daemon_threads = True
    return httpd

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--preserve-model-state',action='store_true')
    args = parser.parse_args()
    controller = Controller()
    if controller.hermes:
        def start_agents():
            try:controller.hermes.start()
            except (OSError,ValueError,RuntimeError):
                controller.last_error='Hermes indisponible ; reprise depuis la console nécessaire.'
                controller.hermes.error=controller.last_error
        threading.Thread(target=start_agents,daemon=True,name='fred-hermes-startup').start()
    controller.client_storage.start()
    controller.remote.workspace.knowledge.start()
    if controller.voice.settings()['enabled']:controller.voice.start()
    server = serve(args.port, controller)
    write_json(HOME / 'interface.pid.json', process_identity(psutil.Process()))
    # HTTP remains on loopback; WireGuard has an isolated in-process network stack.
    try:
        controller.gateway = serve_gateway(controller.remote, controller.remote_backend)
        threading.Thread(target=controller.gateway.serve_forever, daemon=True).start()
    except OSError as error:
        controller.last_error = 'Passerelle Internet indisponible : ' + str(error)
    if controller.remote.metadata()['enabled']:
        try:
            controller.wireguard.activate(controller.gateway is not None)
        except (OSError,ValueError) as error:
            controller.last_error='WireGuard : '+str(error)
    threading.Thread(target=controller.operations.watch,kwargs={'preserve_state':args.preserve_model_state}, daemon=True).start()
    server.serve_forever()
