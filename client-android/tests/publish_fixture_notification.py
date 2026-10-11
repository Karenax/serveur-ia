"""Publish a completed-job event only in the explicit Android test fixture."""
import argparse
import json
from pathlib import Path
import secrets
import sys

root = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--fixture', type=Path, default=root / 'toolchain/android-tests/lots6-8-transport')
args = parser.parse_args()
fixture = args.fixture.resolve()
allowed = (root / 'toolchain/android-tests').resolve()
if not fixture.is_relative_to(allowed) or fixture.name != 'lots6-8-transport':
    raise SystemExit('Only the explicitly isolated Android test fixture is supported.')
profile = json.loads((fixture / 'profile-0.fred-android').read_text(encoding='utf-8'))
if not profile.get('client_name', '').startswith('Fixture Android'):
    raise SystemExit('Personal profiles cannot be used by this fixture helper.')
ids = json.loads((fixture / 'fixture-public.json').read_text(encoding='utf-8'))
sys.path.insert(0, str(root / 'lanceur'))
from workspace import Workspace
from notifications import Notifications
workspace = Workspace(fixture / 'isolated-server')
result = Notifications(workspace).publish(profile['token'].split('_')[1], 'job_completed', 'android-click-' + secrets.token_hex(16), {'kind': 'job', 'id': ids['job'], 'project': ids['project']})
print(json.dumps({'published': result.get('created'), 'fixture': True}))
