"""Back up Agent offline, or restore into a new directory without overwriting."""
import argparse
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["backup", "restore", "verify"])
    parser.add_argument("--output", type=Path)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    if args.mode != 'verify' and args.output is None:
        parser.error('--output requis pour créer une sauvegarde ou une restauration')
    if args.mode == "backup":
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", 8001)) == 0:
                parser.error("Arrêter Agent sur 8001 avant la sauvegarde coordonnée")
        from app.config import settings, STORAGE_DIR
        from sqlalchemy.engine import make_url
        import os
        from app.services.backup import create_backup
        home = Path(os.environ.get("MINIPILOT_HOME", str(Path.home() / ".minipilot")))
        result = create_backup(args.output, Path(make_url(settings.database_url).database), home, STORAGE_DIR)
    elif args.mode == 'restore':
        if args.source is None:
            parser.error("--source requis pour restaurer")
        from app.services.backup import restore_backup
        result = restore_backup(args.source, args.output)
    else:
        if args.source is None:
            parser.error('--source requis pour vérifier une sauvegarde')
        from app.services.backup import verify_backup
        result = verify_backup(args.source)
    print(result)


if __name__ == "__main__":
    main()
