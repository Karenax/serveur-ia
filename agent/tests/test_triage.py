"""Tri des mails : DIVERS, file de validation, accept/assign, idempotence."""
import uuid

RUN = uuid.uuid4().hex[:8]

from fastapi.testclient import TestClient  # noqa: E402

import app.db as brain_db  # noqa: E402
from app.main import app  # noqa: E402

brain_db.init_db()
c = TestClient(app)

TRI_CODE = "TRI-101"


def _upload(subject, sender="client@ex.com", msgid="tri"):
    eml = (f"From: {sender}\r\nTo: moi@boite.fr\r\nSubject: {subject}\r\n"
           f"Message-ID: <{msgid}-{RUN}@x>\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
           f"Corps du message {subject}.").encode()
    r = c.post("/v1/sources/upload-eml", files={"file": ("mail.eml", eml, "message/rfc822")})
    assert r.status_code == 200, r.text
    return r.json()


def _ensure_tri_project():
    r = c.post("/v1/projects", json={"code": TRI_CODE, "name": "Tri test"})
    assert r.status_code in (200, 409), r.text
    if r.status_code == 409:
        projects = c.get("/v1/projects").json()
        return next(p for p in projects if p["code"] == TRI_CODE)["id"]
    return r.json()["id"]


def test_triage_divers_and_queue():
    pid = _ensure_tri_project()
    # 1. mail avec code explicite -> résolu seul, jamais en file de tri
    auto = _upload("[TRI-101] TRI-AUTO devis validé", msgid="tri-auto-1")
    assert auto["status"] == "resolved"
    assert auto["project_id"] == pid
    # 2. mail sans indice -> pending
    pend = _upload("TRI-PENDING réunion chantier sans référence", msgid="tri-pend-1")
    assert pend["status"] == "resolution_pending"

    run = c.post("/v1/triage/run?limit=50").json()
    assert run["triaged"] >= 1
    assert run["divers"] >= 1  # le mail sans indice part en DIVERS

    q = c.get("/v1/triage/queue").json()
    mine = [e for e in q if e["source_id"] == pend["source_id"]]
    assert len(mine) == 1
    assert mine[0]["target_code"] == "DIVERS"
    assert mine[0]["confidence"] < 0.75
    # le mail auto-résolu n'est jamais proposé au tri
    assert not [e for e in q if e["source_id"] == auto["source_id"]]

    # DIVERS exclu des candidats même si le texte contient « divers »
    other = _upload("TRI-DIVERS sujets divers et variés", msgid="tri-divers-1")
    c.post("/v1/triage/run?limit=50")
    q2 = c.get("/v1/triage/queue").json()
    entry = next(e for e in q2 if e["source_id"] == other["source_id"])
    assert entry["target_code"] == "DIVERS"
    assert "explicit_code" not in entry["reason"]

    # idempotence : relancer ne recrée rien
    run2 = c.post("/v1/triage/run?limit=50").json()
    assert run2["triaged"] == 0

    # accept -> rattaché immédiatement à DIVERS ; indexation par le worker durable
    acc = c.post(f"/v1/triage/{mine[0]['proposal_id']}/accept",
                 json={"actor": "test"}).json()
    assert acc["status"] == "resolved"
    assert acc["validated_to"] == "DIVERS"
    st = c.get("/v1/triage/stats").json()
    assert st["divers_count"] >= 1
    assert st["queued"] >= 1  # l'autre mail attend toujours
    from app.services.mail_enrichment import process_next
    assert process_next(pend["source_id"])
    mem = c.get(f"/v1/projects/{st['divers_project_id']}/memory/status").json()
    assert mem["evidence_projections"] >= 1
    # la file ne contient plus le mail validé
    q3 = c.get("/v1/triage/queue").json()
    assert not [e for e in q3 if e["source_id"] == pend["source_id"]]
    assert pid  # projet TRI toujours présent


