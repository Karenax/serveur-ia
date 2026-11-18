"""Real HTTP/internal policy, cross-store scopes, filtered lists and no role spoofing."""
import asyncio
import hashlib
import json
import os
import re
import uuid
from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi.staticfiles import StaticFiles
import pytest

from app import main as web_application
from app.main import app
from app.db import SessionLocal as Brain
from app.models import AuditLog, KnowledgeItem, Project as BrainProject, Proposal, Source
from app.workspace_models import AssistantThread
from app.services import local_dispatch
from app.services.project_access import authorize
from backend.app.db import SessionLocal as ERP
from backend.app.models import BrainLink, Meeting, Milestone
from backend.app.project_identity_schemas import IdentityPatch, PersonCreate, ReferenceCreate
from backend.app.services import project_identity as identity

client = TestClient(app)


def test_missing_project_bundle_reports_unavailability(tmp_path, monkeypatch):
    monkeypatch.setattr(web_application, "MP_WEB_DIST", tmp_path)
    for path in ("/", "/app", "/app/projets"):
        response = client.get(path)
        assert response.status_code == 503
        assert response.json()["detail"] == "L’interface Projets de Kiara est indisponible."
    assert client.get("/static/index.html").status_code == 404


@pytest.fixture
def context(monkeypatch):
    monkeypatch.delenv("AGENT_OPERATOR_PROJECT_IDS", raising=False)
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "owner")
    pids, bids, sources, proposals, threads = [], [], [], [], []
    code = "ACCESS-" + uuid.uuid4().hex[:12]
    for index in range(2):
        pid = client.post("/api/v1/projects", json={"code": code + str(index), "title": f"Accès {index}"}).json()["id"]
        with Brain() as db:
            p = BrainProject(code=code + str(index), name=f"Accès {index}")
            db.add(p)
            db.flush()
            source = Source(project_id=p.id, status="resolved", source_type="email", author="Fictif",
                            original_uri="test://access", sha256=uuid.uuid4().hex * 2)
            db.add(source)
            db.flush()
            proposal = Proposal(project_id=p.id, source_id=source.id, kind="decision", subject="Accès décision",
                                value=f"Projet {index}", status="pending")
            thread = AssistantThread(project_id=p.id, title=f"Accès conversation {index}")
            db.add_all([proposal, thread, KnowledgeItem(project_id=p.id, kind="decision", subject="Accès validé",
                                                       value=f"Projet {index}", status="validated")])
            db.commit()
            bids.append(p.id)
            sources.append(source.id)
            proposals.append(proposal.id)
            threads.append(thread.id)
        with ERP() as db:
            db.add(BrainLink(project_id=pid, brain_project_id=bids[-1], brain_code=code + str(index)))
            db.add(Meeting(project_id=pid, title=f"Accès réunion {index}"))
            db.commit()
        pids.append(pid)
    return {"pids": pids, "bids": bids, "sources": sources, "proposals": proposals, "threads": threads, "code": code}


def role(monkeypatch, value, projects=None):
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", value)
    monkeypatch.setenv("AGENT_OPERATOR_ID", "test-operator")
    if projects is not None:
        monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", json.dumps(projects))


def test_audio_integrity_respects_project_scope(context, monkeypatch):
    permitted, other = context['pids']
    role(monkeypatch, 'owner')
    raw = b'audio-fictif-protege'
    upload = client.post(f'/api/v1/projects/{permitted}/recordings',
                         data={'title':'Réunion fictive', 'date':'2026-11-18', 'num_speakers':0},
                         files={'file':('projet.wav',raw,'audio/wav')})
    assert upload.status_code == 201
    url = f"/api/v1/projects/{permitted}/recordings/{upload.json()['id']}/audio-integrity"
    role(monkeypatch, 'reader', [other])
    assert client.get(url).status_code == 404
    role(monkeypatch, 'reader', [permitted])
    response = client.get(url)
    assert response.status_code == 200 and response.json()['sha256'] == hashlib.sha256(raw).hexdigest()


