"""Apply the configured automatic-classification threshold to pending mail suggestions."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.db import SessionLocal, engine
from app.db_support import backup_sqlite
from app.models import Proposal, Source
from app.services.settings_service import get_section
from app.services.triage import auto_classify_pending, auto_classification_target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    backup = None
    if args.apply:
        if engine.dialect.name != "sqlite" or not engine.url.database:
            parser.error("Une base SQLite fichier est nécessaire pour la sauvegarde")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        backup = Path(settings.storage_dir).parent / "backups" / f"before-mail-auto-threshold-{stamp}.db"
        backup_sqlite(Path(engine.url.database), backup)
    with SessionLocal() as db:
        if args.apply:
            result = auto_classify_pending(db, get_section(db, "ai"))
        else:
            result = {"eligible": sum(bool(auto_classification_target(db, row)) for row in
                db.query(Proposal).join(Source, Proposal.source_id == Source.id).filter(
                Proposal.kind == "project_attach", Proposal.status == "pending",
                Source.source_type == "email", Source.status == "resolution_pending").all())}
    print(json.dumps({**result, "backup": str(backup) if backup else None}, ensure_ascii=True))


if __name__ == "__main__":
    main()
