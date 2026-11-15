"""Isolated WireGuard/API fixture for emulator checks. No live accounts are read."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import secrets
import ssl
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
    parser.add_argument("--reasoning", action="store_true", help="Verify model-specific effort/toggle/automatic native reasoning transport")
    parser.add_argument("--project-chat", action="store_true", help="Exercise project chat over the native tunnel")
    parser.add_argument("--large-original", action="store_true", help="Serve a project original larger than 16 MiB")
    parser.add_argument("--reset-wireguard", action="store_true", help="Allow the native pilot to restart its test tunnel on request")
    parser.add_argument("--tls", type=Path, nargs=2, metavar=("CERTIFICATE", "KEY"),
                        help="Run a local HTTPS fixture instead of WireGuard")
    parser.add_argument("--engine", type=Path, help="Isolated staged bridge, leaving a live production executable untouched")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    stop_file = output / 'stop-fixture'
    stop_file.unlink(missing_ok=True)
    token = "qwen_" + secrets.token_hex(8) + "_" + secrets.token_urlsafe(32)
    state = {"history": None, "revision": 0, "requests": {}, "rejected": 0}
    managed = {"id": "11111111-2222-3333-4444-555555555555", "title": "Projet de recette",
               "brain_project_id": "brain-fixture", "project_kind": "managed", "has_knowledge": True,
               "conversations": [], "documents": [], "memories": []}
    threads = "/v1/business/api/v1/workspace/assistant-threads"
    thread = {"id": "fil-recette", "title": "Discussion enregistrée", "revision": 2,
              "project_id": managed["brain_project_id"], "messages": [
                  {"role": "user", "text": "Ancienne question"},
                  {"role": "assistant", "text": "Ancienne réponse"}]}
    corrector_modes = {}
    model_checks = {"context": 0, "chat": 0, "retired": 0, "local_unloaded": 0, "rejected": 0}
    reasoning_checks = {"context": 0, "chat": 0, "unsupported": 0, "rejected": 0, "combinations": {}}
    reasoning_rows = [
        {"id": "fred-qwen", "provider": "Qwen local", "reasoning_mode": "effort", "reasoning_efforts": ["none", "low", "medium", "high"]},
        {"id": "fred-model-toggle", "provider": "NVIDIA", "reasoning_mode": "toggle", "reasoning_efforts": ["none", "on"]},
        {"id": "fred-model-effort", "provider": "OpenRouter", "reasoning_mode": "effort", "reasoning_efforts": ["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"]},
        {"id": "fred-model-auto", "provider": "Nous Portal", "reasoning_mode": "none", "reasoning_efforts": []},
    ]
    def reasoning_request(body, chat):
        required = {"model", "messages"} | ({"stream", "conversation_id"} if chat else set())
        row = next((row for row in reasoning_rows if row["id"] == body.get("model")), None)
        valid = (required <= set(body) <= required | {"reasoning_effort"} and row is not None
                 and body.get("messages") == [{"role": "user", "content": "Test synthétique Android : raisonnement sélectionné."}]
                 and (not chat or (body.get("stream") is True and isinstance(body.get("conversation_id"), str) and len(body["conversation_id"]) == 32)))
        if not valid:
            reasoning_checks["rejected"] += 1
            return False, False
        effort = body.get("reasoning_effort")
        if ((row["reasoning_efforts"] and effort not in row["reasoning_efforts"])
                or (not row["reasoning_efforts"] and "reasoning_effort" in body)):
            reasoning_checks["unsupported"] += 1
            return False, True
        reasoning_checks["chat" if chat else "context"] += 1
        label = body["model"] + ":" + (effort or "automatic")
        reasoning_checks["combinations"][label] = reasoning_checks["combinations"].get(label, 0) + 1
        return True, False
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
        state["fixture"] = {"project": project, "document": document, "pdf_document": pdf_document, "foreign_document": foreign_document}
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

        do_PUT = do_POST

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
            if args.project_chat and self.path == "/v1/business/api/v1/session":
                self.json_reply({"operator":{"id":"recette","role":"owner"}})
            elif args.project_chat and self.path == "/v1/business/api/v1/project-catalogue":
                self.json_reply([managed])
            elif args.project_chat and self.path.startswith(threads + "?") and self.command == "GET":
                self.json_reply({"items": [thread]})
            elif args.project_chat and self.path == threads + "/fil-recette":
                if self.command == "PUT":
                    with guard:
                        if body.get("expected_revision") != thread["revision"]:
                            self.json_reply({"detail": "Révision de recette obsolète."}, 409)
                            return
                        thread.update(messages=body["messages"], revision=thread["revision"] + 1)
                self.json_reply(thread)
            elif args.project_chat and self.path == "/v1/business/v1/sources/source-recette":
                self.json_reply({"metadata": {"filename": "Notice de recette"},
                                 "artifacts": [{"text": "Texte indexé de la notice."}]})
            elif args.project_chat and self.path == "/v1/business/v1/sources/source-recette/raw":
                copies = 17*1024*1024//256 if args.large_original else 1
                original = bytes(range(256))*copies + b"Kiara original\r\n"
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Disposition", 'attachment; filename="kiara-original.bin"')
                self.send_header("Content-Length", str(len(original)))
                self.send_header("X-Agent-Source-Sha256", hashlib.sha256(original).hexdigest())
                self.end_headers()
                self.wfile.write(original)
            elif args.project_chat and self.path == "/v1/business/v1/projects/chat/stream":
                if body.get("project_id") != managed["brain_project_id"]:
                    self.json_reply({"detail": "Périmètre de recette invalide."}, 403)
                    return
                reply = "Réponse de projet reçue par " + ("HTTPS" if args.tls else "WireGuard")
                evidence = [{"source_id": "source-recette", "excerpt": "Extrait de recette."}]
                events = [f"event: {kind}\ndata: {json.dumps(data)}\n\n".encode()
                          for kind, data in (("delta", {"text": reply}),
                                             ("done", {"answer": reply, "citations": evidence}))]
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Content-Length", str(sum(map(len, events))))
                self.end_headers()
                for event in events:
                    self.wfile.write(event)
                    self.wfile.flush()
                    time.sleep(.15)
            elif self.path == "/v1/models":
                if args.reasoning:
                    self.json_reply({"object": "list", "source": "hermes", "default_model": "fred-model-toggle", "data": [
                        {"id": row["id"], "name": "Fixture " + row["reasoning_mode"], "provider": row["provider"], "available": True,
                         "capabilities": {"thinking": bool(row["reasoning_efforts"]), "reasoning_mode": row["reasoning_mode"], "reasoning_efforts": row["reasoning_efforts"], "images": False, "vision": False, "context_length": 32768}} for row in reasoning_rows]})
                elif args.model_selection:
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
                if args.reasoning:
                    with guard:
                        valid, unsupported = reasoning_request(body, False)
                    self.json_reply({"tokens": 100, "capacity": 32768, "estimated": True, "fits": True} if valid else
                                    {"error": {"code": "reasoning_effort_unavailable" if unsupported else "fixture_rejected", "message": "Synthetic reasoning context rejected"}}, 200 if valid else 400)
                elif args.model_selection:
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
                        if args.project_chat and "Échange éphémère de recette" in json.dumps(body, ensure_ascii=False):
                            self.json_reply({"detail": "Une question éphémère a atteint l’historique."}, 422)
                            return
                        if str(body.get("revision")) != str(state["revision"]):
                            self.json_reply({"error": {"message": "Fixture revision changed"}}, 409)
                            return
                        state["history"] = body.get("history")
                        state["revision"] += 1
                    self.json_reply({"history": state["history"], "revision": str(state["revision"]), "reset_id": "20261006-remove-assistants"})
            elif self.path == "/v1/chat/completions":
                if args.reasoning:
                    with guard:
                        valid, unsupported = reasoning_request(body, True)
                        if len(self.headers.get("X-Qwen-Request", "")) != 32:
                            valid = False
                            reasoning_checks["rejected"] += 1
                    if not valid:
                        self.json_reply({"error": {"code": "reasoning_effort_unavailable" if unsupported else "fixture_rejected", "message": "Synthetic reasoning chat rejected"}}, 400)
                        return
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
                self.json_reply({"projects": [managed], "jobs": [],
                                 "project_catalogue": {"state": "ready", "can_create": False}}
                                if args.project_chat else workspace.snapshot(owner)
                                if workspace else {"projects": [], "documents": []})
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
                if args.tls: counts["tls"] = self.connection.version()
                if args.corrector: counts["corrector_modes"] = corrector_modes
                if args.model_selection: counts["model_selection"] = model_checks
                if args.reasoning: counts["reasoning"] = reasoning_checks
                (output / "request-counts.json").write_text(json.dumps(counts), encoding="utf-8")

    api = ThreadingHTTPServer(("127.0.0.1", 0), API)
    if args.tls:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(*args.tls)
        api.socket = tls.wrap_socket(api.socket, server_side=True)
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
    executable = args.engine.resolve() if args.engine else root / "client-qwen" / "wireguard-bridge.exe"

    def start_bridge(config):
        child = subprocess.Popen([str(executable)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8",
                               creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            child.stdin.write(json.dumps(config) + "\n")
            child.stdin.flush()
            ready = json.loads(child.stdout.readline())
            if not ready.get("ready") or not ready.get("udp_port"):
                raise RuntimeError("Fixture bridge failed to start")
            return child, ready
        except BaseException:
            stop_bridge(child)
            raise

    def stop_bridge(child):
        child.stdin.close()
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()

    process = None
    try:
        config = {"role": "server", "wireguard": {"private_key": server_private}, "listen_port": 0,
                  "upstream_port": api.server_port, "peers": peers}
        ready = {"ready": True, "https_port": api.server_port}
        if not args.tls:
            process, ready = start_bridge(config)
        for index, profile in enumerate(profiles):
            profile["wireguard"]["endpoint"] = "10.0.2.2:" + str(ready.get("udp_port", 51820))
            payload = json.dumps(profile, ensure_ascii=False).encode()
            (output / f"profile-{index}.b64").write_text(base64.b64encode(payload).decode(), encoding="ascii")
            (output / f"profile-{index}.fred-android").write_bytes(payload)
        print(json.dumps({**ready, "profiles": 2}), flush=True)
        (output / "ready.json").write_text(json.dumps(ready), encoding="utf-8")
        deadline = time.monotonic() + args.duration
        reset_file = output / "restart-wireguard"
        restarted_file = output / "wireguard-restarted"
        reset_file.unlink(missing_ok=True)
        restarted_file.unlink(missing_ok=True)
        restarts = 0
        while time.monotonic() < deadline and (process is None or process.poll() is None) and not stop_file.exists():
            if args.reset_wireguard and process and reset_file.exists():
                reset_file.unlink()
                stop_bridge(process)
                process = None
                process, _ = start_bridge({**config, "listen_port": ready["udp_port"]})
                restarts += 1
                restarted_file.write_text(str(restarts), encoding="ascii")
            time.sleep(.5)
    finally:
        if process:
            stop_bridge(process)
        api.shutdown()


if __name__ == "__main__":
    main()
