"""Regressions for the concrete security and context failures of the audit."""
from pathlib import Path
import uuid

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.db import SessionLocal as Brain
from app.models import Project as BrainProject, Source, KnowledgeItem, ProvenanceLink
from app.services.knowledge_context import contexts
from app.services.memory_port import canonical_truth
from backend.app.db import SessionLocal as ERP
from backend.app.models import Project, NetworkLink

client = TestClient(app)


@pytest.fixture(autouse=True)
def owner(monkeypatch):
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'owner')
    monkeypatch.setenv('AGENT_OPERATOR_ID', 'local-reviewer')
    monkeypatch.delenv('AGENT_OPERATOR_PROJECT_IDS', raising=False)


def project():
    return client.post('/api/v1/projects', json={'code': 'SEC-' + uuid.uuid4().hex[:10], 'title': 'Audit fictif'}).json()['id']


def test_legacy_reader_links_are_virtual_and_do_not_write(monkeypatch):
    with ERP() as db:
        row = Project(code='LEG-' + uuid.uuid4().hex, title='Ancien projet fictif')
        db.add(row)
        db.commit()
        pid = row.id
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    response = client.get(f'/api/v1/projects/{pid}/network-links')
    assert response.status_code == 200 and len(response.json()) == 3
    with ERP() as db:
        assert db.query(NetworkLink).filter_by(project_id=pid).count() == 0


def test_new_projects_seed_links_in_the_creation_transaction():
    pid = project()
    with ERP() as db:
        assert db.query(NetworkLink).filter_by(project_id=pid).count() == 3


@pytest.mark.parametrize('code', ['../outside', 'x\\..\\outside', 'C:outside', '..', 'x\nvalue'])
def test_new_reference_rejects_path_components(code):
    assert client.post('/api/v1/projects', json={'code': code, 'title': 'Fictif'}).status_code == 422


def test_exports_are_distinct_downloads_and_legacy_codes_never_write(tmp_path, monkeypatch):
    pid = project()
    with ERP() as db:
        db.get(Project, pid).code = 'x/../../legacy-path'
        db.commit()
    mids = [client.post(f'/api/v1/projects/{pid}/meetings', json={
        'date': '2026-10-22', 'title': f'Réunion fictive {i}', 'decisions': f'Décision {i}'}).json()['id'] for i in range(2)]
    monkeypatch.setenv('MINIPILOT_HOME', str(tmp_path))
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    exports = [client.get(f'/api/v1/projects/{pid}/meetings/{mid}/export').json() for mid in mids]
    assert exports[0]['filename'] != exports[1]['filename']
    assert not list(tmp_path.iterdir())
    for item in exports:
        assert Path(item['filename']).name == item['filename']
        download = client.get(item['download_url'])
        assert download.status_code == 200 and download.text == item['markdown']
        assert 'attachment' in download.headers['content-disposition']


@pytest.mark.parametrize('multipart', [False, True])
def test_streaming_budget_rejects_unannounced_oversize_even_when_parser_catches_it(monkeypatch, multipart):
    from app import http_protection
    monkeypatch.setattr(http_protection, 'body_budget', lambda path: 128)
    demo = FastAPI()
    demo.add_middleware(http_protection.HTTPProtection)
    @demo.post('/sink')
    async def sink(request: Request):
        if multipart:
            try:
                await request.form()
            except Exception:
                return {'parser': 'failed'}
        else:
            await request.body()
        return {'accepted': True}
    data = [b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="f.txt"\r\n\r\n',
            b'x' * 256, b'\r\n--boundary--\r\n'] if multipart else [b'x' * 64] * 3
    result = TestClient(demo).post('/sink', content=iter(data), headers={
        'Content-Type': 'multipart/form-data; boundary=boundary' if multipart else 'application/octet-stream'})
    assert result.status_code == 413 and result.json()['detail'] == 'Requête trop volumineuse'


def test_security_headers_allow_mail_opt_in_but_deny_embedding():
    response = client.get('/')
    assert response.headers['x-frame-options'] == 'DENY'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert 'no-store' in response.headers['cache-control']
    policy = response.headers['content-security-policy']
    assert "frame-ancestors 'none'" in policy and "script-src 'self';" in policy
    assert 'img-src' in policy and 'https:' in policy


