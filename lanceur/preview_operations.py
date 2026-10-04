"""Isolated interface fixture; no model starts and no production settings change."""
import tempfile
from app import Controller, serve
with tempfile.TemporaryDirectory() as folder:
    controller=Controller(folder,include_legacy=False)
    server=serve(8875,controller)
    print('Console de test : http://127.0.0.1:8875',flush=True)
    try:server.serve_forever()
    finally:server.server_close()
