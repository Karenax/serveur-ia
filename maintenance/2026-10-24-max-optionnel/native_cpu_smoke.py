"""Isolated CPU smoke of actual GGUF streaming and French recognition; no GPU inference."""
import array
import json
from pathlib import Path
import sys
import threading
import time
import wave

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'client-voice'))
from max_native import NativeVoice, ProgressiveParakeet


configuration = json.loads((ROOT/'toolchain/voice-max-optional-qa/runtime.json').read_text(encoding='utf-8'))
print('Loading CPU-only native voice', flush=True)
voice = NativeVoice(configuration['root'], 'CPU')
print('Generating synthetic French fixture', flush=True)
started = time.perf_counter(); first = None; chunks = 0; raw = bytearray(); metrics = None
try:
    for frame in voice.stream('Bonjour. La réunion du projet Orion est prévue demain à quinze heures.', threading.Event()):
        if frame.get('raw_pcm'):
            if first is None:
                first = time.perf_counter()-started
                print(json.dumps({'first_audio_s': first}), flush=True)
            chunks += 1; raw.extend(frame['raw_pcm'])
        if frame.get('metrics'):
            metrics = frame['metrics']
finally:
    voice.close()
elapsed = time.perf_counter()-started
with wave.open(str(Path(__file__).with_name('native-french-fixture.wav')), 'wb') as target:
    target.setnchannels(1); target.setsampwidth(2); target.setframerate(24000); target.writeframes(raw)
print('Checking recognition of synthetic speech', flush=True)
samples = array.array('h'); samples.frombytes(raw)
converted = array.array('h', (samples[min(len(samples)-1, int(i*1.5))] for i in range(len(samples)*2//3)))
asr = ProgressiveParakeet(configuration['asr'])
recognition_started = time.perf_counter()
text = asr.transcribe({'raw_pcm': converted.tobytes()})
report = {'device': 'CPU', 'first_audio_s': first, 'generation_s': elapsed, 'chunks': chunks,
          'duration_s': len(raw)/(24000*2), 'streaming_before_completion': first is not None and first < elapsed,
          'metrics': metrics, 'recognized': text, 'asr_s': time.perf_counter()-recognition_started,
          'scope': 'functional CPU smoke only; does not qualify AMD/NVIDIA or perceptual voice quality'}
Path(__file__).with_name('native-cpu-streaming.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(report, ensure_ascii=False), flush=True)
