"""Real disposable WireGuard tunnel: saturated HTTP streams and temporary UDP loss."""
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import socket
import sys
import threading
import time
import unittest
import client
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'lanceur'))
from wg_crypto import keypair
from wireguard_access import Engine


class WireGuardResilienceTests(unittest.TestCase):
    def test_controls_survive_four_streams_and_one_second_udp_outage(self):
        binary=Path(__file__).with_name('wireguard-bridge.exe')
        if not binary.exists():self.skipTest('Build WireGuard first.')
        release=threading.Event();stop=threading.Event();drop=threading.Event()
        private,public=keypair();other_private,other_public=keypair();psk,_=keypair()
        api_token='qwen_'+'0'*16+'_'+secrets.token_urlsafe(32)
        class API(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def do_GET(self):self.respond()
            def do_POST(self):
                self.rfile.read(int(self.headers.get('Content-Length',0)));self.respond()
            def respond(self):
                if self.headers.get('Authorization')!='Bearer '+api_token:
                    self.send_error(401);return
                if self.path=='/v1/voice/speech':
                    self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
                    self.wfile.write(b': stream ready\n\n');self.wfile.flush()
                    release.wait(20)
                    try:self.wfile.write(b'data: {"done":true}\n\n');self.wfile.flush()
                    except OSError:pass
                    return
                body=json.dumps({'data':[{'id':'fixture'}],'cancelled':True}).encode()
                self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        api=ThreadingHTTPServer(('127.0.0.1',0),API)
        threading.Thread(target=api.serve_forever,daemon=True).start()
        engine=None;remote=None;relay=None;relay_thread=None
        try:
            engine=Engine({'role':'server','wireguard':{'private_key':private},'listen_port':0,
                           'upstream_port':api.server_port,
                           'peers':[{'public_key':other_public,'preshared_key':psk,'address':'10.77.0.2/32'}]})
            relay=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);relay.bind(('127.0.0.1',0));relay.settimeout(.1)
            def forward():
                recipient=None
                while not stop.is_set():
                    try:data,address=relay.recvfrom(65536)
                    except socket.timeout:continue
                    except OSError:break
                    if address[1]==engine.port:destination=recipient
                    else:recipient=address;destination=('127.0.0.1',engine.port)
                    if destination and not drop.is_set():
                        try:relay.sendto(data,destination)
                        except OSError:break
            relay_thread=threading.Thread(target=forward,daemon=True);relay_thread.start()
            profile={'url':'wireguard://10.77.0.1:8766','transport':'wireguard','token':api_token,'protocol':4,
                     'wireguard':{'private_key':other_private,'server_public_key':public,'preshared_key':psk,
                                  'address':'10.77.0.2/32','endpoint':f'127.0.0.1:{relay.getsockname()[1]}'}}
            remote=client.Remote(profile)
            # Receiving headers occupies all four data connections until bodies end.
            with ThreadPoolExecutor(max_workers=4) as pool:
                held=list(pool.map(lambda _:remote.open('/v1/voice/speech',b'{}'),range(4)))
            try:
                start=time.monotonic()
                for route in ('/v1/models','/v1/status','/v1/cancel','/v1/voice/cancel'):
                    with remote.open(route,b'{}' if route.endswith('/cancel') else None) as response:
                        self.assertTrue(json.load(response)['cancelled'])
                self.assertLess(time.monotonic()-start,4,'Control traffic must bypass occupied data connections.')
                drop.set();timer=threading.Timer(1,drop.clear);timer.start()
                try:
                    start=time.monotonic()
                    with remote.open('/v1/models') as response:self.assertEqual('fixture',json.load(response)['data'][0]['id'])
                    self.assertLess(time.monotonic()-start,10)
                finally:drop.clear();timer.join(2)
                release.set()
                for response in held:self.assertIn(b'"done":true',response.read())
                self.assertEqual(1,remote.bridge_starts)
                self.assertTrue(remote.bridge.status(remote.opener)['handshake'])
            finally:
                release.set()
                for response in held:response.close()
        finally:
            release.set();stop.set()
            if remote:remote.close()
            if relay:relay.close()
            if relay_thread:relay_thread.join(2)
            if engine:engine.close()
            api.shutdown();api.server_close()


if __name__=='__main__':unittest.main(verbosity=2)
