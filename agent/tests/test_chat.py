"""Assistant mémoire : rappel + synthèse, sources qualifiées, sans LLM réel."""
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app)


def _enable_ai():
    r = c.put("/v1/settings/ai", json={"provider": "ollama", "enabled": True})
    assert r.status_code == 200, r.text


def _disable_ai():
    c.put("/v1/settings/ai", json={"provider": "ollama", "enabled": False})


def _project(code="CHAT-1"):
    r = c.post("/v1/projects", json={"code": code, "name": "Chat test"})
    if r.status_code == 409:
        projects = c.get("/v1/projects").json()
        return next(p for p in projects if p["code"] == code)["id"]
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_chat_requires_enabled_ia():
    _disable_ai()
    pid = _project()
    r = c.post("/v1/projects/chat", json={"query": "jalon ?", "project_id": pid})
    assert r.status_code == 409


def test_chat_unknown_project():
    _enable_ai()
    try:
        r = c.post("/v1/projects/chat",
                   json={"query": "jalon ?", "project_id": "00000000-0000-0000-0000-000000000000"})
        assert r.status_code == 404
    finally:
        _disable_ai()


def test_chat_synthesis_and_citations(monkeypatch):
    import app.routers.core as core
    import app.services.ai_client as ai_client

    pid = _project()

    async def fake_recall(project_id, query, scopes):
        assert query == "date FAT"
        out = []
        if "truth" in scopes:
            out.append({"scope": "truth", "level": "validated", "kind": "milestone",
                        "subject": "FAT", "value": "18/12", "id": "k1"})
        if "evidence" in scopes:
            out.append({"scope": "evidence", "level": "proposed",
                        "text": "le client envisage janvier", "source_id": "s1"})
        return out

    seen = {}

    def fake_chat(cfg, messages, max_tokens=1000, timeout=180):
        seen["n_messages"] = len(messages)
        assert "[V]" in messages[0]["content"] and "[P]" in messages[0]["content"]
        assert "FAT" in messages[1]["content"]
        return "La FAT est au 18/12 [V]. Janvier est évoqué [P]."

    class FakeAdapter:
        async def recall(self, project_id, query, scopes):
            return await fake_recall(project_id, query, scopes)

        async def health(self):
            return {"engine": "fake", "status": "ok"}

    monkeypatch.setattr(core, "get_memory_adapter", lambda db_factory=None: FakeAdapter())
    monkeypatch.setattr(ai_client, "chat_text", fake_chat)
    _enable_ai()
    try:
        r = c.post("/v1/projects/chat",
                   json={"query": "date FAT", "project_id": pid})
        assert r.status_code == 200, r.text
        body = r.json()
        assert "[V]" in body["answer"] and "[P]" in body["answer"]
        assert body["engine"] == "FakeAdapter"
        assert body["projects_queried"] == ["CHAT-1"]
        by_level = {ci["level"] for ci in body["citations"]}
        assert by_level == {"validated", "proposed"}
        assert all(ci["project_code"] == "CHAT-1" for ci in body["citations"])
        assert {ci["reference"] for ci in body["citations"]} == {"V1", "P1"}
    finally:
        _disable_ai()


def test_chat_empty_answer_is_502(monkeypatch):
    import app.routers.core as core
    import app.services.ai_client as ai_client

    pid = _project()

    class FakeAdapter:
        async def recall(self, project_id, query, scopes):
            return [{"scope": "truth", "level": "validated", "value": "x"}]

        async def health(self):
            return {"engine": "fake", "status": "ok"}

    monkeypatch.setattr(core, "get_memory_adapter", lambda db_factory=None: FakeAdapter())
    monkeypatch.setattr(ai_client, "chat_text", lambda *a, **k: None)
    _enable_ai()
    try:
        r = c.post("/v1/projects/chat", json={"query": "date FAT", "project_id": pid})
        assert r.status_code == 502
    finally:
        _disable_ai()


def test_chat_sends_complete_long_evidence_and_returns_complete_citation(monkeypatch):
    import app.routers.core as core
    import app.services.ai_client as ai_client

    pid = _project('CHAT-LONG-CONTEXT')
    text = 'Suivi technique. ' * 500 + 'Décision finale : inox 316L, certificat M74.'

    class Adapter:
        async def recall(self, project_id, query, scopes):
            return [{'scope': 'evidence', 'level': 'proposed', 'text': text, 'source_id': 'long-source'}]

    def answer(cfg, messages, **kwargs):
        assert text in messages[-1]['content']
        return 'Inox 316L, certificat M74 [P1].'

    monkeypatch.setattr(core, 'get_memory_adapter', lambda db_factory=None: Adapter())
    monkeypatch.setattr(ai_client, 'chat_text', answer)
    _enable_ai()
    try:
        response = c.post('/v1/projects/chat', json={'query': 'matériau ?', 'project_id': pid})
        assert response.status_code == 200, response.text
        assert response.json()['citations'][0]['excerpt'] == text
    finally:
        _disable_ai()
