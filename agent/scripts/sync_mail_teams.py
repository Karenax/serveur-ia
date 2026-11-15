"""Backfill eXcent project collaborators from resolved mails; dry run by default."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.db import SessionLocal
from app.db_support import backup_sqlite
from app.models import Source
from app.services.mail_team import correspondents, synchronize
from backend.app.db import DB_PATH, SessionLocal as ERP


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    backup = None
    if args.apply:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        backup = Path("backups") / f"before-mail-teams-{stamp}.db"
        backup_sqlite(DB_PATH, backup)
    with SessionLocal() as brain, ERP() as erp:
        sources = brain.query(Source).filter_by(source_type="email", status="resolved").all()
        eligible = sum(bool(correspondents(source)) for source in sources)
        added = 0
        if args.apply:
            for source in sources:
                added += synchronize(source, erp)
            erp.commit()
    print(json.dumps({"resolved_mails": len(sources), "with_excent_people": eligible,
                      "members_added": added, "backup": str(backup) if backup else None}))


if __name__ == "__main__":
    main()
