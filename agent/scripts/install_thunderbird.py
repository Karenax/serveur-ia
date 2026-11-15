"""Construire le XPI appairé et installer par politique locale Thunderbird."""
import argparse
import configparser
import json
import os
import secrets
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT.parent / 'shared')]
from kiara_shared.thunderbird_package import package


def install_policy(app_dir, output):
    path = app_dir / "distribution" / "policies.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else {}
    if path.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
        shutil.copy2(path, path.with_name(f"policies-before-agent-{stamp}.json"))
    data.setdefault("policies", {}).setdefault("ExtensionSettings", {})["agent-bridge@agent.local"] = {
        "installation_mode": "normal_installed", "install_url": output.resolve().as_uri(), "updates_disabled": True}
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--app-dir", type=Path)
    parser.add_argument("--kiara-profile-exe", type=Path)
    args = parser.parse_args()
    source = ROOT / "extensions" / "thunderbird-agent"
    if args.kiara_profile_exe:
        if sys.platform != "win32":
            parser.error("L’appairage du relais Kiara se fait sur le poste Windows.")
        sys.path[:0] = [str(ROOT.parent / "client-qwen"), str(ROOT.parent / "shared")]
        from client import client_settings, protect, read_profile, settings_path
        from kiara_shared.file_lock import locked
        from kiara_shared.history_store import atomic
        profile = read_profile(args.kiara_profile_exe)
        settings = settings_path(profile)
        output = settings.parent / f"thunderbird-{settings.stem}" / "agent-thunderbird.xpi"
        with locked(settings):
            values = client_settings(profile)
            token = values.get("thunderbird_token") or secrets.token_urlsafe(32)
            package(source, output, token, kiara=True)
            values["thunderbird_token"] = token
            atomic(settings, protect(json.dumps(values)))
    else:
        from app.config import RAW_DIR, STORAGE_DIR
        from app.db import init_db, SessionLocal, engine
        from app.services.mail_identity import backfill
        from app.services.thunderbird import pairing_token
        init_db()
        with SessionLocal() as db:
            count = backfill(db, RAW_DIR, Path(engine.url.database).resolve().parent / "backups")
        output = STORAGE_DIR / "thunderbird" / "agent-thunderbird.xpi"
        package(source, output, pairing_token(create=True))
        print(f"Empreintes existantes : {count}")
    print(f"XPI local : {output}")
    if args.install:
        app_dir = args.app_dir
        if app_dir is None:
            profiles = Path(os.environ["APPDATA"]) / "Thunderbird"
            ini = configparser.ConfigParser()
            ini.read(profiles / "profiles.ini")
            selected = next((ini[s]["Default"] for s in ini.sections() if s.startswith("Install")), None)
            if not selected:
                raise RuntimeError("Profil Thunderbird actif non trouvé ; utiliser --app-dir")
            compatibility = configparser.ConfigParser()
            compatibility.read(profiles / selected / "compatibility.ini")
            app_dir = Path(compatibility["Compatibility"]["LastAppDir"])
        if not (app_dir / "thunderbird.exe").exists():
            raise RuntimeError("Installation Thunderbird introuvable")
        print(f"Politique locale : {install_policy(app_dir, output)}")
        print("Redémarrer Thunderbird pour charger l'extension.")


if __name__ == "__main__":
    main()
