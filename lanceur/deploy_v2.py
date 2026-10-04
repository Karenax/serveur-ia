"""Deploy the verified local build without stopping inference processes."""
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import psutil
from core import ROOT, HOME, HIDDEN, read_json, same_process, write_json
from operations import Operations, VERSION
from releases import status, repackage

def deploy(console_only=False):
    if not status(HOME)["verified"]:raise ValueError("Version compilée non vérifiée.")
    if not console_only:
        result=repackage(HOME)
        print(result['message'],flush=True)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open('http://127.0.0.1:8765/api/remote',timeout=15) as r: remote=json.load(r)
        if remote.get('active',0) or remote.get('queue',{}).get('active',0):
            raise RuntimeError('Une demande distante est active. Relancer ce script une fois la demande terminée.')
    except urllib.error.URLError: pass
    current=same_process(read_json(HOME/'interface.pid.json',{}))
    if current:
        if not any(str(HOME/'app.py').lower() == part.lower() for part in current.cmdline()):
            raise RuntimeError('Identité du processus de la console inattendue.')
        current.terminate()  # Only the console, never its detached model or supervisor.
        current.wait(timeout=15)
        time.sleep(2)
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Start-Interface-Qwen.ps1'),'-SansNavigateur','-PreserverEtatModele'],check=True,creationflags=HIDDEN)
    # Startup remains under the user's Windows identity, preserving DPAPI access.
    class Local: home=HOME
    ops=Operations(Local())
    with opener.open('http://127.0.0.1:8765/api/operations',timeout=15) as r:
        state=json.load(r)
    if state.get('version')!=VERSION:raise RuntimeError('La console active ne correspond pas à la nouvelle version.')
    print('Console '+VERSION+' active. État du modèle et options de démarrage conservés.',flush=True)

if __name__=='__main__':deploy('--console-only' in sys.argv)
