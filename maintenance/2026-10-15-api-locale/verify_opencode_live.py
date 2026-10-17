"""Installed OpenCode 2, isolated config/data, real Fred local API and cloud model."""
import base64
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'client-qwen'),str(ROOT/'lanceur')]
import client
import app_integrations
import releases
from hermes_service import installation, child_environment, prepare_runtime
from connection_settings import HTTPS_ENDPOINT


def main():
    cli=Path(os.environ['APPDATA'])/'ai.opencode.desktop/cli/2.0.29-x64/opencode-cli.exe'
    remote=client.Remote(releases.profile(ROOT/'lanceur/clients/0402a094eeb03bdc.exe'),endpoint=HTTPS_ENDPOINT)
    native_open=remote.open
    def capture(path,data=None,request_id=None):
        if path=='/v1/chat/completions':
            body=json.loads(data)
            print('Third-party request fields: '+json.dumps(sorted(body)),flush=True)
        return native_open(path,data,request_id)
    remote.open=capture
    key=secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix='fred-opencode-live-') as directory:
        root=Path(directory)
        with patch.object(client,'settings_path',return_value=root/'fred-settings.dpapi'):
            local=client.serve_local(remote,key,0)
        threading.Thread(target=local.serve_forever,daemon=True).start()
        process=None
        try:
            with remote.open('/v1/models') as response:catalog=json.load(response)
            model=next(row['id'] for row in catalog['data'] if row['name']=='gpt-6-luna')
            runtime=installation();hermes_home=root/'hermes';hermes_home.mkdir()
            prepare_runtime(hermes_home,runtime)
            hermes_config=json.dumps({'model':{'provider':'serveur-fred','default':model},
                'platform_toolsets':{'cli':[]},'reasoning_effort':'none','agent':{'max_turns':1}})
            (hermes_home/'config.yaml').write_text(app_integrations.hermes_text(hermes_config,
                f'http://127.0.0.1:{local.server_port}/v1',key,model),encoding='utf-8')
            hermes_result=subprocess.run([str(runtime['python']),'-m','hermes_cli.main','chat','-q',
                'Réponds uniquement HERMES_API_OK sans appeler d’outil.','--provider','serveur-fred','-m',model,'--max-turns','1'],
                cwd=runtime['source'],env=child_environment(hermes_home,runtime),capture_output=True,
                text=True,encoding='utf-8',errors='replace',timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
            if hermes_result.returncode or 'HERMES_API_OK' not in hermes_result.stdout:
                diagnostic=(hermes_result.stderr+hermes_result.stdout)[-3500:]
                for secret in (key,remote.token):diagnostic=diagnostic.replace(secret,'[redacted]')
                print(diagnostic);raise AssertionError('Native Hermes answer not confirmed')
            print('Native Hermes: HERMES_API_OK',flush=True)
            config=root/'config/opencode';config.mkdir(parents=True)
            (config/'opencode.json').write_text(app_integrations.opencode_text(json.dumps({'model':'serveur-fred/'+model}),
                f'http://127.0.0.1:{local.server_port}/v1',key,model),encoding='utf-8')
            env={k:v for k,v in os.environ.items() if not k.startswith(('OPENCODE_','XDG_'))}
            env.update(OPENCODE_PASSWORD=secrets.token_urlsafe(32),OPENCODE_TEST_HOME=str(root),
                LOCALAPPDATA=str(root/'local'),APPDATA=str(root/'roaming'),XDG_CONFIG_HOME=str(root/'config'),
                XDG_DATA_HOME=str(root/'data'),XDG_CACHE_HOME=str(root/'cache'),XDG_STATE_HOME=str(root/'state'))
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            server=f'http://127.0.0.1:{port}'
            auth='Basic '+base64.b64encode(('opencode:'+env['OPENCODE_PASSWORD']).encode()).decode()
            with (root/'server.log').open('w',encoding='utf-8') as log:
                process=subprocess.Popen([str(cli),'serve','--hostname','127.0.0.1','--port',str(port)],
                    cwd=root,env=env,stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
                deadline=time.monotonic()+30
                while True:
                    try:
                        with urllib.request.urlopen(urllib.request.Request(server+'/api/config',headers={'Authorization':auth}),timeout=2):break
                    except OSError:
                        if time.monotonic()>deadline:raise
                        time.sleep(.2)
                started=time.monotonic()
                result=subprocess.run([str(cli),'run','--model','serveur-fred/'+model,'--title','Fred real API check',
                    '--format','json','Réponds uniquement OPENCODE_API_OK sans appeler d’outil.','--server',server],
                    cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,
                    creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode:
                    diagnostic=(result.stderr+result.stdout)[-3500:]
                    for secret in (key,env['OPENCODE_PASSWORD'],remote.token):diagnostic=diagnostic.replace(secret,'[redacted]')
                    print(diagnostic)
                    raise AssertionError('OpenCode command failed')
                assert 'OPENCODE_API_OK' in result.stdout,'OpenCode answer not confirmed'
                report={'passed':True,'opencode_version':'2.0.29','model':'gpt-6-luna','transport':'https',
                    'real_model':True,'local_fred_api':True,'personal_opencode_config_untouched':True,
                    'native_hermes_passed':True,'personal_hermes_config_untouched':True,
                    'seconds':round(time.monotonic()-started,2)}
                (OUT/'opencode-live.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
                print(json.dumps(report))
        finally:
            if process is not None:process.terminate();process.wait(timeout=10)
            local.shutdown();local.server_close();remote.close()


if __name__=='__main__':main()