def test_legacy_knowledge_project_link_opens_the_authorized_kiara_project(context, monkeypatch):
    project, other = context["pids"]
    brain = context["bids"][0]
    with ERP() as db:
        db.get(BrainLink, other).brain_project_id = brain
        db.commit()
    url = f"/ui/projects/{brain}"
    overview = client.get(url, follow_redirects=False)
    assert overview.status_code == 307
    assert overview.headers["location"] == f"/app/knowledge?knowledge_project={brain}"
    role(monkeypatch, "reader", [project])
    response = client.get(url, follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == f"/app/projets/{project}/documents/connaissance"


def test_portal_rollback_preserves_writes_and_project_scopes(context, monkeypatch):
    bundle_vars = ("KIARA_REHEARSAL_PREVIOUS_WEB", "KIARA_REHEARSAL_CANDIDATE_WEB")
    if not all(os.environ.get(key) for key in bundle_vars):
        pytest.skip("La répétition requiert les deux bundles de déploiement.")
    previous, candidate = (Path(os.environ[key]).resolve(strict=True) for key in bundle_vars)
    assert previous != candidate
    # Default retains the historical legacy-to-current exercise. A later
    # candidate can also be rehearsed against the immediately preceding build.
    previous_legacy = os.environ.get("KIARA_REHEARSAL_PREVIOUS_LEGACY", "1") == "1"
    markers = ("Redimensionner l’assistant", "Des réponses ancrées dans vos sources")
    routes = [route for route in app.router.routes if getattr(route, "path", None) != "/assets"]

    def serve_bundle(directory, legacy):
        monkeypatch.setattr(web_application, "MP_WEB_DIST", directory)
        monkeypatch.setattr(app.router, "routes", routes.copy())
        app.mount("/assets", StaticFiles(directory=directory / "assets"), name="mp-assets")
        page = client.get("/app/projets")
        assert page.status_code == 200
        assert page.text == (directory / "index.html").read_text(encoding="utf-8")
        asset = re.search(r'src="(/assets/[^"]+\.js)"', page.text).group(1)
        payload = client.get(asset)
        assert payload.status_code == 200
        assert payload.content == (directory / asset.removeprefix("/")).read_bytes()
        assert any(marker in payload.text for marker in markers) is legacy
        return hashlib.sha256(payload.content).hexdigest()

    permitted, excluded = context["pids"]
    role(monkeypatch, "owner", [permitted])
    before = serve_bundle(previous, legacy=previous_legacy)
    existing_path = "/api/v1/workspace/assistant-threads/" + context["threads"][0]
    assert client.get(existing_path).status_code == 200

    after = serve_bundle(candidate, legacy=False)
    assert before != after
    endpoint = "/api/v1/workspace/assistant-threads"
    initial = [{"role": "user", "text": "Écriture effectuée pendant le pilote"}]
    created = client.post(endpoint, json={"project_id": context["bids"][0],
                                          "title": "Fil de recette du pilote", "messages": initial})
    assert created.status_code == 201, created.text
    pilot = created.json()
    path = endpoint + "/" + pilot["id"]

    assert serve_bundle(previous, legacy=previous_legacy) == before
    assert client.get(path).json() == pilot
    assert client.get(existing_path).status_code == 200
    role(monkeypatch, "reader", [excluded])
    assert client.get(path).status_code == 404
    role(monkeypatch, "owner", [permitted])
    messages = initial + [{"role": "assistant", "text": "Suite sur la version rétablie"}]
    saved = client.put(path, json={"messages": messages, "expected_revision": pilot["revision"]})
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] == pilot["revision"] + 1

    assert serve_bundle(candidate, legacy=False) == after
    assert client.get(path).json()["messages"] == messages


