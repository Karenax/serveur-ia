"""Compile-to-window verification against an isolated WireGuard/fake-model fixture."""
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from core import ROOT,HOME,HIDDEN,write_json
from test_remote import RemoteTests
from wireguard_access import Engine
from operations import VERSION
from signing import public

def main():
    fixture=RemoteTests();fixture.setUp();engine=None
    try:
        engine=Engine({'role':'server','wireguard':{'private_key':fixture.wireguard.vault()['private_key']},'listen_port':0,'upstream_port':fixture.gateway.server_port,'peers':fixture.wireguard.peers()})
        with tempfile.TemporaryDirectory(dir=ROOT/'client-qwen') as folder:
            home=Path(folder);target=home/'Accès serveur Fred.exe'
            shutil.copyfile(ROOT/'client-qwen/dist/Accès serveur Fred.exe',target)
            profile={**fixture.profile,'version':VERSION,'protocol':3,'update_public_key':public(HOME)}
            profile['wireguard']={**profile['wireguard'],'endpoint':f'127.0.0.1:{engine.port}'}
            raw=json.dumps(profile).encode()
            with target.open('ab') as stream:stream.write(raw+struct.pack('<I',len(raw))+b'QWENPROFILE1')
            result=home/'result.json'
            process=subprocess.Popen([str(target),'--ui-self-test','--result',str(result)],creationflags=HIDDEN)
            try:code=process.wait(timeout=60)
            except subprocess.TimeoutExpired:
                import psutil
                parent=psutil.Process(process.pid);children=parent.children(recursive=True)
                for child in reversed(children):child.kill()
                parent.kill();psutil.wait_procs(children+[parent],timeout=10)
                raise
            if code or not result.is_file():raise RuntimeError('La fenêtre compilée n’a pas confirmé son contrôle.')
            value=json.loads(result.read_text(encoding='utf-8'))
            if value.get('title')!='Accès serveur Fred' or not value.get('ok'):raise RuntimeError('Nom ou interface cliente incorrects.')
            write_json(HOME/'native-ui-fred.json',value)
            print(json.dumps(value,ensure_ascii=False))
    finally:
        if engine:engine.close()
        fixture.tearDown()

if __name__=='__main__':main()
