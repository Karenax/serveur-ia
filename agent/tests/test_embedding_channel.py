import asyncio
import math

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.embedding_channel import EmbeddingChannel, normalize, rank_vectors


def test_vectors_reject_corruption_and_normalize():
    assert normalize([3, 4], 2) == [0.6, 0.8]
    for vector in ([0, 0], [float('nan'), 1], [float('inf'), 1], [True, 1], [1]):
        with pytest.raises(ValueError):
            normalize(vector, 2)
    with pytest.raises(ValueError):
        rank_vectors([1], [{'id': 'a', 'text': 'a'}], [[1, 0]], 1)


def test_eg2_rebuild_retires_incompatible_passages_only_after_success(monkeypatch, tmp_path):
    from app.services.eg2_memory import EG2MemoryAdapter

    adapter = EG2MemoryAdapter(channel=EmbeddingChannel('http://kiara:8766'), path=tmp_path / 'index.db')
    with adapter._connect() as db:
        db.executemany('INSERT INTO passages VALUES (?,?,?,?,?,?,?)', [
            ('project', 'old', 'source', 0, 'ancien', '[]', 'old-profile'),
            ('project', 'new', 'source', 0, 'actuel', '[]', adapter.channel.profile),
            ('other', 'old', 'source', 0, 'autre projet', '[]', 'old-profile'),
        ])

    outcome = {'status': 'failed'}

    async def rebuild(*args):
        return outcome

    monkeypatch.setattr('app.services.projections.rebuild_from_canon', rebuild)
    assert asyncio.run(adapter.rebuild_project('project'))['status'] == 'failed'
    with adapter._connect() as db:
        assert db.execute('SELECT count(*) FROM passages').fetchone() == (3,)
    outcome['status'] = 'rebuilt'
    assert asyncio.run(adapter.rebuild_project('project'))['status'] == 'rebuilt'
    with adapter._connect() as db:
        assert db.execute('SELECT project,ref FROM passages ORDER BY project').fetchall() == [('other', 'old'), ('project', 'new')]


def test_remote_reorders_batches_applies_roles_and_never_falls_back(monkeypatch):
    calls = []

    def respond(request):
        import json
        payload = json.loads(request.content)
        calls.append(payload)
        assert request.url.path == '/v1/embeddings'
        data = [{'index': idx, 'embedding': [float(idx + 1)] + [0.] * 767}
                for idx, _ in enumerate(payload['input'])]
        return httpx.Response(200, json={'data': list(reversed(data))})

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    channel = EmbeddingChannel('http://server:1234', batch_size=2)
    vectors = asyncio.run(channel.embed(['a', 'b', 'c']))
    assert len(vectors) == 3 and all(math.isclose(sum(v * v for v in vec), 1) for vec in vectors)
    asyncio.run(channel.embed(['question'], query=True))
    assert calls[0]['input'] == ['title: none | text: a', 'title: none | text: b']
    assert calls[-1]['input'] == ['task: search result | query: question']
    assert channel.profile != EmbeddingChannel('http://other:1234').profile
    assert channel.profile != EmbeddingChannel('http://server:1234', model='other').profile


def test_incomplete_or_duplicate_indices_are_rejected(monkeypatch):
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={'data': [{'index': 0, 'embedding': [1.] * 768}] * 2})), **kw))
    with pytest.raises(ValueError, match='indices'):
        asyncio.run(EmbeddingChannel('http://server:1234').embed(['a', 'b']))


def test_diagnostics_share_production_profile_and_report_explicit_failure(monkeypatch):
    from app.db import SessionLocal
    from app.services.settings_service import get_section
    client = TestClient(app)
    assert client.put('/v1/settings/embedding-channel', json={'endpoint': 'file:///x'}).status_code == 422
    assert client.put('/v1/settings/embedding-channel', json={'endpoint': 'http://server:1234'}).status_code == 200
    with SessionLocal() as db:
        assert get_section(db, 'memory')['embedding_endpoint'] == 'http://server:1234'
    async def fail(self, texts, *, query=False):
        raise httpx.ConnectError('remote unavailable')
    monkeypatch.setattr(EmbeddingChannel, 'embed', fail)
    assert client.post('/v1/settings/embedding-channel/test').status_code == 502