@pytest.mark.parametrize("method,path", [
    ("POST", "/api/v1/projects"), ("PATCH", "/api/v1/projects/{pid}"),
    ("POST", "/api/v1/projects/{pid}/tasks"), ("POST", "/api/v1/projects/{pid}/cdc/items"),
    ("POST", "/api/v1/projects/{pid}/milestones/scan"), ("POST", "/api/v1/projects/{pid}/recordings"),
    ("POST", "/api/v1/projects/import-json"), ("POST", "/api/v1/workspace/triage-jobs"),
    ("POST", "/v1/projects"), ("POST", "/v1/sources"), ("PUT", "/v1/settings/ai"),
    ("POST", "/v1/proposals/{proposal}/accept"), ("POST", "/v1/projects/{bid}/memory/reindex"),
    ("DELETE", "/api/v1/projects/{pid}/brain"), ("POST", "/api/v1/open-path"),
])
def test_reader_write_denial_precedes_endpoint_and_cannot_be_spoofed(context, monkeypatch, method, path):
    role(monkeypatch, "reader")
    path = path.format(pid=context["pids"][0], bid=context["bids"][0], proposal=context["proposals"][0])
    out = client.request(method, path, json={"actor": "owner", "role": "owner"}, headers={"x-operator-role": "owner"})
    assert out.status_code == 403, out.text


def test_session_exposes_trusted_role_without_allowing_change(context, monkeypatch):
    role(monkeypatch, "reader", [context["pids"][0]])
    out = client.get("/api/v1/session").json()
    assert out["operator"] == {"id": "test-operator", "role": "reader", "can_edit": False, "can_administer": False,
                                "project_ids": [context["pids"][0]]}
    assert out["token"]
    assert client.get("/health").status_code == 200
    assert client.get("/app/projects").status_code == 200


def test_scoped_mail_validation_keeps_other_projects_private(context, monkeypatch):
    first, second = context['bids']
    with Brain() as db:
        records = []
        for target in (first, second):
            source = Source(status='resolution_pending', source_type='email', author='Tri de recette',
                            original_uri='test://triage', sha256=uuid.uuid4().hex * 2)
            db.add(source)
            db.flush()
            proposal = Proposal(source_id=source.id, project_id=target, kind='project_attach', status='pending',
                                subject='Tri de recette', value='{}', confidence=.8)
            db.add(proposal)
            db.flush()
            records.append((source.id, proposal.id))
        db.commit()
    role(monkeypatch, 'owner', [context['pids'][0]])
    visible, hidden = records
    page = client.get('/v1/mail/page?scope=pending&q=Tri%20de%20recette').json()
    assert [row['source_id'] for row in page['rows']] == [visible[0]]
    assert client.get(f'/v1/sources/{visible[0]}').status_code == 200
    assert client.get(f'/v1/sources/{hidden[0]}').status_code == 404
    assert client.post(f'/api/v1/brain/triage/{hidden[1]}/accept', json={}).status_code == 404
    assert client.post(f'/api/v1/brain/triage/{visible[1]}/assign', json={'project_id': second}).status_code == 404
    assert client.post('/api/v1/workspace/triage-jobs', json={}).status_code == 403
    result = client.post(f'/api/v1/brain/triage/{visible[1]}/accept', json={'actor': 'spoofed'})
    assert result.status_code == 200, result.text
    with Brain() as db:
        assert db.get(Source, visible[0]).project_id == first
        assert db.get(Source, hidden[0]).status == 'resolution_pending'
        assert db.query(AuditLog.actor).filter(AuditLog.event_type == 'source.processed.v1',
            AuditLog.payload['source_id'].as_string() == visible[0]).scalar() == 'test-operator'


