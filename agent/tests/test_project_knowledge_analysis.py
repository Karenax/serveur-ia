"""Durable idle scheduling, evidence isolation and preservation of human decisions."""
import json
import threading
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal as Brain
from app.models import Project as BrainProject, KnowledgeItem, Source, ProvenanceLink
from app.services import llm_activity
from backend.app.db import SessionLocal as Erp
from backend.app.models import Project, BrainLink, CdcItem, Milestone
from backend.app.project_knowledge_models import ProjectKnowledgeAnalysis
from backend.app.services import project_knowledge_analysis as service
from backend.app.services.project_operator import Operator, operator_context

client = TestClient(app)


@pytest.fixture
def project(monkeypatch):
    with Brain() as brain, Erp() as erp:
        bp = BrainProject(code=uuid.uuid4().hex, name="Analyse fictive")
        brain.add(bp)
        brain.commit()
        p = Project(title="Analyse fictive")
        erp.add(p)
        erp.flush()
        erp.add(BrainLink(project_id=p.id, brain_project_id=bp.id))
        target = CdcItem(project_id=p.id, kind="constraint", title="Tenue à 50 °C", source_quote="Tenue à 50 °C", knowledge_status="confirmed")
        erp.add(target)
        milestone = Milestone(project_id=p.id, title="FAT", contractual_date="2026-10-15")
        erp.add(milestone)
        erp.commit()
        info = {"id": p.id, "brain": bp.id, "target": target.id, "milestone": milestone.id}
    monkeypatch.setattr(service, "configured_operator", lambda: Operator("local", "owner", frozenset([info["id"]])))
    monkeypatch.setattr("backend.app.routers.cdc.brain_ai_settings", lambda: {"enabled": True, "provider": "openai_compatible", "model": "test"})
    return info


def knowledge(project, value="Essai à 50 °C réalisé : conforme, PV signé.", **kwargs):
    with Brain() as db:
        row = KnowledgeItem(project_id=project["brain"], kind="fact", subject="PV thermique", value=value, validated_by="human", **kwargs)
        db.add(row)
        db.commit()
        return row.id


def answer(project, kid, **kwargs):
    return {"findings": [{"target_id": project["target"], "state": "satisfied", "reason": "Essai à 50 °C documenté.",
                          "knowledge_id": kid, "quote": "Essai à 50 °C réalisé : conforme, PV signé."}], "dates": [], "highlights": [], **kwargs}


def run():
    return service.process_next(idle_seconds=0)


def make_due(project):
    with Erp() as db:
        db.get(ProjectKnowledgeAnalysis, project["id"]).next_due = service.now() - timedelta(seconds=1)
        db.commit()


def test_due_legacy_report_with_exact_inputs_is_reused(project, monkeypatch):
    kid = knowledge(project)
    monkeypatch.setattr(service, "analyse", lambda *args: answer(project, kid))
    assert run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        completed = job.completed_at
        old = {key: value for key, value in job.report.items() if key != "_baseline"}
        job.report = old
        db.commit()
    make_due(project)
    monkeypatch.setattr(service, "analyse", lambda *args: pytest.fail("The inputs are identical"))
    assert run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert job.completed_at == completed and job.next_due > service.now()
        assert job.report["_baseline"]["knowledge"].keys() == {kid}
        assert {key: value for key, value in job.report.items() if key != "_baseline"} == old
        assert "_baseline" not in service.describe(db, project["id"])["report"]


def test_new_information_keeps_other_proof_and_sends_only_new_text(project, monkeypatch):
    old = knowledge(project)
    monkeypatch.setattr(service, "analyse", lambda *args: answer(project, old))
    assert run()
    new = knowledge(project, "Essai de contrôle prévu le lendemain.")
    make_due(project)
    calls = []

    def analyse(cfg, passages, targets, dates):
        calls.append(([row["id"] for row in passages], [row["id"] for row in targets], dates))
        return {"findings": [], "dates": [], "highlights": []}

    monkeypatch.setattr(service, "analyse", analyse)
    assert run()
    assert calls == [([new], [project["target"]], True)]
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert job.report["findings"][0]["proofs"][0]["knowledge_id"] == old
        assert job.report["knowledge_count"] == 2


