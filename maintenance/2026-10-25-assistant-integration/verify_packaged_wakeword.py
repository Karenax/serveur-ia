"""Exercise the shipped Windows worker on synthetic WAVs, without microphone access."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import wave
import audioop

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'client-qwen/build-tools'))
from PyInstaller.archive.readers import CArchiveReader


def main():
    archive=CArchiveReader(str(ROOT/'client-qwen/dist/Accès serveur Fred.exe'))
    worker=ROOT/'client-qwen/voice/conversation-worker/conversation-worker.exe'
    assert hashlib.sha256(archive.extract('voice\\conversation-worker\\conversation-worker.exe')).hexdigest()==hashlib.sha256(worker.read_bytes()).hexdigest()
    results=[]
    for sample,expected in [('bonjour-kiara',1),('clara',0),('kiara',0),('ordinary',0)]:
        # Production capture already supplies 16 kHz. Normalize the 24 kHz
        # synthetic TTS recordings before using the shipped fixture reader;
        # SciPy remains intentionally excluded from the public worker.
        with tempfile.TemporaryDirectory(prefix='kiara-wake-fixture-') as temporary:
            fixture=Path(temporary)/'sample.wav'
            with wave.open(str(OUT/'audio'/(sample+'.wav'))) as source:
                assert source.getsampwidth()==2 and source.getnchannels()==1
                raw=source.readframes(source.getnframes());rate=source.getframerate()
            if rate!=16000:raw=audioop.ratecv(raw,2,1,rate,16000,None)[0]
            with wave.open(str(fixture),'wb') as destination:
                destination.setnchannels(1);destination.setsampwidth(2);destination.setframerate(16000);destination.writeframes(raw)
            run=subprocess.run([str(worker),'--models',str(ROOT/'client-qwen/voice/wakeword'),
                '--resources',str(ROOT/'client-qwen/voice'),'--mode','wakeword','--fixture',str(fixture)],
                capture_output=True,text=True,encoding='utf-8',timeout=40,creationflags=subprocess.CREATE_NO_WINDOW)
        assert run.returncode==0,'Packaged keyword fixture failed'
        lines=[json.loads(line) for line in run.stdout.splitlines() if line.startswith('{')]
        result=next(r for r in lines if r['phase']=='test_done')
        assert len(result['turns'])==expected
        results.append({'sample':sample,'detected':len(result['turns']),'seconds':result['audio_seconds']})
    report={'passed':True,'shipped_worker_verified':True,'microphone_opened':False,'synthetic_samples_only':True,'samples':results}
    (OUT/'windows-packaged-wakeword.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
