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

def validate_endpoint(value):
    if not isinstance(value,str) or len(value)>300:
        raise ValueError('Adresse attendue : IP-ou-DNS:port, par exemple 192.168.1.40:51820.')
    value=value.strip()
    try:
        host,port=value.rsplit(':',1)
        if not port.isdecimal() or not 1<=int(port)<=65535:
            raise ValueError()
        if host.startswith('[') and host.endswith(']'):
            address=ipaddress.ip_address(host[1:-1])
            if address.version!=6:raise ValueError()
        elif not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?',host):
            raise ValueError()
        elif ':' in host:
            raise ValueError()
    except (ValueError,TypeError):
        raise ValueError('Adresse attendue : IP-ou-DNS:port, sans http:// ni chemin /v1.')
    return host+':'+str(int(port))

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

def validate_profile(profile):
    if not isinstance(profile,dict):raise ValueError('Profil client invalide.')
    if profile.get('url')!='wireguard://10.77.0.1:8766':raise ValueError('Adresse API privée invalide.')
    if profile.get('protocol', 1) not in (1, 2, 3):
        raise ValueError('Ce profil nécessite une version plus récente d’Accès serveur Fred.')
    if profile.get('transport') != 'wireguard':
        raise ValueError('Cet accès doit utiliser WireGuard.')
    if not isinstance(profile.get('token'),str) or not re.fullmatch(r'qwen_[0-9a-f]{16}_[A-Za-z0-9_-]{43}',profile['token']):
        raise ValueError('Clé API serveur invalide.')
    wg = profile.get('wireguard')
    if not isinstance(wg,dict):
        raise ValueError('Profil WireGuard absent.')
    for field in ('private_key','server_public_key','preshared_key'):
        try:
            value=base64.b64decode(wg[field],validate=True)
            if len(value)!=32: raise ValueError()
        except (KeyError,TypeError,ValueError):
            raise ValueError('Clé WireGuard invalide.')
    try:
        address=ipaddress.ip_interface(wg['address'])
        if address.network.prefixlen!=32 or address.ip not in ipaddress.ip_network('10.77.0.0/24') or int(str(address.ip).split('.')[-1]) not in range(2,255):
            raise ValueError()
        validate_endpoint(wg['endpoint'])
    except (KeyError,TypeError,ValueError):
        raise ValueError('Adresse du tunnel ou du serveur invalide.')
    routes=profile.get('local_routes',[])
    if not isinstance(routes,list) or len(routes)>16:
        raise ValueError('Adresses locales du serveur invalides.')
    try:
        for route in routes:
            endpoint=validate_endpoint(route['endpoint'])
            host,_=endpoint.rsplit(':',1)
            address=ipaddress.ip_address(host)
            network=ipaddress.ip_network(route['network'])
            if address.version!=4 or not address.is_private or address.is_loopback or address not in network:
                raise ValueError()
    except (ValueError,TypeError,KeyError):
        raise ValueError('Adresses locales du serveur invalides.')
    return profile

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