def test_triage_assign_to_chosen_project():
    _ensure_tri_project()
    pend = _upload("TRI-ASSIGN commande à réaffecter", msgid="tri-assign-1")
    c.post("/v1/triage/run?limit=50")
    q = c.get("/v1/triage/queue").json()
    entry = next(e for e in q if e["source_id"] == pend["source_id"])
    assert entry["target_code"] == "DIVERS"
    projects = c.get("/v1/projects").json()
    tri = next(p for p in projects if p["code"] == TRI_CODE)
    res = c.post(f"/v1/triage/{entry['proposal_id']}/assign",
                 json={"project_id": tri["id"], "actor": "test"}).json()
    assert res["status"] == "resolved"
    assert res["validated_to"] == TRI_CODE
    assert res["items"] >= 1  # extraction heuristique au rattachement
    src = c.get(f"/v1/sources/{pend['source_id']}").json()
    assert src["project_id"] == tri["id"]
    # proposition doublement traitée -> 404
    again = c.post(f"/v1/triage/{entry['proposal_id']}/accept", json={"actor": "test"})
    assert again.status_code == 404


def test_triage_ai_hint_prefers_project_over_divers():
    # IA simulée : hint explicite vers TRI-101 (branchée APRES l'upload pour
    # que le mail reste en attente et passe par le tri).
    import app.services.ai_client as ai_client

    def fake_classify(cfg, subject, body, sender, projects, timeout=None, participants=None):
        return {"project_hints": [TRI_CODE], "items": [], "summary": "suggéré",
                "raw_model": "fake", "provider": "fake"}

    # Pas d’historique de contact partagé : ce scénario teste l’indice IA seul.
    pend = _upload("TRI-HINT devis à classer par IA", sender=f"hint-{RUN}@unseen.test", msgid="tri-hint-1")
    assert pend["status"] == "resolution_pending"
    c.put("/v1/settings/ai", json={"provider": "ollama", "enabled": True})
    orig = ai_client.classify_email
    ai_client.classify_email = fake_classify
    try:
        run = c.post("/v1/triage/run?limit=50").json()
        assert run["triaged"] >= 1
        q = c.get("/v1/triage/queue").json()
        assert not any(e["source_id"] == pend["source_id"] for e in q)
        from app.models import Proposal, Source
        with brain_db.SessionLocal() as db:
            entry=db.query(Proposal).filter_by(source_id=pend["source_id"],kind="project_attach",status="accepted").one()
            assert "ai_hint" in entry.reason
            assert db.get(Source,pend["source_id"]).project_id==entry.project_id
            assert entry.confidence>=.75
    finally:
        ai_client.classify_email = orig
        c.put("/v1/settings/ai", json={"provider": "ollama", "enabled": False})


def test_reference_alias_suggested_at_import_and_triage(monkeypatch):
    """La référence explicite classe le mail et n'est pas remplacée par un indice IA."""
    from app.db import SessionLocal
    from app.models import Proposal, Source
    from app.services.triage import triage_pending
    import app.services.ai_client as ai_client

    alias = f"AIRB26LTH0806-A-{RUN}"
    pid = c.post("/v1/projects", json={
        "code": f"AIRB25LTH0806-A-{RUN}", "name": "Outillage M&B ajustage",
        "aliases": [alias],
    }).json()["id"]
    source = _upload(f"Livrables {alias} zone ajustage T et x", msgid="explicit-alias")
    assert source["status"] == "resolved"
    assert source["project_id"] == pid
    with SessionLocal() as db:
        initial = db.query(Proposal).filter_by(source_id=source["source_id"], kind="project_attach").one()
        assert initial.project_id == pid
        assert initial.confidence >= 0.9
        monkeypatch.setattr(ai_client, "classify_email", lambda *args: {
            "project_hints": [TRI_CODE], "items": [], "summary": "indice IA erroné",
        })
        result = triage_pending(db, None, {"enabled": True}, limit=1000)
        assert result["errors"] == []
        suggestion = db.query(Proposal).filter_by(
            source_id=source["source_id"], kind="project_attach", status="accepted").one()
        assert suggestion.project_id == pid
        assert "explicit_alias" in suggestion.reason
        assert db.get(Source, source["source_id"]).project_id == pid
        assert db.get(Source, source["source_id"]).status == "resolved"


