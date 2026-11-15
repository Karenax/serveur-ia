"""Preparation diagnostics: inventory is separate from an explicitly tested reply."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import urllib.error
import urllib.request
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from .settings_service import get_section


def selected_configuration(db):
    from .scoped_assistant import _effective_cfg
    cfg = _effective_cfg(db, get_section(db, 'ai'))
    url = urlsplit(str(cfg.get('base_url') or ''))
    if url.scheme not in {'http', 'https'} or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError('Adresse du moteur à vérifier dans les réglages IA')
    identity = {name:cfg.get(name) for name in ('provider', 'base_url', 'model', 'api_key')}
    key = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    return cfg, key, 'local' if url.hostname.casefold() in {'localhost', '127.0.0.1', '::1'} else 'network'


def directory(key):
    from ..config import STORAGE_DIR
    return Path(STORAGE_DIR)/'runtime'/'readiness'/key


def saved(key, kind):
    try:
        root = directory(key)
        identifier = (root/(kind+'.latest')).read_text(encoding='utf-8')
        if str(UUID(identifier)) != identifier:
            return None
        return json.loads((root/(kind+'-'+identifier+'.json')).read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return None


def record(key, kind, value):
    root = directory(key)
    root.mkdir(parents=True, exist_ok=True)
    identifier = str(uuid4())
    value = {**value, 'checked_at':datetime.now(timezone.utc).isoformat()}
    with (root/(kind+'-'+identifier+'.json')).open('x', encoding='utf-8') as sink:
        json.dump(value, sink, ensure_ascii=False)
    temporary = root/(kind+'-'+identifier+'.part')
    temporary.write_text(identifier, encoding='utf-8')
    temporary.replace(root/(kind+'.latest'))
    return value


def generation_snapshot(db):
    try:
        cfg, key, placement = selected_configuration(db)
    except Exception:
        return {'configured':False, 'placement':'unknown', 'model':'', 'inventory':None, 'test':None,
                'detail':'Configuration du moteur à vérifier dans les réglages IA'}
    return {'configured':bool(cfg.get('enabled') and cfg.get('provider') not in {None, '', 'none'} and cfg.get('model')),
            'placement':placement, 'model':str(cfg.get('model') or ''), 'provider':str(cfg.get('provider') or ''),
            'inventory':saved(key, 'inventory'), 'test':saved(key, 'generation'),
            'detail':'Le contrôle des modèles ne lance pas de génération ; le test de réponse est distinct.'}


def fetch(cfg, path):
    headers = {'Authorization':'Bearer '+cfg['api_key']} if cfg.get('api_key') else {}
    base = str(cfg['base_url']).rstrip('/').removesuffix('/v1')
    request = urllib.request.Request(base+path, headers=headers)
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


def probe_generation(db):
    from backend.app.services.project_operator import require_reference_write
    require_reference_write()
    cfg, key, _ = selected_configuration(db)
    value = {'reachable':False, 'installed':None, 'loaded':None, 'generation_tested':False}
    try:
        if not cfg.get('enabled') or cfg.get('provider') == 'none' or not cfg.get('model'):
            value['detail'] = 'IA désactivée ou modèle non sélectionné dans les réglages'
        elif cfg.get('provider') == 'openai_compatible':
            try:
                data = fetch(cfg, '/api/v1/models')
            except urllib.error.HTTPError as exc:
                if exc.code not in {404, 405}:
                    raise
                data = None
            if isinstance(data, dict) and isinstance(data.get('models'), list):
                def matches(row):
                    if not isinstance(row, dict):
                        return False
                    instances = row.get('loaded_instances')
                    return row.get('key') == cfg.get('model') or isinstance(instances, list) and any(
                        isinstance(item, dict) and item.get('id') == cfg.get('model') for item in instances)
                row = next((row for row in data['models'] if matches(row)), None)
                loaded = row.get('loaded_instances') if row is not None else []
                value.update(reachable=True, installed=row is not None,
                             loaded=bool(loaded) if isinstance(loaded, list) else None)
                value['detail'] = 'Inventaire LM Studio reçu ; aucune génération lancée'
            else:
                data = fetch(cfg, '/v1/models')
                announced = any(row.get('id') == cfg.get('model') for row in data.get('data', []))
                value.update(reachable=True, announced=announced)
                value['detail'] = 'Modèle annoncé ; installation et chargement non exposés par ce serveur' if announced else 'Modèle configuré absent de la liste du serveur'
        elif cfg.get('provider') == 'ollama':
            tags = fetch(cfg, '/api/tags')
            running = fetch(cfg, '/api/ps')
            wanted = str(cfg.get('model') or '')
            aliases = {wanted, wanted+':latest'} if ':' not in wanted else {wanted}
            value.update(reachable=True, installed=any(row.get('name') in aliases for row in tags.get('models', [])),
                         loaded=any(row.get('name') in aliases for row in running.get('models', [])))
            value['detail'] = 'Inventaire Ollama reçu ; aucune génération lancée'
        else:
            value['detail'] = 'Inventaire non exposé pour ce fournisseur'
    except Exception as exc:
        value['detail'] = 'Inventaire non confirmé ('+type(exc).__name__+')'
    record(key, 'inventory', value)
    db.expire_all()
    return snapshot(db)


def test_generation(db):
    from backend.app.services.project_operator import require_reference_write
    require_reference_write()
    from . import ai_client, ai_routing
    from .inference_scheduler import priority_scope
    import time
    cfg, key, _ = selected_configuration(db)
    started = time.monotonic()
    value = {'ok':False, 'reply_received':False}
    try:
        if not cfg.get('enabled') or cfg.get('provider') in {None, '', 'none'} or not cfg.get('model'):
            raise ValueError('Génération non configurée')
        # Probe exactly the selected endpoint. A successful fallback must never
        # be presented as a response of the configured network model.
        exact = {**cfg, 'fallback_enabled':False, 'fallback_autostart':False}
        epoch = ai_routing.primary_epoch(cfg)
        with priority_scope('question'):
            reply = ai_client.chat_text(exact, [{'role':'user','content':'Réponds uniquement OK.'}],
                max_tokens=32, timeout=int(cfg.get('timeout_s') or 120), retry_empty=False, raise_errors=True)
        value.update(ok=bool(reply and reply.strip()), reply_received=bool(reply and reply.strip()))
        value['detail'] = 'Réponse réelle reçue ; qualité métier non évaluée' if value['ok'] else 'Le moteur a renvoyé une réponse vide'
        if value['ok']:
            ai_routing.primary_succeeded(cfg, epoch)
    except Exception as exc:
        value['detail'] = 'Réponse non confirmée ('+type(exc).__name__+')'
    value['elapsed_seconds'] = time.monotonic()-started
    record(key, 'generation', value)
    db.expire_all()
    return snapshot(db)


def snapshot(db):
    from backend.app.services.project_operator import require_reference_write
    require_reference_write()
    from .meeting_sessions import capabilities
    from .live_speech import runtime_status as direct_status
    from .meeting_audio import runtime_status as batch_status
    from ..config import STORAGE_DIR
    try:
        import psutil
        memory = psutil.virtual_memory()
        resources = {'available_ram_bytes':memory.available, 'total_ram_bytes':memory.total}
    except (ImportError, OSError):
        resources = {'available_ram_bytes':None, 'total_ram_bytes':None}
    try:
        resources['free_disk_bytes'] = shutil.disk_usage(STORAGE_DIR).free
    except OSError:
        resources['free_disk_bytes'] = None
    cap = capabilities(db)
    native = cap.get('native_capture') or {}
    return {'mode':get_section(db, 'foresight').get('mode', 'network'),
        'capture':{'durable':cap['capture']['durable'], 'installed':native.get('installed'),
                   'ready':native.get('ready'), 'physical_test_passed':native.get('real_test_passed'),
                   'requires_explicit_start':True},
        'transcription':{'batch':batch_status(), 'direct':direct_status()},
        'embeddings':{'network':{'model':get_section(db, 'memory').get('embedding_model'),
            'detail':'L’état du système distingue la connexion et le calcul réel d’un vecteur réseau.'}},
        'generation':generation_snapshot(db), 'resources':resources,
        'offline':{'qualified':False, 'detail':'La chaîne actuelle complète doit encore être vérifiée avec Internet et le LAN réellement coupés.'}}