def test_oversize_during_multipart_stream_closes_open_temporary_files(monkeypatch):
    import asyncio
    from starlette import formparsers
    from app import http_protection
    monkeypatch.setattr(http_protection, 'body_budget', lambda path: 128)
    opened = []
    factory = formparsers.SpooledTemporaryFile

    def tracked_file(*args, **kwargs):
        value = factory(*args, **kwargs)
        opened.append(value)
        return value

    monkeypatch.setattr(formparsers, 'SpooledTemporaryFile', tracked_file)
    demo = FastAPI()
    demo.add_middleware(http_protection.HTTPProtection)

    @demo.post('/sink')
    async def sink(request: Request):
        await request.form()
        return {'accepted': True}

    chunks = [b'--audit\r\nContent-Disposition: form-data; name="file"; filename="x.txt"\r\n\r\n',
              b'x' * 16, b'y' * 128]
    messages = []

    async def receive():
        return {'type': 'http.request', 'body': chunks.pop(0), 'more_body': bool(chunks)}

    async def send(message):
        messages.append(message)

    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
             'method': 'POST', 'scheme': 'http', 'path': '/sink', 'query_string': b'',
             'headers': [(b'content-type', b'multipart/form-data; boundary=audit')],
             'server': ('test', 80), 'client': ('test', 1), 'root_path': ''}
    asyncio.run(demo(scope, receive, send))
    assert next(message['status'] for message in messages if message['type'] == 'http.response.start') == 413
    assert len(opened) == 1 and opened[0].closed


@pytest.fixture
def retained():
    with Brain() as db:
        p = BrainProject(code='KN-' + uuid.uuid4().hex, name='Contexte fictif')
        db.add(p)
        db.flush()
        source = Source(project_id=p.id, status='resolved', source_type='document',
                        original_uri='test://retained-document',
                        sha256=uuid.uuid4().hex * 2, source_metadata={'superseded': True})
        item = KnowledgeItem(project_id=p.id, kind='requirement', subject='Pression maximale', value='10 bars',
                             status='validated', validated_by='auto-default')
        db.add_all([source, item])
        db.flush()
        db.add(ProvenanceLink(knowledge_item_id=item.id, source_id=source.id))
        db.commit()
        return p.id, source.id, item.id


def test_superseded_auto_fact_is_not_recalled_as_current_but_human_history_is_preserved(retained):
    pid, sid, kid = retained
    assert not canonical_truth(Brain, pid, 'pression')
    with Brain() as db:
        db.get(KnowledgeItem, kid).validated_by = 'human-reviewer'
        db.commit()
    hit = canonical_truth(Brain, pid, 'pression')[0]
    assert hit['value'] == '10 bars' and hit['context']['source_state'] == 'historical'
    assert hit['validation_mode'] == 'human'


def test_already_historical_context_is_flagged_before_and_after_generation(retained):
    from app.services.chat_freshness import freeze, finalize
    with Brain() as db:
        metadata = freeze(db, {'citations': [{'source_id': retained[1], 'knowledge_id': retained[2], 'excerpt': '10 bars'}]})
        result = finalize(db, metadata)
        assert result['stale'] is True
        assert any('historique' in warning for warning in result['warnings'])
        assert not any('pendant la réponse' in warning for warning in result['warnings'])


def test_confirmation_requires_current_unique_evidence_and_records_server_identity(retained):
    pid, sid, kid = retained
    path = f'/v1/projects/{pid}/knowledge/{kid}/confirm'
    assert client.post(path, json={'actor': 'claimed-boss'}).status_code == 409
    with Brain() as db:
        db.get(Source, sid).source_metadata = {}
        db.commit()
    assert client.post(path, json={'actor': 'claimed-boss'}).status_code == 200
    with Brain() as db:
        assert db.get(KnowledgeItem, kid).validated_by == 'local-reviewer'
        assert not contexts(db, [db.get(KnowledgeItem, kid)])[kid]['can_confirm']


def test_conflicting_defaults_require_an_explicit_resolution(retained):
    pid, sid, kid = retained
    with Brain() as db:
        db.get(Source, sid).source_metadata = {}
        db.add(KnowledgeItem(project_id=pid, kind='requirement', subject='Pression maximale', value='6 bars',
                             status='validated', validated_by='auto-default'))
        db.commit()
    assert client.post(f'/v1/projects/{pid}/knowledge/{kid}/confirm', json={}).status_code == 409
    listing = client.get('/api/v1/workspace/knowledge', params={'project_id': pid, 'review_only': 'true'}).json()
    assert listing['total'] == 2 and all(item['context']['needs_review'] for item in listing['items'])


