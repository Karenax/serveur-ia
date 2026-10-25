import sys,json,os,hashlib,queue,subprocess,threading,time,base64,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'client-qwen'),str(ROOT/'client-voice'),str(ROOT/'lanceur')]
from max_installation import MaxInstallation
from prepare_max_pack import Release
OUT=Path(__file__).resolve().parent
HOME=ROOT/'toolchain/max-french-pack-qa'
OLD=ROOT/'toolchain/voice-max-optional-qa/packs/vulkan-q4-dcfa1858931e003e'
class Runtime:
    testing=False;maintenance=False
    def status(self):return {'available':True,'busy':False,'message':'Installed; native worker checked separately on CPU'}
    def unload(self):pass
    def test(self):return self.status()
    def begin_maintenance(self):self.maintenance=True
    def end_maintenance(self,removed=False):self.maintenance=False
    def configuration(self):
        try:return json.loads((HOME/'runtime.json').read_text(encoding='utf-8'))
        except FileNotFoundError:return {}
release=Release(ROOT/'toolchain/voice-max-french-release',ROOT/'lanceur')
installer=MaxInstallation(HOME,release,Runtime(),ROOT/'toolchain/asr-models')
catalogue=json.loads((release.directory/'release.json').read_text(encoding='utf-8'))
for item in catalogue['models']:
    target=HOME/'models'/item['name'];target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists():os.link(OLD/item['name'],target)
installer.detect();old_plan=installer.plan()
assert old_plan['download_bytes']==catalogue['runtime']['bytes']+1219245248,old_plan
assert old_plan['reused_bytes']==sum(item['bytes'] for item in catalogue['models'])-1219245248
cache=HOME/'models/tts/talker.gguf'
assert cache.resolve().is_relative_to(HOME.resolve())
cache.unlink();os.link(ROOT/'toolchain/max-french-qa/tts/talker.gguf',cache)
new_plan=installer.plan();assert new_plan['download_bytes']==catalogue['runtime']['bytes']
installer.install(new_plan['plan']);installer.thread.join(90)
assert not installer.thread.is_alive(),installer.status()
assert installer.status()['phase']=='ready',installer.status()
config=installer.runtime.configuration();config['native_device']='CPU'
(HOME/'runtime.json').write_text(json.dumps(config),encoding='utf-8')
root=Path(config['root']);proof={'api':catalogue['runtime_api'],'revision':catalogue['revision'],'upgrade_download_bytes':old_plan['download_bytes'],'reused_bytes':old_plan['reused_bytes'],'runtime_signature_verified':True,'workers':{}}
for engine in ('tts','asr'):
    proc=subprocess.Popen([str(root/'max-worker.exe'),'--config',str(HOME/'runtime.json'),'--engine',engine],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=(OUT/(engine+'-worker.log')).open('w',encoding='utf-8'),text=True,encoding='utf-8',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    frames=queue.Queue()
    def read(stream):
        try:
            for line in stream:frames.put(json.loads(line))
        finally:frames.put(None)
    threading.Thread(target=read,args=(proc.stdout,),daemon=True).start()
    def receive():
        value=frames.get(timeout=90)
        assert value is not None and 'error' not in value,value
        return value
    try:
        ready=receive();assert ready.get('ready'),ready
        identifier='a'*32
        if engine=='tts':command={'id':identifier,'action':'speak','text':'Bonjour, je suis Kiara. Comment puis-je vous aider ?'}
        else:
            with wave.open(str(OUT/'french-1.wav')) as source:raw=source.readframes(source.getnframes())
            import array
            samples=array.array('h');samples.frombytes(raw)
            pcm=array.array('h',(round(samples[(i*3)//2]*(1-((i*3)%2)/2)+samples[min(len(samples)-1,(i*3)//2+1)]*(((i*3)%2)/2)) for i in range(len(samples)*2//3))).tobytes()
            command={'id':identifier,'action':'transcribe','rate':16000,'pcm':base64.b64encode(pcm).decode()}
        proc.stdin.write(json.dumps(command)+'\n');proc.stdin.flush();audio=bytearray();text='';metrics={}
        while True:
            frame=receive();assert frame.get('id')==identifier,frame
            if frame.get('pcm'):audio.extend(base64.b64decode(frame['pcm'],validate=True))
            if 'text' in frame:text=frame['text']
            metrics.update(frame.get('metrics',{}))
            if frame.get('done'):assert not frame.get('cancelled');break
        if engine=='tts':assert len(audio)>24000, len(audio)
        else:assert 'Kiara' in text and 'aider' in text,text
        proof['workers'][engine]={'passed':True,'pcm_bytes':len(audio),'text':text,'metrics':metrics}
    finally:
        proc.stdin.close()
        try:proc.wait(timeout=15)
        except subprocess.TimeoutExpired:proc.kill();proc.wait();raise
    assert proc.returncode==0,proc.returncode
installer.close()
(OUT/'pack-validation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(proof,ensure_ascii=False))
