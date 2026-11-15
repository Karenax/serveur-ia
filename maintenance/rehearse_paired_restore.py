"""Rehearse a paired Kiara restore without opening any service or changing its data."""

import argparse
from contextlib import closing
from datetime import datetime, timezone
from getpass import getpass
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

from verify_agent_restores import verify_files


ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "lanceur"), str(ROOT / "shared")]


def check_database(path):
    with closing(sqlite3.connect(path.resolve(strict=True).as_uri() + "?mode=ro", uri=True)) as db:
        health = db.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = len(db.execute("PRAGMA foreign_key_check").fetchall())
    if health != "ok" or foreign_keys:
        raise ValueError("Une base restaurée ne passe pas les contrôles SQLite.")
    return {"integrity": health, "foreign_key_violations": foreign_keys}


def rehearse(archive, work, python, phrase, progress):
    from agent_service import AgentService
    from app import Controller
    from wg_crypto import private_directory

    if archive.suffix.lower() != ".qwenbackup":
        raise ValueError("Sélectionnez l’archive principale .qwenbackup.")
    if not work.is_dir():
        raise ValueError("Choisissez un dossier de travail existant.")
    pair = archive.with_suffix(".kiara-agent")
    with tempfile.TemporaryDirectory(prefix="kiara-restauration-", dir=work) as temporary:
        root = Path(temporary).resolve(strict=True)
        if root.parent != work or root.is_junction():
            raise ValueError("Le dossier de recette doit être isolé.")
        private_directory(root)
        controller = Controller(root / "lanceur", include_legacy=False)
        try:
            progress("vérifier la paire")
            request = {"file": str(archive), "password": phrase}
            companion = None

            def require_pair(summary):
                nonlocal companion
                companion = summary.get("agent")
                if companion is None or Path(companion["file"]) != pair:
                    raise ValueError("Archive métier associée absente.")
                progress("restaurer les données du lanceur")

            controller.operations.restorations.restore_sync(request, on_inspected=require_pair)
            if controller.remote.metadata()["enabled"]:
                raise ValueError("Les accès de la restauration doivent rester fermés.")
            progress("restaurer les données des Projets")
            service = AgentService(controller.remote, root / "aucune-donnee-active", python, start_workers=False)
            restored = service.restore_archive(companion["file"], root, phrase)
            progress("contrôler les bases et les originaux")
            databases = {
                "espaces": check_database(controller.home / "espaces-prives/espaces.sqlite3"),
                "projets": check_database(restored / "erp/minipilot.db"),
                "connaissances": check_database(restored / "brain/project_brain.db"),
            }
            result = {"archive": archive.name, "companion_sha256": companion["sha256"],
                      "databases": databases, "verified_originals": verify_files(restored),
                      "remote_disabled": True}
        finally:
            controller.operations.backups.close()
            controller.remote.workspace.shutdown()
            controller.wireguard.close()
    return {**result, "isolated_data_removed": True, "verified_at": datetime.now(timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--work", type=Path, required=True)
    parser.add_argument("--business-python", type=Path, required=True)
    recovery = parser.add_mutually_exclusive_group()
    recovery.add_argument("--protected-phrase", type=Path)
    recovery.add_argument("--recovery-file", type=Path)
    args = parser.parse_args()
    phase = "ouvrir la phrase de récupération"

    def progress(label):
        nonlocal phase
        phase = label
        print("Recette — " + label, flush=True)

    try:
        if args.protected_phrase:
            from wg_crypto import protect
            phrase = protect(args.protected_phrase.read_bytes(), decrypt=True).decode("utf-8")
        elif args.recovery_file:
            phrase = args.recovery_file.read_text(encoding="utf-8-sig").strip()
        else:
            phrase = getpass("Phrase de récupération de l’archive : ")
        work = args.work.resolve(strict=True)
        result = rehearse(args.archive.resolve(strict=True), work, args.business_python.resolve(strict=True),
                          phrase, progress)
        (work / "restauration.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                                encoding="utf-8")
        print("Restauration vérifiée dans le dossier de recette.")
    except Exception as failure:
        # Runtime diagnostics can contain private filenames or configuration values.
        print(f"Recette interrompue pendant « {phase} » ({type(failure).__name__}).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
