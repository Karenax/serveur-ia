"""Apply the WireGuard migration while leaving the existing model running."""
import argparse
from html.parser import HTMLParser
import json
import subprocess
import urllib.request
from core import HOME,ROOT,PYTHON,HIDDEN,read_json,same_process
from remote import AccessStore
from wireguard_access import WireGuardAccess

class TokenParser(HTMLParser):
    token=''
    def handle_starttag(self,tag,attributes):
        attrs=dict(attributes)
        if tag=='meta' and attrs.get('name')=='launcher-token':self.token=attrs['content']

def main():
    args=argparse.ArgumentParser()
    args.add_argument('--public-host',required=True)
    args.add_argument('--port',type=int,default=51820)
    args.add_argument('--client-name')
    options=args.parse_args()
    access=WireGuardAccess(AccessStore())
    access.configure({'public_host':options.public_host,'listen_port':options.port})
    process=same_process(read_json(HOME/'interface.pid.json'))
    if process:
        if str(HOME/'app.py').lower() not in ' '.join(process.cmdline()).lower():
            raise ValueError('Le PID ne correspond pas à la console Qwen.')
        process.terminate();process.wait(timeout=10)
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',
                    str(ROOT/'Start-Interface-Qwen.ps1'),'-SansNavigateur'],check=True,creationflags=HIDDEN)
    parser=TokenParser()
    parser.feed(urllib.request.urlopen('http://127.0.0.1:8765',timeout=10).read().decode())
    def post(path,data):
        request=urllib.request.Request('http://127.0.0.1:8765'+path,json.dumps(data).encode(),
                    {'Content-Type':'application/json','X-Launcher-Token':parser.token})
        return json.load(urllib.request.urlopen(request,timeout=30))
    print(post('/api/remote/activate',{})['message'])
    if options.client_name:
        result=post('/api/remote/create-client',{'name':options.client_name})
        print('Client Windows :',HOME/'clients'/(result['id']+'.exe'))

if __name__=='__main__':main()
