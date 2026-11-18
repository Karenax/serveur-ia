"""Temporary loopback transport for a future portal-origin recovery flow.

Not connected to the desktop client yet. All requested ports must be reserved
before recovery begins. One record is held in memory until its verified receipt;
no payload is written to a file by this module.
"""
from __future__ import annotations

import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import secrets
import socket
import threading
from typing import Mapping
from portal_origin_plan import InventoryPlanError, OriginInventoryPlan


def _local_record(payload):
    """Validate a staged local record without returning its private contents."""
    try:
        def unique_record(pairs):
            result = {}
            for key, value in pairs:
                if key in result:raise ValueError('duplicate')
                result[key] = value
            return result
        record = json.loads(payload.decode('utf-8'), object_pairs_hook=unique_record)
        return (isinstance(record,dict) and set(record)=={'type','key','value'} and record['type']=='local'
                and isinstance(record['key'],str) and isinstance(record['value'],str))
    except (UnicodeError,ValueError,RecursionError):
        return False


def _audio_conflict_record(payload):
    """Recognize only complete inline audio or the end of a segmented audio."""
    try:
        def unique_record(pairs):
            result = {}
            for key, value in pairs:
                if key in result:raise ValueError('duplicate')
                result[key] = value
            return result
        record = json.loads(payload.decode('utf-8'), object_pairs_hook=unique_record)
        if not isinstance(record,dict):return False
        if record.get('type')=='audio':
            return (set(record)=={'type','meta','mime','data'} and isinstance(record['meta'],dict)
                    and isinstance(record['mime'],str) and bool(record['mime']) and isinstance(record['data'],str))
        return (record.get('type')=='audio-end' and set(record)=={'type','id'}
                and isinstance(record['id'],str) and bool(record['id']))
    except (UnicodeError,ValueError,RecursionError):
        return False


class RecoveryUnavailable(RuntimeError):
    """At least one origin cannot safely be examined."""


class _ExclusiveServer(ThreadingHTTPServer):
    # Unix needs SO_REUSEADDR for the normal relay to rebind after TIME_WAIT.
    # On Windows it would weaken exclusive ownership of a live port.
    allow_reuse_address = os.name != 'nt'
    daemon_threads = True

    def __init__(self, *args, **kwargs):
        self._connections_lock = threading.Lock()
        self._connections = set()
        super().__init__(*args, **kwargs)

    def server_bind(self):
        # Windows SO_REUSEADDR can permit another process to bind the same port.
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

    def get_request(self):
        connection, address = super().get_request()
        with self._connections_lock:
            self._connections.add(connection)
        return connection, address

    def shutdown_request(self, connection):
        with self._connections_lock:
            self._connections.discard(connection)
        super().shutdown_request(connection)

    def close_connections(self):
        # Listening sockets can be closed while a WebView's speculative TCP
        # connection still waits in a handler. Wake those handlers before the
        # next broker takes the same port and issues a different token.
        with self._connections_lock:
            for connection in self._connections:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass


