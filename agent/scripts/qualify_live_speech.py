"""Real local STT qualification on a caller-supplied fictitious WAV, no DB."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
import unicodedata

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.audio_capture import PreparedAudio
from app.services.live_speech import ResidentWhisper, model_fingerprint, runtime_paths, speech_profile, speech_profile_key


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    audio = args.audio.resolve()
    _, models = runtime_paths()
    started = time.perf_counter()
    resident = ResidentWhisper(audio.parent)
    try:
        resident.start()
        load_s = time.perf_counter() - started
        prepared = PreparedAudio(audio, 0, 0, None, False)
        results = [resident.transcribe(prepared) for _ in range(2)]
    finally:
        resident.close()
    transcript = " ".join(row["text"] for row in results[-1]["segments"])
    folded = "".join(character for character in unicodedata.normalize("NFKD", transcript.lower())
                     if not unicodedata.combining(character))
    expected = ["alpha", "eclairage", "devis", "materiel", "lundi"]
    found = [word for word in expected if word in folded]
    config_path = models / "models.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    binary = Path(config["whisper"]) / "model.bin"
    report = {"passed": len(found) >= 4, "kind": "synthetic_sapi_french",
              "created_at": datetime.now(timezone.utc).isoformat(), "model": config["model"],
              "model_sha256": model_fingerprint(models),
              "runtime_profile": speech_profile(models), "runtime_profile_key": speech_profile_key(models),
              "model_identity": {"size": binary.stat().st_size, "mtime_ns": binary.stat().st_mtime_ns,
                  "config_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest()},
              "audio_sha256": hashlib.sha256(audio.read_bytes()).hexdigest(),
              "duration_ms": results[-1]["duration_ms"], "load_s": round(load_s, 4),
              "compute_s": [item["compute_s"] for item in results],
              "transcript": transcript, "expected_keywords": expected, "found_keywords": found,
              "live_two_tracks_passed": False, "long_session_passed": False}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
