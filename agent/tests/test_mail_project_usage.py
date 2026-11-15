import uuid
from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import Project, Source, AuditLog
from app.routers.mail_search import project_usage


def test_usage_uses_classification_time_decays_and_excludes_discards():
    with SessionLocal() as db:
        projects = [Project(code=uuid.uuid4().hex, name="Test") for _ in range(3)]
        db.add_all(projects)
        db.flush()
        now = datetime.now(timezone.utc)
        for i, days in enumerate([0, 60, 0]):
            source = Source(source_type="email", status="discarded" if i == 2 else "resolved", project_id=projects[i].id,
                            original_uri="", sha256=uuid.uuid4().hex, received_at=now - timedelta(days=500))
            db.add(source)
            db.flush()
            db.add(AuditLog(event_type="source.processed.v1", actor="test", project_id=projects[i].id, created_at=now-timedelta(days=days), payload={"source_id":source.id}))
            if i == 0:
                db.add(AuditLog(event_type="source.processed.v1", actor="test", project_id=projects[i].id, created_at=now-timedelta(days=1), payload={"source_id":source.id}))
        db.flush()
        result = {row["project_id"]:row for row in project_usage(db)["projects"]}
        assert result[projects[0].id]["count"] == 1
        assert result[projects[0].id]["score"] > result[projects[1].id]["score"]
        assert projects[2].id not in result
        db.rollback()
