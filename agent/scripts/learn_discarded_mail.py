"""Recover comparison fingerprints from discard backups without restoring mail."""
import argparse
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

from app.db import SessionLocal
from app.db_support import backup_sqlite
from app.models import AuditLog, Source
from app.services.mail_discard_learning import EVENT, fingerprint


def recover_fingerprints(backups, missing):
    found = {}
    remaining = dict(missing)
    for path in sorted(backups.glob("before-mail-discard-*/project_brain.db"), reverse=True):
        if not remaining:
            break
        try:
            with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as saved:
                # Bound parameters and verify both identity and hash against the live discarded trace.
                for source_id, sha in list(remaining.items()):
                    row = saved.execute("SELECT author,source_metadata,status,sha256 FROM sources WHERE id=?", (source_id,)).fetchone()
                    if not row or row[2] == "discarded" or row[3] != sha:
                        continue
                    body = "\n".join(row[0] or "" for row in saved.execute(
                        "SELECT content_text FROM source_artifacts WHERE source_id=? AND kind='body_text'", (source_id,)))
                    found[source_id] = fingerprint(row[0] or "", json.loads(row[1] or "{}").get("subject", ""), body)
                    remaining.pop(source_id)
        except (sqlite3.Error, ValueError, OSError):
            continue
    return found


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Save fingerprints after SQLite backup")
    args = parser.parse_args()
    with SessionLocal() as db:
        path = Path(db.get_bind().url.database).resolve()
        known = {a.correlation_id for a in db.query(AuditLog).filter_by(event_type=EVENT)
                 if (a.payload or {}).get("fingerprint", {}).get("version") == 1}
        missing = {s.id: s.sha256 for s in db.query(Source).filter_by(source_type="email", status="discarded") if s.id not in known}
        recovered = recover_fingerprints(path.parent / "backups", missing)
        if args.apply and recovered:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
            backup_sqlite(path, path.parent / "backups" / f"before-discard-learning-{stamp}.db")
            for source_id, fp in recovered.items():
                source = db.get(Source, source_id)
                if source and source.status == "discarded" and not db.query(AuditLog.id).filter_by(event_type=EVENT, correlation_id=source_id).first():
                    db.add(AuditLog(event_type=EVENT, actor="discard-history-recovery", correlation_id=source_id,
                                    payload={"fingerprint": fp}))
            db.commit()
        print(json.dumps({"applied": args.apply, "recovered": len(recovered), "unavailable": len(missing) - len(recovered)}))


if __name__ == "__main__":
    main()
