"""User-authorized parser fix + 20 parked conversations, still capped at 30 GiB."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('cache_rollout',
    ROOT / 'maintenance/2026-10-16-diagnostic-opencode/activer_cache.py')
rollout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rollout)
rollout.OUT = HERE / 'activation'
rollout.OUT.mkdir(exist_ok=True)
rollout.CACHE_SLOTS = 20

if __name__ == '__main__':
    rollout.main()