class PortalRecoveryBroker:
    """Reserve local origins and pass one bounded record to one destination."""

    def __init__(self, ports, destination, assets: Mapping[str, bytes], *, max_bytes=16 * 1024 * 1024, inventory_plan=None,
                 allow_same_origin_transfer=False, require_receipt=False, result_source=None, result_mode='transfer',
                 preserve_conflicts=False, allow_review=False, required_archives=(), allow_audio_review=False,
                 snapshot_audio_archives=False):
        ports = tuple(ports)
        if (not isinstance(required_archives,(list,tuple)) or len(required_archives)>1024
                or any(not isinstance(item,str) or not re.fullmatch(
                    r'(?:audio-)?[0-9a-f]{64}' if allow_audio_review else r'[0-9a-f]{64}',item) for item in required_archives)
                or len(set(required_archives))!=len(required_archives)):
            raise ValueError('Empreintes de copies invalides.')
        required_archives=tuple(sorted(required_archives))
        if not ports or len(set(ports)) != len(ports) or any(type(p) is not int or not 1024 <= p <= 65535 for p in ports):
            raise ValueError('Ports de récupération invalides.')
        if (destination not in ports or type(max_bytes) is not int or max_bytes < 1
                or type(allow_same_origin_transfer) is not bool or type(require_receipt) is not bool
                or result_mode not in ('transfer','snapshot','manifest')
                or type(preserve_conflicts) is not bool or type(allow_review) is not bool or type(allow_audio_review) is not bool
                or type(snapshot_audio_archives) is not bool or (snapshot_audio_archives and result_mode!='snapshot')
                or (preserve_conflicts and (result_mode!='transfer' or result_source is None))
                or (allow_review and (result_mode!='transfer' or result_source is None))
                or (allow_audio_review and not allow_review)
                or (required_archives and not allow_review)
                or (result_mode in ('snapshot','manifest') and result_source is None)
                or (result_mode=='manifest' and (not allow_same_origin_transfer or result_source!=destination))
                or (result_source is not None and (type(result_source) is not int or result_source not in ports
                    or not require_receipt or inventory_plan is not None))):
            raise ValueError('Destination de récupération invalide.')
        required = {'/recovery', '/recovery.js', '/portal_origin_recovery.js'}
        allowed = required | {'/recovery/scan','/recovery/transfer','/portal_origin_scan.js',
                              '/portal_origin_inventory.js', '/portal_origin_transfer.js',
                              '/portal_origin_sender.js', '/portal_origin_sender_result.js', '/portal_origin_receiver.js',
                              '/portal_origin_window.js', '/portal_origin_snapshot.js', '/portal_conflict_archive.js',
                              '/portal_conflict_review.js', '/portal_conflict_review.css'}
        if allow_audio_review or snapshot_audio_archives or result_mode=='manifest':
            allowed |= {'/portal_audio_conflict_archive.js','/portal_audio_conflict_review.js','/portal_origin_manifest.js'}
        elif isinstance(inventory_plan,OriginInventoryPlan) and inventory_plan.allows_audio_archives:
            allowed.add('/portal_audio_conflict_archive.js')
        if not required <= set(assets) <= allowed or any(not isinstance(value, bytes) for value in assets.values()):
            raise ValueError('Ressources de récupération invalides.')
        if inventory_plan is not None and (not isinstance(inventory_plan, OriginInventoryPlan) or inventory_plan.ports != ports):
            raise ValueError('Inventaire de récupération invalide.')
        self.token = secrets.token_hex(32)
        self.ports = ports
        self.destination = destination
        self.max_bytes = max_bytes
        self.allow_same_origin_transfer = allow_same_origin_transfer
        self.require_receipt = require_receipt
        self.result_source = result_source
        self.result_mode = result_mode
        self.preserve_conflicts = preserve_conflicts
        self.allow_review = allow_review
        self.allow_audio_review = allow_audio_review
        self.snapshot_audio_archives = snapshot_audio_archives
        self.required_archives = required_archives
        self.assets = dict(assets)
        self._inventory = inventory_plan
        self._pending = None
        self._last_receipt = None
        self._receipt_read = False
        self._conflicted = False
        self._acknowledged = 0
        self._preserved = 0
        self._archived = 0
        self._archive_ids = set()
        self._marked_archive = None
        self._required_verified = not required_archives
        self._reviewed = None
        self._restart_required = False
        self._lock = threading.Lock()
        self._completed = threading.Event()
        self._result_ready = threading.Event()
        self._staged = threading.Event()
        self._review = threading.Event()
        self._receiver_started = threading.Event()
        self._result = None
        self._servers = []
        self._threads = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = 'HTTP/1.1'

            def setup(self):
                super().setup()
                self.connection.settimeout(15)

            def handle(self):
                try:
                    super().handle()
                except (ConnectionError, TimeoutError):
                    pass  # A closing broker cancels idle connections.

            def log_message(self, *_args):
                pass  # Neither tokens nor payloads belong in HTTP logs.

            def response(self, status, content=b'', content_type='application/json', headers=()):
                try:
                    self.send_response(status)
                    self.send_header('Content-Type', content_type)
                    self.send_header('Content-Length', str(len(content)))
                    self.send_header('Cache-Control', 'no-store')
                    self.send_header('X-Content-Type-Options', 'nosniff')
                    self.send_header('Connection', 'close')
                    for key, value in headers:
                        self.send_header(key, value)
                    self.end_headers()
                    if content:
                        self.wfile.write(content)
                except (ConnectionError, TimeoutError):
                    pass  # Cancellation can close the window while a response is in flight.
                finally:
                    self.close_connection = True

            def valid_host(self):
                return self.headers.get_all('Host', []) == [f'127.0.0.1:{self.server.server_port}']

            def authorized(self):
                tokens = self.headers.get_all('X-Kiara-Recovery', [])
                token = tokens[0] if len(tokens) == 1 else ''
                return (self.valid_host()
                        and self.headers.get_all('Origin', []) == [f'http://127.0.0.1:{self.server.server_port}']
                        and token.isascii() and hmac.compare_digest(token, owner.token))

            def do_GET(self):
                if not self.valid_host() or self.path not in owner.assets:
                    return self.response(404)
                mime = ('text/html; charset=utf-8' if self.path in ('/recovery','/recovery/scan','/recovery/transfer')
                        else 'text/css; charset=utf-8' if self.path.endswith('.css') else 'text/javascript; charset=utf-8')
                csp = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
                # Only the interactive destination comparison may play its
                # locally created audio blobs. No network media source is added.
                if self.path == '/recovery/transfer' and self.server.server_port == owner.destination and owner.allow_review:
                    csp += '; media-src blob:'
                return self.response(200, owner.assets[self.path], mime, [('Content-Security-Policy', csp)])

            def do_POST(self):
                if not self.authorized():
                    return self.response(403)
                if self.path not in ('/recovery/stage', '/recovery/read', '/recovery/ack', '/recovery/receipt', '/recovery/inventory', '/recovery/status', '/recovery/complete', '/recovery/result', '/recovery/review', '/recovery/options', '/recovery/fail', '/recovery/archive', '/recovery/required-ok', '/recovery/archive-unavailable'):
                    return self.response(404)
                lengths = self.headers.get_all('Content-Length', [])
                if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or len(lengths[0]) > 10 or not lengths[0].isascii() or not lengths[0].isdigit():
                    return self.response(400)
                length = int(lengths[0])
                maximum = (owner.max_bytes if self.path == '/recovery/stage'
                           else 109 if self.path == '/recovery/ack'
                           else 32 if self.path == '/recovery/receipt'
                           else 97 if self.path == '/recovery/review'
                           else 168 if self.path == '/recovery/archive'
                           else (256*1024 if owner._inventory is not None and owner._inventory.requires_audio_ids else 1024)
                                if self.path == '/recovery/inventory'
                           else (256*1024 if owner.result_mode=='manifest' else 256) if self.path == '/recovery/result' else 0)
                if length > maximum:
                    return self.response(413)
                payload = self.rfile.read(length)
                if len(payload) != length:
                    return self.response(400)
                port = self.server.server_port
                if self.path == '/recovery/archive-unavailable':
                    if port != owner.destination:return self.response(403)
                    if not owner.allow_review or not owner.required_archives:return self.response(404)
                    with owner._lock:
                        if owner._result is not None or owner._required_verified:return self.response(409)
                        owner._result={'status':'archive-unavailable'}
                        owner._result_ready.set()
                    return self.response(200,b'{}')
                if self.path == '/recovery/fail':
                    if port != owner.destination:return self.response(403)
                    if owner.result_source is None or owner.result_mode!='transfer':return self.response(404)
                    with owner._lock:
                        if owner._result is not None:return self.response(409)
                        owner._result={'status':'unavailable'}
                        owner._result_ready.set()
                    return self.response(200,b'{}')
                if self.path == '/recovery/options':
                    if port != owner.destination:return self.response(403)
                    if owner.result_mode=='transfer' and owner.result_source is not None:
                        owner._receiver_started.set()
                    value = {'review':owner.allow_review,'preserve':owner.preserve_conflicts,'required':list(owner.required_archives)}
                    return self.response(200,json.dumps(value).encode('ascii'))
                if self.path == '/recovery/required-ok':
                    if port != owner.destination:return self.response(403)
                    if not owner.allow_review or not owner.required_archives:return self.response(404)
                    with owner._lock:
                        if owner._result is not None:return self.response(409)
                        owner._required_verified=True
                    return self.response(200,b'{}')
                if self.path == '/recovery/archive':
                    if port != owner.destination:return self.response(403)
                    if not owner.allow_review:return self.response(404)
                    with owner._lock:
                        pending=owner._pending
                        try:
                            text=payload.decode('ascii');parts=text.split(':')
                            valid=(owner._required_verified and pending is not None and len(parts)==3
                                   and hmac.compare_digest(parts[0],pending[1]) and hmac.compare_digest(parts[1],pending[2])
                                   and ((re.fullmatch(r'[0-9a-f]{64}',parts[2]) is not None and _local_record(pending[3]))
                                        or (owner.allow_audio_review and re.fullmatch(r'audio-[0-9a-f]{64}',parts[2]) is not None
                                            and _audio_conflict_record(pending[3])))
                                   and parts[2] not in owner._archive_ids)
                        except (UnicodeError,TypeError):valid=False
                        if valid:
                            marked=(pending[1],parts[2])
                            valid=owner._marked_archive is None or owner._marked_archive==marked
                            if valid:owner._marked_archive=marked
                    return self.response(200,b'{}') if valid else self.response(409)
                if self.path == '/recovery/review':
                    if not owner.allow_review:
                        return self.response(404)
                    if port != owner.destination:
                        return self.response(403)
                    with owner._lock:
                        pending = owner._pending
                        valid = owner._required_verified and pending is not None and hmac.compare_digest(payload, f'{pending[1]}:{pending[2]}'.encode('ascii'))
                        if valid:valid = (_local_record(pending[3])
                                          or (owner.allow_audio_review and _audio_conflict_record(pending[3])))
                        if valid:
                            owner._reviewed = pending[1]
                            owner._review.set()
                    return self.response(200,b'{}') if valid else self.response(409)
                if self.path == '/recovery/result':
                    if owner.result_source is None:
                        return self.response(404)
                    if port != owner.result_source:
                        return self.response(403)
                    def unique_result(pairs):
                        value = {}
                        for key, item in pairs:
                            if key in value:
                                raise ValueError('duplicate')
                            value[key] = item
                        return value
                    try:
                        result = json.loads(payload.decode('utf-8'), object_pairs_hook=unique_result)
                        if not isinstance(result, dict):
                            raise ValueError('invalid result')
                        if result.get('status') == 'manifest' and owner.result_mode=='manifest':
                            ids=result.get('audioArchiveIds')
                            if (set(result)!={'status','audioArchiveIds'} or not isinstance(ids,list) or len(ids)>3000
                                    or any(not isinstance(item,str) or not re.fullmatch(r'[0-9a-f]{64}',item) for item in ids)
                                    or len(set(ids))!=len(ids)):
                                raise ValueError('invalid manifest')
                            result['audioArchiveIds']=sorted(ids)
                        elif result.get('status') == 'snapshot' and owner.result_mode=='snapshot':
                            counts=('localEntries','audioChunks','audioArchives') if owner.snapshot_audio_archives else ('localEntries','audioChunks')
                            if (set(result) != {'status','digest',*counts}
                                    or any(type(result[name]) is not int or not 0 <= result[name] <= 9007199254740991
                                           for name in counts)
                                    or (owner.snapshot_audio_archives and result['audioArchives']>3000)
                                    or not isinstance(result['digest'],str) or len(result['digest'])!=64
                                    or any(char not in '0123456789abcdef' for char in result['digest'])):
                                raise ValueError('invalid snapshot')
                        elif result.get('status') == 'ok' and owner.result_mode=='transfer':
                            if (not {'status','copied','identical'} <= set(result) <= {'status','copied','identical','preserved','archived'}
                                    or any(type(result[name]) is not int or not 0 <= result[name] <= 9007199254740991
                                           for name in ('copied', 'identical'))
                                    or any(name in result and (type(result[name]) is not int or not 0 <= result[name] <= 9007199254740991)
                                           for name in ('preserved','archived'))):
                                raise ValueError('invalid counts')
                        elif result.get('status') not in (('conflict','unavailable','restart') if owner.result_mode=='transfer' else ('unavailable',)) or set(result) != {'status'}:
                            raise ValueError('invalid status')
                    except (UnicodeError, ValueError, RecursionError):
                        return self.response(400)
                    with owner._lock:
                        if owner._pending is not None or (owner._last_receipt is not None and not owner._receipt_read):
                            return self.response(409)
                        if owner._conflicted and result['status'] == 'ok':
                            return self.response(409)
                        if result['status'] == 'ok' and not owner._required_verified:
                            return self.response(409)
                        if result['status'] == 'restart' and not owner._restart_required:
                            return self.response(409)
                        if (result['status'] == 'ok'
                                and (result['copied'] + result['identical'] + result.get('preserved',0) + result.get('archived',0) > owner._acknowledged
                                     or result.get('preserved',0)!=owner._preserved or result.get('archived',0)!=owner._archived)):
                            return self.response(409)
                        if owner._result is not None and owner._result != result:
                            return self.response(409)
                        owner._result = result
                        owner._result_ready.set()
                    return self.response(200, b'{}')
                if self.path == '/recovery/receipt':
                    try:
                        transfer_id = payload.decode('ascii')
                        if len(transfer_id) != 32 or any(char not in '0123456789abcdef' for char in transfer_id):
                            raise ValueError('invalid id')
                    except (UnicodeError, ValueError):
                        return self.response(400)
                    with owner._lock:
                        last = owner._last_receipt
                        if last is None or last[1] != transfer_id:
                            return self.response(404)
                        if last[0] != port:
                            return self.response(403)
                        owner._receipt_read = True
                    result = {'id':last[1], 'sha256':last[2]}
                    if last[3] is not None:
                        result['status'] = last[3]
                    return self.response(200, json.dumps(result).encode('ascii'))
                if self.path == '/recovery/complete':
                    if owner._inventory is None:
                        return self.response(404)
                    result = owner._inventory.status()
                    if result['state'] != 'ready':
                        return self.response(409)
                    if port != result['port']:
                        return self.response(403)
                    with owner._lock:
                        if owner._pending is not None:
                            return self.response(409)
                        owner._completed.set()
                    return self.response(200, b'{}')
                if self.path in ('/recovery/inventory', '/recovery/status'):
                    if owner._inventory is None:
                        return self.response(404)
                    if self.path == '/recovery/status':
                        result = owner._inventory.status()
                    else:
                        def unique(pairs):
                            value = {}
                            for key, item in pairs:
                                if key in value:
                                    raise ValueError('duplicate')
                                value[key] = item
                            return value
                        try:
                            report = json.loads(payload.decode('utf-8'), object_pairs_hook=unique)
                            result = owner._inventory.submit(port, report)
                        except (UnicodeError, ValueError, InventoryPlanError):
                            return self.response(400)
                    return self.response(200, json.dumps(result).encode('ascii'))
                if self.path == '/recovery/stage':
                    if owner.result_mode in ('snapshot','manifest'):
                        return self.response(409)
                    if owner._inventory is not None and owner._inventory.status()['state'] != 'needsRecovery':
                        return self.response(409)
                    if owner.result_source is not None and port != owner.result_source:
                        return self.response(403)
                    if (port == owner.destination and not owner.allow_same_origin_transfer) or not payload:
                        return self.response(400)
                    digest = hashlib.sha256(payload).hexdigest()
                    with owner._lock:
                        if owner._result is not None:
                            return self.response(409)
                        if owner._pending is not None:
                            source, transfer_id, previous_digest, previous_payload = owner._pending
                            conflict = (source, previous_digest, previous_payload) != (port, digest, payload)
                        else:
                            if owner.require_receipt and owner._last_receipt is not None and not owner._receipt_read:
                                return self.response(409)
                            conflict = False
                            transfer_id = secrets.token_hex(16)
                            owner._pending = (port, transfer_id, digest, payload)
                            owner._reviewed = None
                            owner._marked_archive = None
                            owner._last_receipt = None
                            owner._receipt_read = False
                            owner._staged.set()
                    if conflict:
                        return self.response(409)
                    return self.response(200, json.dumps({'id': transfer_id, 'sha256': digest}).encode())
                if port != owner.destination:
                    return self.response(403)
                with owner._lock:
                    current = owner._pending
                    if not owner._required_verified:
                        return self.response(409)
                    if current is not None and self.path == '/recovery/ack':
                        receipt = f'{current[1]}:{current[2]}'.encode('ascii')
                        outcome = None
                        valid = hmac.compare_digest(payload, receipt)
                        if valid and owner.result_source is not None:
                            valid = False  # This protocol requires a verified outcome for every record.
                        if not valid:
                            for candidate in ('copied', 'identical', 'conflict', 'archived', 'restart', 'unavailable'):
                                if hmac.compare_digest(payload, receipt + b':' + candidate.encode('ascii')):
                                    valid = True
                                    outcome = candidate
                                    break
                        if valid and outcome in ('archived','restart','unavailable'):
                            valid = owner.allow_review and (_local_record(current[3])
                                    or (owner.allow_audio_review and _audio_conflict_record(current[3])))
                            if outcome == 'restart':valid = valid and owner._reviewed == current[1]
                            if outcome == 'archived':valid = valid and owner._marked_archive is not None and owner._marked_archive[0]==current[1]
                        if valid:
                            # Audio chunks are immutable: divergent bytes must
                            # remain a conflict even for an unchanged source.
                            if (outcome == 'conflict' and owner.preserve_conflicts
                                    and current[3].startswith(b'{"type":"local",')):
                                outcome='preserved'
                                owner._preserved += 1
                            owner._pending = None
                            owner._staged.clear()
                            owner._review.clear()
                            owner._last_receipt = (current[0], current[1], current[2], outcome)
                            owner._receipt_read = False
                            if outcome in ('conflict','unavailable'):
                                owner._conflicted = True
                            elif outcome == 'restart':
                                owner._conflicted = True
                                owner._restart_required = True
                            elif outcome == 'archived':
                                owner._archived += 1
                                owner._archive_ids.add(owner._marked_archive[1])
                                owner._acknowledged += 1
                            elif outcome in ('copied', 'identical', 'preserved'):
                                owner._acknowledged += 1
                            acknowledged = True
                        else:
                            acknowledged = False
                if current is None:
                    return self.response(404)
                source, transfer_id, digest, record = current
                if self.path == '/recovery/read':
                    if payload:
                        return self.response(400)
                    return self.response(200, record, 'application/octet-stream',
                                         [('X-Kiara-Transfer-ID', transfer_id), ('X-Kiara-Record-SHA256', digest),
                                          ('X-Kiara-Source-Port', str(source))])
                return self.response(200, b'{}') if acknowledged else self.response(409)

        try:
            for port in ports:
                self._servers.append(_ExclusiveServer(('127.0.0.1', port), Handler))
        except OSError as error:
            for server in self._servers:
                server.server_close()
            self._servers.clear()
            raise RecoveryUnavailable('Un port de récupération est occupé ou inaccessible.') from error

    def start(self):
        if self._threads or not self._servers:
            raise RuntimeError('La récupération a déjà démarré ou est terminée.')
        try:
            for server in self._servers:
                # Several short-lived brokers may run during recovery.  Bound
                # shutdown latency without changing request or transfer rules.
                thread = threading.Thread(target=server.serve_forever,
                                          kwargs={'poll_interval': 0.05}, daemon=True)
                thread.start()
                self._threads.append(thread)
        except BaseException:
            self.close()
            raise
        return self

    def wait_complete(self, timeout=None):
        """A verified inventory may finish only on its selected origin."""
        if not self._completed.wait(timeout):
            return None
        return self._inventory.status()['port']

    def wait_result(self, timeout=None):
        """Return counts or a failure without reading any transferred records."""
        if not self._result_ready.wait(timeout):
            return None
        with self._lock:
            return None if self._result is None else dict(self._result)

    def wait_staged(self, timeout=None):
        """Signal that a source is ready, without exposing the staged record."""
        return self._staged.wait(timeout)

    def receiver_started(self):
        """A destination authenticated and requested the transfer options."""
        return self._receiver_started.is_set()

    def take_review_request(self):
        """Take an authenticated request to show the destination window."""
        with self._lock:
            if not self._review.is_set():return False
            self._review.clear()
            return self._pending is not None

    def verified_archive_ids(self):
        """Return only content fingerprints for completed archived receipts."""
        with self._lock:
            if not self._required_verified or self._archived!=len(self._archive_ids):
                raise RecoveryUnavailable('Les copies locales ne sont pas vérifiées.')
            return tuple(sorted(self._archive_ids))

    def close(self):
        for server in self._servers[:len(self._threads)]:
            server.shutdown()
        for server in self._servers:
            server.close_connections()
            server.server_close()
        for thread in self._threads:
            thread.join(timeout=5)
        self._threads.clear()
        self._servers.clear()
        with self._lock:
            self._pending = None
            self._last_receipt = None
            self._receipt_read = False
            self._result = None

    def __enter__(self):
        return self.start()

    def __exit__(self, *_args):
        self.close()
