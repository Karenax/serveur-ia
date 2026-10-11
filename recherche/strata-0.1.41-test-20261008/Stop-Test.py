"""Stop only the recorded test server and its children; never the production server."""
import json
from pathlib import Path
import psutil

ROOT = Path(__file__).resolve().parent
state = ROOT / "test-process.json"
if not state.exists():
    print("Aucun serveur de test enregistre.")
    raise SystemExit(0)
record = json.loads(state.read_text(encoding="utf-8-sig"))
config = Path(record["config"]).resolve()
if config.parent != ROOT or config.name not in {f"config-{p}.json" for p in ("reference", "trim", "pipeline", "benchmark", "fp16", "cpu-prefill", "cpu-court", "cpu-court-pin", "cpu-court-pin-4096")}:
    raise SystemExit("Configuration enregistree hors du dossier de test : arret refuse.")
try:
    proc = psutil.Process(record["pid"])
    cmd = proc.cmdline()
except psutil.NoSuchProcess:
    state.unlink()
    print("Le serveur de test est deja arrete.")
    raise SystemExit(0)
if "serve.server" not in cmd or "--config" not in cmd or Path(cmd[cmd.index("--config") + 1]).resolve() != config:
    raise SystemExit("Le PID ne correspond pas au serveur de test : arret refuse.")
children = proc.children(recursive=True)
# Verify every child's ancestry before termination; do not search for processes by name.
for child in reversed(children):
    try:
        if proc.pid in {p.pid for p in child.parents()}:
            child.terminate()
    except psutil.NoSuchProcess:
        pass
try:
    proc.terminate()
except psutil.NoSuchProcess:
    # Stopping the engine can make its Python parent exit before this call.
    pass
psutil.wait_procs(children + [proc], timeout=10)
state.unlink()
print("Serveur de test arrete.")