def test_legacy_full_rerun_switches_to_exactly_recovered_delta(project, monkeypatch):
    original = knowledge(project, "Texte des justificatifs " * 700)
    empty = {"findings": [], "dates": [], "highlights": []}
    monkeypatch.setattr(service, "analyse", lambda *args: empty)
    while run():
        pass
    new = knowledge(project, "Nouveau compte rendu de réception.")
    make_due(project)
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        job.report = {key: value for key, value in job.report.items() if key != "_baseline"}
        from backend.app.routers.cdc import brain_ai_settings
        job.snapshot = service.configured_snapshot(db, project["id"], brain_ai_settings())
        job.working, job.cursor, job.status = empty, 1, "running"
        assert len(service.pending_batches(job.snapshot)) > 2
        db.commit()

    def analyse(cfg, passages, targets, dates):
        assert [row["id"] for row in passages] == [new]
        return empty

    monkeypatch.setattr(service, "analyse", analyse)
    assert run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert job.status == "completed" and job.report["_baseline"]["knowledge"].keys() == {original, new}


def test_removed_proof_rechecks_only_affected_requirements(project, monkeypatch):
    removed = knowledge(project)
    retained = knowledge(project, "Réception de l’outillage prévue en atelier.")
    with Erp() as db:
        other = CdcItem(project_id=project["id"], kind="requirement", title="Transport", source_quote="Transport")
        db.add(other)
        db.commit()
        other_id = other.id
    monkeypatch.setattr(service, "analyse", lambda *args: answer(project, removed))
    assert run()
    make_due(project)
    with Brain() as db:
        db.get(KnowledgeItem, removed).status = "invalidated"
        db.commit()

    def analyse(cfg, passages, targets, dates):
        assert [row["id"] for row in passages] == [retained]
        assert [row["id"] for row in targets] == [project["target"]]
        assert not dates
        return {"findings": [], "dates": [], "highlights": []}

    monkeypatch.setattr(service, "analyse", analyse)
    assert run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert {row["id"] for row in job.report["findings"]} == {project["target"], other_id}
        assert all(not row["proofs"] for row in job.report["findings"])


def test_budget_deferral_persists_lot_and_retry(project, monkeypatch):
    knowledge(project, "Long texte " * 800)
    calls = []

    def analyse(cfg, passages, targets, dates):
        calls.append(passages)
        if len(calls) == 2:
            raise llm_activity.Deferred("Quota", retry_after_seconds=120)
        return {"findings": [], "dates": [], "highlights": []}

    monkeypatch.setattr(service, "analyse", analyse)
    assert run()
    assert not run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert job.status == "waiting_idle" and job.cursor == 1 and not job.error
        assert job.retry_after > service.now() + timedelta(seconds=100)
        job.retry_after = service.now() - timedelta(seconds=1)
        db.commit()
    assert run()
    assert calls[1] == calls[2] and calls[0] != calls[1]


def test_managed_gateway_budget_response_is_a_deferral(monkeypatch):
    import io
    from urllib.error import HTTPError
    from app.services import ai_client

    gateway = "http://127.0.0.1:8768"
    monkeypatch.setenv("AGENT_KIARA_INFERENCE_URL", gateway)

    def urlopen(request, timeout):
        assert request.get_header("X-kiara-inference-priority") == "project-analysis"
        body = b'{"error":{"code":"background_budget","retry_after_seconds":45}}'
        raise HTTPError(request.full_url, 429, "Quota", {}, io.BytesIO(body))

    monkeypatch.setattr(ai_client.urllib.request, "urlopen", urlopen)
    with llm_activity.idle(0) as available:
        assert available
        with pytest.raises(llm_activity.Deferred) as caught:
            ai_client._post_json(gateway + "/v1/chat/completions", {})
    assert caught.value.retry_after_seconds == 45


def test_completed_analysis_48h_and_canonical_data_unchanged(project, monkeypatch):
    kid = knowledge(project)
    monkeypatch.setattr(service, "analyse", lambda *args: answer(project, kid))
    assert run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert job.status == "completed"
        assert job.next_due - job.completed_at == timedelta(hours=48)
        assert job.report["counts"]["satisfied"] == 1
        assert db.get(CdcItem, project["target"]).knowledge_status == "confirmed"
        assert db.get(Milestone, project["milestone"]).contractual_date == "2026-10-15"
        report = service.describe(db, project["id"])
        assert not report["stale"] and report["items"][0]["proofs"][0]["knowledge_id"] == kid
    monkeypatch.setattr(service, "analyse", lambda *args: pytest.fail("Reanalysed before 48 hours"))
    assert not run()


