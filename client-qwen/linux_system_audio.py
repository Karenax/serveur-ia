"""Temporary PulseAudio/PipeWire monitor source owned by the local relay.

The worker never records audio. It exposes the current default output monitor
as a uniquely named input and removes only its own module when its parent closes
the control pipe. The webview still requests and owns the media stream.
"""
from __future__ import annotations

import json
import queue
import re
import signal
import subprocess
import sys
import threading
from uuid import UUID

_NAME = re.compile(r'^[A-Za-z0-9_.-]+$')
_TIMEOUT = 5


def _pactl(*args):
    try:
        result = subprocess.run(['pactl', *args], check=True, capture_output=True,
                                text=True, timeout=_TIMEOUT)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError('La boucle audio Linux est indisponible.') from exc
    return result.stdout.strip()


def _unload_owned(module_id, source_name):
    for line in _pactl('list', 'short', 'modules').splitlines():
        fields = line.split('\t')
        if fields[0] != module_id:
            continue
        if (len(fields) < 3 or fields[1] != 'module-remap-source'
                or f'source_name={source_name}' not in fields[2].split()):
            raise RuntimeError('La boucle audio a changé ; fermeture non confirmée.')
        _pactl('unload-module', module_id)
        return
    # The module is already gone; never unload a different module.


def _worker(lease_id):
    module_id = None
    source_name = None
    closed = False
    def stop_signal(_signum, _frame):
        raise SystemExit(1)
    signal.signal(signal.SIGTERM, stop_signal)
    try:
        sink = _pactl('get-default-sink')
        if not _NAME.fullmatch(sink):
            raise RuntimeError('Sortie audio par défaut invalide.')
        monitor = sink + '.monitor'
        sources = _pactl('list', 'short', 'sources').splitlines()
        if not any(len(fields := line.split('\t')) > 1 and fields[1] == monitor for line in sources):
            raise RuntimeError('La sortie audio ne propose pas de boucle de capture.')
        suffix = UUID(lease_id).hex
        source_name = 'kiara_output_' + suffix
        label = 'Kiara_sortie_' + suffix
        module_id = _pactl('load-module', 'module-remap-source', f'master={monitor}',
                           f'source_name={source_name}', f'source_properties=device.description={label}')
        if not module_id.isascii() or not module_id.isdecimal():
            raise RuntimeError('Identification de la boucle audio impossible.')
        print(json.dumps({'label': label}), flush=True)
        # EOF is also delivered if the relay terminates unexpectedly.
        sys.stdin.readline()
        closed = True
    except (ValueError, RuntimeError) as exc:
        print(json.dumps({'error': str(exc)}, ensure_ascii=False), flush=True)
    finally:
        if module_id and module_id.isascii() and module_id.isdecimal():
            try:
                _unload_owned(module_id, source_name)
            except RuntimeError:
                closed = False
    return 0 if closed else 1


class LinuxSystemAudio:
    """One owned source at a time, with idempotent start and explicit stop."""
    def __init__(self):
        self._lock = threading.RLock()
        self._active = None
        self._used = set()

    @staticmethod
    def _valid(lease_id):
        try:
            return isinstance(lease_id, str) and str(UUID(lease_id)) == lease_id
        except (TypeError, ValueError, AttributeError):
            return False

    def start(self, lease_id):
        if not self._valid(lease_id):
            raise ValueError('Identifiant de boucle audio invalide.')
        with self._lock:
            if self._active:
                if self._active['id'] == lease_id and self._active['process'].poll() is None:
                    return {'lease_id': lease_id, 'label': self._active['label']}
                raise ValueError('Une boucle audio reste à fermer.')
            if lease_id in self._used:
                raise ValueError('Cette boucle audio a déjà été fermée.')
            # A stop arriving before a delayed start must make that start fail.
            self._used.add(lease_id)
            process = subprocess.Popen([sys.executable, '-u', __file__, '--worker', lease_id],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                       stderr=subprocess.DEVNULL, text=True, bufsize=1, close_fds=True)
            output = queue.Queue(maxsize=1)
            threading.Thread(target=lambda: output.put(process.stdout.readline()), daemon=True).start()
            try:
                line = output.get(timeout=3 * _TIMEOUT + 5)
                result = json.loads(line)
                expected = 'Kiara_sortie_' + UUID(lease_id).hex
                if not isinstance(result, dict) or result.get('label') != expected or process.poll() is not None:
                    raise ValueError(result.get('error', 'Boucle audio indisponible.') if isinstance(result, dict) else 'Boucle audio indisponible.')
            except (queue.Empty, ValueError, TypeError):
                process.stdin.close()
                try:
                    process.wait(timeout=_TIMEOUT + 2)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try: process.wait(timeout=_TIMEOUT + 2)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()
                raise ValueError('Impossible de préparer la boucle audio Linux.') from None
            self._active = {'id': lease_id, 'label': expected, 'process': process}
            return {'lease_id': lease_id, 'label': expected}

    def stop(self, lease_id):
        if not self._valid(lease_id):
            raise ValueError('Identifiant de boucle audio invalide.')
        with self._lock:
            active = self._active
            if active is None or active['id'] != lease_id:
                self._used.add(lease_id)
                return {'closed': True}
            process = active['process']
            if process.poll() is None:
                process.stdin.close()
            try:
                code = process.wait(timeout=_TIMEOUT + 2)
            except subprocess.TimeoutExpired:
                raise ValueError('Fermeture de la boucle audio non confirmée.') from None
            if code:
                raise ValueError('Fermeture de la boucle audio non confirmée.')
            self._active = None
            return {'closed': True}

    def close(self):
        with self._lock:
            if self._active:
                self.stop(self._active['id'])


if __name__ == '__main__':
    if len(sys.argv) != 3 or sys.argv[1] != '--worker' or not LinuxSystemAudio._valid(sys.argv[2]):
        raise SystemExit(2)
    raise SystemExit(_worker(sys.argv[2]))
