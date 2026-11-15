"""Remote-first routing with a loopback-only LM Studio emergency model."""
from __future__ import annotations

import json
import hashlib
import http.client
import logging
from contextlib import contextmanager
from pathlib import Path
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from urllib.parse import urlsplit

_lock = threading.Lock()
_local_lock = threading.Lock()
_down_until: dict[str, float] = {}
OFFLINE_WAIT_SECONDS = 120
_outages: dict[tuple, dict] = {}
_failure_epochs: dict[str, int] = {}
_release_states: dict[tuple[str, str, str], dict] = {}
_recovery_versions: dict[tuple[str, str, str], int] = {}
_routing_configured = False
_configured_target: tuple[str, str, str] | None = None
_configured_principal: tuple[str, str, str, str] | None = None
LOG = logging.getLogger(__name__)


def _consent_key(cfg):
    return (_principal_identity(cfg), str(cfg.get('fallback_base_url') or 'http://127.0.0.1:1234').rstrip('/'),
            str(cfg.get('fallback_model') or 'google/gemma-4-e4b'))


def offline_status(cfg):
    """Read-only: never probe, start a server or load a model from a status read."""
    with _lock:
        outage = dict(_outages.get(_consent_key(cfg), {}))
    elapsed = max(0, time.monotonic()-outage['since']) if outage else 0
    enabled = bool(cfg.get('enabled') and cfg.get('fallback_enabled') and cfg.get('provider') != 'none')
    return {'outage_id': outage.get('id'), 'remaining_seconds': max(0, OFFLINE_WAIT_SECONDS-elapsed),
            'approval_required': bool(enabled and outage and elapsed >= OFFLINE_WAIT_SECONDS
                                      and outage.get('decision') is None),
            'decision': outage.get('decision'),
            'using_fallback': bool(enabled and outage.get('decision') == 'offline')}


def decide_offline(cfg, outage_id, decision):
    if decision not in {'offline', 'wait'}:
        raise ValueError('Choix de connexion invalide')
    with _lock:
        outage = _outages.get(_consent_key(cfg))
        if (not cfg.get('enabled') or not cfg.get('fallback_enabled') or not outage
                or outage['id'] != outage_id or time.monotonic()-outage['since'] < OFFLINE_WAIT_SECONDS):
            raise ValueError('La connexion a changé ; vérifiez son état avant de choisir')
        outage['decision'] = decision
    return offline_status(cfg)


def require_offline_consent(cfg):
    key = cfg.get('_fallback_consent_key')
    with _lock:
        outage = _outages.get(key, {})
        allowed = (outage.get('decision') == 'offline'
                   and time.monotonic()-outage['since'] >= OFFLINE_WAIT_SECONDS)
    if not allowed:
        raise RuntimeError('Serveur IA indisponible. Le mode hors ligne attend votre validation dans État du système.')


def transport_failure(exc: BaseException) -> bool:
    if isinstance(exc, urllib.error.HTTPError):
        return exc.code in {502, 503, 504}
    return isinstance(exc, (urllib.error.URLError, ConnectionError, TimeoutError, http.client.RemoteDisconnected))


def local_config(cfg: dict) -> dict | None:
    if not cfg.get("enabled") or not cfg.get("fallback_enabled") or cfg.get("provider") == "none":
        return None
    base = str(cfg.get("fallback_base_url") or "http://127.0.0.1:1234").rstrip("/")
    url = urlsplit(base)
    if url.scheme != "http" or url.hostname not in {"localhost", "127.0.0.1", "::1"} or url.username or url.password:
        raise ValueError("Le secours LM Studio doit utiliser une adresse HTTP locale sans identifiants")
    target = (str(cfg.get("base_url") or ""), base,
              str(cfg.get("fallback_model") or "google/gemma-4-e4b"))
    with _lock:
        recovery_version = _recovery_versions.get(target, 0)
    return {**cfg, "provider": "openai_compatible", "base_url": base,
            "model": cfg.get("fallback_model") or "google/gemma-4-e4b",
            "api_key": "", "fallback_enabled": False, "using_fallback": True,
            "_fallback_consent_key": _consent_key(cfg),
            "_fallback_release_target": target,
            "_fallback_recovery_version": recovery_version}


