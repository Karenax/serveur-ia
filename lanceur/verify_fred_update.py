"""Actual legacy 3.1 helper -> current Fred build, native acknowledgement, isolated keys."""
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import time
import psutil
from core import ROOT,HOME,HIDDEN,write_json,read_json
from operations import VERSION
from signing import public
from releases import profile,digest
from test_remote import RemoteTests
from wireguard_access import Engine
from wg_crypto import protect,private_directory

def main():
    fixture=RemoteTests();fixture.setUp();engine=None;owned=[]
    legacy=ROOT/'client-qwen/dist/QwenClient.exe'
    if not legacy.is_file():raise RuntimeError('Binaire 3.1 conservé nécessaire pour le contrôle de migration.')
    try:
        engine=Engine({'role':'server','wireguard':{'private_key':fixture.wireguard.vault()['private_key']},'listen_port':0,'upstream_port':fixture.gateway.server_port,'peers':fixture.wireguard.peers()})
        with tempfile.TemporaryDirectory(dir=ROOT/'client-qwen') as folder:
            home=Path(folder);private_directory(home);work=home/'qwen-update-native';work.mkdir()
            target=home/'QwenClient.exe';helper=work/'QwenUpdate.exe';source=work/'QwenClient.base.exe'
            values={**fixture.profile,'version':'3.1.0','protocol':3,'update_public_key':public(HOME)}
            values['wireguard']={**values['wireguard'],'endpoint':f'127.0.0.1:{engine.port}'}
            raw=json.dumps(values).encode();shutil.copyfile(legacy,target)
            with target.open('ab') as stream:stream.write(raw+struct.pack('<I',len(raw))+b'QWENPROFILE1')
            previous=digest(target);shutil.copyfile(target,helper);shutil.copyfile(ROOT/'client-qwen/dist/Accès serveur Fred.exe',source)
            release=read_json(ROOT/'client-qwen/dist/release.json')
            plan=work/'plan.dpapi';plan.write_bytes(protect(json.dumps({'target':str(target),'source':str(source),'profile':values,'release':release,'pid':99999999,'created':0}).encode()))
            import os
            environment={**os.environ,'LOCALAPPDATA':str(home/'local-data')}
            process=subprocess.Popen([str(helper),'--apply-update',str(plan)],env=environment,creationflags=HIDDEN)
            try:
                deadline=time.monotonic()+70
                while time.monotonic()<deadline:
                    for entry in psutil.process_iter(['pid','exe','create_time']):
                        try:
                            if entry.info['exe'] and Path(entry.info['exe']).resolve()==target.resolve() and all(p.pid!=entry.pid for p in owned):owned.append(entry)
                        except (OSError,psutil.Error):pass
                    result=read_json(home/'QwenClient-update-result.json',{})
                    if result.get('ok'):break
                    if process.poll() is not None:raise RuntimeError('Le helper a terminé sans confirmation de la fenêtre.')
                    if (work/'error.txt').exists():raise RuntimeError((work/'error.txt').read_text(encoding='utf-8'))
                    time.sleep(.1)
                else:raise RuntimeError('Migration native sans confirmation après 70 secondes.')
                process.wait(timeout=15)
                installed=profile(target)
                checks={'from':'3.1.0','to':installed['version'],'native_acknowledged':read_json(work/'started.json',{}).get('ready',False),
                        'keys_preserved':installed['token']==values['token'] and installed['wireguard']==values['wireguard'],
                        'previous_preserved':digest(home/'QwenClient.previous-3.1.0.exe')==previous,
                        'plan_removed':not plan.exists(),'profile_version_matches':installed['version']==VERSION}
                assert checks['keys_preserved'] and checks['native_acknowledged'] and checks['previous_preserved'] and checks['profile_version_matches']
                write_json(HOME/'native-update-fred.json',checks);print(json.dumps(checks))
            finally:
                if process.poll() is None:
                    parent=psutil.Process(process.pid);owned.extend(parent.children(recursive=True));owned.append(parent)
                targets={p.pid:p for p in owned}
                for parent in list(targets.values()):
                    try:targets.update({p.pid:p for p in parent.children(recursive=True)})
                    except psutil.Error:pass
                for item in reversed(list(targets.values())):
                    try:item.kill()
                    except psutil.Error:pass
                psutil.wait_procs(list(targets.values()),timeout=10)
    finally:
        if engine:engine.close()
        fixture.tearDown()

if __name__=='__main__':main()
