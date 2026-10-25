"""Probe the signed packaged runtime without downloading or loading model weights."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'client-qwen'),str(ROOT/'lanceur')]
from advanced_voice import AdvancedVoice
from voice_max_package import package
from core import HOME

def main():
    catalogue,archive=package(HOME,ROOT/'toolchain/releases-staging/max-gpu-pack')
    assert catalogue['runtime_api']==4
    with tempfile.TemporaryDirectory(prefix='max-gpu-probe-',dir=ROOT/'toolchain') as temporary:
        home=Path(temporary).resolve();assert home.is_relative_to((ROOT/'toolchain').resolve())
        root=home/'packs'/catalogue['revision'];root.mkdir(parents=True)
        with zipfile.ZipFile(archive) as source:
            for entry in catalogue['runtime']['files']:
                path=root/entry['name'];assert path.resolve().is_relative_to(root.resolve())
                raw=source.read(entry['name']);assert hashlib.sha256(raw).hexdigest()==entry['sha256']
                path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        manifest={entry['name']:{'bytes':entry['bytes'],'sha256':entry['sha256']} for entry in [*catalogue['models'],*catalogue['runtime']['files']]}
        (home/'runtime.json').write_text(json.dumps({'format':2,'root':str(root),'catalogue':catalogue,'manifest':manifest}),encoding='utf-8')
        runtime=AdvancedVoice(home)
        try:
            status=runtime.detect_devices();assert status['gpu']['checked'] and not status['gpu']['error']
            assert not runtime.processes and not status['loaded']
            selected=status['gpu']['recommended']
            if selected:
                runtime.set_gpu(selected);reopened=AdvancedVoice(home)
                try:assert reopened.gpu_selection()==selected
                finally:reopened.close()
            report={'passed':True,'revision':catalogue['revision'],'runtime_api':4,'models_present':False,'models_loaded':False,
                    'probe_process_finished':True,'selection_persisted':bool(selected),'gpu':status['gpu'],
                    'scope':'Native GPU discovery on this NVIDIA host only; no AMD inference or voice benchmark.'}
            (OUT/'packaged-probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(report),flush=True)
        finally:runtime.close()

if __name__=='__main__':main()
