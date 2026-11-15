"""Synchronize durable Windows capture fragments with the Agent meeting service."""

import hashlib
import json
import os
import queue
import re
import secrets
import subprocess
import threading
import time
import urllib.error
from uuid import UUID, uuid4

from history_store import atomic


MAX_FRAGMENT_BYTES = 512 * 1024
MAX_RECEIPT_BYTES = 64 * 1024
MAX_CAPTURE_MS = 12 * 60 * 60 * 1000


class DesktopCapture:
    def __init__(self, remote, helper, directory):
        self.remote, self.helper, self.directory = remote, helper, directory
        self.lock = threading.RLock()
        self.transfer_lock = threading.Lock()
        self.closing = threading.Event()
        self.process = None
        self.current = None
        self.events = queue.Queue()
        self.inventory = None
        self.helper_environment = {**os.environ, 'PYINSTALLER_RESET_ENVIRONMENT': '1'}

    def start_transfer_worker(self):
        threading.Thread(target=self.retry_transfers, name='agent-capture-transfer', daemon=True).start()

    def retry_transfers(self):
        while not self.closing.wait(5):
            for sid in self.journal_sessions():
                if self.closing.is_set():
                    return
                if not self.transfer_lock.acquire(blocking=False):
                    break
                try:
                    item = self.load(sid)
                    if item.get('transfer_requested') is True:
                        self.finish_stop(item)
                except urllib.error.HTTPError as error:
                    error.close()
                except (OSError, ValueError, KeyError, TypeError):
                    continue  # The retained journal will be retried while Kiara is open.
                finally:
                    self.transfer_lock.release()

    def journal_sessions(self):
        for journal in self.directory.glob('*/capture.json'):
            sid = journal.parent.name
            if re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}', sid):
                yield sid

    def call(self, sid, suffix='', data=None):
        target = f'/v1/business/api/v1/meeting-sessions/{sid}{suffix}'
        with self.open(target, None if data is None else json.dumps(data).encode()) as response:
            return json.load(response)

    def open(self, *args, **kwargs):
        if self.closing.is_set():
            raise OSError('Le relais Kiara se ferme.')
        timeout = 900 if args[0].endswith('/finalize') else 20
        return self.remote.open(*args, **kwargs, timeout=timeout)

    def status(self, sid=None):
        with self.lock:
            if self.inventory is None:
                self.inventory = json.loads(subprocess.check_output([str(self.helper), '--inventory'],
                    stdin=subprocess.DEVNULL, encoding='utf-8', timeout=12, env=self.helper_environment,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0)))
            devices = self.inventory.get('devices', [])
            items = []
            for identity in self.journal_sessions():
                try:
                    item = self.load(identity)
                except (OSError, ValueError, KeyError, TypeError):
                    continue
                alive = bool(self.current and self.current['session_id'] == identity
                             and self.process and self.process.poll() is None)
                state = item['state'] if alive else 'stopped' if item.get('transfer_requested') else 'interrupted'
                items.append({'session_id': identity, 'state': state, 'tracks': item['tracks'],
                              'process_alive': alive, 'can_control': True})
            return {'installed': True, 'ready': bool(devices and self.inventory.get('interactive_session')),
                    'devices': devices, 'active': items,
                    'session': next((item for item in items if item['session_id'] == sid), None),
                    'loopback_ready': False, 'real_test_passed': False, 'microphone_test_passed': False}

    def load(self, sid):
        with (self.directory / sid / 'capture.json').open('rb') as stream:
            item = json.loads(stream.read(8193))
        if item['session_id'] != sid:
            raise ValueError('Journal de séance invalide.')
        return item

    def persist(self, item):
        atomic(self.directory / item['session_id'] / 'capture.json', json.dumps(item).encode())

    def wait_event(self, predicate, *, timeout=8):
        deadline = time.monotonic() + timeout
        while True:
            try:
                event = self.events.get(timeout=max(0, deadline - time.monotonic()))
            except queue.Empty:
                raise ValueError('Le helper Windows ne répond pas.') from None
            if event is None or event.get('kind') == 'error':
                raise ValueError('La capture Windows a été interrompue. Les fragments restent sur ce poste.')
            if predicate(event):
                return

    def send(self, operation, state):
        self.process.stdin.write(json.dumps({'op': operation}) + '\n')
        self.process.stdin.flush()
        self.wait_event(lambda event: event.get('kind') == 'state' and event.get('state') == state)

    def close_helper(self):
        process, self.process = self.process, None
        if process is None:
            return
        try:
            process.stdin.close()
        except OSError:
            pass
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def close(self):
        self.closing.set()
        with self.lock:
            self.close_helper()

    def start(self, sid, body):
        tracks, devices = body.get('tracks'), body.get('devices', {})
        if (not isinstance(tracks, list) or not 1 <= len(tracks) <= 2
                or any(track not in ('mic', 'system') for track in tracks) or len(set(tracks)) != len(tracks)
                or not isinstance(devices, dict) or any(track not in tracks or type(index) is not int or index < 0
                                                         for track, index in devices.items())):
            raise ValueError('Choisissez les pistes et périphériques à enregistrer.')
        if self.current:
            raise ValueError('Terminez la capture Windows en cours.')
        row = self.call(sid)
        if row['revision'] != body['expected_revision'] or row['state'] != 'created' or row.get('chunks'):
            raise ValueError('Actualisez la séance ou créez une nouvelle séance audio.')
        folder = self.directory / sid
        folder.mkdir(parents=True, exist_ok=True)
        if (folder / 'capture.json').exists() or (folder / 'audio').exists():
            raise ValueError('Des fragments ou une réservation restent à vérifier dans cette séance.')
        owner = str(uuid4())
        self.current = {'session_id': sid, 'state': 'starting', 'tracks': tracks, 'owner': owner,
                        'start_command': body['command_id']}
        self.persist(self.current)
        try:
            row = self.call(sid, '/browser-capture/reserve', {**command(row), 'owner_id': owner})
            request = folder / 'helper.json'
            atomic(request, json.dumps({'session_id': sid, 'storage': str(folder), 'directory': str(folder / 'audio'),
                                        'tracks': tracks, 'devices': devices}).encode())
            self.events = events = queue.Queue()
            self.process = subprocess.Popen([str(self.helper), '--request', str(request), '--parent-pid', str(os.getpid())],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding='utf-8',
                env=self.helper_environment, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            output = self.process.stdout

            def read():
                try:
                    for line in output:
                        event = json.loads(line)
                        if event.get('kind') != 'chunk':
                            events.put(event)
                finally:
                    output.close()
                    events.put(None)

            threading.Thread(target=read, daemon=True).start()
            # The one-file helper extracts PyAV and its libraries on startup.
            self.wait_event(lambda event: event.get('kind') == 'ready', timeout=25)
            row = self.call(sid, '/resume', {**command(row), 'browser_capture_owner_id': owner})
            self.send('start', 'recording')
            self.current['state'] = 'recording'
            self.persist(self.current)
            return row
        except Exception:
            self.close_helper()
            self.current['state'] = 'interrupted'
            self.persist(self.current)
            raise

    def control(self, sid, operation, body):
        with self.lock:
            nonce = body.get('command_id', '')
            if str(UUID(sid)) != sid or (operation != 'stop' and (
                    not isinstance(nonce, str) or str(UUID(nonce)) != nonce
                    or type(body.get('expected_revision')) is not int or body['expected_revision'] < 1)):
                raise ValueError('Commande de séance invalide.')
            if operation == 'start':
                if (self.current and self.current['session_id'] == sid and self.current['start_command'] == nonce
                        and self.current['state'] == 'recording' and self.process and self.process.poll() is None):
                    return self.call(sid)
                return self.start(sid, body)
            if self.current and self.current['session_id'] != sid:
                raise ValueError('Une autre séance utilise la capture Windows.')
            try:
                item = self.current or self.load(sid)
            except FileNotFoundError:
                if operation == 'stop':
                    return self.call(sid)
                raise
            if operation == 'stop':
                try:
                    if self.process and self.process.poll() is None:
                        self.send('stop', 'stopped')
                finally:
                    self.close_helper()
                if not item.get('transfer_requested'):
                    item['transfer_requested'] = True
                    item['state'] = 'stopped'
                    self.persist(item)
                self.current = None
            else:
                return self.change_capture(sid, operation, item)
        with self.transfer_lock:
            try:
                item = self.load(sid)
            except FileNotFoundError:
                return self.call(sid)
            return self.finish_stop(item)

    def finish_stop(self, item):
        sid, owner = item['session_id'], item['owner']
        row = self.call(sid)
        reservation = row.get('browser_capture')
        if reservation and (reservation['owner_id'] != owner or not reservation['can_control']):
            raise ValueError('La réservation de la séance a changé.')
        if not reservation and not item.get('release_pending'):
            if row['state'] != 'created' or (self.directory / sid / 'audio').exists():
                raise ValueError('La réservation de la séance n’est plus active.')
            (self.directory / sid / 'capture.json').unlink(missing_ok=True)
            return row
        audio = self.directory / sid / 'audio'
        if reservation and audio.is_dir():
            if any(not intent.with_suffix('.json').is_file() for intent in audio.glob('*.intent')):
                raise ValueError('Un fragment Windows est incomplet. Le journal et les fichiers restent sur ce poste.')
            for _ in upload_journal(self, audio, sid):
                pass
        row = self.call(sid)
        reservation = row.get('browser_capture')
        if reservation:
            if reservation['owner_id'] != owner or not reservation['can_control']:
                raise ValueError('La réservation de la séance a changé.')
            item['release_pending'] = True
            self.persist(item)
            row = self.call(sid, '/browser-capture/release', {**command(row), 'owner_id': owner})
        if row['state'] != 'completed':
            if 'finalize_command' not in item:
                item['finalize_command'] = command(row)
                self.persist(item)
            finalize = item['finalize_command']
            try:
                row = self.call(sid, '/finalize', finalize)
            except urllib.error.HTTPError as error:
                if error.code == 409:
                    try:
                        outcome = self.call(sid, '/commands/' + finalize['command_id'])
                    except urllib.error.HTTPError as lookup_error:
                        if lookup_error.code != 404:
                            lookup_error.close()
                            raise error from None
                        lookup_error.close()
                        outcome = None
                    if outcome is None or outcome.get('status') == 'rejected':
                        del item['finalize_command']
                        self.persist(item)
                raise
        (self.directory / sid / 'capture.json').unlink(missing_ok=True)
        return row

    def change_capture(self, sid, operation, item):
        owner = item['owner']
        if self.process is None or self.process.poll() is not None:
            raise ValueError('La capture est arrêtée. Conservez les fragments de la séance.')
        row = self.call(sid)
        reservation = row.get('browser_capture')
        if not reservation or reservation['owner_id'] != owner or not reservation['can_control']:
            raise ValueError('La réservation de la séance a changé.')
        target = 'paused' if operation == 'pause' else 'recording'
        if row['state'] != target:
            row = self.call(sid, '/' + operation, {**command(row), 'browser_capture_owner_id': owner})
        if item['state'] != target:
            self.send(operation, target)
            item['state'] = target
            self.persist(item)
        return row


def command(row):
    return {'command_id': str(uuid4()), 'expected_revision': row['revision']}


def upload_journal(remote, directory, session_id):
    """Replay published journal entries in track/sequence order, preserving originals."""
    for manifest in sorted(directory.glob('*.json')):
        if not re.fullmatch(r'(mic|system)-[0-9]{8}\.json', manifest.name):
            continue
        if manifest.is_symlink() or manifest.resolve(strict=True).parent != directory.resolve(strict=True):
            raise ValueError('Journal audio hors du dossier de capture.')
        with manifest.open('rb') as stream:
            raw = stream.read(16385)
        if len(raw) > 16384:
            raise ValueError('Journal audio trop volumineux.')
        packet = json.loads(raw)
        if (not isinstance(packet, dict) or type(packet.get('sequence')) is not int
                or f'{packet.get("track")}-{packet["sequence"]:08d}.json' != manifest.name):
            raise ValueError('Nom du journal audio invalide.')
        yield upload_fragment(remote, directory, session_id, packet)


def upload_fragment(remote, directory, session_id, packet):
    """Verify the local journal and return only an exact remote acknowledgement."""
    if str(UUID(session_id)) != session_id or packet.get('session_id') != session_id:
        raise ValueError('Séance du fragment invalide.')
    track = packet.get('track')
    sequence = packet.get('sequence')
    size = packet.get('size_bytes')
    start = packet.get('start_ms')
    duration = packet.get('duration_ms')
    digest = packet.get('sha256')
    command = packet.get('command_id')
    if (packet.get('kind') != 'chunk' or track not in ('mic', 'system')
            or type(sequence) is not int or not 0 <= sequence < 100_000_000
            or type(size) is not int or not 0 < size <= MAX_FRAGMENT_BYTES
            or type(start) is not int or type(duration) is not int or start < 0 or duration <= 0
            or start + duration > MAX_CAPTURE_MS or not isinstance(digest, str)
            or not re.fullmatch(r'[0-9a-f]{64}', digest)
            or not isinstance(command, str) or str(UUID(command)) != command):
        raise ValueError('Journal de fragment audio invalide.')

    filename = f'{track}-{sequence:08d}.ogg'
    root = directory.resolve(strict=True)
    path = (root / filename).resolve(strict=True)
    if path.parent != root or path.name != filename:
        raise ValueError('Fragment audio hors du dossier de capture.')
    with path.open('rb') as stream:
        raw = stream.read(MAX_FRAGMENT_BYTES + 1)
    if len(raw) != size or not raw.startswith(b'OggS') or hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Le fragment audio ne correspond pas à son journal.')

    boundary = 'kiara-' + secrets.token_hex(16)
    marker = f'--{boundary}\r\n'.encode('ascii')
    fields = {'command_id': command, 'sha256': digest, 'start_ms': start, 'duration_ms': duration}
    parts = [marker + f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode('ascii')
             for name, value in fields.items()]
    parts.extend((marker + f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
                  'Content-Type: audio/ogg\r\n\r\n'.encode('ascii'), raw, f'\r\n--{boundary}--\r\n'.encode('ascii')))
    body = b''.join(parts)
    target = f'/v1/business/api/v1/meeting-sessions/{session_id}/chunks/{track}/{sequence}'
    with remote.open(target, body, method='PUT', content_type=f'multipart/form-data; boundary={boundary}',
                     content_length=len(body)) as response:
        payload = response.read(MAX_RECEIPT_BYTES + 1)
    if len(payload) > MAX_RECEIPT_BYTES:
        raise ValueError('Reçu audio trop volumineux.')
    receipt = json.loads(payload)
    accepted = {'track': track, 'seq': sequence, 'sha256': digest, 'size_bytes': size}
    if (not isinstance(receipt, dict) or receipt.get('acknowledged') is not True
            or receipt.get('session_id') != session_id or receipt.get('accepted_chunk') != accepted):
        raise ValueError('Le reçu Agent ne correspond pas au fragment conservé.')
    return receipt
