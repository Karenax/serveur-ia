"""Boundaries of the real Windows service: integrity, cancel, mic lifetime and fencing."""
import hashlib,json,sys,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'client-qwen'))
from local_voice import VoiceService

class Response:
    status=200;url='https://model.test/download';headers={}
    def __init__(self,data):self.data=data;self.offset=0
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def read(self,count):data=self.data[self.offset:self.offset+count];self.offset+=len(data);return data
class Engine:
    def __init__(self,*args):self.phase='listening';self.destroyed=False
    def status(self):return {'phase':self.phase,'text':'Bonjour','seconds':1}
    def feed(self,data):pass
    def stop(self):self.phase='ready'
    def cancel(self):self.phase='cancelled'
    def close(self):self.destroyed=True
class Capture:
    instances=[]
    def __init__(self):self.closed=False;self.instances.append(self)
    def read(self):time.sleep(.01);return b'\0'*3200
    def close(self):self.closed=True
class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.root=Path(self.folder.name);self.resources=self.root/'resources';self.resources.mkdir();self.data=b'Pinned model test content';self.spec={'bytes':len(self.data),'sha256':hashlib.sha256(self.data).hexdigest(),'url':'https://model.test/download'};(self.resources/'model.json').write_text(json.dumps(self.spec));self.service=VoiceService(self.resources,self.root/'cache',capture_factory=Capture);Capture.instances=[]
    def tearDown(self):self.service.close();self.folder.cleanup()
    def wait(self,phase):
        until=time.monotonic()+3
        while time.monotonic()<until:
            state=self.service.status()
            if state['phase']==phase:return state
            time.sleep(.01)
        self.fail(str(self.service.status()))
    def install(self):
        response=Response(self.data)
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=response;self.service.action({'action':'install'});self.wait('idle')
        self.service.thread.join(1)
    def test_hash_checked_before_publish_and_no_network_during_dictation(self):
        self.install();self.assertEqual(self.service.model.read_bytes(),self.data)
        with patch('local_voice.NativeEngine',Engine),patch('urllib.request.build_opener',side_effect=AssertionError('Audio network access')):
            state=self.service.action({'action':'start'});self.wait('listening');time.sleep(.03)
            self.service.action({'action':'stop','session':state['session']});self.wait('ready');self.service.thread.join(1)
            self.assertTrue(Capture.instances[0].closed);self.assertEqual(self.service.status()['text'],'Bonjour')
    def test_corruption_cannot_be_loaded(self):
        self.install();self.service.model.write_bytes(b'X'*len(self.data))
        with patch('local_voice.NativeEngine',side_effect=AssertionError('Corrupt model loaded')):self.service.action({'action':'start'});self.wait('error')
    def test_corrupt_download_preserves_existing_model(self):
        self.service.cache.mkdir();self.service.model.write_bytes(b'OLD')
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=Response(b'X'*len(self.data));self.service.action({'action':'install'});self.wait('error')
        self.assertEqual(self.service.model.read_bytes(),b'OLD');self.assertFalse(self.service.model.with_suffix('.part').exists())
    def test_stale_stop_cannot_cancel_current_session(self):
        self.install()
        with patch('local_voice.NativeEngine',Engine):
            current=self.service.action({'action':'start'});self.wait('listening')
            with self.assertRaises(ValueError):self.service.action({'action':'stop','session':'stale'})
            self.assertEqual(self.service.status()['phase'],'listening');self.service.action({'action':'cancel','session':current['session']});self.wait('cancelled')
    def test_command_cannot_inject_paths_or_models(self):
        for value in ({'action':'start','path':'secret'},{'action':'start','model':'base'},{'action':'delete'},[],{'action':'stop','session':''}):
            with self.assertRaises(ValueError):self.service.action(value)
    def test_capture_failure_keeps_error_and_releases_engine(self):
        self.install();created=[]
        def native(*args):value=Engine();created.append(value);return value
        def capture():raise OSError('Microphone denied')
        self.service.capture_factory=capture
        with patch('local_voice.NativeEngine',native):self.service.action({'action':'start'});self.wait('error');self.service.thread.join(1)
        self.assertTrue(created[0].destroyed);self.assertEqual(self.service.status()['message'],'Microphone denied')
    def test_resume_range_and_hash(self):
        self.service.cache.mkdir();self.service.model.with_suffix('.part').write_bytes(self.data[:5]);response=Response(self.data[5:]);response.status=206;response.headers={'Content-Range':f'bytes 5-{len(self.data)-1}/{len(self.data)}'}
        with patch('urllib.request.build_opener') as opener:
            opener.return_value.open.return_value=response;self.service.action({'action':'install'});self.wait('idle');self.assertEqual(opener.return_value.open.call_args.args[0].get_header('Range'),'bytes=5-')
        self.assertEqual(self.service.model.read_bytes(),self.data)
    def test_reject_bad_resume(self):
        self.service.cache.mkdir();self.service.model.with_suffix('.part').write_bytes(self.data[:5]);response=Response(self.data[5:]);response.status=206;response.headers={'Content-Range':'bytes 0-4/5'}
        with patch('urllib.request.build_opener') as opener:opener.return_value.open.return_value=response;self.service.action({'action':'install'});self.wait('error')
        self.assertFalse(self.service.model.exists())

if __name__=='__main__':unittest.main(verbosity=2)
