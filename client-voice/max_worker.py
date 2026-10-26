"""Isolated optional ASR/TTS workers. Installed models only; PCM stays in memory."""
import argparse
import base64
from contextlib import redirect_stdout
from collections import OrderedDict
import json
import hashlib
import os
from pathlib import Path
import queue
import sys
import threading
import time
from french_voice import reference

os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'


def emit(value):
    print(json.dumps(value, ensure_ascii=False), flush=True)


def load_engine(configuration, engine):
    home = Path(configuration[engine]).parent.resolve()
    for name, expected in configuration['manifest'].items():
        if not name.startswith(engine+'/') and not (engine=='tts' and name.startswith('voices/')):
            continue
        file = (home/name).resolve()
        if not file.is_relative_to(home) or not file.is_file() or file.stat().st_size != expected['bytes']:
            raise ValueError('Modèle Max manquant ou incomplet. Réparez son installation.')
        with file.open('rb') as source:
            if hashlib.file_digest(source, 'sha256').hexdigest() != expected['sha256']:
                raise ValueError('Modèle Max corrompu. Réparez son installation.')
    import torch
    device = configuration['device']
    torch.set_num_threads(min(8, os.cpu_count() or 2))
    if device.startswith('cuda'):
        required = 12 if engine == 'asr' else 6
        if not torch.cuda.is_available() or torch.cuda.mem_get_info(device)[0] < required*1024**3:
            raise ValueError('Mémoire GPU libre insuffisante pour le mode Max. Choisissez Low.')
        dtype = torch.float16
    else:
        dtype = torch.float32
    if engine == 'asr':
        from transformers import AutoProcessor, VoxtralRealtimeForConditionalGeneration
        folder = Path(configuration['asr'])
        processor = AutoProcessor.from_pretrained(folder, local_files_only=True)
        model = VoxtralRealtimeForConditionalGeneration.from_pretrained(folder,
            local_files_only=True, use_safetensors=True, dtype=dtype, attn_implementation='sdpa').to(device).eval()
        return (model, processor, torch, device, dtype)
    from qwen_tts import Qwen3TTSModel
    model = Qwen3TTSModel.from_pretrained(configuration['tts'], local_files_only=True,
        device_map=device, dtype=dtype, attn_implementation='sdpa')
    wav,text,_=reference(home)
    prompt=model.create_voice_clone_prompt(ref_audio=str(wav),ref_text=text,x_vector_only_mode=False)
    return (model, prompt, torch, device, dtype)


def infer(loaded, engine, command, cancelled):
    import numpy as np
    from transformers import StoppingCriteria, StoppingCriteriaList
    class Stop(StoppingCriteria):
        def __call__(self, input_ids, scores, **kwargs):
            return cancelled.is_set()
    criteria = StoppingCriteriaList([Stop()])
    model, processor, torch, device, dtype = loaded
    started = time.perf_counter()
    with torch.inference_mode():
        if engine == 'asr':
            raw = base64.b64decode(command['pcm'], validate=True)
            audio = np.frombuffer(raw, dtype='<i2').astype(np.float32)/32768
            batch = processor(audio, return_tensors='pt').to(device, dtype=dtype)
            tokens = model.generate(**batch, max_new_tokens=512, do_sample=False, stopping_criteria=criteria)
            text = processor.batch_decode(tokens, skip_special_tokens=True)[0].strip()[:6000]
            duration = len(audio)/16000
            elapsed=time.perf_counter()-started
            yield {'text': text, 'metrics': {'rtf': elapsed/max(.01, duration), 'elapsed_ms': elapsed*1000}}
        else:
            waves, rate = model.generate_voice_clone(text=command['text'], language='French',
                voice_clone_prompt=processor,
                max_new_tokens=2048, do_sample=False, stopping_criteria=criteria)
            audio = np.asarray(waves[0], dtype=np.float32).reshape(-1)
            if rate != 24000:
                from scipy.signal import resample_poly
                import math
                divisor = math.gcd(rate, 24000)
                audio = resample_poly(audio, 24000//divisor, rate//divisor)
            if len(audio) > 60*24000 or not len(audio) or not np.isfinite(audio).all():
                raise ValueError('Réponse audio Max invalide ou trop longue.')
            elapsed = time.perf_counter()-started
            pcm = (np.clip(audio, -1, 1)*32767).astype('<i2').tobytes()
            for offset in range(0, len(pcm), 9600):
                if cancelled.is_set():
                    break
                yield {'rate': 24000, 'pcm': base64.b64encode(pcm[offset:offset+9600]).decode()}
            yield {'metrics': {'rtf': elapsed/(len(audio)/24000), 'first_audio_ms': elapsed*1000}}


from worker_protocol import CommandInbox


def serve(configuration, engine):
    inbox=CommandInbox(engine)
    commands,stop,closed=inbox.commands,inbox.stop,inbox.closed
    with redirect_stdout(sys.stderr):
        loaded = load_engine(configuration, engine)
    inbox.start()
    emit({'ready': True})
    while not closed.is_set():
        command = commands.get()
        if command is None:
            break
        identifier = command['id']
        inbox.begin(identifier)
        try:
            if not stop.is_set():
                output=iter(infer(loaded, engine, command, stop))
                while True:
                    try:
                        with redirect_stdout(sys.stderr):frame=next(output)
                    except StopIteration:break
                    if stop.is_set():
                        break
                    emit({'id': identifier, **frame})
            emit({'id': identifier, 'done': True, 'cancelled': stop.is_set()})
        except Exception:
            emit({'id': identifier, 'error': 'Le traitement Max a échoué. Raccrochez puis réessayez avec Low.'})
        finally:
            inbox.finish()


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8'); sys.stderr.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    parser.add_argument('--engine', choices=('asr', 'tts'), required=True)
    args = parser.parse_args()
    try:
        serve(json.loads(Path(args.config).read_text(encoding='utf-8')), args.engine)
    except Exception as error:
        emit({'error': str(error) if isinstance(error, (ValueError, OSError)) else 'Chargement du mode Max impossible. Vérifiez son installation.'})
