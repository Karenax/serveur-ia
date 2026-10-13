"""Synthetic audit reproductions. No real model, credential or production data."""
import copy
import base64
import json
from pathlib import Path
import secrets
import sys
import tempfile
import time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path[:0] = [str(ROOT / "lanceur"), str(ROOT / "client-qwen")]
from test_hermes_conversations import ConversationsTests
from history_store import validate, HistoryError
from hermes_backup import HermesBackup
from workspace import DEFAULT_LIMITS
from test_hermes_inference import PrivateInferenceTests
from client_storage import ClientStorage
import sqlite3
from chat_attachments import validate_parts

findings = {}


def fixture(check):
    case = ConversationsTests()
    case.setUp()
    try:
        return check(case)
    finally:
        case.tearDown()


def invalid_history(case):
    messages = [{"role": "user", "content": "Question", "turn_id": case.request}]
    messages.extend({"role": "assistant" if i % 2 == 0 else "user", "content": "x"} for i in range(997))
    messages.append({"role": "user", "content": "Question finale", "turn_id": case.request})
    # Start at the accepted 1000-message boundary, then generate one answer.
    messages.insert(0, {"role": "assistant", "content": "Préface"})
    history = {"currentId": "discussion", "conversations": [{"id": "discussion", "title": "Discussion", "messages": messages}]}
    messages[1].pop("turn_id", None)
    validate(history)
    current = case.store.workspace.history_read(case.a)
    case.store.workspace.history_write(case.a, {"history": history, "revision": current["revision"], "reset_id": current["reset_id"], "generation": current["generation"]})
    case.data["messages"] = copy.deepcopy(messages)
    list(case.manager.stream(case.a, case.data, case.request, "discussion"))
    after = case.store.workspace.history_read(case.a)["history"]
    rejected = ""
    try:
        validate(after)
    except HistoryError as exc:
        rejected = str(exc)
    return {"before_messages": len(messages), "after_messages": len(after["conversations"][0]["messages"]), "client_validation_error": rejected,
            "run_state": case.manager.reconcile(case.a, case.request, "discussion")["status"]}


def unbounded_runs(case):
    data = {"messages": [{"role": "user", "content": "S" * (2 * 1024 * 1024)}], "reasoning_effort": "none"}
    for index in range(6):
        list(case.manager.stream(case.b, data, secrets.token_hex(16), "audit-" + str(index)))
    with case.store.workspace.db() as db:
        usage = case.store.workspace.usage(db, case.b)
    with case.manager.db() as db:
        rows = db.execute("SELECT COUNT(*) FROM agent_runs WHERE owner=?", (case.b,)).fetchone()[0]
    failure = ""
    try:
        HermesBackup(case.manager.root).export({case.a, case.b})
    except ValueError as exc:
        failure = str(exc)
    return {"runs": rows, "request_bytes_each": 2 * 1024 * 1024, "canonical_used_bytes": usage,
            "integration_db_bytes": case.manager.path.stat().st_size, "backup_error": failure}


def history_size(case):
    history = {"currentId": "discussion", "conversations": [{"id": "discussion", "title": "Discussion", "messages": [
        {"role": "assistant", "content": "A" * (8 * 1024 * 1024)},
        {"role": "user", "content": "Question", "turn_id": case.request}]}]}
    validate(history)
    current = case.store.workspace.history_read(case.a)
    case.store.workspace.history_write(case.a, {"history": history, "revision": current["revision"], "reset_id": current["reset_id"], "generation": current["generation"]})
    case.service.output = "R" * (1536 * 1024)
    case.data["messages"] = copy.deepcopy(history["conversations"][0]["messages"])
    list(case.manager.stream(case.a, case.data, case.request, "discussion"))
    after = case.store.workspace.history_read(case.a)["history"]
    failure = ""
    try:
        validate(after)
    except HistoryError as exc:
        failure = str(exc)
    return {"before_bytes": len(json.dumps(history, ensure_ascii=False).encode()), "after_bytes": len(json.dumps(after, ensure_ascii=False).encode()), "client_validation_error": failure}


def memory_quota(case):
    workspace = case.store.workspace
    project = workspace.action(case.b, {"action": "project_create", "title": "Quota"})["id"]
    original = "M" * 1500
    memory = workspace.action(case.b, {"action": "memory_create", "project": project, "text": original})["id"]
    workspace.admin_action({"action": "policy", "owner": case.b, "limits": {**DEFAULT_LIMITS, "storage_mb": 1}}, {case.a, case.b})
    history = {"currentId": "padding", "conversations": [{"id": "padding", "title": "Padding", "messages": [{"role": "user", "content": ""}]}]}
    with workspace.db() as db:
        used = workspace.usage(db, case.b)
    overhead = len(json.dumps(history, ensure_ascii=False).encode())
    history["conversations"][0]["messages"][0]["content"] = "P" * (1024 * 1024 - 1000 - used - overhead)
    workspace.history_write(case.b, {"history": history, "revision": 0, "reset_id": case.store.workspace.history_read(case.b)["reset_id"]})
    with workspace.db() as db:
        used_before = workspace.usage(db, case.b)
    failure = ""
    try:
        workspace.action(case.b, {"action": "memory_save", "id": memory, "text": original})
    except ValueError as exc:
        failure = str(exc)
    return {"unchanged_memory_bytes": len(original), "available_quota_bytes": 1024 * 1024 - used_before, "actual_storage_delta_bytes": 0, "error": failure}