def test_triage_force_retriage():
    """Tout ré-analyser : anciennes propositions soldées, nouvelles créées."""
    from app.services.triage import is_analyzed
    from app.db import SessionLocal

    pend = _upload("TRI-FORCE rapport à ré-analyser", msgid="tri-force-1")
    assert pend["status"] == "resolution_pending"
    db = SessionLocal()
    try:
        assert not is_analyzed(db, pend["source_id"])
    finally:
        db.close()
    r1 = c.post("/v1/triage/run?limit=50").json()
    assert r1["triaged"] >= 1
    db = SessionLocal()
    try:
        assert is_analyzed(db, pend["source_id"])
    finally:
        db.close()
    q1 = c.get("/v1/triage/queue").json()
    first = next(e for e in q1 if e["source_id"] == pend["source_id"])

    # run normal : rien de neuf (déjà analysé)
    r2 = c.post("/v1/triage/run?limit=50").json()
    assert r2["triaged"] == 0

    # force : l'ancienne est soldée, une fraîche la remplace
    r3 = c.post("/v1/triage/run?limit=50&force=true").json()
    assert r3["triaged"] >= 1
    assert r3.get("force") is True
    q2 = c.get("/v1/triage/queue").json()
    mine = [e for e in q2 if e["source_id"] == pend["source_id"]]
    assert len(mine) == 1
    assert mine[0]["proposal_id"] != first["proposal_id"]
    # nettoyage
    c.post(f"/v1/triage/{mine[0]['proposal_id']}/accept", json={"actor": "test"})


def test_human_confirmations_improve_next_import_and_reclassification_updates_profile():
    # Keep this manual-validation learning scenario below the selected threshold.
    assert c.put("/v1/settings/mail",json={"auto_classification_threshold":1}).status_code==200
    a = c.post("/v1/projects", json={"code": f"HUM-A-{RUN}", "name": "Dossier alpha"}).json()["id"]
    b = c.post("/v1/projects", json={"code": f"HUM-B-{RUN}", "name": "Dossier beta"}).json()["id"]
    sender = f"Alice <learning-{RUN}@example.test>"
    validated = []
    for i in range(3):
        source = _upload(f"Échange particulier numéro {i}", sender=sender, msgid=f"learning-{i}")
        result = c.post(f"/v1/resolution/{source['source_id']}/confirm", json={"project_id": a})
        assert result.status_code == 200, result.text
        validated.append(source["source_id"])
    new = _upload("Sujet différent à orienter", sender=sender, msgid="learning-new")
    queue = c.get("/v1/triage/queue?limit=1000").json()
    entry = next(e for e in queue if e["source_id"] == new["source_id"])
    assert entry["target_project_id"] == a and entry["confidence"] >= 0.75
    assert any(e["key"] == "learned_sender" and e["samples"] == 3 for e in entry["evidence"])
    paged = c.get(f"/v1/mail/page?scope=pending&project_id={a}").json()
    page_entry = next(e for e in paged["rows"] if e["source_id"] == new["source_id"])
    assert page_entry["evidence"] == entry["evidence"]
    assert page_entry["candidates"] == entry["candidates"]
    assert new["status"] == "resolution_pending"
    learning = c.get("/api/v1/brain/triage/learning").json()
    profile = next(p for p in learning["projects"] if p["project_id"] == a)
    assert profile["validated_mail_count"] == 3
    assert f"learning-{RUN}@example.test" in profile["known_senders"]
    assert c.post(f"/v1/resolution/{validated[0]}/confirm", json={"project_id": b}).status_code == 200
    next_mail = _upload("Autre thème inconnu", sender=sender, msgid="learning-corrected")
    assert not next_mail["candidates"] or max(p["score"] for p in next_mail["candidates"]) < 0.75
    # Les suggestions de ce test passent au tri pour laisser la file des
    # nouveaux libre au scénario de scan automatique qui suit.
    assert c.post("/v1/triage/run?limit=1000").status_code == 200



