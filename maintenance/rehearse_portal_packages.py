"""Restart the business service from two Kiara packages against the same test databases."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
from zipfile import ZipFile


THREADS = "/api/v1/workspace/assistant-threads"
PILOT_MESSAGES = [{"role": "user", "text": "Échange écrit pendant le pilote."}]
ROLLBACK_MESSAGES = PILOT_MESSAGES + [{"role": "assistant", "text": "Suite écrite après le retour arrière."}]


def worker(phase, fixtures):
    from fastapi.testclient import TestClient
    from app.main import app

    def payload(response, status):
        if response.status_code != status:
            raise RuntimeError(f"{phase}: attendu {status}, reçu {response.status_code}: {response.text[:250]}")
        return response.json()

    with TestClient(app) as client:
        token = payload(client.get("/api/v1/session"), 200)["token"]
        headers = {"X-Agent-Token": token}
        page = client.get("/app/projets")
        page.raise_for_status()
        asset = re.search(r'src="(/assets/[^"]+\.js)"', page.text).group(1)
        script = client.get(asset)
        script.raise_for_status()
        legacy = "Redimensionner l’assistant" in script.text
        assert legacy == (phase in {"previous", "rollback"})
        result = {"bundle_sha256": hashlib.sha256(script.content).hexdigest()}
        if phase == "previous":
            for index in range(2):
                project = payload(client.post("/api/v1/projects", headers=headers,
                                              json={"code": f"RECETTE-{index}", "title": f"Projet de recette {index}"}), 201)
                link = payload(client.post(f"/api/v1/projects/{project['id']}/brain/ensure", headers=headers), 200)
                fixtures[f"project{index}"] = project["id"]
                if index == 0:
                    fixtures["brain"] = link["brain_project_id"]
            old = payload(client.post(THREADS, headers=headers, json={"project_id": fixtures["brain"],
                          "title": "Fil antérieur", "messages": []}), 201)
            fixtures["old"] = old["id"]
        elif phase == "candidate":
            created = payload(client.post(THREADS, headers=headers, json={"project_id": fixtures["brain"],
                              "title": "Fil du pilote", "messages": PILOT_MESSAGES}), 201)
            fixtures["pilot"] = created["id"]
            fixtures["revision"] = created["revision"]
        else:
            path = THREADS + "/" + fixtures["pilot"]
            saved = payload(client.get(path), 200)
            if phase == "rollback":
                assert saved["messages"] == PILOT_MESSAGES
                assert saved["revision"] == fixtures["revision"]
                os.environ["AGENT_OPERATOR_ROLE"] = "reader"
                os.environ["AGENT_OPERATOR_PROJECT_IDS"] = json.dumps([fixtures["project1"]])
                payload(client.get(path), 404)
                os.environ["AGENT_OPERATOR_ROLE"] = "owner"
                os.environ["AGENT_OPERATOR_PROJECT_IDS"] = json.dumps([fixtures["project0"]])
                changed = payload(client.put(path, headers=headers, json={"messages": ROLLBACK_MESSAGES,
                                  "expected_revision": saved["revision"]}), 200)
                assert changed["revision"] == saved["revision"] + 1
            else:
                assert saved["messages"] == ROLLBACK_MESSAGES
                assert saved["revision"] == fixtures["revision"] + 1
        payload(client.get(THREADS + "/" + fixtures["old"]), 200)
    return {"fixtures": fixtures, **result}


def unpack(archive, destination):
    with ZipFile(archive) as package:
        for name in package.namelist():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or ":" in name or "\\" in name:
                raise ValueError(f"Chemin inattendu dans le paquet: {name}")
        package.extractall(destination)


def rehearse(previous, candidate, report):
    with tempfile.TemporaryDirectory(prefix="kiara-retour-paquets-") as directory:
        root = Path(directory)
        data = root / "data"
        data.mkdir()
        roots = {label: root / label for label in ("previous", "candidate")}
        for name, archive in (("previous", previous), ("candidate", candidate)):
            unpack(archive, roots[name])
        env = {key: value for key, value in os.environ.items()
               if not key.startswith(("AGENT_", "MINIPILOT_", "PB_"))}
        env.update(AGENT_TESTING="1", AGENT_START_WORKERS="0", AGENT_OPERATOR_ROLE="owner",
                   MINIPILOT_HOME=str(data), PB_DATABASE_URL="sqlite:///" + (data / "brain.db").as_posix(),
                   PB_STORAGE_DIR=str(data / "storage"), PB_INFOMANIAK_DIR="", PB_MEMORY_ENGINE="fake",
                   PYTHONIOENCODING="utf-8")
        fixtures = {}
        evidence = {}
        for phase, label in (("previous", "previous"), ("candidate", "candidate"),
                             ("rollback", "previous"), ("reopen-candidate", "candidate")):
            package = roots[label]
            env["PYTHONPATH"] = os.pathsep.join(str(package / name) for name in ("shared", "agent"))
            if fixtures:
                env["AGENT_OPERATOR_PROJECT_IDS"] = json.dumps([fixtures["project0"]])
            run = subprocess.run([sys.executable, str(Path(__file__).resolve()), "--worker",
                                  phase, json.dumps(fixtures)], cwd=package / "agent", env=env,
                                 text=True, encoding="utf-8", capture_output=True, timeout=90)
            if run.returncode:
                raise RuntimeError(f"{phase} a échoué:\n{run.stderr[-3500:]}")
            response = json.loads(run.stdout.splitlines()[-1])
            fixtures = response["fixtures"]
            evidence[phase] = response["bundle_sha256"]
        assert evidence["previous"] == evidence["rollback"]
        assert evidence["candidate"] == evidence["reopen-candidate"]
        assert evidence["candidate"] != evidence["previous"]
    result = {"verified_at": datetime.now(timezone.utc).isoformat(), "bundles": evidence,
              "archives": {label: hashlib.sha256(path.read_bytes()).hexdigest()
                           for label, path in (("previous", previous), ("candidate", candidate))},
              "pilot_write_preserved": True, "rollback_write_preserved": True, "foreign_project_denied": True}
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", nargs=2, help=argparse.SUPPRESS)
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(worker(args.worker[0], json.loads(args.worker[1]))))
    elif args.previous and args.candidate and args.report:
        rehearse(args.previous.resolve(strict=True), args.candidate.resolve(strict=True), args.report)
    else:
        parser.error("--previous, --candidate et --report sont requis")
