"""Isolated WireGuard/API fixture for emulator checks. No live accounts are read."""
import argparse
import base64
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption


def keypair():
    key = X25519PrivateKey.generate()
    enc = lambda raw: base64.b64encode(raw).decode("ascii")
    return (enc(key.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())),
            enc(key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=int, default=3600)
    parser.add_argument("--lots6-8", action="store_true", help="Use actual isolated Workspace/Notifications modules")
    parser.add_argument("--corrector", action="store_true", help="Verify direct-corrector bodies in the real Android tunnel")
    parser.add_argument("--model-selection", action="store_true", help="Verify public catalogue and selected-model chat/context native transport")
    parser.add_argument("--engine", type=Path, help="Isolated staged bridge, leaving a live production executable untouched")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    stop_file = output / 'stop-fixture'
    stop_file.unlink(missing_ok=True)
    token = "qwen_" + secrets.token_hex(8) + "_" + secrets.token_urlsafe(32)
    state = {"history": None, "revision": 0, "requests": {}, "rejected": 0}
    corrector_modes = {}
    model_checks = {"context": 0, "chat": 0, "retired": 0, "local_unloaded": 0, "rejected": 0}
    cloud_model = "fred-model-0123456789abcdef"
    model_available = True
    guard = threading.Lock()
    workspace = notifications = None
    owner = token.split("_")[1]
    if args.lots6_8:
        sys.path.insert(0, str(root / "lanceur"))
        from workspace import Workspace
        from notifications import Notifications
        workspace = Workspace(output / "isolated-server")
        notifications = Notifications(workspace)
        project = workspace.action(owner, {"action": "project_create", "title": "Fixture Android sources"})["id"]
        document = workspace.action(owner, {"action": "document_create", "project": project, "title": "Notice Android", "text": "Le code ORCHIDEE permet de vérifier la fidélité des citations. Version initiale."})["id"]
        from test_document_research import text_pdf
        pdf = text_pdf(["Introduction à la validation Android.", "La garantie du véhicule Atlas est de 37 mois. Code ORCHIDEEPDF."])
        pdf_document = workspace.action(owner, {"action": "document_upload", "project": project, "title": "Garantie Android.pdf", "data": base64.b64encode(pdf).decode()})["id"]
        foreign_owner = secrets.token_hex(8)
        foreign_project = workspace.action(foreign_owner, {"action": "project_create", "title": "Autre propriétaire"})["id"]
        foreign_document = workspace.action(foreign_owner, {"action": "document_create", "project": foreign_project, "title": "Privé", "text": "Secret isolé"})["id"]
        source = workspace.action(owner, {"action": "search", "project": project, "query": "ORCHIDEE"})["sources"][0]
        job = workspace.action(owner, {"action": "job_create", "project": project, "title": "Résultat Android", "prompt": "Vérifier ORCHIDEE", "request_key": secrets.token_hex(16)})["id"]
        with workspace.db() as db:
            db.execute("UPDATE jobs SET state='completed',result=? WHERE id=?", (json.dumps({"text": "Résultat avec une citation fidèle : ORCHIDEE.", "sources": [source]}), job))
        notifications.publish(owner, "job_completed", "android-seed-job", {"kind": "job", "id": job, "project": project})
        state["fixture"] = {"project": project, "document": document, "pdf_document": pdf_document, "job": job, "foreign_document": foreign_document}
        (output / "fixture-public.json").write_text(json.dumps(state["fixture"]), encoding="utf-8")

    class API(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *_):
            pass

        def json_reply(self, value, status=200):
            payload = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self):
            self.route()

        def do_POST(self):
            self.route()

        def route(self):
            nonlocal model_available
            if self.headers.get("Authorization") != "Bearer " + token:
                with guard:
                    state["rejected"] += 1
                self.json_reply({"error": {"message": "Fixture authentication required"}}, 401)
                return
            size = int(self.headers.get("Content-Length", "0"))
            if size > 10 * 1024 * 1024:
                self.json_reply({"error": {"message": "Fixture body too large"}}, 413)
                return
            body = json.loads(self.rfile.read(size)) if size else {}
            with guard:
                label = self.command + " " + self.path
                state["requests"][label] = state["requests"].get(label, 0) + 1
            if self.path == "/v1/models":
                if args.model_selection:
                    self.json_reply({"object": "list", "source": "hermes", "default_model": cloud_model,
                                     "api_key": "SYNTHETIC_NOT_SECRET", "data": [
                                         {"id": "fred-qwen", "name": "Fixture local", "label": "Fixture local", "provider": "Qwen local", "available": False,
                                          "capabilities": {"thinking": True, "vision": False, "images": False, "context_length": None}},
                                         {"id": cloud_model, "name": "Fixture cloud", "label": "Fixture cloud", "provider": "OpenRouter", "available": model_available,
                                          "api_key": "SYNTHETIC_NOT_SECRET", "base_url": "https://fixture.invalid/",
                                          "capabilities": {"thinking": True, "vision": True, "images": True, "context_length": 131072, "files": ["txt", "md"]}}]})
                else:
                    self.json_reply({"object": "list", "data": [{"id": "fred-fixture", "object": "model", "capabilities": {"thinking": True, "images": False, "files": ["txt", "md"]}}]})
            elif self.path == "/v1/status":
                self.json_reply({"status": "ready", "model": "fred-fixture", "model_loaded": True, "context_window": 32768})
            elif self.path == "/v1/device" and self.command == "POST":
                if body.get("kind") not in ("pc", "phone", "tablet") or not isinstance(body.get("version"), str):
                    self.json_reply({"error": {"message": "Fixture device declaration invalid"}}, 400)
                else:
                    self.json_reply({"id": token.split("_")[1], "server_epoch": time.time(), "declared": body})
            elif self.path == "/v1/context":
                if args.model_selection:
                    valid = (set(body) == {"model", "messages"} and body.get("messages") == [{"role": "user", "content": "Test synthétique Android : modèle distant."}])
                    with guard:
                        if valid and body.get("model") == "fred-model-retired": model_checks["retired"] += 1
                        elif valid and body.get("model") == cloud_model: model_checks["context"] += 1
                        else: model_checks["rejected"] += 1
                    if valid and body.get("model") == "fred-model-retired":
                        self.json_reply({"error": {"code": "model_unavailable", "message": "Synthetic model unavailable"}}, 503)
                    elif valid and body.get("model") == cloud_model:
                        self.json_reply({"tokens": 100, "capacity": 131072, "estimated": True, "fits": True})
                    else:
                        self.json_reply({"error": {"message": "Synthetic model context contract rejected"}}, 400)
                else:
                    self.json_reply({"tokens": 100, "capacity": 32768, "estimated": False, "fits": True})
            elif self.path == "/v1/history":
                with guard:
                    if self.command == "POST":
                        if str(body.get("revision")) != str(state["revision"]):
                            self.json_reply({"error": {"message": "Fixture revision changed"}}, 409)
                            return
                        state["history"] = body.get("history")
                        state["revision"] += 1
                    self.json_reply({"history": state["history"], "revision": str(state["revision"]), "reset_id": "20261006-remove-assistants"})
            elif self.path == "/v1/chat/completions":
                if args.model_selection:
                    if body == {"stream": True, "text_transform": {"mode": "correct", "text": "Texte synthétique Android à transformer."}}:
                        with guard:
                            model_checks["local_unloaded"] += 1
                            (output / "request-counts.json").write_text(json.dumps({"requests": state["requests"], "rejected": state["rejected"], "model_selection": model_checks}), encoding="utf-8")
                        self.json_reply({"error": {"code": "model_unloaded", "message": "Synthetic local Qwen unloaded"}}, 503)
                        return
                    valid = (set(body) == {"model", "messages", "stream", "conversation_id"}
                             and body.get("model") == cloud_model and body.get("stream") is True
                             and body.get("messages") == [{"role": "user", "content": "Test synthétique Android : modèle distant."}]
                             and isinstance(body.get("conversation_id"), str) and len(body["conversation_id"]) == 32
                             and len(self.headers.get("X-Qwen-Request", "")) == 32)
                    with guard:
                        model_checks["chat" if valid else "rejected"] += 1
                    if not valid:
                        self.json_reply({"error": {"message": "Synthetic selected model chat contract rejected"}}, 400)
                        return
                    model_available = False
                if args.corrector:
                    transform = body.get("text_transform", {})
                    mode = transform.get("mode") if isinstance(transform, dict) else None
                    valid = (set(body) <= {"text_transform", "stream", "model"}
                             and isinstance(transform, dict) and set(transform) == {"mode", "text"}
                             and mode in ("correct", "professional", "friendly")
                             and transform.get("text") == "Texte synthétique Android à transformer."
                             and not any(key in body for key in ("messages", "project", "document", "conversation_id"))
                             and body.get("stream") is True
                             and len(self.headers.get("X-Qwen-Request", "")) == 32)
                    with guard:
                        corrector_modes[str(mode)] = {"body_preserved": valid, "calls": corrector_modes.get(str(mode), {}).get("calls", 0) + 1}
                    if not valid:
                        self.json_reply({"error": {"message": "Synthetic corrector contract rejected"}}, 400)
                        return
                text = "Connexion Android WireGuard vérifiée. **Réponse de test** reçue par le tunnel."
                if not body.get("stream"):
                    self.json_reply({"choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}]})
                    return
                events = []
                for word in text.split(" "):
                    events.append("data: " + json.dumps({"choices": [{"delta": {"content": word + " "}}]}, ensure_ascii=False) + "\n\n")
                events.append("data: [DONE]\n\n")
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(sum(len(e.encode()) for e in events)))
                self.end_headers()
                for event in events:
                    self.wfile.write(event.encode())
                    self.wfile.flush()
                    time.sleep(.025)
            elif self.path == "/v1/cancel":
                self.json_reply({"cancelled": True})
            elif self.path == "/v1/workspace":
                self.json_reply(workspace.snapshot(owner) if workspace else {"projects": [], "documents": [], "jobs": []})
            elif self.path in ("/v1/workspace/action", "/v1/notifications", "/v1/notifications/action") and workspace:
                try:
                    if self.path == "/v1/workspace/action": result = workspace.action(owner, body)
                    elif self.path == "/v1/notifications": result = notifications.snapshot(owner)
                    else: result = notifications.action(owner, body)
                    self.json_reply(result)
                except Exception as error:
                    from workspace import Denied, Conflict
                    self.json_reply({"error": {"message": str(error)}}, 403 if isinstance(error, Denied) else 409 if isinstance(error, Conflict) else 400)
            else:
                self.json_reply({"error": {"message": "Unknown fixture route"}}, 404)
            with guard:
                counts = {k: state[k] for k in ("requests", "rejected")}
                if args.corrector: counts["corrector_modes"] = corrector_modes
                if args.model_selection: counts["model_selection"] = model_checks
                (output / "request-counts.json").write_text(json.dumps(counts), encoding="utf-8")

    api = ThreadingHTTPServer(("127.0.0.1", 0), API)
    threading.Thread(target=api.serve_forever, daemon=True).start()
    server_private, server_public = keypair()
    peers, profiles = [], []
    for index in range(2):
        private, public = keypair()
        psk = base64.b64encode(os.urandom(32)).decode()
        address = f"10.77.0.{123 + index}/32"
        peers.append({"public_key": public, "preshared_key": psk, "address": address})
        profiles.append({"url": "wireguard://10.77.0.1:8766", "transport": "wireguard", "protocol": 3,
                         "client_name": "Fixture Android " + ("téléphone" if index == 0 else "tablette"), "token": token,
                         "wireguard": {"private_key": private, "server_public_key": server_public,
                                       "preshared_key": psk, "address": address}})
    process = subprocess.Popen([str(args.engine.resolve() if args.engine else root / "client-qwen" / "wireguard-bridge.exe")], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        config = {"role": "server", "wireguard": {"private_key": server_private}, "listen_port": 0,
                  "upstream_port": api.server_port, "peers": peers}
        process.stdin.write(json.dumps(config) + "\n")
        process.stdin.flush()
        ready = json.loads(process.stdout.readline())
        if not ready.get("ready") or not ready.get("udp_port"):
            raise RuntimeError("Fixture bridge failed to start")
        for index, profile in enumerate(profiles):
            profile["wireguard"]["endpoint"] = "10.0.2.2:" + str(ready["udp_port"])
            payload = json.dumps(profile, ensure_ascii=False).encode()
            (output / f"profile-{index}.b64").write_text(base64.b64encode(payload).decode(), encoding="ascii")
            (output / f"profile-{index}.fred-android").write_bytes(payload)
        print(json.dumps({"ready": True, "udp_port": ready["udp_port"], "profiles": 2}), flush=True)
        deadline = time.monotonic() + args.duration
        while time.monotonic() < deadline and process.poll() is None and not stop_file.exists():
            time.sleep(.5)
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        api.shutdown()


if __name__ == "__main__":
    main()
