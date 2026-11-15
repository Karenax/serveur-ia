"""Isolated audio worker: CPU by default, optional verified CUDA Whisper."""
import argparse
from contextlib import nullcontext
import time
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def emit(**event):
    print(json.dumps(event, ensure_ascii=False), flush=True)


def maximum_duration_seconds():
    from app.operational_limits import CAPTURE_DURATION_MS
    return CAPTURE_DURATION_MS / 1000


def assign_words(words, turns):
    """Assign each timed word to its largest speaker overlap, preserving turns."""
    rows = []
    for word in words:
        start, end = float(word.start), float(word.end)
        overlaps = [(max(0, min(end, t.end) - max(start, t.start)), t.speaker) for t in turns]
        best = max(overlaps, default=(0, -1))
        speaker = f"SPEAKER_{best[1] + 1:02d}" if best[0] > 0 else "UNKNOWN"
        text = word.word
        if rows and rows[-1]["speaker"] == speaker and start - rows[-1]["end"] < 1.5:
            rows[-1]["text"] += text
            rows[-1]["end"] = end
        else:
            rows.append({"start": start, "end": end, "speaker": speaker, "text": text})
    return rows


def main():
    import av
    import sherpa_onnx
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--speakers", type=int, default=0)
    parser.add_argument("--profile-key")
    args = parser.parse_args()
    models = json.loads((args.models / "models.json").read_text(encoding="utf-8"))
    from speech_runtime import device, configured_cuda_profile, profile_key, cuda_libraries
    profile = configured_cuda_profile(args.models, task="meeting") if device() == "cuda" else None
    if profile and args.profile_key != profile_key(profile):
        raise ValueError("La configuration CUDA audio a changé avant son chargement")
    if not profile and args.profile_key:
        raise ValueError("Une clé CUDA ne peut pas charger un worker CPU")
    with cuda_libraries(profile) if profile else nullcontext():
        from faster_whisper import WhisperModel
        from faster_whisper.audio import decode_audio
        transcribe_meeting(args, models, av, sherpa_onnx, WhisperModel, decode_audio, profile)


def transcribe_meeting(args, models, av, sherpa_onnx, WhisperModel, decode_audio, profile):
    maximum = maximum_duration_seconds()
    with av.open(str(args.audio)) as container:
        duration_hint = container.duration / av.time_base if container.duration else None
        if duration_hint and duration_hint > maximum:
            raise ValueError("Enregistrement supérieur à la capacité de capture de 12 heures.")
    if duration_hint is None or duration_hint > 900:
        return transcribe_windowed(args, models, av, sherpa_onnx, WhisperModel,
                                   profile, duration_hint=duration_hint)
    emit(stage="decoding", progress=1)
    samples = decode_audio(str(args.audio), sampling_rate=16000)
    duration = len(samples) / 16000
    if duration <= 0 or duration > maximum:
        raise ValueError("Audio vide ou durée supérieure à la capacité de capture.")
    emit(stage="speakers", progress=5, duration_seconds=duration)
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(model=models["segmentation"]),
            num_threads=4, provider="cpu"),
        embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=models["embedding"], num_threads=4, provider="cpu"),
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=args.speakers or -1, threshold=0.5),
        min_duration_on=0.3, min_duration_off=0.5)
    if not config.validate():
        raise ValueError("Modèles de séparation des voix invalides ; relancer l’installation audio.")
    diarizer = sherpa_onnx.OfflineSpeakerDiarization(config)
    def report(done, total):
        emit(stage="speakers", progress=5 + 30 * done / max(1, total))
        return 0
    turns = diarizer.process(samples, callback=report).sort_by_start_time()
    del diarizer
    emit(stage="transcribing", progress=35)
    model = load_whisper(models, WhisperModel, profile)
    segments, info = model.transcribe(samples, beam_size=5, language="fr", word_timestamps=True,
                                      vad_filter=True, condition_on_previous_text=False)
    rows = []
    for segment in segments:
        rows.extend(assign_words(segment.words or [], turns))
        emit(stage="transcribing", progress=min(98, 35 + 63 * segment.end / duration),
             processed_seconds=min(duration, segment.end))
    finish_transcription(rows, info.language, duration)


