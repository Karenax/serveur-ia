"""Cached, independent connection checks. Never ingest or edit project data."""
import hashlib
import json
import sqlite3
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timezone
from urllib.parse import urlsplit

from .eg2_memory import index_path
from .embedding_channel import EmbeddingChannel, normalize, shared_api_key
from . import ai_routing
from .inference_scheduler import engine_key, lease

_lock = threading.Lock()
_cache = {}
_last_llm_test = {}
TTL = 300
HTTP_TIMEOUT_SECONDS = 20
PRIMARY_READY_MAX_AGE_SECONDS = 6


def _settings_key(settings):
    return hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()


def record_llm_test(ai, outcome):
    """Publish the explicit test without exposing provider errors or credentials."""
    state = 'ok' if outcome.get('ok') else 'error'
    detail = 'Test manuel réussi : serveur LLM joignable.' if outcome.get('ok') else 'Le test manuel du LLM a échoué ; consultez les réglages.'
    if not ai.get('enabled') or ai.get('provider') == 'none':
        state, detail = 'disabled', 'IA désactivée dans les réglages'
    elif outcome.get('ok') and ai.get('provider') == 'openai_compatible':
        detail = 'Test manuel réussi : réponse du modèle reçue.'
    value = result(state, detail, ai.get('model', ''), ai.get('provider', ''))
    with _lock:
        _last_llm_test.clear()
        _last_llm_test.update(key=_settings_key(ai), expires=time.monotonic()+TTL, value=value)


def result(state, detail, model="", provider=""):
    return {"state": state, "detail": detail, "model": model, "provider": provider,
            "checked_at": datetime.now(timezone.utc).isoformat()}


def http_json(url, key="", payload=None, timeout_s=HTTP_TIMEOUT_SECONDS):
    headers = {"Content-Type": "application/json"}
    if key and key != "local":
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(url, headers=headers,
                                     data=json.dumps(payload).encode() if payload is not None else None)
    if payload is not None:
        deadline = time.monotonic() + timeout_s
        category = 'embedding' if urlsplit(url).path.endswith('/embeddings') else 'generation'
        with lease(engine_key(url, category=category), timeout=timeout_s):
            with urllib.request.urlopen(request, timeout=max(0.01, deadline - time.monotonic())) as response:
                return json.loads(response.read())
    with urllib.request.urlopen(request, timeout=timeout_s) as response:
        return json.loads(response.read())


def llm_check(ai):
    provider, model = ai.get("provider", "none"), ai.get("model", "")
    if not ai.get("enabled") or provider == "none":
        return result("disabled", "IA désactivée dans les réglages", model, provider)
    base = (ai.get("base_url") or "").rstrip("/")
    if provider == "ollama":
        epoch = ai_routing.primary_epoch(ai)
        data = http_json(base.removesuffix('/v1') + '/api/tags')
        models = [row.get("name", "") for row in data.get("models", [])]
        exists = model in models or (":" not in model and model+":latest" in models)
        if exists:
            ai_routing.primary_succeeded(ai, epoch)
    elif provider == "openai_compatible":
        epoch = ai_routing.primary_epoch(ai)
        started = time.monotonic()
        data = http_json(base if base.endswith('/models') else base.removesuffix('/v1')+'/v1/models', ai.get('api_key', ''))
        models = [row.get('id', '') for row in data.get('data', [])]
        exists = model in models
        if exists and 0 <= time.monotonic()-started <= PRIMARY_READY_MAX_AGE_SECONDS:
            ai_routing.primary_ready(ai, epoch, model)
    else:
        return result("unknown", "Fournisseur non pris en charge par ce contrôle", model, provider)
    return result("ok" if exists else "warning",
                  "Serveur accessible, modèle annoncé. La génération n’est pas testée par ce témoin."
                  if exists else "Serveur accessible, modèle configuré absent de la liste", model, provider)