def unavailable(cfg: dict):
    with _lock:
        primary = str(cfg.get("base_url"))
        now = time.monotonic()
        _down_until[primary] = now + 60
        first_failure = _consent_key(cfg) not in _outages
        _outages.setdefault(_consent_key(cfg), {'since': now, 'id': uuid.uuid4().hex, 'decision': None})
        _failure_epochs[primary] = _failure_epochs.get(primary, 0) + 1
    if first_failure:
        LOG.warning("Serveur IA principal indisponible ; mode local soumis au délai et à la validation utilisateur")


@contextmanager
def local_generation(cfg: dict, *, timeout: float = 30):
    """Reserve before loading; foreground must precede the engine reservation."""
    from .inference_scheduler import DEFAULT_WAIT_SECONDS, engine_key, lease, waiting_policy
    from .llm_activity import foreground
    if cfg.get('using_fallback'):
        require_offline_consent(cfg)
    delay, cancel = waiting_policy()
    deadline = time.monotonic() + delay if delay is not None else None
    try:
        with foreground(timeout=delay, cancel=cancel):
            remaining = max(0, deadline-time.monotonic()) if deadline is not None else DEFAULT_WAIT_SECONDS
            with lease(engine_key(cfg['base_url']), timeout=min(DEFAULT_WAIT_SECONDS, remaining), cancel=cancel):
                ensure_local(cfg)
                yield
    finally:
        release_recovered_fallback(cfg)


def primary_epoch(cfg: dict) -> int:
    with _lock:
        return _failure_epochs.setdefault(str(cfg.get('base_url')), 0)


def _release_target(cfg: dict) -> tuple[str, str, str] | None:
    if cfg.get('using_fallback'):
        return None
    fallback = local_config(cfg)
    primary = str(cfg.get('base_url') or '')
    url = urlsplit(primary)
    # A local principal must keep its model, even when fallback is configured.
    if fallback is None or url.scheme not in {'http', 'https'} or not url.hostname:
        return None
    if url.hostname.lower() in {'localhost', '127.0.0.1', '::1'}:
        return None
    return primary, fallback['base_url'], str(fallback['model'])


def _loaded_instances(base: str, model: str) -> list[str]:
    with urllib.request.urlopen(base + '/api/v1/models', timeout=5) as response:
        inventory = json.load(response)
    models = inventory.get('models')
    if not isinstance(models, list):
        raise ValueError('Invalid LM Studio inventory')
    instances = []
    for row in models:
        if row.get('key') == model:
            for instance in row.get('loaded_instances', []):
                identifier = instance.get('id')
                if not isinstance(identifier, str) or not identifier:
                    raise ValueError('Invalid LM Studio instance')
                instances.append(identifier)
    return list(dict.fromkeys(instances))


def _release_current(target, epoch):
    primary = target[0]
    with _lock:
        return (_failure_epochs.get(primary, 0) == epoch
                and primary not in _down_until
                and (not _routing_configured or target == _configured_target))


@contextmanager
def settings_update(cfg: dict):
    """Serialize an AI configuration commit with local model management."""
    global _routing_configured, _configured_target, _configured_principal
    with _local_lock:
        target = _release_target(cfg)
        with _lock:
            primaries = set(_failure_epochs) | {item[0] for item in _release_states}
            for primary in primaries:
                _failure_epochs[primary] = _failure_epochs.get(primary, 0)+1
        yield
        with _lock:
            # A probe may have created its first epoch or queued a release while
            # the settings transaction was in flight. Invalidate the CURRENT set
            # at commit before publishing the new identity/releasing management.
            for primary in set(_failure_epochs) | {item[0] for item in _release_states}:
                _failure_epochs[primary] = _failure_epochs.get(primary, 0)+1
            _configured_target, _routing_configured = target, True
            _configured_principal = _principal_identity(cfg)
            _outages.clear()


