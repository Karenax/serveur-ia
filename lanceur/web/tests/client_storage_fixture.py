"""Dedicated-folder console fixture with two synthetic identities."""
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import Controller, serve
from workspace import HISTORY_RESET_ID

with tempfile.TemporaryDirectory(prefix='fred-folder-ui-') as temporary:
    c = Controller(Path(temporary), include_legacy=False)
    alice = c.remote.issue('Alice synthétique'); bob = c.remote.issue('Bob synthétique')
    w = c.remote.workspace
    w.history_write(alice['id'], {'revision': 0, 'reset_id': HISTORY_RESET_ID,
        'history': {'currentId': 'a', 'conversations': [{'id': 'a', 'title': 'Essai', 'messages': [{'role': 'user', 'content': 'Exemple de conversation Alice'}]}]}})
    c.client_storage.start(); c.client_storage.synchronize()
    with socket.socket() as probe: probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
    server = serve(port, c); threading.Thread(target=server.serve_forever, daemon=True).start()
    print(json.dumps({'url': 'http://127.0.0.1:' + str(port), 'root': str(c.client_storage.root),
        'alice': alice['id'], 'bob': bob['id'], 'fixture': True}), flush=True)
    try: sys.stdin.readline()
    finally:
        server.shutdown(); server.server_close(); c.client_storage.close()
        c.operations.backups.close(); w.shutdown()
