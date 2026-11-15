"""Resident local Whisper worker. JSON lines; no network or DB access."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import json
import os
from pathlib import Path
import sys
import time


def emit(**event):
    print(json.dumps(event, ensure_ascii=False), flush=True)


def transcribe(model, samples, request):
    offset = int(request.get("offset_ms", 0))
    begin = int(request.get("clip_start_ms", 0))
    end = request.get("clip_end_ms")
    duration = len(samples) * 1000 / 16000
    if duration <= 0 or duration > 7200000:
        raise ValueError("Audio vide ou supérieur à deux heures")
    if begin < 0 or begin >= duration or (end is not None and int(end) <= begin):
        raise ValueError("Fenêtre de transcription hors audio")
    finish = min(duration, int(end)) if end is not None else duration
    cropped = samples[int(begin * 16):int(finish * 16)]
    parts, _ = model.transcribe(cropped, language="fr", beam_size=5,
        word_timestamps=True, vad_filter=True, condition_on_previous_text=False,
        no_speech_threshold=0.6, compression_ratio_threshold=2.4,
        vad_parameters={"min_silence_duration_ms": 250})
    rows = []
    keep_from = int(request.get("keep_from_ms", offset + begin))
    revise_from = request.get('revise_from_ms')
    context_rows = []
    if revise_from is not None and not offset + begin <= int(revise_from) < keep_from <= offset + finish:
        raise ValueError('Fenêtre de révision audio incohérente')
    for part in parts:
        if part.no_speech_prob > 0.85:
            continue
        if revise_from is not None:
            previous_words = [word for word in part.words or []
                if int(revise_from) <= offset + begin + (word.start + word.end) * 500 < keep_from]
            previous_text = ''.join(word.word for word in previous_words).strip()
            if previous_text:
                context_rows.append({'start_ms': max(int(revise_from), offset + begin + round(previous_words[0].start * 1000)),
                    'end_ms': min(keep_from, offset + begin + round(previous_words[-1].end * 1000)),
                    'text': previous_text, 'speaker': request.get('track', 'UNKNOWN')})
        words = [word for word in part.words or []
                 if offset + begin + (word.start + word.end) * 500 >= keep_from]
        text = "".join(word.word for word in words).strip()
        if not text or part.no_speech_prob > 0.85:
            continue
        rows.append({"start_ms": max(keep_from, offset + begin + round(words[0].start * 1000)),
                     "end_ms": min(offset + round(finish), offset + begin + round(words[-1].end * 1000)),
                     "text": text, "speaker": request.get("track", "UNKNOWN")})
    result = {"segments": rows, "duration_ms": round(duration), "language": "fr"}
    if revise_from is not None:
        result['context_segments'] = context_rows
    return result


def decode_request(request, storage, decode_audio):
    """Decode optional admitted native overlap in memory, preserving originals."""
    path = Path(request['path']).resolve()
    if not path.is_relative_to(storage) or not path.is_file():
        raise ValueError('Audio hors stockage autorisé')
    context = request.get('context')
    if context is not None:
        if not isinstance(context, dict) or set(context) != {'path', 'duration_ms'}:
            raise ValueError('Contexte audio explicite requis')
        milliseconds = context['duration_ms']
        previous = Path(context['path']).resolve()
        if (type(milliseconds) is not int or not 0 < milliseconds <= 5000
                or not previous.is_relative_to(storage) or not previous.is_file()
                or previous.stat().st_size > 160044 or previous == path):
            raise ValueError('Contexte audio hors limites')
        try:
            from .audio_codec import opus_duration_ms
        except ImportError:  # Executed directly in the isolated speech runtime.
            from audio_codec import opus_duration_ms
        duration = opus_duration_ms(previous.read_bytes())
        if not milliseconds <= duration <= 5000:
            raise ValueError('Durée du contexte audio incohérente')
    samples = decode_audio(str(path), sampling_rate=16000)
    if context is not None:
        import numpy as np
        before = decode_audio(str(previous), sampling_rate=16000)
        count = milliseconds * 16
        if len(before) < count or len(before) > 80000:
            raise ValueError('Contexte décodé incohérent')
        samples = np.concatenate((before[-count:], samples))
    return samples


def main():
    from offline_guard import verify
    from speech_runtime import (device, configured_cuda_profile, profile_key, cuda_libraries,
                                construct_cuda_model, cuda_ready)
    offline = verify()
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--storage", type=Path, required=True)
    parser.add_argument("--profile-key")
    args = parser.parse_args()
    config = json.loads((args.models / "models.json").read_text(encoding="utf-8"))
    threads = int(os.environ.get("PB_SPEECH_THREADS", config.get("cpu_threads", 4)))
    if not 1 <= threads <= 16:
        raise ValueError("Threads STT hors limites")
    profile = configured_cuda_profile(args.models) if device() == "cuda" else None
    if profile and args.profile_key != profile_key(profile):
        raise ValueError("La configuration CUDA audio a changé avant son chargement")
    if not profile and args.profile_key:
        raise ValueError("Une clé CUDA ne peut pas charger un worker CPU")
    with cuda_libraries(profile) if profile else nullcontext():
        import faster_whisper
        from faster_whisper import WhisperModel
        from faster_whisper.audio import decode_audio
        started = time.perf_counter()
        if profile:
            import ctranslate2
            model, observed = construct_cuda_model(WhisperModel, profile,
                faster_whisper.__version__, ctranslate2.__version__)
            emit(**cuda_ready(profile, observed, time.perf_counter() - started, offline))
        else:
            model = WhisperModel(config["whisper"], device="cpu", compute_type="int8",
                                 cpu_threads=threads, local_files_only=True)
            emit(kind="ready", model=config.get("model", ""), load_s=time.perf_counter() - started,
                 offline_guard=offline, cpu_threads=threads, device="cpu", compute_type="int8", runtime_version="1.2.1")
        serve(model, config, threads, args, decode_audio)


def serve(model, config, threads, args, decode_audio):
    storage = args.storage.resolve()
    for line in sys.stdin:
        request = {}
        try:
            if len(line) > 16384:
                raise ValueError("Commande audio trop longue")
            request = json.loads(line)
            if request.get("op") == "stop":
                break
            if request.get("op") == "batch_group_pcm_v1":
                from grouped_pcm_worker import transcribe_group
                started = time.perf_counter()
                result = transcribe_group(model, request, storage, decode_audio, transcribe,
                    loaded_profile={"model": config.get("model", ""), "model_path": config["whisper"],
                                    "cpu_threads": threads, "runtime_version": "1.2.1"})
                emit(kind="result", request_id=request["request_id"], **result,
                     compute_s=round(time.perf_counter() - started, 4))
                continue
            started = time.perf_counter()
            samples = decode_request(request, storage, decode_audio)
            result = transcribe(model, samples, request)
            emit(kind="result", request_id=request["request_id"], **result,
                 compute_s=round(time.perf_counter() - started, 4))
        except Exception as exc:
            emit(kind="error", request_id=request.get("request_id"),
                 error=f"{type(exc).__name__}: traitement audio local impossible")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        main()
    except Exception as exc:
        emit(kind="error", error=f"{type(exc).__name__}: chargement du runtime audio impossible")
        raise SystemExit(1)
