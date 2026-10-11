"""Download the pinned public Small model; verify it before exposing it to clients."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent

def main():
    spec = json.loads((ROOT / 'model.json').read_text(encoding='utf-8'))
    target = ROOT.parent / 'toolchain/voice-models/ggml-small.bin'
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        partial = target.with_suffix('.part')
        with urllib.request.urlopen(spec['url'], timeout=30) as response, partial.open('wb') as output:
            size = 0
            while block := response.read(1024 * 1024):
                size += len(block)
                if size > spec['bytes']:
                    raise ValueError('Model exceeds its pinned size')
                output.write(block)
        with partial.open('rb') as stream:
            downloaded_digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if size != spec['bytes'] or downloaded_digest != spec['sha256']:
            raise ValueError('Pinned model verification failed')
        partial.replace(target)
    with target.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if target.stat().st_size != spec['bytes'] or digest != spec['sha256']:
        raise ValueError('Existing model verification failed')
    print(json.dumps({'path': str(target), 'bytes': target.stat().st_size, 'sha256': digest}))

if __name__ == '__main__':
    main()