def test_authenticated_embedding_channel_scopes_credentials_and_preserves_profile(monkeypatch):
    from app.db import SessionLocal
    from app.routers.embedding_channel import configured_channel
    from app.services.eg2_memory import EG2MemoryAdapter
    from app.services.settings_service import save_section

    key = 'test-kiara-credential'
    endpoint = 'http://kiara:17841/v1'
    with SessionLocal() as db:
        save_section(db, 'ai', {'provider': 'openai_compatible', 'base_url': 'http://kiara:17841', 'api_key': key})
        save_section(db, 'memory', {'embedding_endpoint': endpoint, 'embedding_model': 'google/embeddinggemma-2'})
        diagnostic = configured_channel(db)
    production = EG2MemoryAdapter(SessionLocal).channel
    assert diagnostic.api_key == production.api_key == key
    assert key not in repr(production)
    assert production.profile == EmbeddingChannel(endpoint, model=production.model, api_key='rotated').profile

    def respond(request):
        assert request.headers['Authorization'] == 'Bearer ' + key
        assert request.url.path == '/v1/embeddings'
        return httpx.Response(200, json={'data': [{'index': 0, 'embedding': [1.] * 768}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    assert len(asyncio.run(production.embed(['authenticated request']))[0]) == 768
    for other in ('http://other:17841/v1', 'http://kiara:17842/v1', 'https://kiara:17841/v1',
                  'http://kiara:17841/other/v1', 'http://kiara.evil:17841/v1'):
        with SessionLocal() as db:
            save_section(db, 'memory', {'embedding_endpoint': other})
            assert configured_channel(db).api_key == ''
        assert EG2MemoryAdapter(SessionLocal).channel.api_key == ''


def test_embedding_connection_check_uses_same_scoped_credential(monkeypatch):
    from app.services import connection_health
    calls = []

    def respond(url, key='', payload=None, timeout_s=600):
        calls.append((url, key))
        return {'data': [{'embedding': [1.] * 768}]}

    monkeypatch.setattr(connection_health, 'http_json', respond)
    ai = {'provider': 'openai_compatible', 'base_url': 'http://kiara:17841', 'api_key': 'secret'}
    assert connection_health.embedding_check(ai, {'embedding_endpoint': 'http://kiara:17841/v1'})['state'] == 'ok'
    assert calls[-1] == ('http://kiara:17841/v1/embeddings', 'secret')
    connection_health.embedding_check(ai, {'embedding_endpoint': 'http://other:17841'})
    assert calls[-1][1] == ''


@pytest.mark.parametrize('busy_status', [429, 503])
def test_busy_relay_recovers_without_switching_models_and_limits_retries(monkeypatch, busy_status):
    calls, delays = [], []
    status = [busy_status, 200]

    def respond(request):
        import json
        calls.append(json.loads(request.content))
        return httpx.Response(status.pop(0) if status else 429, headers={'Retry-After': '1'},
                              json={'data': [{'index': 0, 'embedding': [1.] * 768}]})

    async def sleep(delay):
        delays.append(delay)

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    monkeypatch.setattr(asyncio, 'sleep', sleep)
    channel = EmbeddingChannel('http://kiara:17841', model='google/embeddinggemma-2')
    assert len(asyncio.run(channel.embed(['question'], query=True))[0]) == 768
    assert calls[0] == calls[1] and delays == [1]
    calls.clear()
    with pytest.raises(httpx.HTTPStatusError) as error:
        asyncio.run(channel.embed(['still busy']))
    assert error.value.response.status_code == 429
    assert len(calls) == 20


def test_embedding_retry_releases_slot_and_does_not_wait_for_generation(monkeypatch):
    from app.services.inference_scheduler import async_lease, engine_key

    endpoint = 'http://kiara:8766'
    attempts = []

    def respond(request):
        import json
        content = json.loads(request.content)['input'][0]
        attempts.append(content)
        if len(attempts) == 1:
            return httpx.Response(429, headers={'Retry-After': '1'})
        return httpx.Response(200, json={'data': [{'index': 0, 'embedding': [1.] * 768}]})

    original_client = httpx.AsyncClient
    original_sleep = asyncio.sleep
    channel = EmbeddingChannel(endpoint, timeout_s=2)
    monkeypatch.setattr(httpx, 'AsyncClient',
                        lambda **kw: original_client(transport=httpx.MockTransport(respond), **kw))

    async def on_retry(delay):
        if delay == 1:
            await channel.embed(['question'], query=True)
        else:
            await original_sleep(delay)

    monkeypatch.setattr(asyncio, 'sleep', on_retry)

    async def run():
        async with async_lease(engine_key(endpoint)):
            await channel.embed(['document'])

    asyncio.run(run())
    assert attempts == ['title: none | text: document', 'task: search result | query: question',
                        'title: none | text: document']


def test_unified_search_sends_configured_key_and_uses_existing_vectors(tmp_path, monkeypatch):
    import uuid
    from app.db import SessionLocal
    from app.models import Project, Source, SourceArtifact
    from app.services.eg2_memory import EG2MemoryAdapter
    from app.services.settings_service import save_section

    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'owner')
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS', raising=False)
    calls = []

    def respond(request):
        assert request.headers['Authorization'] == 'Bearer test-search-key'
        calls.append(request.url.path)
        return httpx.Response(200, json={'data': [{'index': 0, 'embedding': [1.] * 768}]})

    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(respond), **kw))
    text = 'Le fournisseur annonce un retard de livraison.'
    with SessionLocal() as db:
        save_section(db, 'ai', {'provider': 'openai_compatible', 'base_url': 'http://kiara:17841', 'api_key': 'test-search-key'})
        save_section(db, 'memory', {'embedding_endpoint': 'http://kiara:17841', 'embedding_model': 'google/embeddinggemma-2',
                                    'index_path': str(tmp_path / 'search.db')})
        project = Project(code='KIARA-' + uuid.uuid4().hex, name='Essai recherche authentifiée')
        db.add(project)
        db.flush()
        source = Source(project_id=project.id, status='resolved', source_type='document', original_uri='test://kiara', sha256=uuid.uuid4().hex)
        db.add(source)
        db.flush()
        db.add(SourceArtifact(source_id=source.id, kind='body_text', content_text=text))
        db.commit()
        pid, sid = project.id, source.id
    adapter = EG2MemoryAdapter(SessionLocal)
    asyncio.run(adapter.remember_evidence(pid, text, {'source_id': sid}))
    before = adapter.path.read_bytes()
    response = TestClient(app).get('/v1/search', params={'q': 'décalage approvisionnement', 'project_id': pid})
    assert response.status_code == 200
    assert response.json()['semantic_status'] == 'ok'
    assert response.json()['items'][0]['source_id'] == sid
    assert adapter.path.read_bytes() == before
    assert calls == ['/v1/embeddings', '/v1/embeddings']