def late_mcp():
    case = PrivateInferenceTests()
    case.setUp()
    try:
        project_a = case.store.workspace.action(case.a, {"action": "project_create", "title": "Ancien projet"})["id"]
        project_b = case.store.workspace.action(case.a, {"action": "project_create", "title": "Nouveau projet"})["id"]
        data = {"messages": [{"role": "user", "content": "Lire le projet"}]}
        old_request = secrets.token_hex(16)
        _, old = case.manager._prepare(case.a, data, old_request, "old-conversation", project_a, None, False)
        old["cancelled"].set()
        case.manager._update(case.a, old_request, state="cancelled")
        case.manager.active.pop(case.a); case.store.active -= 1
        _, current = case.manager._prepare(case.a, data, secrets.token_hex(16), "new-conversation", project_b, None, False)
        # A delayed request uses the persistent profile tool key from the old turn.
        call = {"jsonrpc": "2.0", "id": 42, "method": "tools/call", "params": {"name": "fred_workspace_info", "arguments": {}}}
        status, raw = case.post("/mcp", call, "tool-A")
        result = json.loads(raw)["result"]
        actual = result["structuredContent"]["data"]["project"]
        return {"http_status": status, "is_error": result["isError"], "old_turn_cancelled": old["cancelled"].is_set(), "intended_project": project_a,
                "returned_project": actual["id"], "returned_title": actual["title"], "current_project": project_b}
    finally:
        case.tearDown()


def client_storage_schema(case):
    storage = ClientStorage(case.store)
    try:
        storage.synchronize()
        project = case.store.workspace.action(case.a, {"action": "project_create", "title": "Projet exporté"})["id"]
        identity = secrets.token_hex(16)
        case.store.workspace.action(case.a, {"action": "conversation_save", "project": project, "id": identity,
            "title": "Conversation du projet", "revision": 0, "reset_id": case.store.workspace.history_read(case.a)["reset_id"],
            "messages": [{"role": "user", "content": "Test"}], "archived": False})
        failure = ""
        try:
            storage.synchronize()
        except sqlite3.Error as exc:
            failure = str(exc)
        return {"export_before_project_conversation": "success", "project_conversation_saved": True, "export_after_project_conversation_error": failure}
    finally:
        storage.close()


def image_history(case):
    image = "data:image/png;base64," + base64.b64encode(b"\x89PNG\r\n\x1a\n" + b"synthetic-audit-image").decode()
    content = [{"type": "text", "text": "Décris cette image"}, {"type": "image_url", "image_url": {"url": image}}]
    validate_parts(content, "user")
    case.data["messages"] = [{"role": "user", "content": content}, {"role": "assistant", "content": "Image décrite"}, {"role": "user", "content": "Relis le détail sur l’image précédente"}]
    list(case.manager.stream(case.a, case.data, case.request, "imported-image-chat"))
    body = next(c[3] for c in case.service.calls if c[2] == "/v1/runs")
    history = body["conversation_history"]
    return {"fred_history_image_parts": 1, "native_history_image_parts": sum(
        sum(p.get("type") == "image_url" for p in m["content"]) if isinstance(m["content"], list) else 0 for m in history),
        "native_first_user_content": history[0]["content"], "previous_image_transmitted": image in json.dumps(body)}


for name, check in [("invalid_history_count", invalid_history), ("unbounded_runs_backup_failure", unbounded_runs), ("invalid_history_size", history_size), ("memory_quota_unchanged_edit", memory_quota), ("client_storage_schema_mismatch", client_storage_schema), ("past_image_removed_from_native_history", image_history)]:
    findings[name] = fixture(check)
    print(name, json.dumps(findings[name], ensure_ascii=False), flush=True)
    (OUT / "reproductions.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
findings["late_mcp_uses_next_turn_scope"] = late_mcp()
print("late_mcp_uses_next_turn_scope", json.dumps(findings["late_mcp_uses_next_turn_scope"], ensure_ascii=False), flush=True)
(OUT / "reproductions.json").write_text(json.dumps(findings, ensure_ascii=False, indent=2), encoding="utf-8")
