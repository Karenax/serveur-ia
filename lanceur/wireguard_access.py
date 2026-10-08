"""Autonomous WireGuard server and per-recipient portable clients."""
import atexit
import base64
import json
import ipaddress
from pathlib import Path
import queue
import re
import secrets
import socket
import subprocess
import threading
import psutil
from core import HOME,ROOT,HIDDEN,read_json,write_json
from wg_crypto import keypair,protect,private_directory

SERVER_IP='10.77.0.1'
UDP_PORT=51820
ENGINE=ROOT/'client-qwen/wireguard-bridge.exe'

def network_routes(port):
    routes=[]
    for values in psutil.net_if_addrs().values():
        for value in values:
            if value.family!=socket.AF_INET or not value.netmask:continue
            address=ipaddress.ip_address(value.address)
            if address.is_loopback or address.is_link_local or not address.is_private:continue
            route={'endpoint':f'{address}:{port}','network':str(ipaddress.ip_network(f'{address}/{value.netmask}',strict=False))}
            if route not in routes:routes.append(route)
    return routes[:16]

def validate_settings(data):
    host=data.get('public_host','').strip()
    if not host or len(host)>253 or not re.fullmatch(r'[A-Za-z0-9.:-]+',host) or host.startswith('-'):
        raise ValueError('Indiquer l’IP publique fixe ou le nom DNS du serveur, sans protocole ni port.')
    port=data.get('listen_port',UDP_PORT)
    if isinstance(port,bool) or not isinstance(port,int) or not 1<=port<=65535:
        raise ValueError('Port UDP attendu entre 1 et 65535.')
    return {'public_host':host,'listen_port':port}

class Engine:
    def __init__(self,config,executable=ENGINE):
        self.lock=threading.RLock();self.events=queue.Queue()
        self.process=subprocess.Popen([str(executable)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,
                                      stderr=subprocess.DEVNULL,creationflags=HIDDEN)
        def read():
            for line in self.process.stdout:
                try:self.events.put(json.loads(line))
                except ValueError:pass
            self.events.put({'error':'Le moteur WireGuard s’est arrêté.'})
        self.reader=threading.Thread(target=read,daemon=True);self.reader.start()
        try:
            self.send(config)
            status=self.events.get(timeout=20)
            if not status.get('ready'):raise ValueError(status.get('error','Démarrage WireGuard impossible.'))
            self.port=status['udp_port']
        except (OSError,ValueError,KeyError,queue.Empty):
            self.close()
            raise ValueError('Le serveur WireGuard ne démarre pas. Vérifier si son port UDP est déjà utilisé.')
    def send(self,data):
        self.process.stdin.write(json.dumps(data).encode()+b'\n');self.process.stdin.flush()
    def update(self,peers):
        with self.lock:
            try:
                self.send({'peers':peers})
                result=self.events.get(timeout=10)
                if not result.get('peers_updated'):raise ValueError()
            except (OSError,ValueError,queue.Empty):
                raise ValueError('Mise à jour du tunnel impossible. Désactiver puis réactiver WireGuard.')
    def running(self):return self.process.poll() is None
    def close(self):
        with self.lock:
            try:self.process.stdin.close()
            except OSError:pass
            try:self.process.wait(timeout=4)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=4)
            self.reader.join(timeout=1)
            self.process.stdout.close()

