"""Create an isolated voice fixture reusing the existing transport harness."""
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
TESTS=ROOT/'lanceur/web/tests'
fixture=(TESTS/'lots6_8_fixture.py').read_text(encoding='utf-8')
fixture=fixture.replace("ROOT/'toolchain/releases-staging/windows-3.5.18/wireguard-bridge.exe'","ROOT/'client-qwen/wireguard-bridge.exe'")
fixture=fixture.replace("controller = Controller(home, include_legacy=False)","controller = Controller(home, include_legacy=False)\n        controller.voice.configure(True)\n        import time\n        deadline=time.monotonic()+60\n        while not controller.voice.ready.is_set() and time.monotonic()<deadline:time.sleep(.1)\n        assert controller.voice.ready.is_set(),controller.voice.status()")
fixture=fixture.replace('controller.wireguard.close()','controller.wireguard.close();controller.voice.close()')
fixture=fixture.replace('admin = serve(0,controller)',"from core import available_port\n        available_port('127.0.0.1',24800)\n        admin = serve(24800,controller)")
extra='''
class ConversationModel(FakeModel):
    def do_POST(self):
        if self.path!='/v1/chat/completions':return super().do_POST()
        import time
        data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        self.captured.append((dict(self.headers),data))
        self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
        try:
            for text in ['La livraison du projet Orion est prévue le 23 novembre. ']+['Je continue à expliquer la réponse et les documents. ']*30:
                self.wfile.write(('data: '+json.dumps({'choices':[{'delta':{'content':text}}]})+'\\n\\n').encode());self.wfile.flush();time.sleep(.15)
            self.wfile.write(b'data: [DONE]\\n\\n')
        except (OSError,BrokenPipeError):pass

FakeModel=ConversationModel
'''
fixture=fixture.replace("if __name__=='__main__':main()",extra+"\nif __name__=='__main__':main()")
fixture=fixture.replace("if __name__=='__main__': main()",extra+"\nif __name__=='__main__':main()")
assert 'class ConversationModel' in fixture
(TESTS/'conversation_fixture.py').write_text(fixture,encoding='utf-8')
source=(TESTS/'voice_ui.mjs').read_text(encoding='utf-8')
prefix=source.split('try{\n await cdp')[0]
prefix=prefix.replace("voix-small-20261011/browser","conversation-windows-20261011/browser").replace("lots6_8_fixture.py","conversation_fixture.py")
prefix=prefix.replace('awaitPromise:true','awaitPromise:true,userGesture:true')
(TESTS/'conversation_ui.mjs').write_text(prefix+(TESTS/'conversation_ui_body.mjs').read_text(encoding='utf-8'),encoding='utf-8')