def test_thunderbird_reply_context_only_prepares_replies_to_visible_classified_mail(context, monkeypatch):
    allowed, hidden = context['sources']
    with Brain() as db:
        for key in (allowed, hidden):
            db.get(Source, key).source_metadata = {'message_id': f'<{key}@example.test>'}
        db.commit()
    role(monkeypatch, 'owner', [context['pids'][0]])
    monkeypatch.setenv('AGENT_OPERATOR_ID', 'kiara-thunderbird-reply')
    status = client.get('/v1/thunderbird/status').json()
    assert status['reply_only'] is True
    assert 'folders' not in status and 'jobs' not in status
    assert client.get('/v1/sources').status_code == 403
    assert client.post('/v1/thunderbird/bridge/jobs/claim').status_code == 403
    draft = {'identity_id': 'recette', 'to': ['contact@example.test'], 'subject': 'Réponse de recette', 'body': 'Texte fictif'}
    assert client.post('/v1/thunderbird/drafts', json=draft).status_code == 403
    assert client.post('/v1/thunderbird/drafts', json={**draft, 'reply_source_id': hidden}).status_code == 404
    response = client.post('/v1/thunderbird/drafts', json={**draft, 'reply_source_id': allowed})
    assert response.status_code == 200, response.text
    try:
        assert response.json()['status'] == 'queued'
    finally:
        from app.models import ThunderbirdJob
        with Brain() as db:
            db.query(ThunderbirdJob).filter_by(id=response.json()['job_id']).delete()
            db.commit()


def test_scoped_mail_rejection_preserves_content_and_prevents_further_triage(context, monkeypatch):
    from email.message import EmailMessage
    import hashlib

    from app.config import RAW_DIR
    from app.models import ValidationDecision
    from app.services.triage import pending_triage_query

    eml = EmailMessage()
    eml["Subject"] = "Mail de recette"
    eml.set_content("Contenu fictif")
    eml.add_attachment("Pièce fictive", filename="notice.txt")
    original = eml.as_bytes()
    digest = hashlib.sha256(original).hexdigest()
    (RAW_DIR / f"{digest}.eml").write_bytes(original)

    records = []
    with Brain() as db:
        for project_id in context["bids"]:
            source = Source(status="resolution_pending", source_type="email", original_uri="test://rejection",
                            sha256=digest if not records else uuid.uuid4().hex * 2,
                            source_metadata={"subject": "Mail de recette"})
            db.add(source)
            db.flush()
            proposal = Proposal(source_id=source.id, project_id=project_id, kind="project_attach",
                                status="pending", subject="Mail de recette", value="{}")
            db.add(proposal)
            db.flush()
            records.append((source.id, proposal.id))
        db.commit()

    visible, hidden = records
    role(monkeypatch, "reader", [context["pids"][0]])
    assert client.post(f"/v1/triage/{visible[1]}/reject").status_code == 403
    role(monkeypatch, "owner", [context["pids"][0]])
    assert client.post(f"/v1/triage/{hidden[1]}/reject").status_code == 404
    result = client.post(f"/v1/triage/{visible[1]}/reject")
    assert result.status_code == 200, result.text
    assert result.json() == {"source_id": visible[0], "status": "rejected"}
    assert client.post(f"/v1/triage/{visible[1]}/reject").status_code == 404
    assert client.get("/v1/mail/page?scope=pending&q=Mail%20de%20recette").json()["total"] == 0
    with Brain() as db:
        source = db.get(Source, visible[0])
        assert source.status == "rejected"
        assert source.source_metadata["subject"] == "Mail de recette"
        assert pending_triage_query(db, force=True).filter(Source.id == visible[0]).count() == 0
        assert db.get(Source, hidden[0]).status == "resolution_pending"
        decision = db.query(ValidationDecision).filter_by(proposal_id=visible[1]).one()
        assert (decision.decision, decision.actor) == ("reject", "test-operator")

    archive = "/v1/mail/page?scope=rejected&q=Mail%20de%20recette"
    detail = f"/v1/sources/{visible[0]}"
    assert [row["source_id"] for row in client.get(archive).json()["rows"]] == [visible[0]]
    assert client.get(detail).json()["status"] == "rejected"
    assert client.get(detail + "/raw").content == original
    assert client.get(detail + "/attachments/0").content.decode().strip() == "Pièce fictive"

    monkeypatch.setenv("AGENT_OPERATOR_ID", "other-editor")
    assert client.get(archive).json()["total"] == 0
    assert client.get(detail).status_code == 404
    assert client.get(detail + "/raw").status_code == 404
    assert client.get(detail + "/attachments/0").status_code == 404

    role(monkeypatch, "owner", [context["pids"][1]])
    assert client.get(archive).json()["total"] == 0
    assert client.get(detail).status_code == 404

    role(monkeypatch, "reader", [context["pids"][0]])
    assert client.get(archive).json()["total"] == 0
    assert client.get(detail).status_code == 404

    role(monkeypatch, "owner")
    monkeypatch.delenv("AGENT_OPERATOR_PROJECT_IDS")
    assert [row["source_id"] for row in client.get(archive).json()["rows"]] == [visible[0]]


