"""Loopback-only qualification using a fictitious SAPI voice; never open mic."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import unicodedata
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.services.live_speech import (ResidentWhisper, _windows_job, runtime_paths,
                                     consolidate_session_audio)
from app.services.audio_capture import PreparedAudio
from app.services.native_audio import inventory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    devices = inventory(refresh=True)
    loops = [item for item in devices.get("devices", []) if item["isLoopbackDevice"]]
    if not devices.get("interactive_session") or not loops:
        raise ValueError("Aucun loopback interactif disponible ; matériel non qualifié")
    sid = str(uuid.uuid4())
    storage = args.directory.resolve() / sid
    storage.mkdir(parents=True)
    request = {"session_id": sid, "storage": str(storage), "directory": str(storage / "chunks"),
               "tracks": ["system"], "sequences": {"system": 0}, "offset_ms": 0}
    request_path = storage / "request.json"
    request_path.write_text(json.dumps(request), encoding="utf-8")
    python, _ = runtime_paths()
    process = subprocess.Popen([str(python), "-u", "scripts/native_audio_capture.py", "--request", str(request_path),
        "--parent-pid", str(os.getpid())], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True, encoding="utf-8", creationflags=subprocess.CREATE_NO_WINDOW)
    job = _windows_job(process)
    events, packets = queue.Queue(), []

    def read():
        for line in process.stdout:
            event = json.loads(line)
            if event.get("kind") == "chunk":
                packets.append(event)
            events.put(event)

    threading.Thread(target=read, daemon=True).start()

    def wait_state(expected):
        while True:
            event = events.get(timeout=35)
            if event.get("kind") == "error":
                raise ValueError(event["error"])
            if event.get("kind") == expected or event.get("state") == expected:
                return event

    def control(op, expected):
        if process.poll() is not None:
            wait_state(expected)
        process.stdin.write(json.dumps({"op": op}) + "\n")
        process.stdin.flush()
        return wait_state(expected)

    try:
        ready = wait_state("ready")
        control("start", "recording")
        time.sleep(.25)
        sentence = "Bonjour. Ceci est une réunion fictive de qualification. Le projet Alpha concerne l'installation d'un éclairage industriel. Marie prépare le devis jeudi et Paul vérifie le matériel vendredi. La prochaine réunion aura lieu lundi."
        command = "$v=New-Object -ComObject SAPI.SpVoice;$v.Voice=@($v.GetVoices() | Where-Object {$_.GetDescription() -match 'Hortense'})[0];$v.Speak('" + sentence.replace("'", "''") + "') | Out-Null"
        voice = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, timeout=40, creationflags=subprocess.CREATE_NO_WINDOW)
        if voice.returncode:
            raise ValueError("La voix fictive SAPI ne peut pas être lue sur les haut-parleurs")
        time.sleep(.3)
        control("pause", "paused")
        paused_count = len(packets)
        control("resume", "recording")
        time.sleep(.1)
        control("stop", "stopped")
        process.wait(10)
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait(5)
        for stream in (process.stdin, process.stdout):
            try:
                stream.close()
            except OSError:
                pass
        job[0].CloseHandle(job[1])
    if not packets:
        raise ValueError("Loopback ouvert mais aucun audio capturé")
    chunks = [{**packet, "id": f"chunk-{packet['sequence']}", "storage_path": packet["path"],
               "mime_type": "audio/wav"} for packet in packets]
    mixed = consolidate_session_audio(chunks, lambda item: item["storage_path"], storage_root=storage)
    stt = ResidentWhisper(storage)
    try:
        result = stt.transcribe(PreparedAudio(mixed, 0, 0, None, False), track="system")
    finally:
        stt.close()
    text = " ".join(item["text"] for item in result["segments"])
    folded = "".join(char for char in unicodedata.normalize("NFKD", text.lower()) if not unicodedata.combining(char))
    found = [word for word in ("alpha", "eclairage", "devis", "materiel", "lundi") if word in folded]
    report = {"passed": len(found) >= 4, "created_at": datetime.now(timezone.utc).isoformat(),
              "kind": "synthetic_sapi_speaker_output_loopback_only", "microphone_opened": False,
              "version": devices["version"], "device_name": loops[0]["name"], "ready": ready,
              "chunks": len(chunks), "pause_drained_chunks": paused_count,
              "audio_sha256": hashlib.sha256(mixed.read_bytes()).hexdigest(),
              "duration_ms": result["duration_ms"], "stt_compute_s": result["compute_s"],
              "transcript": text, "found_keywords": found, "teams_desktop_tested": False,
              "long_hardware_capture_tested": False}
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
