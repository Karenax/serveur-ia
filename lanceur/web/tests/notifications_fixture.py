"""Real console + notification storage, isolated from production processes."""
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import Controller, serve
from core import write_json


def main():
    with tempfile.TemporaryDirectory(prefix='fred-notifications-proof-') as folder:
        home = Path(folder)
        write_json(home / 'base-strata.json', {'model_name': 'isolated-notifications',
            'host': '127.0.0.1', 'port': 49998, 'api_key': '',
            'tokenizer': str(home / 'fake-tokenizer'), 'exe': str(home / 'fake-engine.exe'),
            'env': {'CUDA_VISIBLE_DEVICES': '0,1'}, 'args': ['--pack', str(home / 'fake-pack'),
            '--native', str(home / 'fake-model.gguf'), '--max-context', '32768', '--pool-workers', '15']})
        controller = Controller(home, include_legacy=False)
        controller.state = lambda: {'status': 'arrete', 'running': False, 'error': '',
            'ram': {'available_gib': 32, 'total_gib': 64, 'percent': 50}, 'gpus': [],
            'disks': [], 'logs': 'Validation isolée des notifications.', 'queue': {},
            'lan_ips': ['127.0.0.1'], 'operations': controller.operations.status()}
        inbox = controller.remote.notifications
        for kind in ('backup_failed', 'backup_copy_failed', 'storage_low', 'restore_failed'):
            inbox.publish('admin', kind, 'fixture:' + kind)
        owner = controller.remote.issue('Appareil isolé')['id']
        inbox.publish(owner, 'job_completed', 'private-not-visible')
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0)); port = probe.getsockname()[1]
        server = serve(port, controller)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        print(json.dumps({'fixture': True, 'url': f'http://127.0.0.1:{port}',
                          'home': str(home), 'owner': owner}), flush=True)
        try:
            for line in sys.stdin:
                command = json.loads(line)
                if command.get('action') == 'stop':
                    break
                if command.get('action') == 'publish':
                    print(json.dumps(inbox.publish('admin', command.get('type', 'backup_failed'), command['key'])), flush=True)
                elif command.get('action') == 'snapshot':
                    print(json.dumps({'admin': inbox.admin(), 'private': inbox.snapshot(owner)}), flush=True)
                elif command.get('action') == 'maintenance':
                    controller.maintenance_active = command.get('enabled', True)
                    controller.remote.workspace.maintenance = command.get('enabled', True)
                    print(json.dumps({'changed': True}), flush=True)
        finally:
            server.shutdown(); server.server_close(); thread.join(5)
            controller.remote.workspace.shutdown()
            controller.operations.backups.close()


if __name__ == '__main__':
    main()
