"""Reproducible isolated lot-8 proofs with source fingerprints."""
import hashlib
import io
import json
from pathlib import Path
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'preuves' / 'lots-6-8' / 'notifications'
SOURCES = ['lanceur/notifications.py', 'lanceur/workspace.py', 'lanceur/remote.py',
           'lanceur/operations.py', 'lanceur/app.py', 'lanceur/web/notifications.js',
           'lanceur/web/notifications.css']


def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    before = hashes(); start = time.perf_counter(); stream = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromNames(['test_notifications', 'test_notifications_transport'])
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    after = hashes(); duration = time.perf_counter() - start
    (OUTPUT / 'notifications-tests.log').write_text(stream.getvalue(), encoding='utf-8')
    report = {'date': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'tests': result.testsRun,
              'result': 'PASS' if result.wasSuccessful() else 'FAIL',
              'duration_seconds': round(duration, 3), 'failures': len(result.failures),
              'errors': len(result.errors), 'production_data_used': False,
              'source_unchanged': before == after, 'source_before': before, 'source_after': after}
    (OUTPUT / 'notifications-tests.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in report.items() if key not in ('source_before', 'source_after')}), flush=True)
    return 0 if result.wasSuccessful() and before == after else 1


if __name__ == '__main__':
    raise SystemExit(main())
