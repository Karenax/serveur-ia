"""Evaluate the multilingual Nemotron 3.5 streaming model, CPU and French forced."""
import json
import math
import time
import urllib.request
import wave
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from scipy.signal import resample_poly
import sherpa_onnx
import compare


def main():
    compare.REPO = 'csukuangfj2/sherpa-onnx-nemotron-3.5-asr-streaming-0.6b-560ms-int8-2026-06-11'
    compare.REVISION = 'ab43d895f5985b1bbab8b6eac8607fcdc05343f3'
    compare.MODEL_FOLDER = compare.WORK / 'nemotron'
    metadata = json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{compare.REPO}/revision/{compare.REVISION}?blobs=true', timeout=30))
    items = [item for item in metadata['siblings'] if item['rfilename'] in ('encoder.int8.onnx', 'decoder.int8.onnx', 'joiner.int8.onnx', 'tokens.txt')]
    with ThreadPoolExecutor(max_workers=3) as pool:
        files = list(pool.map(compare.download, items))
    (compare.WORK / 'nemotron-downloads.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
    print('Nemotron 3.5 downloaded and hash-checked.', flush=True)
    folder = compare.MODEL_FOLDER
    started = time.perf_counter()
    asr = sherpa_onnx.OnlineRecognizer.from_transducer(
        encoder=str(folder / 'encoder.int8.onnx'), decoder=str(folder / 'decoder.int8.onnx'),
        joiner=str(folder / 'joiner.int8.onnx'), tokens=str(folder / 'tokens.txt'),
        model_type='nemo_transducer', num_threads=4, provider='cpu', enable_endpoint_detection=False)
    loaded = time.perf_counter() - started
    results = []
    for path in [compare.ROOT / 'preuves/voix-small-20261011/francais.wav', compare.WORK / 'parakeet/test_wavs/fr.wav']:
        with wave.open(str(path)) as source:
            rate = source.getframerate()
            pcm = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32) / 32768
        if rate != 16000:
            divisor = math.gcd(rate, 16000)
            pcm = resample_poly(pcm, 16000 // divisor, rate // divisor).astype(np.float32)
        for variant, audio in [('original', pcm), ('quiet', pcm * .15), ('noise', np.clip(pcm + np.random.default_rng(42).normal(0, .008, len(pcm)), -1, 1).astype(np.float32))]:
            start = time.perf_counter()
            stream = asr.create_stream()
            stream.set_option('language', 'fr-FR')
            first = None
            for offset in range(0, len(audio), 1600):
                stream.accept_waveform(16000, audio[offset:offset+1600])
                while asr.is_ready(stream):
                    asr.decode_stream(stream)
                if first is None and asr.get_result(stream).strip():
                    first = (offset + 1600) / 16000
            stream.accept_waveform(16000, np.zeros(16000, dtype=np.float32))
            stream.input_finished()
            while asr.is_ready(stream):
                asr.decode_stream(stream)
            result = {'fixture': path.name, 'variant': variant, 'first_partial_audio_seconds': first,
                      'compute_seconds': time.perf_counter() - start, 'text': asr.get_result(stream)}
            results.append(result); print(json.dumps(result, ensure_ascii=True), flush=True)
    (compare.WORK / 'nemotron-results.json').write_text(json.dumps({'loading_seconds': loaded, 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