def test_knowledge_demotion_obeys_reader_and_project_scope(context, monkeypatch):
    with Brain() as db:
        item = db.query(KnowledgeItem).filter_by(project_id=context['bids'][1]).first()
        kid = item.id
    path = f"/v1/projects/{context['bids'][1]}/knowledge/{kid}/invalidate"
    role(monkeypatch, 'reader')
    assert client.post(path, json={'actor': 'owner'}).status_code == 403
    role(monkeypatch, 'owner', [context['pids'][0]])
    assert client.post(path, json={'actor': 'owner'}).status_code == 404
    wrong = f"/v1/projects/{context['bids'][0]}/knowledge/{kid}/invalidate"
    assert client.post(wrong, json={'actor': 'owner'}).status_code == 404
    bridge = f"/api/v1/projects/{context['pids'][0]}/brain/knowledge/{kid}/invalidate"
    assert client.post(bridge, json={'actor': 'owner'}).status_code == 404


def test_scoped_reader_lists_and_counters_include_only_explicitly_linked_projects(context, monkeypatch):
    role(monkeypatch, "reader", [context["pids"][0]])
    assert [row["id"] for row in client.get("/api/v1/portfolio").json()] == [context["pids"][0]]
    assert [row["id"] for row in client.get("/v1/projects").json()] == [context["bids"][0]]
    sources = client.get("/v1/sources").json()
    assert [row["source_id"] for row in sources] == [context["sources"][0]]
    assert client.get("/v1/stats").json() == {"pending_count": 0, "proposals_count": 1}
    assert [row["id"] for row in client.get("/v1/proposals").json()] == [context["proposals"][0]]
    actions = client.get("/api/v1/actions").json()
    assert actions["pending_mails"] == 0 and all(row["project_id"] == context["pids"][0] for row in actions["actions"])
    knowledge = client.get("/api/v1/workspace/knowledge").json()
    assert knowledge["total"] == 1
    assert all(row["project_id"] == context["bids"][0] for row in knowledge["items"])
    assert all([p["id"] for p in row["erp_projects"]] == [context["pids"][0]] for row in knowledge["items"])
    assert client.get("/api/v1/workspace/meetings").json()["total"] == 1
    assert client.get("/api/v1/workspace/assistant-threads").json()["total"] == 1
    search = client.get("/api/v1/search", params={"q": "Accès"}).json()
    assert search and all(row["project_id"] == context["pids"][0] for row in search)


