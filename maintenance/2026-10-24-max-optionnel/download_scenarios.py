"""Quote the signed pack for fresh install, existing Low and existing Max; no download."""
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'client-qwen'),str(Path(__file__).parent)]
from advanced_voice import AdvancedVoice
from max_installation import MaxInstallation
from qualify_optional import LocalRelease

results={}
device={'checked':True,'eligible':True,'cards':[{'vendor':'nvidia','name':'NVIDIA fixture for size quotation'}]}
for name,home,shared in (
    ('fresh',ROOT/'toolchain/voice-max-size-new',ROOT/'toolchain/voice-max-size-missing-low'),
    ('low_installed',ROOT/'toolchain/voice-max-size-new',ROOT/'toolchain/asr-models'),
    ('max_installed',ROOT/'toolchain/voice-max-optional-qa',ROOT/'toolchain/asr-models')):
    runtime=AdvancedVoice(home)
    with patch('max_installation.hardware',return_value=device):
        installer=MaxInstallation(home,LocalRelease(),runtime,shared);installer.detect()
    try:
        results[name]=installer.plan()
    finally:
        installer.close();runtime.close()
Path(__file__).with_name('download-scenarios.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:{f:v[f] for f in ('download_bytes','required_disk_bytes','reused_bytes')} for k,v in results.items()},ensure_ascii=False))
