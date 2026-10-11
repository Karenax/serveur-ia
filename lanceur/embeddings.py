"""Independent EG2 lifecycle; no torch or transformers inside the Qwen backend."""
import atexit
from collections import OrderedDict
import http.client
import json
import math
import os
from pathlib import Path
import secrets
import socket
import subprocess
import threading
import time
from core import ROOT, HIDDEN

MODEL = ROOT / 'toolchain' / 'eg2-model'
PYTHON = ROOT / 'toolchain' / 'eg2-python' / 'Scripts' / 'python.exe'
DIMENSIONS = 768


def validate_vectors(vectors, count):
    if not isinstance(vectors, list) or len(vectors) != count: raise ValueError('Réponse EG2 invalide.')
    for vector in vectors:
        if not isinstance(vector, list) or len(vector) != DIMENSIONS:
            raise ValueError('Dimensions EG2 invalides.')
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in vector):
            raise ValueError('Vecteur EG2 non fini.')
        norm = math.sqrt(sum(v * v for v in vector))
        if not .98 <= norm <= 1.02: raise ValueError('Vecteur EG2 non normalisé.')
    return vectors


class EmbeddingService:
    def __init__(self, workspace):
        self.workspace = workspace
        self.lock = threading.RLock()
        self.slot = threading.Lock()
        self.query_waiting=threading.Event();self.query_failures=OrderedDict()
        self.process = None; self.port = None; self.token = None
        self.state = 'arrete'; self.error = ''; self.started = 0
        self.ready = {}; self.query_cache = OrderedDict()
        self.last_seconds = None; self.failures = 0; self.retry_at = 0
        atexit.register(self.stop)

    def enabled(self):
        with self.workspace.db() as db:
            row = db.execute("SELECT value FROM settings WHERE key='eg2_enabled'").fetchone()
        return bool(row and row[0] == 'true')

    def configure(self, enabled):
        if type(enabled) is not bool: raise ValueError('Activation EG2 invalide.')
        with self.workspace.db() as db:
            db.execute("INSERT OR REPLACE INTO settings VALUES('eg2_enabled',?)", ('true' if enabled else 'false',))
        if enabled:
            self.failures = 0; self.retry_at = 0; self.start()
        else: self.stop()
        return self.status()

    def call(self, path, body=None, timeout=2):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=timeout)
        try:
            headers = {'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'}
            connection.request('POST' if body is not None else 'GET', path,
                json.dumps(body, ensure_ascii=False).encode() if body is not None else None, headers)
            response = connection.getresponse(); raw = response.read(512 * 1024 + 1)
            if len(raw) > 512 * 1024 or response.status != 200: raise ValueError('Moteur EG2 indisponible ou occupé.')
            return json.loads(raw)
        finally: connection.close()

    def start(self):
        with self.lock:
            if self.process and self.process.poll() is None: return
            if not PYTHON.is_file() or not (MODEL / 'model.safetensors').is_file():
                self.state = 'non_installe'; self.error = 'Installer le moteur et les poids avec Install-EG2.ps1.'; return
            with socket.socket() as listener:
                listener.bind(('127.0.0.1', 0)); self.port = listener.getsockname()[1]
            self.token = secrets.token_urlsafe(32)
            env = dict(os.environ, FRED_EG2_TOKEN=self.token, CUDA_VISIBLE_DEVICES='',
                HF_HUB_DISABLE_TELEMETRY='1', OMP_NUM_THREADS='2', MKL_NUM_THREADS='2')
            import psutil
            self.process = subprocess.Popen([str(PYTHON), str(Path(__file__).with_name('embedding_worker.py')),
                '--model', str(MODEL), '--port', str(self.port), '--threads', '2',
                '--parent',str(os.getpid()),'--parent-created',str(psutil.Process().create_time())],
                stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                cwd=ROOT, env=env, creationflags=HIDDEN)
            self.started = time.monotonic(); self.state = 'chargement'; self.error = ''; self.ready = {}

    def tick(self):
        if self.workspace.maintenance: return
        if not self.enabled():
            if self.process: self.stop()
            return
        with self.lock:
            if self.process and self.process.poll() is not None:
                self.process = None; self.state = 'erreur'; self.error = 'Le moteur EG2 s’est arrêté.'
                self.failures += 1; self.retry_at = time.monotonic() + 30
            if self.process is None:
                if self.failures >= 3 or time.monotonic() < self.retry_at: return
                self.start()
            if self.process is None: return
            try:
                health = self.call('/health', timeout=.5)
                if health.get('service') != 'fred-eg2' or health.get('dimensions') != DIMENSIONS:
                    raise ValueError('Moteur incompatible.')
                self.ready = health; self.state = 'pret'; self.error = ''
            except (OSError, ValueError, http.client.HTTPException):
                if time.monotonic() - self.started > 180:
                    self.stop(); self.state = 'erreur'; self.error = 'Chargement EG2 trop long.'
                    self.failures += 1; self.retry_at = time.monotonic() + 30

    def stop(self):
        with self.lock:
            process = self.process; self.process = None
            if process and process.poll() is None:
                import psutil
                try:
                    parent=psutil.Process(process.pid)
                    victims=parent.children(recursive=True)+[parent]
                    for victim in reversed(victims):
                        try:victim.terminate()
                        except psutil.NoSuchProcess:pass
                    _,alive=psutil.wait_procs(victims,timeout=3)
                    for victim in alive:
                        try:victim.kill()
                        except psutil.NoSuchProcess:pass
                    process.wait(timeout=3)
                except (psutil.NoSuchProcess,subprocess.TimeoutExpired):pass
            self.ready = {}; self.query_cache.clear();self.query_failures.clear();self.query_waiting.clear(); self.state = 'arrete'

    def encode(self, texts, mode='document', timeout=8):
        if self.state != 'pret' or not self.enabled() or self.workspace.maintenance:
            raise ValueError('EG2 indisponible.')
        key = texts[0] if mode == 'query' and len(texts) == 1 else None
        if key is not None:
            with self.lock:
                if key in self.query_cache: return [list(self.query_cache[key])]
                if self.query_failures.get(key,0)>time.monotonic():raise ValueError('EG2 temporairement indisponible pour cette question.')
            self.query_waiting.set()
        elif self.query_waiting.is_set():raise ValueError('Demande interactive prioritaire.')
        if not self.slot.acquire(timeout=2 if key is not None else .15):
            if key is not None:self.query_waiting.clear()
            raise ValueError('EG2 occupé.')
        try:
            result = self.call('/embeddings', {'texts': texts, 'mode': mode}, timeout)
            vectors = validate_vectors(result.get('vectors'), len(texts))
            self.last_seconds = result.get('seconds')
            if key is not None:
                with self.lock:
                    self.query_cache[key] = tuple(vectors[0])
                    while len(self.query_cache) > 64: self.query_cache.popitem(last=False)
            return vectors
        except (OSError,ValueError,http.client.HTTPException):
            if key is not None:
                with self.lock:
                    self.query_failures[key]=time.monotonic()+30
                    while len(self.query_failures)>64:self.query_failures.popitem(last=False)
            raise
        finally:
            self.slot.release()
            if key is not None:self.query_waiting.clear()

    def status(self):
        enabled=self.enabled()
        with self.lock:
            return {'model': 'EmbeddingGemma 2', 'engine': 'Sentence Transformers / PyTorch',
                'enabled': enabled, 'status': self.state, 'error': self.error,
                'device': 'cpu', 'precision': 'float32', 'threads': 2, 'dimensions': DIMENSIONS,
                'pid': (self.ready.get('pid') or self.process.pid) if self.process and self.process.poll() is None else None,
                'last_seconds': self.last_seconds, 'parameters': self.ready.get('parameters')}