def test_scoped_mail_page_and_usage_never_expose_other_projects(context, monkeypatch):
    with Brain() as db:
        for project, source in zip(context['bids'], context['sources'], strict=True):
            db.add(AuditLog(event_type='source.processed.v1', project_id=project, actor='test',
                            payload={'source_id': source}))
        db.commit()
    role(monkeypatch, 'reader', [context['pids'][0]])
    response = client.get('/v1/mail/page', params={'scope': 'resolved'})
    assert response.status_code == 200
    assert response.json()['total'] == 1
    assert [row['source_id'] for row in response.json()['rows']] == [context['sources'][0]]
    assert client.get('/v1/mail/page', params={'project_id': context['bids'][1]}).status_code == 404
    assert client.get('/v1/mail/page', params={'scope': 'pending'}).status_code == 403
    usage = client.get('/v1/mail/project-usage')
    assert usage.status_code == 200
    assert [row['project_id'] for row in usage.json()['projects']] == [context['bids'][0]]


@pytest.mark.parametrize("path", [
    "/api/v1/projects/{pid}", "/api/v1/projects/{pid}/brain/knowledge",
    "/v1/projects/{bid}/knowledge", "/v1/sources/{source}",
    "/api/v1/workspace/assistant-threads/{thread}", "/ui/projects/{bid}",
])
def test_foreign_object_is_hidden_even_if_uuid_is_known(context, monkeypatch, path):
    role(monkeypatch, "reader", [context["pids"][0]])
    path = path.format(pid=context["pids"][1], bid=context["bids"][1], source=context["sources"][1], thread=context["threads"][1])
    assert client.get(path).status_code == 404


def test_empty_scope_does_not_mean_all_projects(context, monkeypatch):
    role(monkeypatch, "reader", [])
    assert client.get("/api/v1/portfolio").json() == []
    assert client.get("/v1/projects").json() == []
    assert client.get("/api/v1/workspace/knowledge").json() == {"items": [], "total": 0}


def test_http_and_internal_dispatch_enforce_same_scope_and_role(context, monkeypatch):
    role(monkeypatch, "reader", [context["pids"][0]])
    assert [row["id"] for row in local_dispatch.call("GET", "/v1/projects")] == [context["bids"][0]]
    with pytest.raises(HTTPException) as error:
        local_dispatch.call("POST", "/v1/projects", {"code": "Denied", "name": "Denied"})
    assert error.value.status_code == 403
    with pytest.raises(HTTPException) as error:
        local_dispatch.call("GET", "/v1/settings")
    assert error.value.status_code == 403
    with pytest.raises(HTTPException) as error:
        local_dispatch.call("GET", f"/v1/sources/{context['sources'][1]}")
    assert error.value.status_code == 404


def test_scoped_editor_can_modify_visible_project_but_not_foreign_project_or_administration(context, monkeypatch):
    role(monkeypatch, "editor", [context["pids"][0]])
    assert client.patch(f"/api/v1/projects/{context['pids'][0]}", json={"title": "Édition autorisée"}).status_code == 200
    assert client.patch(f"/api/v1/projects/{context['pids'][1]}", json={"title": "Interdit"}).status_code == 404
    assert client.put("/v1/settings/ai", json={}).status_code == 403
    assert client.get("/v1/settings").status_code == 403
    assert client.get("/api/v1/workspace/mail-activity").status_code == 403
    assert client.post("/api/v1/projects", json={"code": "Interdit", "title": "Interdit"}).status_code == 403
    assert client.post("/api/v1/projects/import-json", json={}).status_code == 403
    assert client.put(f"/api/v1/projects/{context['pids'][0]}/brain", json={"brain_project_id": context["bids"][1]}).status_code == 403


@pytest.mark.parametrize("action", ["transcribe", "synthesize", "cancel"])
def test_scoped_audio_commands_accept_empty_json_body_and_still_check_project(context, monkeypatch, action):
    visible, foreign = context["pids"]
    headers = {"Content-Type": "application/json"}
    target = f"/api/v1/projects/{visible}/recordings/fixture/{action}"
    role(monkeypatch, "owner", [visible])
    response = client.post(target, headers=headers)
    assert response.status_code == 404 and "Enregistrement" in response.json()["detail"]
    response = client.post(target.replace(visible, foreign), headers=headers)
    assert response.status_code == 404 and response.json()["detail"] == "Projet introuvable"
    response = client.post(target, content="{", headers=headers)
    assert response.status_code == 422 and response.json()["detail"] == "Corps JSON invalide"
    role(monkeypatch, "reader", [visible])
    assert client.post(target, headers=headers).status_code == 403


