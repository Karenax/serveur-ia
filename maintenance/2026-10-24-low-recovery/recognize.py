"""Two spoken French turns through the real local engines; no microphone or server writes."""
import argparse,ctypes,json,os,sys,time,wave
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'client-voice'))
parser=argparse.ArgumentParser();parser.add_argument('--engine',choices=['parakeet','whisper'],required=True);args=parser.parse_args()
import numpy as np
with wave.open(str(ROOT/'toolchain/android-tests/conversation.wav'),'rb') as source:audio=np.frombuffer(source.readframes(source.getnframes()),dtype='<i2').copy()
sequence=np.concatenate([audio,np.zeros(3*16000,dtype=np.int16),audio,np.zeros(3*16000,dtype=np.int16)])
started=time.monotonic();trace=[]
if args.engine=='parakeet':
    from recognition import Recognizer
    engine=Recognizer(Path(os.environ['LOCALAPPDATA'])/'QwenClient/asr')
    def feed(frame):engine.accept(frame.astype(np.float32)/32768)
    def status():return {'phase':'listening',**engine.status()}
    def close():engine.close()
else:
    folder=ROOT/'client-qwen/voice';directory=os.add_dll_directory(str(folder));dll=ctypes.CDLL(str(folder/'fredvoice.dll'))
    dll.fred_voice_create_conversation.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.c_int];dll.fred_voice_create_conversation.restype=ctypes.c_void_p
    handle=dll.fred_voice_create_conversation(str(ROOT/'toolchain/voice-models/ggml-small.bin').encode(),str(folder).encode(),4)
    dll.fred_voice_feed.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int];dll.fred_voice_status.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int];dll.fred_voice_destroy.argtypes=[ctypes.c_void_p]
    def feed(frame):dll.fred_voice_feed(handle,frame.ctypes.data,len(frame))
    def status():
        buffer=ctypes.create_string_buffer(524288);assert dll.fred_voice_status(handle,buffer,len(buffer))>0;return json.loads(buffer.value)
    def close():dll.fred_voice_destroy(handle)
try:
    end=time.monotonic()+60
    while status()['phase']=='loading' and time.monotonic()<end:time.sleep(.05)
    assert status()['phase']=='listening',status()
    loaded=time.monotonic()-started;last=None
    def sample(level=0):
        global last
        value=status();signature=json.dumps({k:value.get(k) for k in ['partial','text','speech_id','processing','turns','pending']},sort_keys=True)
        if signature!=last:trace.append({'at':round(time.monotonic()-started,3),'audio_level':level,**value});last=signature
    for offset in range(0,len(sequence),1600):
        frame=sequence[offset:offset+1600];feed(frame);sample(float(np.sqrt(np.mean((frame.astype(np.float32)/32768)**2))));time.sleep(.1)
    end=time.monotonic()+90
    while len(status().get('turns',[]))<2 and time.monotonic()<end:sample();time.sleep(.1)
    sample();value=status();result={'engine':args.engine,'passed':len(value.get('turns',[]))>=2,'loading_seconds':round(loaded,3),'elapsed_seconds':round(time.monotonic()-started,3),'final':value,'trace':trace}
    path=Path(__file__).with_name(args.engine+'.json');path.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='trace'},ensure_ascii=False),flush=True)
finally:close()
