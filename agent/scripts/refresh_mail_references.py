"""Audit, puis réparation facultative des références explicites en attente.

python -m scripts.refresh_mail_references [--learned] [--apply]
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.db import SessionLocal, engine
from app.db_support import backup_sqlite
from app.services.mail_reference_refresh import refresh_reference_suggestions


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Sauvegarder puis réparer les suggestions")
    parser.add_argument("--learned", action="store_true", help="Inclure les critères appris des validations humaines")
    args = parser.parse_args()
    backup = None
    if args.apply:
        if engine.dialect.name != "sqlite" or not engine.url.database:
            parser.error("Une base SQLite fichier est nécessaire pour la sauvegarde")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        backup = Path(settings.storage_dir).parent / "backups" / f"before-mail-references-{stamp}.db"
        backup_sqlite(Path(engine.url.database), backup)
    with SessionLocal() as db:
        result = refresh_reference_suggestions(db, apply=args.apply, learned=args.learned)
    print(json.dumps({**result, "backup": str(backup) if backup else None}, ensure_ascii=True))


if __name__ == "__main__":
    main()