def test_query_parameter_cannot_expand_authorized_scope(context, monkeypatch):
    role(monkeypatch, "reader", [context["pids"][0]])
    assert client.get("/api/v1/workspace/knowledge", params={"project_id": context["bids"][1]}).status_code == 404
    assert client.get("/api/v1/workspace/meetings", params={"project_id": context["pids"][1]}).status_code == 404
    assert client.get("/v1/sources", params={"project_id": context["bids"][1]}).status_code == 404


def test_chat_and_recall_are_read_queries_with_project_scope(context, monkeypatch):
    role(monkeypatch, "reader", [context["pids"][0]])
    authorize("POST", f"/v1/projects/{context['bids'][0]}/memory/recall", body={"query": "Dates"})
    assert client.post("/v1/projects/chat", json={"project_id": context["bids"][1], "query": "Dates"}).status_code == 404
    allowed = client.post("/v1/projects/chat", json={"project_id": context["bids"][0], "query": "Dates"})
    assert allowed.status_code == 409 and "IA désactivée" in allowed.text


def test_private_foreign_person_cannot_be_assigned_by_known_uuid(context, monkeypatch):
    with ERP() as db:
        person = identity.create_person(db, PersonCreate(first_name="Personne", last_name="Privée"))
        ref = identity.create_reference(db, ReferenceCreate(kind="client", code="PRIVATE-" + uuid.uuid4().hex[:8], label="Privé"))
        db.commit()
    role(monkeypatch, "editor", [context["pids"][0]])
    with ERP() as db:
        with pytest.raises(HTTPException) as error:
            identity.patch_identity(db, context["pids"][0], IdentityPatch(expected_revision=0, responsible_id=person["id"]))
        assert error.value.status_code == 404
        db.rollback()
        with pytest.raises(HTTPException) as error:
            identity.patch_identity(db, context["pids"][0], IdentityPatch(expected_revision=0, client_id=ref["id"]))
        assert error.value.status_code == 404
        db.rollback()


def test_invalid_operator_configuration_fails_closed(context, monkeypatch):
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "unknown")
    assert client.get("/api/v1/session").status_code == 503
    monkeypatch.setenv("AGENT_OPERATOR_ROLE", "reader")
    monkeypatch.setenv("AGENT_OPERATOR_PROJECT_IDS", "all")
    assert client.get("/api/v1/portfolio").status_code == 503


def test_local_host_and_origin_checks_still_precede_authorization(context, monkeypatch):
    role(monkeypatch, "reader")
    assert client.get("/api/v1/session", headers={"host": "foreign.invalid"}).status_code == 400
    assert client.post("/api/v1/projects", json={}, headers={"origin": "https://foreign.invalid"}).status_code == 403


def test_every_registered_write_route_is_denied_to_reader(context, monkeypatch):
    role(monkeypatch, "reader")

    def routes(router):
        for route in router.routes:
            included = getattr(route, "original_router", None)
            if included is not None:
                yield from routes(included)
            else:
                yield route

    checked = 0
    for route in routes(app):
        path = getattr(route, "path", "")
        if not path.startswith(("/api/v1/", "/v1/")):
            continue
        for method in (getattr(route, "methods", None) or set()) - {"GET", "HEAD", "OPTIONS"}:
            if path in {"/v1/projects/chat", "/v1/projects/chat/stream", "/api/v1/brain/chat",
                        "/api/v1/meeting-sessions/{sid}/ask", "/api/v1/meeting-sessions/{sid}/live-answers",
                        "/api/v1/projects/{project_id}/planning/templates/{version_id}/preview",
                        "/api/v1/projects/{project_id}/documents/preview",
                        "/api/v1/projects/{project_id}/documents/discover",
                        "/api/v1/projects/{project_id}/documents/artifacts/{artifact_id}/publication-preview",
                        "/api/v1/projects/{project_id}/deliverable-plan/selection/preview"} or path.endswith("/memory/recall"):
                continue
            concrete = re.sub(r"\{[^}]+\}", context["pids"][0], path)
            response = client.request(method, concrete, json={})
            assert response.status_code == 403, f"{method} {path}: {response.text}"
            checked += 1
    assert checked >= 70  # Verify the registered ERP and Brain commands, not just sample URLs.