def _principal_identity(cfg: dict) -> tuple[str, str, str, str]:
    # Bind readiness to the credential actually used by HTTP, without retaining
    # the raw key in this identity or exposing it through status/log output.
    credential = hashlib.sha256(str(cfg.get('api_key') or '').encode('utf-8')).hexdigest()
    return (str(cfg.get('provider') or ''), str(cfg.get('base_url') or ''),
            str(cfg.get('model') or ''), credential)


def primary_ready(cfg: dict, epoch: int, observed_model: str):
    """Notify only a fresh exact-model inventory, never a cached health/TCP state."""
    if (cfg.get('provider') != 'openai_compatible' or not observed_model
            or observed_model != cfg.get('model')):
        return
    with _lock:
        if (_routing_configured and _principal_identity(cfg) != _configured_principal):
            return
        if _failure_epochs.get(str(cfg.get('base_url')), 0) != epoch:
            return
    # settings_update/new outage between these checks and admission increments
    # the epoch; primary_succeeded and the queued worker both recheck it.
    primary_succeeded(cfg, epoch)


def _release_local(target: tuple[str, str, str], epoch: int):
    from .inference_scheduler import engine_key, lease
    _, base, model = target
    state, error = 'cancelled', None
    try:
        # Includes a normal long generation/load; a newer outage/configuration
        # cancels this wait immediately instead of occupying a stale queue slot.
        class RecoveryCancel:
            def is_set(self):
                return not _release_current(target, epoch)
        with lease(engine_key(base), priority=50, timeout=3600, cancel=RecoveryCancel()):
            with _local_lock:
                if not _release_current(target, epoch):
                    return
                with _lock:
                    if _release_states.get(target, {}).get('epoch') == epoch:
                        _release_states[target]['state'] = 'unloading'
                for identifier in _loaded_instances(base, model):
                    if not _release_current(target, epoch):
                        return
                    request = urllib.request.Request(base + '/api/v1/models/unload',
                        data=json.dumps({'instance_id': identifier}).encode(),
                        headers={'Content-Type': 'application/json'}, method='POST')
                    with urllib.request.urlopen(request, timeout=5) as response:
                        result = json.load(response)
                    if result.get('instance_id') != identifier:
                        raise ValueError('Invalid LM Studio unload acknowledgement')
                if _loaded_instances(base, model):
                    raise RuntimeError('Fallback model remains loaded')
                state = 'unloaded'
                LOG.info('LLM principal rétabli ; modèle de secours LM Studio déchargé')
    except Exception as exc:
        if _release_current(target, epoch):
            state, error = 'error', type(exc).__name__
            LOG.warning('Déchargement du secours LM Studio non confirmé (%s)', error)
    finally:
        with _lock:
            if _release_states.get(target, {}).get('epoch') == epoch:
                _release_states[target] = {'epoch': epoch, 'state': state,
                    'error': error, 'retry_at': time.monotonic()+30 if error else 0}


def primary_succeeded(cfg: dict, epoch: int):
    """Useful reply or fresh exact-model readiness releases idle local memory."""
    with _lock:
        if (_failure_epochs.get(str(cfg.get('base_url')), 0) == epoch
                and (not _routing_configured or _principal_identity(cfg) == _configured_principal)):
            _outages.pop(_consent_key(cfg), None)
    target = _release_target(cfg)
    if target is None:
        return
    with _lock:
        if _routing_configured and target != _configured_target:
            return
        if _failure_epochs.get(target[0], 0) != epoch:
            return  # A response started before a newer outage cannot release.
        _down_until.pop(target[0], None)
        _recovery_versions[target] = _recovery_versions.get(target, 0) + 1
    _queue_release(target, epoch)


def release_recovered_fallback(cfg: dict):
    """A late local call must not undo an already confirmed remote recovery."""
    from .inference_scheduler import engine_key
    target = cfg.get('_fallback_release_target')
    if not cfg.get('using_fallback') or not isinstance(target, tuple) or len(target) != 3:
        return
    if cfg.get('model') != target[2] or engine_key(cfg['base_url']) != engine_key(target[1]):
        return
    with _lock:
        # Only a previous exact-model recovery can authorize this release.
        # A TCP connection or an expired outage cooldown is insufficient.
        recovered = _release_states.get(target)
        selected_version = cfg.get('_fallback_recovery_version')
        if (recovered is None or not isinstance(selected_version, int)
                or _recovery_versions.get(target, 0) <= selected_version):
            return
        epoch = recovered['epoch']
    _queue_release(target, epoch)


