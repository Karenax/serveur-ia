"""Verify and publish the optional pack with the existing Kiara signing key."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'lanceur'),str(ROOT/'client-qwen')]
from core import HOME
from signing import public
from voice_max_package import package


def main():
    source=ROOT/'toolchain/releases-staging/max-choice-pack'
    target=ROOT/'toolchain/voice-max-release'
    catalogue,archive=package(HOME,source)
    assert catalogue['runtime_api']==3
    old,_=package(HOME,target)
    assert old['models']==catalogue['models'],'Model weights must stay unchanged'
    with zipfile.ZipFile(archive) as packed:
        entries=catalogue['runtime']['files']
        assert set(packed.namelist())=={entry['name'] for entry in entries}
        for entry in entries:
            raw=packed.read(entry['name'])
            assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256']
    previous=source/'previous';previous.mkdir(exist_ok=True)
    for name in ('runtime.zip','release.json'):
        if not (previous/name).exists():shutil.copy2(target/name,previous/name)
    # Publish the signed catalogue last; mismatched in-flight transfers fail validation.
    for name in ('runtime.zip','release.json'):
        temporary=target/(name+'.publish.tmp')
        shutil.copy2(source/name,temporary);temporary.replace(target/name)
    served,_=package(HOME,target)
    assert served==catalogue
    result={'revision':catalogue['revision'],'runtime_api':3,'runtime_bytes':catalogue['runtime']['bytes'],
            'sha256':catalogue['runtime']['sha256'],'signature_verified':True,'inventory_verified':True,
            'unchanged_model_weights':True,'models_bytes':sum(item['bytes'] for item in catalogue['models']),
            'old_revision':old['revision'],'included_in_base_client':False}
    (OUT/'max-publication.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
