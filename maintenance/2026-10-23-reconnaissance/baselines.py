"""Same public/local French audio for Zipformer and the installed Whisper Small."""
import json
from pathlib import Path
import sys
import time
import wave
import numpy as np
import sherpa_onnx
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'toolchain/asr-research-20261023'
sys.path.insert(0, str(ROOT / 'client-qwen'))
from local_voice import NativeEngine


def wait(engine, phase):
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        state = engine.status()
        if state['phase'] == phase:
            return state
        if state['phase'] == 'error':
            raise ValueError(state)
        time.sleep(.02)
    raise TimeoutError(engine.status())


def main():
    folder = ROOT / 'toolchain/conversation-models'
    zipformer = sherpa_onnx.OnlineRecognizer.from_transducer(
        tokens=str(folder / 'tokens.txt'), encoder=str(folder / 'encoder.onnx'),
        decoder=str(folder / 'decoder.onnx'), joiner=str(folder / 'joiner.onnx'),
        num_threads=4, provider='cpu', enable_endpoint_detection=False)
    results = []
    for path in [ROOT / 'preuves/voix-small-20261011/francais.wav', WORK / 'parakeet/test_wavs/fr.wav']:
        with wave.open(str(path)) as source:
            rate = source.getframerate()
            pcm = np.frombuffer(source.readframes(source.getnframes()), dtype='<i2').astype(np.float32) / 32768
        if rate != 16000:
            import math
            divisor = math.gcd(rate, 16000)
            pcm = resample_poly(pcm, 16000 // divisor, rate // divisor).astype(np.float32)
        for variant, audio in [('original', pcm), ('quiet', pcm * .15), ('noise', np.clip(pcm + np.random.default_rng(42).normal(0, .008, len(pcm)), -1, 1).astype(np.float32))]:
            start = time.perf_counter()
            stream = zipformer.create_stream()
            stream.accept_waveform(16000, np.concatenate([np.zeros(4800, np.float32), audio, np.zeros(48000, np.float32)]))
            stream.input_finished()
            while zipformer.is_ready(stream):
                zipformer.decode_stream(stream)
            result = {'model': 'Zipformer', 'fixture': path.name, 'variant': variant,
                      'compute_seconds': time.perf_counter() - start, 'text': zipformer.get_result(stream)}
            results.append(result); print(json.dumps(result, ensure_ascii=True), flush=True)
            engine = NativeEngine(ROOT / 'client-qwen/voice', ROOT / 'toolchain/voice-models/ggml-small.bin')
            try:
                wait(engine, 'listening')
                start = time.perf_counter()
                data = (audio * 32767).astype('<i2').tobytes()
                for offset in range(0, len(data), 32000):
                    engine.feed(data[offset:offset + 32000])
                engine.stop()
                final = wait(engine, 'ready')
                result = {'model': 'Whisper Small', 'fixture': path.name, 'variant': variant,
                          'compute_seconds': time.perf_counter() - start, 'text': final['text']}
                results.append(result); print(json.dumps(result, ensure_ascii=True), flush=True)
            finally:
                engine.close()
    (WORK / 'baseline-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
