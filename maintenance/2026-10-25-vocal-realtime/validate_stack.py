"""Install the signed runtime, then replay actual audio through VAD/STT/LLM/TTS."""
import base64,json,os,queue,re,sys,threading,time,uuid,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path[:0]=[str(ROOT/'client-qwen'),str(ROOT/'client-voice'),str(ROOT/'lanceur')]
sys.path.append(str(Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/python/Lib/site-packages'))
import numpy as np
from max_asr import available_devices
from max_recognition import MaxRecognizer
from advanced_voice import AdvancedVoice
from max_installation import MaxInstallation
from prepare_max_pack import Release
from core import read_json,BASE_PATH
from validate_live_lots6_8 import get
from voice_response import configure,respond

sys.stdout.reconfigure(encoding='utf-8')
print('Detect native cards',flush=True)
home=ROOT/'toolchain/vocal-realtime-stack-qa';home.mkdir(exist_ok=True)
cards=available_devices(ROOT/'toolchain/max-realtime-qa')
print('Native cards returned',flush=True)
card=next(item for item in cards if 'P2200' in item['description'])
(home/'gpu.json').write_text(json.dumps({'device':card['id']}),encoding='utf-8')
cached=home/'models/asr/ggml-large-v3-turbo-q5_0.bin';cached.parent.mkdir(parents=True,exist_ok=True)
if not cached.exists():os.link(ROOT/'toolchain/max-realtime-models/ggml-large-v3-turbo-q5_0.bin',cached)
runtime=AdvancedVoice(home)
installer=MaxInstallation(home,Release(ROOT/'toolchain/voice-max-realtime-release',ROOT/'lanceur'),runtime,ROOT/'toolchain/asr-models')
proof={};cfg=read_json(BASE_PATH)
try:
    print('Detect installation hardware',flush=True);installer.detect();print('Plan',flush=True);plan=installer.plan();print('Install',plan,flush=True);installer.install(plan['plan'])
    installer.thread.join(180)
    assert not installer.thread.is_alive(),installer.status()
    assert installer.status()['phase']=='ready',installer.status()
    status=runtime.status();assert status['available'] and status['loaded'],status
    assert status['device']['id']==card['id'],status
    benchmark=json.loads((home/'benchmark.json').read_text(encoding='utf-8'))
    assert benchmark['functional'],benchmark
    proof={'revision':runtime.configuration()['catalogue']['revision'],'runtime_api':6,
           'signature_verified':True,'installation':{k:plan[k] for k in ('download_bytes','reused_bytes','required_disk_bytes')},
           'device':status['device'],'benchmark':benchmark,'turns':[]}
    runtime.warm('probe',uuid.uuid4().hex)
    def synth(text):
        return b''.join(base64.b64decode(frame['pcm']) for frame in runtime.frames('probe','speak',{'request_id':uuid.uuid4().hex,'text':text}) if frame.get('pcm'))
    def transcribe(audio,**segments):
        raw=(np.clip(audio,-1,1)*32767).astype('<i2').tobytes()
        return runtime.transcribe('probe',{'rate':16000,'pcm':base64.b64encode(raw).decode(),'request_id':uuid.uuid4().hex,**segments})['text']
    for index,question in enumerate(('Combien font douze plus dix-sept ?','Comment retrouver mes anciennes conversations ?')):
        assert not get('/api/state')['queue']['active'],'Wait for production requests'
        raw=synth(question);samples=np.frombuffer(raw,dtype='<i2').astype(np.float32)/32768
        # Test-only resampling; live capture is already 16 kHz.
        samples=np.interp(np.arange(len(samples)*2//3)*1.5,np.arange(len(samples)),samples).astype(np.float32)
        recognizer=MaxRecognizer(runtime.configuration()['asr'],transcribe,'Whisper Turbo · français')
        start=time.monotonic();end_audio=start+len(samples)/16000;turn=None
        try:
            for offset in range(0,len(samples)+4*16000,1600):
                frame=samples[offset:offset+1600] if offset<len(samples) else np.zeros(1600,np.float32)
                recognizer.accept(frame)
                wait=start+(offset+len(frame))/16000-time.monotonic()
                if wait>0:time.sleep(wait)
                turns=recognizer.status()['turns']
                if turns:
                    assert offset+len(frame)>=len(samples),'Premature input segmentation'
                    assert len(turns)==1,turns
                    turn=turns[0];break
            assert turn,recognizer.status()
        finally:recognizer.close()
        assert len(turn['text'])<140,('Recognition loop',turn['text'])
        if index==0:assert 'plus' in turn['text'].lower(),turn['text']
        else:assert 'conversations' in turn['text'].lower(),turn['text']
        recognized_at=time.monotonic();parts=queue.Queue();reply=[];audio=bytearray();errors=[]
        timings={'first_text':None,'first_audio':None};playback_end=[0.0];gaps=[]
        def play():
            try:
                while True:
                    part=parts.get()
                    if part is None:break
                    for frame in runtime.frames('probe','speak',{'request_id':uuid.uuid4().hex,'text':part}):
                        if not frame.get('pcm'):continue
                        pcm=base64.b64decode(frame['pcm']);now=time.monotonic()
                        while playback_end[0]-now>4:time.sleep(.02);now=time.monotonic()
                        if timings['first_audio'] is None:timings['first_audio']=now
                        if playback_end[0] and now>playback_end[0]:gaps.append(now-playback_end[0])
                        playback_end[0]=max(playback_end[0],now+.03)+len(pcm)/48000
                        audio.extend(pcm)
            except Exception as error:errors.append(str(error))
        player=threading.Thread(target=play);player.start();buffer=['']
        def delta(text):
            if timings['first_text'] is None:timings['first_text']=time.monotonic()
            reply.append(text);buffer[0]+=text
            while match:=re.search(r'[.!?](?=\s)',buffer[0]):
                end=match.end();part=buffer[0][:end].strip();buffer[0]=buffer[0][end:].lstrip()
                if part:parts.put(part)
        body=configure({'messages':[{'role':'system','content':'Tu es Kiara. Réponds en français naturel en deux phrases courtes. La rubrique Historique permet de retrouver les conversations.'},{'role':'user','content':turn['text']}],
                        'stream':True,'max_tokens':1024,'reasoning_effort':'none','chat_template_kwargs':{'enable_thinking':False},'strata_mcp':False})
        route=respond(cfg.get('port',8080),cfg.get('model_name','local'),cfg.get('api_key',''),body,lambda:True,lambda:None,delta)
        assert route['action']=='answer',route
        if buffer[0].strip():parts.put(buffer[0].strip())
        parts.put(None);player.join(60);assert not player.is_alive() and not errors,errors
        assert audio and timings['first_audio'],timings
        if index==0:assert '29' in ''.join(reply) or 'vingt-neuf' in ''.join(reply),reply
        with wave.open(str(OUT/f'complete-turn-{index+1}.wav'),'wb') as target:
            target.setnchannels(1);target.setsampwidth(2);target.setframerate(24000);target.writeframes(audio)
        row={'question':question,'recognized':turn['text'],'answer':''.join(reply).strip(),
             'recognition_after_recording_ms':(recognized_at-end_audio)*1000,
             'first_text_after_recording_ms':(timings['first_text']-end_audio)*1000,
             'first_audio_after_recording_ms':(timings['first_audio']-end_audio)*1000,
             'output_seconds':len(audio)/48000,'max_playback_gap_ms':max(gaps,default=0)*1000}
        proof['turns'].append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    (OUT/'stack-validation.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
finally:installer.close();runtime.close()
