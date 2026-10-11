"""Private, offline EG2 CPU worker. Only Fred's parent process can call it."""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def serve(model_path, token, port, threads, parent, parent_created):
    os.environ['CUDA_VISIBLE_DEVICES'] = ''
    os.environ['HF_HUB_OFFLINE'] = '1'
    os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
    os.environ['TOKENIZERS_PARALLELISM'] = 'false'
    import psutil
    def watch_parent():
        while True:
            time.sleep(2)
            try:
                process=psutil.Process(parent)
                if abs(process.create_time()-parent_created)>.01:os._exit(0)
                if psutil.Process().memory_info().rss>4*1024**3:os._exit(2)
            except psutil.Error:os._exit(0)
    threading.Thread(target=watch_parent,daemon=True).start()
    import torch
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    model = SentenceTransformer(str(model_path), device='cpu', local_files_only=True,
        trust_remote_code=False, config_kwargs={'vision_config': None, 'audio_config': None},
        model_kwargs={'torch_dtype': torch.float32, 'attn_implementation': 'eager'})
    model.max_seq_length = 2048
    config_hash = hashlib.sha256((Path(model_path) / 'config.json').read_bytes()).hexdigest()
    guard = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass

        def reply(self, code, value):
            raw = json.dumps(value, allow_nan=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(raw)

        def authorized(self):
            return hmac.compare_digest(self.headers.get('Authorization', ''), 'Bearer ' + token)

        def do_GET(self):
            if not self.authorized(): return self.reply(403, {'error': 'Accès privé.'})
            if self.path != '/health': return self.reply(404, {'error': 'Route inconnue.'})
            self.reply(200, {'service': 'fred-eg2', 'model': 'google/embeddinggemma-2',
                'device': 'cpu', 'precision': 'float32', 'dimensions': 768, 'config_hash': config_hash,
                'parameters': sum(p.numel() for p in model.parameters()), 'threads': threads,'pid':os.getpid()})

        def do_POST(self):
            if not self.authorized(): return self.reply(403, {'error': 'Accès privé.'})
            if self.path != '/embeddings': return self.reply(404, {'error': 'Route inconnue.'})
            if not guard.acquire(blocking=False): return self.reply(429, {'error': 'Moteur occupé.'})
            try:
                length = int(self.headers.get('Content-Length', '0'))
                if not 0 < length <= 65536: raise ValueError('Requête trop volumineuse.')
                self.connection.settimeout(15)
                data = json.loads(self.rfile.read(length))
                texts = data.get('texts'); mode = data.get('mode')
                if mode not in ('query', 'document') or not isinstance(texts, list) or not 1 <= len(texts) <= 8:
                    raise ValueError('Lot invalide.')
                if any(not isinstance(s, str) or not s.strip() or len(s) > 4500 for s in texts):
                    raise ValueError('Texte invalide.')
                start = time.monotonic()
                # Titles are formatted by Fred; suppress the model's default prefix.
                prompt = 'task: search result | query: ' if mode == 'query' else ''
                with torch.inference_mode():
                    vectors = model.encode(texts, prompt=prompt, batch_size=4,
                        normalize_embeddings=True, show_progress_bar=False).tolist()
                if not all(len(v) == 768 for v in vectors): raise ValueError('Dimensions invalides.')
                self.reply(200, {'vectors': vectors, 'seconds': time.monotonic() - start})
            except (ValueError, TypeError, KeyError): self.reply(400, {'error': 'Requête EG2 invalide.'})
            except Exception: self.reply(503, {'error': 'Échec du calcul EG2.'})
            finally: guard.release()

    server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    server.daemon_threads = True
    server.serve_forever()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--model', required=True)
    parser.add_argument('--port', type=int, required=True)
    parser.add_argument('--threads', type=int, default=2)
    parser.add_argument('--parent',type=int,required=True)
    parser.add_argument('--parent-created',type=float,required=True)
    args = parser.parse_args()
    token = os.environ.pop('FRED_EG2_TOKEN')
    serve(Path(args.model), token, args.port, args.threads,args.parent,args.parent_created)
