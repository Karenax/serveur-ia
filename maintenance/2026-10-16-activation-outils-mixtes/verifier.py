"""Verify the restarted service using existing cache and real-tool probes."""
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location('live_probe',
    ROOT / 'maintenance/2026-10-16-outils-booleens/verifier_live.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
probe.HERE = HERE
probe.measure.OUT = HERE / 'validation-cache'
probe.measure.OUT.mkdir(exist_ok=True)
probe.measure.REPORT['purpose'] = 'Integration after activation of hybrid JSON/XML and required-field fix'

if __name__ == '__main__':
    probe.main()
