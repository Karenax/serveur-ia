import json,sys,time,wave,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'client-qwen'))
import psutil
from local_voice import NativeEngine,Microphone
spec=json.loads((ROOT/'client-voice/model.json').read_text())
with wave.open(str(Path(__file__).with_name('francais.wav')),'rb') as stream:
    assert (stream.getframerate(),stream.getnchannels(),stream.getsampwidth())==(16000,1,2)
    pcm=stream.readframes(stream.getnframes())
process=psutil.Process();baseline=process.memory_info().rss;peak=baseline;watch=True
def monitor():
    global peak
    while watch:peak=max(peak,process.memory_info().rss);time.sleep(.05)
thread=threading.Thread(target=monitor);thread.start()
model=ROOT/'toolchain/voice-models/ggml-small.bin';binary=ROOT/'client-qwen/voice'
def until(engine,phases,timeout=100):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        value=engine.status()
        if value['phase'] in phases:return value
        if value['phase']=='error':raise AssertionError(value)
        time.sleep(.05)
    raise AssertionError('Native timeout '+str(engine.status()))
try:
    started=time.monotonic();v=NativeEngine(binary,model);until(v,{'listening'});loaded=time.monotonic()-started
    # Feed at microphone speed to observe progressive, provisional text.
    progress=[]
    for offset in range(0,len(pcm),3200):
        v.feed(pcm[offset:offset+3200]);time.sleep(.1)
        state=v.status()
        if state['text'] and (not progress or state['text']!=progress[-1]['text']):progress.append({'seconds':state['seconds'],'text':state['text']})
    for _ in range(18):v.feed(b'\0'*3200);time.sleep(.1)
    # Silence stabilizes the phrase, but never ends the dictation or sends it.
    assert v.status()['phase']=='listening'
    v.stop();final=until(v,{'ready'});v.close()
    assert 'réunion' in final['text'].lower() and 'demain' in final['text'].lower(),final
    assert progress,'No progressive result during dictation'
    v=NativeEngine(binary,model);until(v,{'listening'});v.feed(b'\0'*3200);v.stop();silence=until(v,{'ready'});assert silence['text']=='';v.close()
    v=NativeEngine(binary,model);v.cancel();cancel=until(v,{'cancelled'});assert cancel['text']=='';v.close()
    try:
        microphone=Microphone();microphone.close();capture='WinMM microphone opened and closed'
    except OSError as error:capture=str(error)
    watch=False;thread.join();time.sleep(.2)
    result={'passed':True,'fixture':'Synthetic French speech, Microsoft Hortense Desktop','audio_seconds':len(pcm)/32000,'model':'small multilingual','loading_seconds':loaded,'progress':progress,'final':final,'silence':silence,'cancel':cancel,'baseline_rss_bytes':baseline,'peak_rss_bytes':peak,'released_rss_bytes':process.memory_info().rss,'capture':capture}
    Path(__file__).with_name('windows-native-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))
finally:watch=False;thread.join()