def test_foreground_activity_blocks_background_and_releases():
    with llm_activity.foreground():
        with llm_activity.idle(0) as available:
            assert not available
    arrived, completed = threading.Event(), threading.Event()
    def foreground():
        arrived.set()
        with llm_activity.foreground():
            completed.set()
    with llm_activity.idle(0) as available:
        assert available
        thread = threading.Thread(target=foreground)
        thread.start()
        assert arrived.wait(1)
        # Synchronize on the condition, not on timing-dependent sleeps.
        with llm_activity._condition:
            assert llm_activity._condition.wait_for(lambda: llm_activity._waiting > 0, timeout=1)
        assert not completed.is_set()
        with pytest.raises(llm_activity.Deferred):
            llm_activity.acquire()
    thread.join(2)
    assert completed.is_set() and llm_activity.status()["active_calls"] == 0


@pytest.mark.parametrize("cfg", [{}, {"base_url": "http://fixture.test:1234"}])
def test_stream_activity_releases_on_generator_close(monkeypatch, cfg):
    from app.services.ai_stream import ChatStream
    from app.services import inference_scheduler as scheduler
    monkeypatch.setattr(ChatStream, "_iterate", lambda self: iter(["premier", "second"]))
    stream = iter(ChatStream(cfg, []))
    assert next(stream) == "premier" and llm_activity.status()["active_calls"] == 1
    assert scheduler.status()["active"] == (1 if cfg else 0)
    stream.close()
    assert llm_activity.status()["active_calls"] == 0
    assert scheduler.status()["active"] == scheduler.status()["waiting"] == 0


@pytest.mark.parametrize("cfg,message", [
    ({}, "fournisseur IA configuré"),
    ({"enabled": True, "provider": "none"}, "fournisseur IA configuré"),
    ({"enabled": True, "provider": "openai_compatible"}, "Adresse du serveur IA invalide"),
    ({"enabled": True, "provider": "ollama", "base_url": "http://[invalid"}, "Adresse du serveur IA invalide"),
    ({"enabled": True, "provider": "openai_compatible", "base_url": "http://fixture.test:invalid"}, "Adresse du serveur IA invalide"),
    ({"enabled": True, "provider": "ollama", "base_url": "http://user:secret@fixture.test"}, "Adresse du serveur IA invalide"),
])
def test_stream_incomplete_configuration_keeps_public_error_and_releases_activity(monkeypatch, cfg, message):
    from app.services import ai_stream, inference_scheduler as scheduler
    monkeypatch.setattr(ai_stream.http.client, "HTTPConnection", lambda *_args, **_kwargs: pytest.fail("Invalid configuration must not open transport"))
    with pytest.raises(ai_stream.ChatStreamError, match=message) as caught:
        list(ai_stream.ChatStream(cfg, []))
    assert "secret" not in str(caught.value)
    assert llm_activity.status()["active_calls"] == 0
    assert scheduler.status()["active"] == scheduler.status()["waiting"] == 0


def test_background_empty_response_uses_one_network_call(monkeypatch):
    from app.services import ai_client
    calls = []
    monkeypatch.setenv("AGENT_KIARA_INFERENCE_URL", "http://fixture")
    monkeypatch.setattr(ai_client, "_post_json", lambda *args, **kwargs: calls.append(args) or {"choices": [{"message": {"content": ""}}]})
    with pytest.raises(ValueError):
        service.analyse({"enabled": True, "provider": "openai_compatible", "model": "test", "base_url": "http://fixture"}, [], [], False)
    assert len(calls) == 1 and calls[0][1]["reasoning_effort"] == "none"
    schema = calls[0][1]["response_format"]["json_schema"]["schema"]
    assert set(schema["required"]) == {"findings", "dates", "highlights"}
    assert all(field["maxItems"] == 0 for field in schema["properties"].values())


def test_llm_receives_bounded_text_without_duplicated_full_values(monkeypatch):
    from app.services import ai_client
    sent = []
    monkeypatch.setattr(ai_client, "chat_json", lambda cfg, payload, **kwargs: sent.append(payload) or '{"findings":[],"dates":[],"highlights":[]}')
    service.analyse({}, [{"id": "k", "text": "Selected text", "value": "Full text" * 10000, "provenance": ["internal"], "sources": []}], [], False)
    body = json.loads(sent[0]["messages"][1]["content"])
    assert body["knowledge"] == [{"id": "K1", "text": "Selected text"}] and len(json.dumps(body)) < 100