def test_storage_refusal_precedes_any_write(tmp_path, monkeypatch):
    from app.services import storage_capacity
    monkeypatch.setattr(storage_capacity.shutil, 'disk_usage', lambda path: type('Usage', (), {'free': 1024})())
    with pytest.raises(Exception) as error:
        storage_capacity.require_capacity(tmp_path / 'not-created', 2048)
    assert error.value.status_code == 507 and not list(tmp_path.iterdir())


def test_secret_redaction_preserves_public_settings_and_safe_log_text():
    import logging
    from app.services.logging_setup import RedactingFormatter
    from app.services.settings_service import public_settings
    value = {'nested': [{'access_token': 'private-token', 'name': 'Visible'}], 'api_key_set': True}
    public = public_settings(value)
    assert public == {'nested': [{'access_token_set': True, 'name': 'Visible'}], 'api_key_set': True}
    record = logging.LogRecord('audit', logging.WARNING, '', 1,
        'Reprise nécessaire : api_key="private key with spaces" Authorization: Bearer token-123 dpapi:YWJj', (), None)
    text = RedactingFormatter('%(message)s').format(record)
    assert 'Reprise nécessaire' in text and all(value not in text for value in ['private key', 'with spaces', 'token-123', 'YWJj'])


def test_document_parser_timeout_is_bounded_and_original_is_preserved(tmp_path, monkeypatch):
    from app.services import document_sandbox
    original = tmp_path / 'retained.txt'
    original.write_text('Original fictif conservé', encoding='utf-8')
    monkeypatch.setattr(document_sandbox, 'EXTRACTION_TIMEOUT_SECONDS', 0.001)
    with pytest.raises(ValueError, match='trop longue'):
        document_sandbox.extract(original, original.name, 'library')
    assert original.read_text(encoding='utf-8') == 'Original fictif conservé'


def test_document_parser_does_not_inherit_the_agent_supervision_pipe(tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    original = tmp_path / 'original.txt'
    original.write_text('Texte de recette pour les jalons.', encoding='utf-8')
    root = Path(__file__).resolve().parents[1]
    # Keep the parent's pipe open as the Kiara supervisor does for Agent.
    script = ('from pathlib import Path; import sys; '
              'from app.services.document_sandbox import extract_cdc; '
              'path = Path(sys.argv[1]); print(extract_cdc(path, path.name)[0].text)')
    with subprocess.Popen([sys.executable, '-c', script, str(original)], cwd=root,
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as parent:
        try:
            assert parent.wait(timeout=20) == 0, parent.stderr.read().decode(errors='replace')
            assert b'Texte de recette' in parent.stdout.read()
        finally:
            if parent.poll() is None:
                parent.kill()


def test_runtime_console_and_file_both_redact_secrets_and_tracebacks(tmp_path, monkeypatch):
    import io
    import logging
    from app.services import logging_setup
    stream = io.StringIO()
    console = logging.StreamHandler(stream)
    console.setFormatter(logging.Formatter('SERVER %(levelname)s %(message)s'))
    loggers = [logging.getLogger(name) for name in ('', 'uvicorn', 'uvicorn.error', 'uvicorn.access')]
    for logger in loggers:
        monkeypatch.setattr(logger, 'handlers', [])
    loggers[1].addHandler(console)
    monkeypatch.setattr(loggers[1], 'propagate', False)
    monkeypatch.setattr(logging_setup, 'STORAGE_DIR', tmp_path)
    logging_setup.configure_logging()
    try:
        try:
            raise ValueError('password="secret in traceback"')
        except ValueError:
            loggers[1].error('Reprise : access_token="secret in message"', exc_info=True)
        for text in [stream.getvalue(), (tmp_path / 'logs/agent.log').read_text(encoding='utf-8')]:
            assert 'secret in' not in text and 'ValueError' in text and 'Reprise' in text
        assert 'SERVER ERROR' in stream.getvalue()
    finally:
        for existing in loggers[0].handlers:
            existing.close()


def test_reader_cannot_confirm_retained_fact(retained, monkeypatch):
    monkeypatch.setenv('AGENT_OPERATOR_ROLE', 'reader')
    assert client.post(f'/v1/projects/{retained[0]}/knowledge/{retained[2]}/confirm', json={}).status_code == 403
