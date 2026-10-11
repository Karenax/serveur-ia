"""Fred integration lifecycle, without modifying the personal Hermes installation."""
from __future__ import annotations
import atexit
from pathlib import Path
import threading
import time
from core import read_json, write_json
from hermes_accounts import HermesAccounts
from hermes_service import HermesService
from hermes_inference import HermesPrivateServer
from hermes_conversations import HermesConversations
from hermes_tools import FredTools
from hermes_web import NativeHermesWeb
from hermes_projects import HermesProjects
from hermes_models import HermesModels, NativeModelSource


class HermesFred:
    def __init__(self, store, backend, *, port=8643, private_port=8768, source=None):
        self.store, self.backend = store, backend
        self.lock = threading.RLock()
        self.private = HermesPrivateServer(store, backend, port=private_port)
        self.accounts = HermesAccounts(store.home, self.private.url + '/v1', self.private.url + '/mcp',
                                       authorized=self.profile_allowed)
        self.service = HermesService(self.accounts, port, source=source)
        self.conversations = HermesConversations(store, self.accounts, self.service)
        self.models = HermesModels(store,backend,self.accounts,source=NativeModelSource())
        self.accounts.models = self.conversations.models = self.private.models = self.models
        self.models.on_changed = self._models_changed
        self.projects = HermesProjects(self.accounts, store.workspace, self.service)
        self.conversations.projects = self.projects
        self.tools = FredTools(store.workspace, self.tool_allowed)
        self.tools.web = NativeHermesWeb(source=source)
        self.private.accounts, self.private.conversations, self.private.tools = self.accounts, self.conversations, self.tools
        self.started = False
        self.error = ''
        self.report = {}
        self.monitor = None
        self.halt = threading.Event()
        atexit.register(self.close)

    def profile_allowed(self, owner):
        # Provisioning/readiness works with distant ingress disabled. Active
        # inference/tool calls additionally check valid_owner and their run.
        records = read_json(self.store.path, {})
        client = next((c for c in records.get('clients', []) if c['id'] == owner), None)
        try: revoked = self.store.revocations.contains(owner)
        except (OSError, ValueError): return False
        return bool(client and not revoked and not client.get('revoked') and not client.get('suspended')
                    and (not client.get('expires_epoch') or client['expires_epoch'] > time.time()))

    def tool_allowed(self, owner, context):
        return bool(context and self.conversations.context(owner) is context and self.conversations.valid(owner, context))

    def start(self):
        with self.lock:
            if self.started and self.service.status().get('available'): return self.status()
            self.halt.clear()
            self.private.start()
            records = read_json(self.store.path, {})
            self.report = self.accounts.migrate(records.get('clients', []), port=self.service.port)
            self.service.start()
            for owner in self.report.get('ready', []):
                self.probe(owner)
                self.projects.synchronize(owner)
            self.started = True
            self.error = ''
            if not self.monitor or not self.monitor.is_alive():
                self.monitor = threading.Thread(target=self.watch, daemon=True, name='fred-hermes-policy')
                self.monitor.start()
            return self.status()

    def probe(self, owner):
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            try:
                value = self.service.capabilities(owner)
                if '/v1/runs' not in str(value): raise ValueError('API de conversations Hermes indisponible.')
                return value
            except (OSError, ValueError, RuntimeError):
                if self.halt.wait(.3): break
        raise ValueError('Le profil Hermes ne répond pas ; création à reprendre dans la console.')

    def ensure(self, owner, name=''):
        value = self.accounts.ensure(owner, name, port=self.service.port)
        if not value.get('ready'): raise ValueError('Ce profil Hermes est désactivé.')
        if not self.started: self.start()
        self.probe(owner)
        return self.accounts.public(owner)

    def public(self, owner): return self.accounts.public(owner)

    def model_catalog(self, owner): return self.models.catalog(owner)
    def select_model(self, owner, requested=None): return self.models.select(owner,requested)

    def _models_changed(self):
        with self.conversations.lock:
            for owner,context in list(self.conversations.active.items()):
                if not self.models.valid(owner,context['model_selection']):self.conversations.cancel(owner,context['request_id'])
            for owner in self.accounts.owners(ready_only=True):
                if self.profile_allowed(owner):
                    context=self.conversations.active.get(owner)
                    selected=context['model_selection'] if context and self.models.valid(owner,context['model_selection']) else None
                    self.accounts.materialize(owner,self.service.port,selection=selected)

    def watch(self):
        while not self.halt.wait(.5):
            with self.conversations.lock: contexts = list(self.conversations.active.items())
            for owner, context in contexts:
                if not self.conversations.valid(owner,context) or time.monotonic() - context['created'] > self.conversations.timeout:
                    self.conversations.cancel(owner, context['request_id'])
                pending = context.get('approval')
                if pending and pending['expires_epoch'] < time.time(): self.conversations.cancel(owner, context['request_id'])

    def cancel(self, owner, request=None): return self.conversations.cancel(owner, request)
    def status(self, owner=None):
        result = self.conversations.status(owner)
        if owner is None: result.update(service=self.service.status(), migration=self.report, error=self.error)
        return result
    def action(self, owner, value): return self.conversations.action(owner, value)
    def stream(self, *args, **kwargs): return self.conversations.stream(*args, **kwargs)
    def generate(self, *args, **kwargs): return self.conversations.generate(*args, **kwargs)
    def merge_completed(self, *args): return self.conversations.merge_completed(*args)

    def synchronize_projects(self, owner):
        try:
            self.projects.synchronize(owner)
            self.error = ''
            return {'state': 'ready'}
        except (OSError, ValueError, RuntimeError):
            self.error = 'Synchronisation des projets Hermes à reprendre.'
            return {'state': 'pending', 'message': self.error}

    def close(self):
        with self.lock:
            if self.halt.is_set(): return
            self.halt.set()
            self.conversations.close()
            self.service.close()
            self.private.close()
            self.started = False


def configured(home):
    value = read_json(Path(home) / 'hermes-integration.json', {})
    return value if isinstance(value, dict) and value.get('enabled') is True else None