def embedding_check(ai, memory):
    model = memory.get('embedding_model') or 'text-embedding-embeddinggemma-2'
    base = (memory.get('embedding_endpoint') or 'http://192.9.110.115:1234').rstrip('/').removesuffix('/v1')
    data = http_json(base + '/v1/embeddings', key=shared_api_key(ai, base), timeout_s=min(memory.get('timeout_s', 600), HTTP_TIMEOUT_SECONDS), payload={
        'model': model, 'input': 'task: search result | query: Agent test de connexion', 'encoding_format': 'float'})
    try:
        normalize((data.get('data') or [{}])[0].get('embedding', []), 768)
    except ValueError:
        return result('error', 'Le moteur ne renvoie pas de vecteur EG2 valide', model, 'openai_compatible')
    return result('ok', 'Vecteur EG2 calculé : 768 dimensions.', model, 'openai_compatible')


def memory_check(memory):
    from ..db import SessionLocal
    from ..models import MemoryProjection
    from .memory_factory import resolve_engine
    engine = resolve_engine(SessionLocal)
    if engine == 'fake':
        return result('disabled', 'Adaptateur de test SQL', provider=engine)
    path = index_path(memory)
    if not path.is_file():
        return result('warning', 'Index EG2 non initialisé', provider='eg2')
    channel = EmbeddingChannel(memory.get('embedding_endpoint') or 'http://192.9.110.115:1234',
                               memory.get('embedding_model') or 'text-embedding-embeddinggemma-2')
    with closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True, timeout=2)) as database:
        counts = dict(database.execute('SELECT profile, count(*) FROM passages GROUP BY profile'))
    count = sum(counts.values())
    if count != counts.get(channel.profile, 0):
        return result('warning', 'Profil EG2 incompatible avec tout ou partie de l’index. Reconstruisez l’index des projets concernés.', provider='eg2')
    with SessionLocal() as db:
        failed = db.query(MemoryProjection).filter_by(status='failed').count()
        pending = db.query(MemoryProjection).filter_by(status='pending').count()
    return result('warning' if failed or pending else 'ok',
                  f'Index EG2 lisible : {count} passages ; {pending} en attente, {failed} en échec. Rappel non testé.', provider='eg2')


def guarded(check, *args):
    try:
        return check(*args)
    except Exception as exc:
        if check is llm_check and ai_routing.transport_failure(exc):
            ai_routing.unavailable(args[0])
        # Provider exceptions may contain request URLs or keys: expose only the class.
        return result('error', f'Connexion non confirmée ({type(exc).__name__})')


def _refresh(key, ai, memory):
    probes = {'llm': (llm_check, (ai,)), 'embedding': (embedding_check, (ai, memory)),
              'memory': (memory_check, (memory,))}
    with ThreadPoolExecutor(max_workers=3) as pool:
        tasks = {name: pool.submit(guarded, check, *args) for name, (check, args) in probes.items()}
        for name, task in tasks.items():
            value = task.result()
            with _lock:
                if _cache.get('key') == key:
                    failures = _cache.setdefault('failures', {})
                    failures[name] = failures.get(name, 0) + 1 if value['state'] == 'error' else 0
                    previous = _cache['values'].get(name)
                    # Keep the last confirmed state (and its timestamp) for one failed probe.
                    if (value['state'] == 'error' and failures[name] < 2
                            and previous and previous['state'] in ('ok', 'warning')):
                        continue
                    _cache['values'][name] = value
    with _lock:
        if _cache.get('key') == key:
            delay = 60 if any(_cache.get('failures', {}).values()) else TTL
            _cache.update(running=False, expires=time.monotonic()+delay)


def connection_status(ai, memory):
    key = hashlib.sha256(json.dumps([ai, memory], sort_keys=True).encode()).hexdigest()
    with _lock:
        if _cache.get('key') != key:
            _cache.clear()
            _cache.update(key=key, running=False, expires=0, values={
                name: result('checking', 'Vérification en cours') for name in ('llm', 'embedding', 'memory')})
        if not _cache['running'] and time.monotonic() >= _cache['expires']:
            _cache['running'] = True
            threading.Thread(target=_refresh, args=(key, dict(ai), dict(memory)), daemon=True,
                             name='connection-health').start()
        services = {name: dict(value) for name, value in _cache['values'].items()}
        # A probe started before the manual test must not overwrite its result.
        if (_last_llm_test.get('key') == _settings_key(ai)
                and time.monotonic() < _last_llm_test['expires']):
            services['llm'] = dict(_last_llm_test['value'])
        return {'services': services,
                'refreshing': _cache['running'], 'cache_seconds': TTL,
                'offline': ai_routing.offline_status(ai)}