def load_whisper(models, WhisperModel, profile):
    if profile:
        import faster_whisper
        import ctranslate2
        from speech_runtime import construct_cuda_model, cuda_ready
        loaded_at = time.perf_counter()
        model, observed = construct_cuda_model(WhisperModel, profile,
            faster_whisper.__version__, ctranslate2.__version__)
        emit(**cuda_ready(profile, observed, time.perf_counter()-loaded_at,
                         {"enabled": False, "local_files_only": True, "network_isolation_verified": False}))
    else:
        model = WhisperModel(models["whisper"], device="cpu", compute_type="int8", cpu_threads=4, local_files_only=True)
    return model


def finish_transcription(rows, language, duration, **details):
    rows = [dict(row, id=f"seg-{i + 1}", text=row["text"].strip()) for i, row in enumerate(rows) if row["text"].strip()]
    if not rows:
        raise ValueError("Aucune parole exploitable détectée dans cet enregistrement.")
    emit(stage="transcribed", progress=100, processed_seconds=duration, duration_seconds=duration,
         result={"segments": rows, "language": language, **details})


def transcribe_windowed(args, models, av, sherpa_onnx, WhisperModel, profile, *,
                       duration_hint=None, window_seconds=900, overlap_seconds=60):
    # Sixty seconds overlap supplies thirty seconds of context around each ownership boundary.
    from types import SimpleNamespace
    from scripts.meeting_audio_windows import (
        cluster_speakers, decode_windows, owned_words, speaker_prototypes,
    )

    embedding_config = sherpa_onnx.SpeakerEmbeddingExtractorConfig(
        model=models['embedding'], num_threads=4, provider='cpu')
    config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=models['segmentation']), num_threads=4, provider='cpu'),
        embedding=embedding_config,
        clustering=sherpa_onnx.FastClusteringConfig(num_clusters=-1, threshold=0.5),
        min_duration_on=0.3, min_duration_off=0.5)
    if not config.validate():
        raise ValueError('Modèles de séparation des voix invalides')
    diarizer = sherpa_onnx.OfflineSpeakerDiarization(config)
    extractor = sherpa_onnx.SpeakerEmbeddingExtractor(embedding_config)
    model = load_whisper(models, WhisperModel, profile)
    features, rows = [], []
    duration, count, language = 0., 0, 'fr'

    def progress(stage, seconds):
        denominator = max(duration_hint or 0, seconds + window_seconds)
        emit(stage=stage, progress=min(98, 5 + 90 * seconds / denominator),
             processed_seconds=seconds,
             **({'duration_seconds': duration_hint} if duration_hint else {}))

    windows = decode_windows(args.audio, av, window_seconds=window_seconds,
        overlap_seconds=overlap_seconds, maximum_seconds=maximum_duration_seconds())
    try:
        for window in windows:
            count += 1
            progress('speakers', window.bounds[0])
            turns = diarizer.process(window.samples).sort_by_start_time()
            prototypes = speaker_prototypes(window.samples, turns, extractor)
            local = {}
            for speaker, vector in prototypes.items():
                local[speaker] = len(features)
                features.append(vector)
            mapped_turns = [SimpleNamespace(start=t.start, end=t.end, speaker=local[t.speaker])
                            for t in turns if t.speaker in local]
            parts, info = model.transcribe(window.samples, beam_size=5, language='fr',
                word_timestamps=True, vad_filter=True, condition_on_previous_text=False)
            language = info.language
            for part in parts:
                kept = owned_words(part.words or [], window)
                for row in assign_words(kept, mapped_turns):
                    rows.append({**row, 'start': row['start'] + window.offset,
                                 'end': row['end'] + window.offset})
                progress('transcribing', min(window.bounds[1], window.offset + part.end))
            duration = window.offset + window.duration
    finally:
        windows.close()
    labels = cluster_speakers(features, sherpa_onnx, num_speakers=args.speakers)
    for row in rows:
        if row['speaker'] != 'UNKNOWN':
            index = int(row['speaker'].removeprefix('SPEAKER_')) - 1
            row['speaker'] = labels[index]
    finish_transcription(rows, language, duration, decode_windows=count,
                         diarization_scope='global_window_prototypes')


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        main()
    except Exception as exc:
        emit(error=f"{type(exc).__name__}: {exc}")
        sys.exit(1)
