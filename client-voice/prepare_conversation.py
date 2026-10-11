"""Fetch only public, pinned ONNX models; publish a hash-checked client catalogue."""
import hashlib
import json
import os
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / 'toolchain/conversation-models'

def metadata(repo):
    with urllib.request.urlopen('https://huggingface.co/api/models/' + repo, timeout=30) as response:
        return json.load(response)

def download(url, name):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        with urllib.request.urlopen(url, timeout=60) as response, path.with_suffix('.part').open('wb') as output:
            while block := response.read(1024 * 1024):
                output.write(block)
                if output.tell() > 300 * 1024 * 1024:
                    raise ValueError('Unexpected public model size')
        os.replace(path.with_suffix('.part'), path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    print(name, path.stat().st_size, digest, flush=True)
    return dict(name=name, url=url, bytes=path.stat().st_size, sha256=digest)

if __name__ == '__main__':
    records = []
    repo = 'shaojieli/sherpa-onnx-streaming-zipformer-fr-2023-04-14'
    info = metadata(repo)
    names = [s['rfilename'] for s in info['siblings']]
    for component in ('encoder', 'decoder', 'joiner'):
        matches = [n for n in names if n.startswith(component) and n.endswith('.int8.onnx')]
        if not matches:
            matches = [n for n in names if n.startswith(component) and n.endswith('.onnx') and '.int8.' not in n]
        assert len(matches) == 1, (component, matches)
        records.append(download(f'https://huggingface.co/{repo}/resolve/{info["sha"]}/{matches[0]}', component + '.onnx'))
    records.append(download(f'https://huggingface.co/{repo}/resolve/{info["sha"]}/tokens.txt', 'tokens.txt'))
    turn_repo = 'pipecat-ai/smart-turn-v3'
    turn = metadata(turn_repo)
    records.append(download(f'https://huggingface.co/{turn_repo}/resolve/{turn["sha"]}/smart-turn-v3.2-cpu.onnx', 'smart-turn.onnx'))
    records.append(download('https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx', 'silero-vad.onnx'))
    spec = dict(format=1, model='Zipformer français + Silero + Smart Turn 3.2', files=records,
                revisions={repo: info['sha'], turn_repo: turn['sha']})
    (ROOT / 'client-voice/conversation-models.json').write_text(json.dumps(spec, indent=2) + '\n', encoding='utf-8')
