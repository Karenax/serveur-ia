"""Upgrade the existing server pack through its installer; retain models and rollback."""
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-voice'),str(OUT)]
from core import HOME
from prepare_max_pack import Release
from kiara_shared.voice_runtime import AdvancedVoice
from kiara_shared.voice_packs import MaxInstallation
from deliver import idle,models,user_fingerprints,get


def main():
    idle()
    home=ROOT/'toolchain/voice-max-server'
    before=json.loads((home/'runtime.json').read_text(encoding='utf-8'))
    expected=json.loads((ROOT/'toolchain/voice-max-release/release.json').read_text())['revision']
    original_models=models();original_users=user_fingerprints()
    saved=OUT/'previous-server-voice';saved.mkdir(exist_ok=True)
    for name in ('runtime.json','benchmark.json','gpu.json'):
        if (home/name).exists() and not (saved/name).exists():shutil.copy2(home/name,saved/name)
    runtime=AdvancedVoice(home)
    installer=MaxInstallation(home,Release(ROOT/'toolchain/voice-max-release',HOME),runtime,ROOT/'toolchain/asr-models')
    succeeded=False
    try:
        assert not runtime.status()['busy'] and not runtime.status()['loaded']
        installer.detect();plan=installer.plan()
        installer.install(plan['plan'])
        deadline=time.monotonic()+300
        while installer.thread.is_alive() and time.monotonic()<deadline:installer.thread.join(2)
        assert not installer.thread.is_alive(),'Server voice installation timed out'
        assert installer.status()['phase']=='ready',installer.status()['message']
        assert runtime.configuration()['catalogue']['revision']==expected
        benchmark=json.loads((home/'benchmark.json').read_text(encoding='utf-8'))
        assert benchmark.get('functional'),benchmark
        succeeded=True
    finally:
        installer.close();runtime.close()
        if not succeeded:
            for name in ('runtime.json','benchmark.json','gpu.json'):
                if (saved/name).exists():shutil.copy2(saved/name,home/name)
    assert models()==original_models and user_fingerprints()==original_users
    proof={'passed':True,'previous_revision':before['catalogue']['revision'],'revision':expected,
           'models_preserved':True,'user_data_preserved':True,'native_benchmark':benchmark,
           'workers_unloaded':not runtime.status()['loaded'],'microphone_opened':False,
           'previous_configuration':str(saved)}
    (OUT/'server-voice-installation.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in proof.items() if k!='native_benchmark'}))


if __name__=='__main__':main()
