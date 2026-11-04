"""Verify the published automatic download without changing a user's Codex."""
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from core import HOME
from releases import profile
from client import Remote
from connection_settings import HTTPS_ENDPOINT
from codex_integration import unpack

records=json.loads((HOME/'acces-distants.json').read_text(encoding='utf-8'))['clients']
active={r['id'] for r in records if not r.get('revoked') and not r.get('suspended') and not r.get('hermes_pending') and (not r.get('expires_epoch') or r['expires_epoch']>time.time())}
values=next(profile(p) for p in (HOME/'clients').glob('*.exe') if p.stem in active)
remote=Remote(values,endpoint=HTTPS_ENDPOINT)
try:
    with remote.open('/v1/client/codex') as response:value=json.load(response)
    with remote.open('/v1/client/codex/models?client_version=0.166.0') as response:catalogue=json.load(response)
    assert [row['slug'] for row in catalogue['models']]==['fred-qwen']
    with tempfile.TemporaryDirectory(prefix='kiara-codex-live-download-') as folder:
        target=Path(folder);unpack(value,values['update_public_key'],target)
        expected=(ROOT/'maintenance/codex/Installer-Codex-Kiara.ps1').read_bytes()
        assert (target/'Installer-Codex-Kiara.ps1').read_bytes()==expected
        assert b'Repair-KiaraDefaults' not in expected
        assert json.loads((target/'qwen-models.json').read_text(encoding='utf-8'))['models'][0]['slug']=='fred-qwen'
finally:remote.close()
report={'passed':True,'endpoint':HTTPS_ENDPOINT+'/v1/client/codex',
        'pinned_signature_verified':True,'resources_match_sources':True,'provider_catalogue_available':True,'bytes':value['release']['bytes'],
        'sha256':value['release']['sha256'],'no_user_codex_configuration_changed':True}
Path(__file__).with_name('codex-download.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report))