def test_progress_totals_match_eligible_mail_sources():
    from app.models import Source, Proposal
    before = c.get("/v1/triage/stats").json()
    with brain_db.SessionLocal() as db:
        ids = []
        for source_type, status in (("email", "resolution_pending"), ("email", "resolution_pending"),
                                    ("email", "resolved"), ("email", "discarded"), ("document", "resolution_pending")):
            source = Source(source_type=source_type, status=status, original_uri="test-progress",
                            sha256=uuid.uuid4().hex)
            db.add(source)
            db.flush()
            ids.append(source.id)
        # A generic candidate still needs analysis; a pending AI suggestion does not.
        for source_id, reason in ((ids[0], "résolution à confirmer"), (ids[1], "triage IA : déjà analysé")):
            db.add(Proposal(source_id=source_id, project_id=before["divers_project_id"], kind="project_attach",
                            subject="Classement test", value="DIVERS", reason=reason))
        db.commit()
    after = c.get("/v1/triage/stats").json()
    assert after["pending_sources"] == before["pending_sources"] + 2
    assert after["new_sources"] == before["new_sources"] + 1
    # The ERP bridge exposes the same count used by the React counter.
    assert c.get("/api/v1/brain/triage/stats").json()["new_sources"] == after["new_sources"]
    # The suite shares its temporary database: keep these synthetic candidates
    # out of the following automatic-scan scenario.
    with brain_db.SessionLocal() as db:
        db.query(Source).filter(Source.id.in_(ids)).update({"status": "discarded"}, synchronize_session=False)
        db.query(Proposal).filter(Proposal.source_id.in_(ids)).update({"status": "superseded"}, synchronize_session=False)
        db.commit()


def test_auto_scan_once_new_only(tmp_path):
    """Le passage auto ingère les nouveaux .eml puis ne trie que les nouveaux."""
    from app.db import SessionLocal
    from app.services.auto_scan import AUTO_SCAN_STATE, run_auto_scan_once

    d = tmp_path / "eml"
    d.mkdir()
    for i in (1, 2):
        (d / f"auto-{i}.eml").write_bytes(
            ("From: auto@ex.com\r\nTo: moi@boite.fr\r\n"
             f"Subject: TRI-AUTO-SCAN {i}\r\nMessage-ID: <auto-{i}@x>\r\n"
             "Content-Type: text/plain; charset=utf-8\r\n\r\nBonjour.").encode())
    prev = c.get("/v1/settings/mail").json()
    c.put("/v1/settings/mail", json={"folder": str(d), "auto_scan": True,
                                     "scan_interval_minutes": 5})
    try:
        res = run_auto_scan_once()
        assert res["scan"]["imported"] == 2
        assert res["triage"]["triaged"] == 2
        assert AUTO_SCAN_STATE["last_result"]["triage"]["triaged"] == 2
        assert AUTO_SCAN_STATE["last_error"] is None
        # second passage : rien de neuf
        res2 = run_auto_scan_once()
        assert res2["triage"]["triaged"] == 0
        # un nouveau fichier : seul lui est trié
        (d / "auto-3.eml").write_bytes(
            ("From: auto@ex.com\r\nTo: moi@boite.fr\r\n"
             "Subject: TRI-AUTO-SCAN 3\r\nMessage-ID: <auto-3@x>\r\n"
             "Content-Type: text/plain; charset=utf-8\r\n\r\nBonjour.").encode())
        res3 = run_auto_scan_once()
        assert res3["scan"]["imported"] == 1
        assert res3["triage"]["triaged"] == 1
    finally:
        c.put("/v1/settings/mail", json={
            "folder": prev.get("folder", ""), "auto_scan": prev.get("auto_scan", True),
            "scan_interval_minutes": prev.get("scan_interval_minutes", 5)})
        db = SessionLocal()
        try:
            from app.models import Proposal, Source
            for subj in ("TRI-AUTO-SCAN 1", "TRI-AUTO-SCAN 2", "TRI-AUTO-SCAN 3"):
                for s in db.query(Source).all():
                    if (s.source_metadata or {}).get("subject") == subj:
                        for pr in db.query(Proposal).filter_by(source_id=s.id).all():
                            pr.status = "rejected"
            db.commit()
        finally:
            db.close()
