"""Download pinned Bolt artifacts and a CPU-only llama.cpp runtime; verify hashes."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time
import urllib.request
import zipfile

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
MODELS = Path('D:/modèle')
RUNTIME = ROOT / 'toolchain/llama-bolt-b11854-cpu'
HEADERS = {'User-Agent': 'Kiara-local-benchmark/1.0'}


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=60) as response:
        return json.load(response)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(item):
    path = Path(item['path'])
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.stat().st_size == item['bytes'] and digest(path) == item['sha256']:
            print(json.dumps({'verified_existing': path.name}), flush=True)
            return item
        raise ValueError(f'Existing file differs; left untouched: {path}')
    partial = path.with_suffix(path.suffix + '.part')
    for attempt in range(5):
        offset = partial.stat().st_size if partial.exists() else 0
        if offset == item['bytes']:
            break
        headers = dict(HEADERS)
        if offset:
            headers['Range'] = f'bytes={offset}-'
        try:
            with urllib.request.urlopen(urllib.request.Request(item['url'], headers=headers), timeout=60) as response:
                resume = response.status == 206 and offset > 0
                if not resume:
                    offset = 0
                with partial.open('ab' if resume else 'wb') as stream:
                    last = time.monotonic()
                    while block := response.read(4 * 1024 * 1024):
                        stream.write(block)
                        offset += len(block)
                        if time.monotonic() - last > 10:
                            print(json.dumps({'file': path.name, 'downloaded_mb': round(offset / 1e6), 'percent': round(100 * offset / item['bytes'], 1)}), flush=True)
                            last = time.monotonic()
            break
        except OSError as error:
            print(json.dumps({'retry': attempt + 1, 'file': path.name, 'error': str(error)}), flush=True)
            if attempt == 4:
                raise
    actual = digest(partial)
    if partial.stat().st_size != item['bytes'] or actual != item['sha256']:
        raise ValueError(f'Integrity check failed: {partial}')
    partial.rename(path)
    print(json.dumps({'verified': path.name, 'bytes': item['bytes'], 'sha256': actual}), flush=True)
    return item


def main():
    specs = [
        ('unsloth/NVIDIA-Nemotron-3.5-Bolt-E4B-GGUF', 'NVIDIA-Nemotron-3.5-Bolt-E4B-UD-Q4_K_XL.gguf'),
        ('nvidia/NVIDIA-Nemotron-3.5-Bolt-E4B-4GB-DFlash', 'Nemotron-3.5-Bolt-E4B-DFlash-BF16.gguf'),
    ]
    items = []
    for repo, filename in specs:
        info = get_json(f'https://huggingface.co/api/models/{repo}?blobs=true')
        entry = next(item for item in info['siblings'] if item['rfilename'] == filename)
        items.append({'repo': repo, 'revision': info['sha'], 'filename': filename, 'bytes': entry['size'],
                      'sha256': entry['lfs']['sha256'], 'path': str(MODELS / filename),
                      'url': f'https://huggingface.co/{repo}/resolve/{info["sha"]}/{filename}'})
    release = get_json('https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/b11854')
    asset = next(item for item in release['assets'] if item['name'] == 'llama-b11854-bin-win-cpu-x64.zip')
    archive = OUT / asset['name']
    items.append({'repo': 'ggml-org/llama.cpp', 'revision': 'b11854', 'filename': asset['name'],
                  'bytes': asset['size'], 'sha256': asset['digest'].removeprefix('sha256:'),
                  'path': str(archive), 'url': asset['browser_download_url']})
    (OUT / 'download-plan.json').write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding='utf-8')
    with ThreadPoolExecutor(max_workers=3) as pool:
        verified = list(pool.map(fetch, items))
    if not RUNTIME.exists():
        RUNTIME.mkdir(parents=True)
        with zipfile.ZipFile(archive) as bundle:
            for entry in bundle.infolist():
                target = (RUNTIME / entry.filename).resolve()
                if not target.is_relative_to(RUNTIME.resolve()):
                    raise ValueError('Invalid archive member')
            bundle.extractall(RUNTIME)
    (OUT / 'downloads.json').write_text(json.dumps({'verified': verified, 'runtime': str(RUNTIME)}, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'complete': True, 'runtime': str(RUNTIME)}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
