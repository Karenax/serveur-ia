"""Status distinguishes actual indexing, waiting work and stale Thunderbird presence."""
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models import AppSetting
from app.services.settings_service import save_section
from app.services.mail_activity import snapshot
from app.services.projections import active_mail_indexing, track_mail_indexing
from app.workspace_models import TriageJob


def test_stale_thunderbird_never_looks_running(monkeypatch):
    with SessionLocal() as db:
        save_section(db, "thunderbird_status", {
            "last_seen": (datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat(),
            "version": "0.1.0", "sync": {"running": True}})
        actual=snapshot(db)
        assert actual["transfer"]["state"] == "offline"
        assert actual["transfer"]["total"] is None
        assert any("0.2.0" in event["text"] for event in actual["events"])


def test_live_transfer_progress_and_eml_isolation():
    with SessionLocal() as db:
        save_section(db, "thunderbird_status", {
            "last_seen": datetime.now(timezone.utc).isoformat(), "version": "0.2.0",
            "sync": {"running": True, "processed": 12, "total": 80}})
        actual=snapshot(db)
        assert actual["transfer"]["state"] == "running"
        assert actual["transfer"]["processed"] == 12 and actual["transfer"]["total"] == 80
        save_section(db,"mail",{"source":"folder"})
        assert snapshot(db)["transfer"]["state"] != "running"


def test_actual_memory_indexing_and_error_cleanup():
    assert active_mail_indexing() == 0
    try:
        with track_mail_indexing():
            with SessionLocal() as db:
                assert snapshot(db)["indexing"]["state"] == "running"
            raise RuntimeError("memory unavailable")
    except RuntimeError:
        pass
    assert active_mail_indexing() == 0


def test_sidebar_activity_endpoint_is_read_only():
    client=TestClient(app)
    with SessionLocal() as db:
        before=db.query(AppSetting).count()
    response=client.get("/api/v1/workspace/mail-activity")
    assert response.status_code == 200
    assert all(key in response.json() for key in ("transfer","analysis","indexing","events"))
    with SessionLocal() as db:
        assert db.query(AppSetting).count() == before


def test_failed_analysis_stays_visible_despite_waiting_mails(monkeypatch):
    from app.services.auto_scan import AUTO_SCAN_STATE
    monkeypatch.setitem(AUTO_SCAN_STATE, "running", False)
    with SessionLocal() as db:
        job=TriageJob(status="queued", total=10, processed=3)
        db.add(job)
        db.commit()
        try:
            assert snapshot(db)["analysis"]["state"] == "queued"
            job.status="failed"
            db.commit()
            actual=snapshot(db)["analysis"]
            assert actual["state"] == "failed" and actual["detail"] == "Analyse à reprendre"
        finally:
            job.status="cancelled"
            db.commit()