class WireGuardAccess:
    def __init__(self,store,home=HOME):
        self.store=store;self.home=Path(home)
        self.settings_path=self.home/'wireguard.json'
        self.directory=self.home/'wireguard-prive'
        self.vault_path=self.directory/'secrets.dpapi'
        self.lock=threading.RLock();self.engine=None
        if not self.settings_path.exists():write_json(self.settings_path,{'public_host':'','listen_port':UDP_PORT,'public_key':''})
        atexit.register(self.close)

    def settings(self):return read_json(self.settings_path)
    def vault(self):
        if not self.vault_path.exists():
            private_directory(self.directory)
            private,public=keypair()
            values=self.settings();values['public_key']=public;write_json(self.settings_path,values)
            self.save_vault({'private_key':private,'peers':{}})
        return json.loads(protect(self.vault_path.read_bytes(),decrypt=True))
    def save_vault(self,data):
        temporary=self.vault_path.with_suffix('.tmp')
        temporary.write_bytes(protect(json.dumps(data).encode()))
        temporary.replace(self.vault_path)
    def configure(self,data):
        with self.lock:
            old=self.settings();new=validate_settings(data)
            if self.engine and self.engine.running() and old['listen_port']!=new['listen_port']:
                raise ValueError('Désactiver WireGuard avant de changer le port UDP.')
            values={**old,**new};write_json(self.settings_path,values)
            self.vault()
            self.store.configure({'enabled':self.store.metadata()['enabled'],'url':'wireguard://10.77.0.1:8766'})
            return self.status()
    def peers(self):
        vault=self.vault()
        return [{'public_key':c['wireguard_public_key'],'address':c['address'],
                 'preshared_key':vault['peers'][c['id']]} for c in self.store.metadata()['clients']
                if not c['revoked'] and c.get('wireguard_public_key') and c['id'] in vault['peers']]
    def new_peer(self,access):
        with self.lock:
            settings=validate_settings(self.settings());vault=self.vault()
            allocated={c.get('address') for c in self.store.metadata()['clients']}
            address=next((f'10.77.0.{n}/32' for n in range(2,255) if f'10.77.0.{n}/32' not in allocated),None)
            if address is None:raise ValueError('Toutes les adresses clients sont occupées.')
            private,public=keypair();psk=base64.b64encode(secrets.token_bytes(32)).decode()
            vault['peers'][access['id']]=psk;self.save_vault(vault)
            self.store.set_peer(access['id'],public,address)
            host=settings['public_host'];host=f'[{host}]' if ':' in host else host
            return {'transport':'wireguard','url':'wireguard://10.77.0.1:8766','token':access['token'],
                    'local_routes':network_routes(settings['listen_port']),
                    'wireguard':{'private_key':private,'server_public_key':self.settings()['public_key'],
                                 'preshared_key':psk,'address':address,'endpoint':f"{host}:{settings['listen_port']}"}}
    def create_client(self,name,model):
        with self.lock:
            self.vault();private_directory(self.home/'clients')
            result=self.store.executable(name,model,self.new_peer)
            if self.engine and self.engine.running():
                try:self.engine.update(self.peers())
                except ValueError:
                    self.store.revoke(result['id'])
                    raise
            return {**result,'message':'EXE personnel prêt. Remettez-le à son destinataire : aucun login requis.'}
    def activate(self,gateway_ready=True):
        with self.lock:
            if not gateway_ready:raise ValueError('La passerelle IA locale ne fonctionne pas sur le port 8766.')
            settings=validate_settings(self.settings())
            if self.engine and self.engine.running():self.engine.update(self.peers())
            else:
                self.engine=Engine({'role':'server','wireguard':{'private_key':self.vault()['private_key']},
                                    'listen_port':settings['listen_port'],'upstream_port':8766,'peers':self.peers()})
            self.store.configure({'enabled':True,'url':'wireguard://10.77.0.1:8766'})
            return {'message':f"WireGuard actif en UDP {settings['listen_port']}. La box et le pare-feu Windows doivent autoriser ce port."}
    def revoke(self,identity):
        with self.lock:
            self.store.revoke(identity)
            if self.engine and self.engine.running():self.engine.update(self.peers())
            return {'message':'Accès personnel révoqué dans l’API et dans le tunnel WireGuard.'}
    def delete(self,identity):
        with self.lock:
            result=self.store.delete(identity)
            if self.engine and self.engine.running():self.engine.update(self.peers())
            return result
    def deactivate(self):
        with self.lock:
            self.store.configure({'enabled':False,'url':self.store.metadata()['url']})
            self.close()
            return {'message':'Accès WireGuard arrêté.'}
    def close(self):
        if self.engine:self.engine.close();self.engine=None
    def status(self):
        values=self.settings();running=bool(self.engine and self.engine.running())
        return {**values,'running':running,'compiled':ENGINE.is_file(),
                'firewall':read_json(self.home/'wireguard-fw.json',{'state':'unknown'}),
                'message':f"WireGuard écoute en UDP {values['listen_port']}." if running else 'WireGuard est arrêté.',
                'api_address':'wireguard://10.77.0.1:8766'}

def firewall(home=HOME):
    settings=read_json(Path(home)/'wireguard.json')
    port=validate_settings(settings)['listen_port']
    helper=HOME/'Autoriser-WireGuard.ps1'
    subprocess.Popen(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(helper),
                      '-Port',str(port),'-Program',str(ENGINE),'-ResultPath',str(Path(home)/'wireguard-fw.json')],creationflags=HIDDEN)
    return {'message':'Vérification de l’autorisation Windows. Une validation administrateur apparaît seulement si la règle WireGuard doit être créée ou modifiée.'}