def test_model_reference_codes_map_to_persistent_evidence_ids(monkeypatch):
    quote = "La réception en atelier a été validée."
    knowledge = [{"id": "knowledge-id", "text": quote, "sources": ["source-id"]}]
    targets = [{"id": "target-id", "title": "Réception", "kind": "requirement", "wording": "", "criterion": ""}]
    finding = {"target_id": "C1", "knowledge_id": "K1", "quote": quote, "state": "satisfied", "reason": "Réception"}

    def reply(cfg, payload, **kwargs):
        body = json.loads(payload["messages"][1]["content"])
        assert body["knowledge"][0]["id"] == "K1"
        assert body["targets"][0]["id"] == "C1"
        return json.dumps({"findings": [finding, {**finding, "knowledge_id": "K2"}], "dates": [], "highlights": []})

    monkeypatch.setattr("app.services.ai_client.chat_json", reply)
    result = service.supported(service.analyse({}, knowledge, targets, False), knowledge, targets, False)
    assert result["findings"] == [{**finding, "target_id": "target-id", "knowledge_id": "knowledge-id", "sources": ["source-id"]}]


def test_evidence_is_checked_in_all_passages_of_the_same_knowledge_item():
    quote = "La réception en atelier a été validée."
    # A short tail can share a batch with the preceding 6,000-character passage.
    knowledge = {"id": "k", "subject": "Réception", "value": quote + " " + "x" * 5500, "sources": ["s"]}
    batch, targets, dates = service.batches({"knowledge": [knowledge], "targets": []})[0]
    assert len(batch) == 2 and all(row["id"] == "k" for row in batch)
    result = {"findings": [], "dates": [], "highlights": [
        {"knowledge_id": "k", "quote": quote, "reason": "Réception"},
        {"knowledge_id": "other", "quote": quote, "reason": "Autre"},
        {"knowledge_id": "k", "quote": "Réception jamais effectuée.", "reason": "Autre"},
    ]}
    confirmed = service.supported(result, batch, targets, dates)
    assert confirmed["highlights"] == [{**result["highlights"][0], "sources": ["s"]}]


def test_priority_deferral_is_not_an_llm_failure(project, monkeypatch):
    knowledge(project)
    def deferred(*args, **kwargs):
        raise llm_activity.Deferred("Interactive call waiting")
    monkeypatch.setattr("app.services.ai_client._post_json", deferred)
    assert not run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert job.status == "waiting_idle" and not job.error and not job.retry_after


def test_background_inference_preserves_idle_window_for_knowledge_analysis(monkeypatch):
    import io
    import time
    from app.services import ai_client
    from app.services.inference_scheduler import priority_scope

    last_interaction = time.monotonic() - 60
    monkeypatch.setattr(llm_activity, '_last_activity', last_interaction)
    monkeypatch.setattr(ai_client.urllib.request, 'urlopen', lambda *args, **kwargs: io.BytesIO(b'{}'))
    url = 'http://fixture.test/v1/chat/completions'
    with priority_scope('background'):
        ai_client._post_json(url, {})
    assert llm_activity._last_activity == last_interaction
    with llm_activity.idle(30) as available:
        assert available

    monkeypatch.setattr(llm_activity, '_last_activity', last_interaction)
    ai_client._post_json(url, {})
    with llm_activity.idle(30) as available:
        assert not available


def test_knowledge_analysis_can_reserve_next_turn_during_automated_scan():
    import threading
    started, finish = threading.Event(), threading.Event()

    def scan():
        with llm_activity.foreground(count_as_interaction=False):
            started.set()
            finish.wait(5)

    worker = threading.Thread(target=scan)
    worker.start()
    try:
        assert started.wait(2)
        with llm_activity.idle(0) as available:
            assert available
            with llm_activity.foreground():
                assert llm_activity.status()['active_calls'] == 1
    finally:
        finish.set()
        worker.join(5)
    assert llm_activity.status()['active_calls'] == 0


def test_busy_model_does_not_call_llm(project, monkeypatch):
    knowledge(project)
    monkeypatch.setattr(service, "analyse", lambda *args: pytest.fail("Called a busy model"))
    with llm_activity.foreground():
        assert not run()
    with Erp() as db:
        assert db.get(ProjectKnowledgeAnalysis, project["id"]).status == "waiting_idle"


@pytest.mark.parametrize("fault", ["foreign_id", "invented_quote", "foreign_target", "empty"])
def test_unusable_response_never_completes_or_asserts_compliance(project, monkeypatch, fault):
    kid = knowledge(project)
    result = answer(project, kid)
    if fault == "foreign_id":
        result["findings"][0]["knowledge_id"] = uuid.uuid4().hex
    elif fault == "invented_quote":
        result["findings"][0]["quote"] = "L'ensemble des fonctions est conforme."
    elif fault == "foreign_target":
        result["findings"][0]["target_id"] = uuid.uuid4().hex
    monkeypatch.setattr("app.services.ai_client.chat_json", lambda *args, **kwargs: "" if fault == "empty" else json.dumps(result))
    assert not run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert job.status == "failed" and not job.completed_at and not job.report
        assert job.cursor == 0 and job.retry_after > service.now()


