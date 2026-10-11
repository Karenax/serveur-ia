"""Real Controller on disposable storage. Communicates only on stdin/loopback."""
import base64
import hashlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from app import Controller, serve
from core import write_json
from restoration import atomic
from wg_crypto import protect


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def main():
    with tempfile.TemporaryDirectory(prefix='fred-console-backend-') as folder:
        home = Path(folder)
        # Pre-seed a completely synthetic base; Controller must not copy the
        # workstation's model configuration, paths or API key into this fixture.
        write_json(home / 'base-strata.json', {'model_name': 'fixture-console-model',
            'host': '127.0.0.1', 'port': 49998, 'api_key': '', 'tokenizer': str(home / 'fake-tokenizer'),
            'exe': str(home / 'fake-engine.exe'), 'env': {'CUDA_VISIBLE_DEVICES': '0,1'},
            'args': ['--pack', str(home / 'fake-pack'), '--native', str(home / 'fake-model.gguf'),
                '--max-context', '32768', '--pool-workers', '15']})
        controller = Controller(home, include_legacy=False)
        controller.remote_backend = lambda: (49998, 'fixture-console-model', '')
        # Metrics are synthetic; all administration, encryption and restoration are real.
        controller.state = lambda: {'status': 'arrete', 'running': False, 'error': '',
            'ram': {'available_gib': 32, 'total_gib': 64, 'percent': 50}, 'gpus': [], 'disks': [],
            'logs': 'Instance de validation isolée — aucune donnée de production.', 'queue': {},
            'lan_ips': ['127.0.0.1'], 'operations': controller.operations.status()}
        controller.wireguard.configure({'public_host': '127.0.0.1', 'listen_port': 51820})
        initial = controller.wireguard.create_android('Téléphone preuve navigateur', 'fixture-console-model', 'Propriétaire preuve', 'phone')
        owner = initial['id']
        workspace = controller.remote.workspace
        project = workspace.action(owner, {'action': 'project_create', 'title': 'Projet preuve navigateur'})['id']
        original = 'Original UTF-8 : café, téléphone et tablette.\n'.encode()
        document = workspace.action(owner, {'action': 'document_upload', 'project': project,
            'title': 'preuve-original.txt', 'data': base64.b64encode(original).decode()})['id']
        history = {'conversations': [{'id': 'browser-proof', 'title': 'Preuve navigateur',
            'messages': [{'role': 'user', 'content': 'Message avant sauvegarde.'}]}], 'currentId': 'browser-proof'}
        workspace.history_write(owner, {'history': history, 'revision': 0, 'reset_id': workspace.history_read(owner)['reset_id']})
        controller.remote.configure({'enabled': False, 'url': 'wireguard://10.77.0.1:8766'})
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        server = serve(port, controller)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        def snapshot():
            state = workspace.history_read(owner)
            downloaded = workspace.action(owner, {'action': 'document_download', 'id': document})
            metadata = controller.remote.metadata()
            owner_record = next(c for c in metadata['clients'] + metadata.get('archived_clients', []) if c['id'] == owner)
            return {'settings_sha256': digest(controller.settings()), 'history_sha256': digest(state['history']),
                'original_sha256': hashlib.sha256(base64.b64decode(downloaded['data'])).hexdigest(),
                'generation': state['generation'], 'documents': sum(len(p['documents']) for p in workspace.snapshot(owner)['projects']),
                'devices': len(controller.remote.metadata()['clients']), 'enabled': controller.remote.metadata()['enabled'],
                'owner_valid': controller.remote.valid_owner(owner), 'owner_revoked': owner_record['revoked'],
                'owner_suspended': owner_record.get('suspended', False)}

        print(json.dumps({'fixture': True, 'url': f'http://127.0.0.1:{port}', 'owner': owner,
            'home': str(home), 'backup_destination': str(home / 'backup-proof'),
            'secondary_destination': str(home / 'backup-secondary-proof')}), flush=True)
        recovery_fault = None
        try:
            for line in sys.stdin:
                command = json.loads(line)
                if command.get('action') == 'snapshot':
                    print(json.dumps({'snapshot': snapshot()}), flush=True)
                elif command.get('action') == 'mutate':
                    previous = workspace.history_read(owner)
                    workspace.history_write(owner, {'history': {'conversations': [{'id': 'browser-proof', 'title': 'Preuve navigateur',
                        'messages': [{'role': 'user', 'content': 'Message après sauvegarde.'}]}], 'currentId': 'browser-proof'},
                        'revision': previous['revision'], 'reset_id': previous['reset_id'], 'generation': previous['generation']})
                    workspace.action(owner, {'action': 'document_upload', 'project': project,
                        'title': 'document-apres.txt', 'data': base64.b64encode(b'after snapshot').decode()})
                    current = controller.settings()
                    controller.save({**current, 'context': 8192 if current['context'] != 8192 else 16384})
                    print(json.dumps({'mutated': True, 'snapshot': snapshot()}), flush=True)
                elif command.get('action') == 'stop':
                    break
                elif command.get('action') == 'inject-recovery-failure':
                    original_settings = controller.settings()
                    raw = controller.settings_path.read_bytes()
                    atomic(home / 'securite' / 'retour-restauration.dpapi', protect(json.dumps({'reglages.json': base64.b64encode(raw).decode()}).encode()))
                    controller.save({**original_settings, 'context': 8192 if original_settings['context'] != 8192 else 16384})
                    journal = {'id': 'synthetic-recovery-proof', 'state': 'applying', 'phase': 'recovery_failed',
                        'active': True, 'started': time.time(), 'message': 'Retour incomplet simulé : corriger le stockage puis réessayer.'}
                    write_json(home / 'securite' / 'restauration.json', journal)
                    controller.operations.restorations.job = journal
                    controller.remote.maintenance = True
                    workspace.maintenance = True
                    recovery_fault = patch('restoration.atomic', side_effect=OSError('Synthetic storage failure'))
                    recovery_fault.start()
                    print(json.dumps({'injected': True, 'original_settings_sha256': digest(original_settings)}), flush=True)
                elif command.get('action') == 'repair-recovery':
                    if recovery_fault:
                        recovery_fault.stop()
                        recovery_fault = None
                    print(json.dumps({'repaired': True}), flush=True)
                else:
                    print(json.dumps({'error': 'Commande de fixture inconnue.'}), flush=True)
        finally:
            if recovery_fault:
                recovery_fault.stop()
            server.shutdown()
            server.server_close()
            if controller.operations.restorations.thread:
                controller.operations.restorations.thread.join(10)
            controller.operations.backups.close()
            workspace.shutdown()


if __name__ == '__main__':
    main()
