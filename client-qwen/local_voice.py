"""Whisper Small dictation on this PC; audio never enters the remote transport."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import queue
import secrets
import shutil
import threading
import time
import urllib.request

ACTIVE = {'installing', 'verifying', 'loading', 'listening', 'finishing', 'cancelling'}

class HTTPSRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not newurl.startswith('https://'):
            raise ValueError('Redirection non sécurisée.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)

class NativeEngine:
    def __init__(self, binary_dir: Path, model: Path, threads=4):
        self.directory = os.add_dll_directory(str(binary_dir))
        self.dll = ctypes.CDLL(str(binary_dir / 'fredvoice.dll'))
        self.dll.fred_voice_create.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_int]
        self.dll.fred_voice_create.restype = ctypes.c_void_p
        for name in ('stop', 'cancel', 'destroy'):
            fn = getattr(self.dll, 'fred_voice_' + name)
            fn.argtypes = [ctypes.c_void_p]; fn.restype = None
        self.dll.fred_voice_feed.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_int16), ctypes.c_int]
        self.dll.fred_voice_feed.restype = None
        self.dll.fred_voice_status.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int]
        self.dll.fred_voice_status.restype = ctypes.c_int
        self.handle = self.dll.fred_voice_create(str(model).encode('utf-8'), str(binary_dir).encode('utf-8'), threads)
        if not self.handle:
            raise OSError('Le moteur de dictée ne peut pas démarrer.')
    def status(self):
        output = ctypes.create_string_buffer(131072)
        if self.dll.fred_voice_status(self.handle, output, len(output)) <= 0:
            raise OSError('État du moteur vocal invalide.')
        return json.loads(output.value.decode('utf-8'))
    def feed(self, pcm: bytes):
        if not pcm or len(pcm) > 32000 or len(pcm) % 2:
            raise ValueError('Trame audio invalide.')
        values = (ctypes.c_int16 * (len(pcm) // 2)).from_buffer_copy(pcm)
        self.dll.fred_voice_feed(self.handle, values, len(values))
    def stop(self): self.dll.fred_voice_stop(self.handle)
    def cancel(self): self.dll.fred_voice_cancel(self.handle)
    def close(self):
        if self.handle:
            self.dll.fred_voice_destroy(self.handle); self.handle = None
        self.directory.close()

class WaveFormat(ctypes.Structure):
    _fields_ = [('tag', wintypes.WORD), ('channels', wintypes.WORD), ('rate', wintypes.DWORD),
                ('average', wintypes.DWORD), ('align', wintypes.WORD), ('bits', wintypes.WORD), ('extra', wintypes.WORD)]
class WaveHeader(ctypes.Structure):
    _fields_ = [('data', ctypes.c_void_p), ('length', wintypes.DWORD), ('recorded', wintypes.DWORD),
                ('user', ctypes.c_size_t), ('flags', wintypes.DWORD), ('loops', wintypes.DWORD),
                ('next', ctypes.c_void_p), ('reserved', ctypes.c_size_t)]

class Microphone:
    """WinMM capture with bounded buffers, outside the browser permission model."""
    def __init__(self):
        self.dll = ctypes.WinDLL('winmm')
        self.handle = wintypes.HANDLE(); self.items = queue.Queue(maxsize=8); self.overflow = False
        callback_type = ctypes.WINFUNCTYPE(None, wintypes.HANDLE, wintypes.UINT, ctypes.c_size_t, ctypes.c_size_t, ctypes.c_size_t)
        def returned(handle, message, instance, header, unused):
            if message == 0x3c0:
                try: self.items.put_nowait(header)
                except queue.Full: self.overflow = True
        self.callback = callback_type(returned)
        self.dll.waveInOpen.argtypes = [ctypes.POINTER(wintypes.HANDLE), wintypes.UINT, ctypes.POINTER(WaveFormat), ctypes.c_size_t, ctypes.c_size_t, wintypes.DWORD]
        for name in ('waveInPrepareHeader', 'waveInUnprepareHeader', 'waveInAddBuffer'):
            getattr(self.dll, name).argtypes = [wintypes.HANDLE, ctypes.POINTER(WaveHeader), wintypes.UINT]
        for name in ('waveInStart', 'waveInStop', 'waveInReset', 'waveInClose'):
            getattr(self.dll, name).argtypes = [wintypes.HANDLE]
        spec = WaveFormat(1, 1, 16000, 32000, 2, 16, 0)
        result = self.dll.waveInOpen(ctypes.byref(self.handle), 0xffffffff, ctypes.byref(spec), ctypes.cast(self.callback, ctypes.c_void_p).value, 0, 0x30000)
        if result:
            raise OSError('Microphone indisponible. Vérifiez le micro et son autorisation dans Windows.')
        self.buffers = [ctypes.create_string_buffer(3200) for _ in range(4)]
        self.headers = [WaveHeader(ctypes.cast(data, ctypes.c_void_p).value, len(data), 0, 0, 0, 0, None, 0) for data in self.buffers]
        try:
            for header in self.headers:
                if self.dll.waveInPrepareHeader(self.handle, ctypes.byref(header), ctypes.sizeof(header)) or self.dll.waveInAddBuffer(self.handle, ctypes.byref(header), ctypes.sizeof(header)):
                    raise OSError('Le microphone ne peut pas enregistrer.')
            if self.dll.waveInStart(self.handle): raise OSError('Le microphone ne peut pas démarrer.')
        except Exception:
            self.close(); raise
    def read(self):
        if self.overflow: raise OSError('Capture audio interrompue. Réessayez la dictée.')
        try: pointer = self.items.get(timeout=.1)
        except queue.Empty: return b''
        header = ctypes.cast(pointer, ctypes.POINTER(WaveHeader)).contents
        data = ctypes.string_at(header.data, header.recorded)
        if self.dll.waveInAddBuffer(self.handle, ctypes.byref(header), ctypes.sizeof(header)):
            raise OSError('Capture audio interrompue. Réessayez la dictée.')
        return data
    def close(self):
        if self.handle:
            self.dll.waveInStop(self.handle); self.dll.waveInReset(self.handle)
            for header in getattr(self, 'headers', []):
                if header.flags & 2:
                    self.dll.waveInUnprepareHeader(self.handle, ctypes.byref(header), ctypes.sizeof(header))
            self.dll.waveInClose(self.handle); self.handle = wintypes.HANDLE()

class VoiceService:
    def __init__(self, resources: Path, cache: Path | None = None, *, capture_factory=Microphone):
        self.resources = resources
        self.spec = json.loads((resources / 'model.json').read_text(encoding='utf-8'))
        self.cache = cache or Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'QwenClient/voice'
        self.model = self.cache / 'ggml-small.bin'
        self.lock = threading.RLock(); self.cancelled = threading.Event()
        self.engine = None; self.thread = None; self.capture_factory = capture_factory; self.closed = False
        self.verified = None
        self.value = {'phase': 'idle', 'text': '', 'message': 'Dictée locale · français', 'session': '', 'seconds': 0}
    def installed(self):
        try: return self.model.stat().st_size == self.spec['bytes']
        except OSError: return False
    def status(self):
        with self.lock:
            if self.engine and self.value['phase'] != 'error':
                self.value = {**self.value, **self.engine.status()}
            return {**self.value, 'installed': self.installed(), 'model': 'Whisper Small', 'model_bytes': self.spec['bytes'], 'local': True}
    def action(self, values):
        if not isinstance(values, dict) or set(values) - {'action', 'session'}:
            raise ValueError('Commande vocale invalide.')
        command = values.get('action')
        with self.lock:
            if self.closed: raise ValueError('Client en cours de fermeture.')
            state = self.status()
            if command in ('stop', 'cancel'):
                if not isinstance(values.get('session'), str) or values['session'] != self.value['session'] or not values['session']:
                    raise ValueError('Cette dictée n’est plus active.')
                if self.engine:
                    (self.engine.stop if command == 'stop' else self.engine.cancel)()
                elif state['phase'] in ACTIVE:
                    self.cancelled.set()
                    self.value['phase'] = 'cancelling'
                elif command == 'cancel':
                    self.value.update(phase='cancelled', text='', message='Dictée annulée.')
                return self.status()
            if command not in ('install', 'start', 'remove'):
                raise ValueError('Commande vocale non disponible.')
            if state['phase'] in ACTIVE or (self.thread and self.thread.is_alive()):
                raise ValueError('Une opération vocale est déjà en cours.')
            if command == 'remove':
                self.model.unlink(missing_ok=True); self.model.with_suffix('.part').unlink(missing_ok=True); self.verified = None
                self.value.update(phase='idle', text='', message='Dictée désinstallée.'); return self.status()
            if command == 'start' and not self.installed():
                raise ValueError('Installez la dictée française avant d’ouvrir le microphone.')
            self.cancelled = threading.Event()
            self.value = {'phase': 'installing' if command == 'install' else 'loading', 'text': '', 'message': 'Installation de la dictée…' if command == 'install' else 'Chargement de la dictée…', 'session': secrets.token_hex(16), 'seconds': 0}
            self.thread = threading.Thread(target=self._install if command == 'install' else self._record, daemon=True)
            self.thread.start(); return self.status()
    def _verify(self):
        stat = self.model.stat(); signature = (stat.st_size, stat.st_mtime_ns)
        if self.verified == signature: return
        with self.model.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if stat.st_size != self.spec['bytes'] or digest != self.spec['sha256']:
            raise ValueError('Fichier de dictée invalide. Réinstallez la dictée française.')
        self.verified = signature
    def _install(self):
        try:
            from file_lock import locked
            self.cache.mkdir(parents=True, exist_ok=True)
            with locked(self.model):
                if self.cancelled.is_set(): return
                if self.installed():
                    try: self._verify(); return
                    except ValueError: pass
                if shutil.disk_usage(self.cache).free < self.spec['bytes'] + 64 * 1024 * 1024:
                    raise ValueError('Il faut environ 550 Mo d’espace libre pour installer la dictée.')
                partial = self.model.with_suffix('.part')
                offset = partial.stat().st_size if partial.exists() else 0
                if offset >= self.spec['bytes']: offset = 0
                request = urllib.request.Request(self.spec['url'], headers={'User-Agent': 'Kiara-local-dictation/1.0', **({'Range': f'bytes={offset}-'} if offset else {})})
                opener = urllib.request.build_opener(HTTPSRedirect())
                with opener.open(request, timeout=20) as response:
                    if not response.url.startswith('https://'): raise ValueError('Connexion non sécurisée.')
                    if response.status == 206:
                        if not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                            raise ValueError('Reprise du téléchargement invalide.')
                    elif response.status == 200: offset = 0
                    else: raise ValueError('Téléchargement indisponible.')
                    with partial.open('ab' if offset else 'wb') as output:
                        size = offset
                        while not self.cancelled.is_set():
                            data = response.read(256 * 1024)
                            if not data: break
                            size += len(data)
                            if size > self.spec['bytes']: raise ValueError('Fichier de dictée trop volumineux.')
                            output.write(data)
                            with self.lock: self.value['downloaded_bytes'] = size
                if self.cancelled.is_set(): return
                with self.lock: self.value.update(phase='verifying', message='Vérification de la dictée…')
                with partial.open('rb') as stream: digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                if size != self.spec['bytes'] or digest != self.spec['sha256']:
                    partial.unlink(missing_ok=True); raise ValueError('Téléchargement incomplet ou invalide. Réessayez.')
                if self.cancelled.is_set(): return
                partial.replace(self.model); self._verify()
        except (OSError, ValueError) as error:
            with self.lock: self.value.update(phase='error', message=str(error) if isinstance(error, ValueError) else 'Installation impossible. Vérifiez Internet et l’espace disponible.')
        finally:
            with self.lock:
                if self.value['phase'] != 'error': self.value.update(phase='cancelled' if self.cancelled.is_set() else 'idle', message='Installation annulée.' if self.cancelled.is_set() else 'Dictée installée. Vous pouvez ouvrir le microphone.')
    def _record(self):
        microphone = None; engine = None
        try:
            self._verify()
            with self.lock:
                if self.cancelled.is_set(): return
                engine = NativeEngine(self.resources, self.model); self.engine = engine
            while True:
                with self.lock:
                    state = engine.status(); self.value.update(state)
                if state['phase'] == 'listening':
                    if microphone is None: microphone = self.capture_factory()
                    audio = microphone.read()
                    if audio:
                        with self.lock: engine.feed(audio)
                else:
                    if microphone:
                        microphone.close(); microphone = None
                    if state['phase'] in ('ready', 'cancelled', 'error'): break
                    time.sleep(.05)
        except (OSError, ValueError) as error:
            with self.lock:
                if engine: engine.cancel()
                self.value.update(phase='error', message=str(error))
        finally:
            if microphone: microphone.close()
            with self.lock: self.engine = None
            if engine: engine.close()
            with self.lock:
                if self.cancelled.is_set() and self.value['phase'] != 'error': self.value.update(phase='cancelled', text='', message='Dictée annulée.')
    def close(self):
        with self.lock:
            self.closed = True; self.cancelled.set()
            if self.engine: self.engine.cancel()
        if self.thread: self.thread.join(timeout=5)
