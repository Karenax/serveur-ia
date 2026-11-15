"""Server-managed inference configuration applies without rewriting Agent settings."""

from app.db import SessionLocal
from app.services.settings_service import get_all, get_section


def test_managed_gateway_settings_do_not_expose_secret(monkeypatch):
    monkeypatch.setenv('AGENT_KIARA_INFERENCE_URL', 'http://127.0.0.1:8766')
    monkeypatch.setenv('PB_API_KEY', 'test-internal-secret')
    with SessionLocal() as db:
        ai = get_section(db, 'ai')
        memory = get_section(db, 'memory')
        public = get_all(db)
    assert ai['enabled'] and ai['provider'] == 'openai_compatible'
    assert ai['base_url'] == memory['embedding_endpoint'] == 'http://127.0.0.1:8766'
    assert memory['embedding_model'] == 'google/embeddinggemma-2'
    assert ai['api_key'] == 'test-internal-secret'
    assert public['ai']['enabled'] and public['ai']['provider'] == 'openai_compatible'
    assert public['memory']['embedding_endpoint'] == 'http://127.0.0.1:8766'
    assert 'test-internal-secret' not in str(public)