def test_changed_knowledge_during_call_discards_result(project, monkeypatch):
    kid = knowledge(project)
    def changed(*args):
        with Brain() as db:
            db.get(KnowledgeItem, kid).status = "invalidated"
            db.commit()
        return answer(project, kid)
    monkeypatch.setattr(service, "analyse", changed)
    assert run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert job.status == "queued" and not job.report and job.cursor == 0


def test_resume_batches_and_conflicts_are_unclear(project, monkeypatch):
    knowledge(project, "A" * 7000)
    calls = []
    def analysed(cfg, chunk, targets, dates):
        calls.append(chunk[0]["text"])
        return {"findings": [{"target_id": project["target"], "knowledge_id": chunk[0]["id"], "quote": "A" * 20,
                              "state": "satisfied" if len(calls) == 1 else "not_satisfied", "reason": "Interprétations contradictoires."}],
                "dates": [], "highlights": []}
    monkeypatch.setattr(service, "analyse", analysed)
    assert run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert job.cursor == 1 and job.status == "running"
        job.status = "waiting_idle"  # persisted state after interrupted idle lease
        db.commit()
    assert run()
    with Erp() as db:
        job = db.get(ProjectKnowledgeAnalysis, project["id"])
        assert job.status == "completed" and job.report["findings"][0]["state"] == "unclear"
    assert len(calls) == 2 and calls[0] != calls[1]


def test_missing_proof_is_unknown_and_stale_report_visible(project, monkeypatch):
    kid = knowledge(project)
    monkeypatch.setattr(service, "analyse", lambda *args: {"findings": [], "dates": [], "highlights": []})
    assert run()
    with Erp() as db:
        assert db.get(ProjectKnowledgeAnalysis, project["id"]).report["counts"]["unknown"] == 1
    with Brain() as db:
        db.get(KnowledgeItem, kid).value = "Essai à refaire après modification."
        db.commit()
    response = client.get(f"/api/v1/projects/{project['id']}/knowledge-analysis").json()
    assert response["stale"] and response["items"][0]["state"] == "unknown"


@pytest.mark.parametrize("validator", [None, "auto-default", "human"])
def test_foreign_source_not_used_and_read_only_scope(project, monkeypatch, validator):
    with Brain() as db:
        kid = KnowledgeItem(project_id=project["brain"], kind="fact", subject="Non confirmé", value="Essai prétendu conforme", validated_by=validator)
        source = Source(project_id=None, source_type="email", status="resolved", original_uri="test://foreign", sha256=uuid.uuid4().hex * 2)
        db.add_all([kid, source])
        db.flush()
        db.add(ProvenanceLink(knowledge_item_id=kid.id, source_id=source.id))
        db.commit()
    monkeypatch.setattr(service, "analyse", lambda *args: pytest.fail("No admissible knowledge"))
    assert run()
    with Erp() as db:
        assert db.get(ProjectKnowledgeAnalysis, project["id"]).report["knowledge_count"] == 0
        with operator_context(Operator("reader", "reader", frozenset())):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as error:
                service.describe(db, project["id"])
            assert error.value.status_code == 404
    assert client.get(f"/api/v1/projects/{project['id']}/knowledge-analysis?limit=100").status_code == 422


def test_date_proposals_require_explicit_date_and_do_not_overwrite(project, monkeypatch):
    kid = knowledge(project, "FAT prévue le 20/10/2026. FAT prévue le 21/10 sans année.")
    monkeypatch.setattr(service, "analyse", lambda *args: {"findings": [], "highlights": [], "dates": [
        {"knowledge_id": kid, "title": "FAT", "quote": "FAT prévue le 20/10/2026.", "date": "2026-10-20", "date_type": "forecast_date"},
        {"knowledge_id": kid, "title": "FAT", "quote": "FAT prévue le 21/10 sans année.", "date": "2026-10-21", "date_type": "forecast_date"}]})
    assert run()
    with Erp() as db:
        dates = db.get(ProjectKnowledgeAnalysis, project["id"]).report["dates"]
        assert len(dates) == 1 and dates[0]["date"] == "2026-10-20"
        row = db.get(Milestone, project["milestone"])
        assert not row.forecast_date and row.contractual_date == "2026-10-15"