def test_unscoped_editor_cannot_restore_global_references_through_archive_alias(context, monkeypatch):
    role(monkeypatch, "editor")
    assert client.post("/api/v1/projects/import-json", json={}).status_code == 403


def test_scoped_editor_is_not_blocked_from_project_ai_configuration_consumption(context, monkeypatch):
    role(monkeypatch, "editor", [context["pids"][0]])
    out = client.post(f"/api/v1/projects/{context['pids'][0]}/cdc/ai-generate", json={"text": "x" * 100})
    assert out.status_code == 409 and "injoignable" in out.text


def test_global_llm_context_and_erp_dates_do_not_cross_visible_scope(context, monkeypatch):
    from app.routers.core import prepare_chat
    from app.schemas import ChatQuery
    from app.services.settings_service import save_section
    from backend.app.services.milestones import chat_hits

    with ERP() as erp:
        # A shared Brain identity does not grant access to another ERP table.
        link = erp.get(BrainLink, context["pids"][1])
        link.brain_project_id = context["bids"][0]
        erp.add(Milestone(project_id=context["pids"][1], title="DATE PRIVÉE", forecast_date="2099-01-01"))
        erp.add(Milestone(project_id=context["pids"][0], title="DATE AUTORISÉE", forecast_date="2027-01-01"))
        erp.commit()
    calls = []

    class Memory:
        async def recall(self, project_id, query, scopes):
            calls.append(project_id)
            return []

    monkeypatch.setattr("app.routers.core.get_memory_adapter", lambda _: Memory())
    with Brain() as brain:
        save_section(brain, "ai", {"enabled": True})
    role(monkeypatch, "reader", [context["pids"][0]])
    with Brain() as brain:
        cfg, messages, metadata = asyncio.run(prepare_chat(ChatQuery(query="Dates des jalons"), brain))
        assert cfg["enabled"] is True
        assert calls == [context["bids"][0]]
        assert metadata["projects_queried"] == [context["code"] + "0"]
        assert "DATE PRIVÉE" not in str(messages) and "2099-01-01" not in str(messages)
        contexts = client.get("/api/v1/workspace/knowledge").json()["items"]
        assert all([p["id"] for p in row["erp_projects"]] == [context["pids"][0]] for row in contexts)
        targets = brain.query(BrainProject).all()
        # The service filters ERP links even when a trusted caller passes all Brain targets.
        hits = chat_hits(targets, "Dates")
        assert all(hit["subject"] != "DATE PRIVÉE" for hit in hits)
        assert any(hit["subject"] == "DATE AUTORISÉE" and "2027-01-01" in hit["value"] for hit in hits)


def test_foreign_source_cannot_be_exposed_via_a_visible_project_proposal(context, monkeypatch):
    with Brain() as db:
        forged = Proposal(project_id=context["bids"][0], source_id=context["sources"][1], kind="decision",
                          subject="Source hors périmètre", value="Texte privé", status="pending")
        db.add(forged)
        db.commit()
        identifier = forged.id
    role(monkeypatch, "editor", [context["pids"][0]])
    listed = client.get("/api/v1/workspace/proposals").json()
    assert listed["total"] == 1 and identifier not in {row["id"] for row in listed["items"]}
    assert client.post(f"/v1/proposals/{identifier}/accept", json={"actor": "owner"}).status_code == 404
