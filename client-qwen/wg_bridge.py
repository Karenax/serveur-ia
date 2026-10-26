from kiara_shared.profiles import validate_endpoint, validate_profile
"""WireGuard in a child process with an in-memory network stack; no OS adapter."""
import base64
import ipaddress
import json
import hashlib
import os
from pathlib import Path
import queue
import re
import secrets
import socket
import subprocess
import sys
import threading
import tempfile
from file_lock import locked

def bridge_executable():
    """Keep Windows firewall identity stable across one-file client launches."""
    source=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/'wireguard-bridge.exe'
    if not source.is_file():
        raise ValueError('Le moteur WireGuard intégré est absent.')
    if not getattr(sys,'frozen',False):
        return source
    data=source.read_bytes()
    digest=hashlib.sha256(data).hexdigest()
    directory=Path(os.environ['LOCALAPPDATA'])/'AccesServeurFred'/'WireGuard'/digest
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/'wireguard-bridge.exe'
    with locked(target):
        if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest()==digest:
            return target
        descriptor,name=tempfile.mkstemp(prefix='bridge-',suffix='.tmp',dir=directory)
        try:
            with os.fdopen(descriptor,'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name,target)
        finally:
            if os.path.exists(name):os.unlink(name)
    return target


def local_ipv4():
    try:return {value[4][0] for value in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET)}
    except OSError:return set()

def connection_candidates(profile,addresses=None):
    """Prefer the server's LAN address only when this PC belongs to its subnet."""
    addresses=local_ipv4() if addresses is None else addresses
    local=[]
    for route in profile.get('local_routes',[]):
        network=ipaddress.ip_network(route['network'])
        endpoint=route['endpoint'];host,port=endpoint.rsplit(':',1)
        if host in addresses:local.append('127.0.0.1:'+port)
        if any(ipaddress.ip_address(value) in network for value in addresses):local.append(endpoint)
    return list(dict.fromkeys([*local,profile['wireguard']['endpoint']]))


class Bridge:
    def __init__(self,profile):
        validate_profile(profile)
        executable=bridge_executable()
        self.key=secrets.token_urlsafe(32)
        self.process=subprocess.Popen([str(executable)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL,creationflags=0x08000000)
        try:
            self.process.stdin.write(json.dumps({'wireguard':profile['wireguard'],'api_token':profile['token'],'bridge_token':self.key}).encode()+b'\n')
            self.process.stdin.flush()
            events=queue.Queue()
            threading.Thread(target=lambda:events.put(self.process.stdout.readline()),daemon=True).start()
            state=json.loads(events.get(timeout=20))
            if not state.get('ready') or not isinstance(state.get('port'),int) or not 1<=state['port']<=65535:
                raise ValueError(state.get('error','Le moteur WireGuard ne démarre pas.'))
            self.url=f"http://127.0.0.1:{state['port']}"
        except (OSError,ValueError,queue.Empty) as error:
            self.close()
            raise ValueError('WireGuard ne démarre pas : vérifier l’adresse du serveur et son DNS.') from error

    def status(self,opener):
        import urllib.request
        request=urllib.request.Request(self.url+'/bridge/status',headers={'X-Qwen-Bridge':self.key})
        try:
            with opener.open(request,timeout=3) as response:return json.load(response)
        except (OSError,ValueError):return {}

    def close(self):
        if self.process.stdin and not self.process.stdin.closed:
            try:self.process.stdin.close()
            except OSError:pass
        try:self.process.wait(timeout=4)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=4)
        self.process.stdout.close()