def _queue_release(target: tuple[str, str, str], epoch: int):
    with _lock:
        if (_failure_epochs.get(target[0], 0) != epoch or target[0] in _down_until
                or (_routing_configured and target != _configured_target)):
            return
        previous = _release_states.get(target, {})
        if previous.get('epoch') == epoch:
            if previous.get('state') in {'waiting', 'unloading'}:
                return
            if previous.get('retry_at', 0) > time.monotonic():
                return
        _release_states[target] = {'epoch': epoch, 'state': 'waiting', 'error': None}
    try:
        threading.Thread(target=_release_local, args=(target, epoch),
                         name='lmstudio-release', daemon=True).start()
    except RuntimeError:
        with _lock:
            _release_states[target] = {'epoch': epoch, 'state': 'error',
                'error': 'RuntimeError', 'retry_at': time.monotonic()+30}


def ensure_local(cfg: dict):
    """Start the installed CLI server/model when needed, without visible windows."""
    if cfg.get('using_fallback'):
        require_offline_consent(cfg)
    if not cfg.get("fallback_autostart"):
        return
    def ready():
        try:
            with urllib.request.urlopen(cfg["base_url"] + "/api/v1/models", timeout=2) as response:
                return any(m.get("key") == cfg["model"] and m.get("loaded_instances")
                           for m in json.load(response).get("models", []))
        except (OSError, ValueError):
            return False
    if ready():
        return
    with _local_lock:
        if cfg.get('using_fallback'):
            require_offline_consent(cfg)
        if ready():
            return
        cli = Path.home() / ".lmstudio" / "bin" / "lms.exe"
        if not cli.is_file():
            raise RuntimeError("CLI LM Studio introuvable pour démarrer le modèle de secours")
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        url = urlsplit(cfg["base_url"])
        for args in (["server", "start", "--port", str(url.port or 1234), "--bind", "127.0.0.1"],
                     ["load", str(cfg["model"]), "--identifier", str(cfg["model"]),
                      "--context-length", "8192", "--yes"]):
            if cfg.get('using_fallback'):
                require_offline_consent(cfg)
            result = subprocess.run([str(cli), *args], capture_output=True, timeout=600, creationflags=flags)
            if result.returncode:
                raise RuntimeError("LM Studio n'a pas pu démarrer son serveur ou charger le modèle de secours")
            if ready():
                return
        if not ready():
            raise RuntimeError("Le modèle de secours n'est pas disponible dans LM Studio")


def resolve(cfg: dict) -> dict:
    fallback = local_config(cfg)
    if fallback is None:
        return cfg
    with _lock:
        down = _down_until.get(str(cfg.get("base_url")), 0) > time.monotonic()
    if not down:
        url = urlsplit(str(cfg.get("base_url") or ""))
        if url.scheme not in {"http", "https"} or not url.hostname:
            return cfg
        try:
            with socket.create_connection((url.hostname, url.port or (443 if url.scheme == "https" else 80)), timeout=5):
                return cfg
        except OSError:
            unavailable(cfg)
    return fallback if offline_status(cfg)['using_fallback'] else cfg


def status(cfg: dict) -> dict:
    offline = offline_status(cfg)
    active = local_config(cfg) if offline['using_fallback'] else cfg
    target = _release_target(cfg)
    with _lock:
        release = dict(_release_states.get(target, {'state': 'idle'}))
    release.pop('epoch', None)
    release.pop('retry_at', None)
    return {"using_fallback": bool(active.get("using_fallback")), "provider": active.get("provider"),
            "model": active.get("model"), "base_url": active.get("base_url"), "retry_primary_after_s": 60,
            "offline": offline,
            "local_model_release": release}
