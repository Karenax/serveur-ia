"""Reproducible local CPU comparison; public fixtures only, no personal audio."""
import hashlib
import json
from pathlib import Path
import sys
import time
import urllib.request
import wave
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'toolchain/asr-research-20261023'
REPO = 'csukuangfj/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8'
REVISION = '2bda32ec70b097a55adaa07d9a7173915b43cc78'
MODEL_FOLDER = WORK / 'parakeet'
sys.path.insert(0, str(ROOT / 'client-qwen'))


def download(item):
    name = item['rfilename']
    path = MODEL_FOLDER / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with urllib.request.urlopen(f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}', timeout=60) as response, path.with_suffix('.part').open('wb') as output:
            while block := response.read(1024 * 1024):
                output.write(block)
                if output.tell() > item['size']:
                    raise ValueError('Unexpected download size')
        path.with_suffix('.part').replace(path)
    data = path.read_bytes()
    if len(data) != item['size']:
        raise ValueError('Incomplete download')
    if 'lfs' in item:
        assert hashlib.sha256(data).hexdigest() == item['lfs']['sha256']
    else:
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == item['blobId']
    return {'name': name, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest(),
            'url': f'https://huggingface.co/{REPO}/resolve/{REVISION}/{name}'}


def main():
    import numpy as np
    import sherpa_onnx
    WORK.mkdir(parents=True, exist_ok=True)
    metadata = json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true', timeout=30))
    items = [item for item in metadata['siblings'] if item['rfilename'] in ('encoder.int8.onnx', 'decoder.int8.onnx', 'joiner.int8.onnx', 'tokens.txt', 'test_wavs/fr.wav')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        files = list(pool.map(download, items))
    (WORK / 'downloads.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
    print('Public models downloaded and verified.', flush=True)
    folder = WORK / 'parakeet'
    started = time.perf_counter()
    asr = sherpa_onnx.OfflineRecognizer.from_transducer(
        encoder=str(folder / 'encoder.int8.onnx'), decoder=str(folder / 'decoder.int8.onnx'),
        joiner=str(folder / 'joiner.int8.onnx'), tokens=str(folder / 'tokens.txt'),
        model_type='nemo_transducer', num_threads=4, provider='cpu')
    loaded = time.perf_counter() - started
    results = []
    fixtures = [ROOT / 'preuves/voix-small-20261011/francais.wav', ROOT / 'preuves/conversation-windows-20261011/fred-francais.wav', folder / 'test_wavs/fr.wav']
    for path in fixtures:
        with wave.open(str(path)) as source:
            assert source.getnchannels() == 1 and source.getsampwidth() == 2
            rate = source.getframerate()
            pcm = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32) / 32768
        for label, audio in [('original', pcm), ('quiet', pcm * .15), ('noise', np.clip(pcm + np.random.default_rng(42).normal(0, .008, len(pcm)), -1, 1).astype(np.float32))]:
            started = time.perf_counter()
            stream = asr.create_stream()
            stream.accept_waveform(rate, audio)
            asr.decode_stream(stream)
            result = {'file': str(path.relative_to(ROOT)), 'variant': label, 'seconds': len(pcm) / rate,
                      'compute_seconds': time.perf_counter() - started, 'text': stream.result.text}
            results.append(result)
            print(json.dumps(result, ensure_ascii=True), flush=True)
    result = {'model': REPO, 'revision': REVISION, 'provider': 'cpu', 'threads': 4,
              'loading_seconds': loaded, 'fixtures': results,
              'limits': 'Three fixtures: two synthetic and one public sample of unverified speaker provenance; not a representative French benchmark.'}
    (WORK / 'parakeet-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
