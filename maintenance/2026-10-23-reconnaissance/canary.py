"""Smaller French-capable mobile candidate, evaluated without changing Fred."""
import json
import time
import urllib.request
import wave
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import sherpa_onnx
import compare


def main():
    compare.REPO='csukuangfj/sherpa-onnx-nemo-canary-180m-flash-en-es-de-fr-int8'
    compare.REVISION='9077164e0d3dd1d5353743e89ceaa1d3a770838c'
    compare.MODEL_FOLDER=compare.WORK/'canary'
    metadata=json.load(urllib.request.urlopen(f'https://huggingface.co/api/models/{compare.REPO}/revision/{compare.REVISION}?blobs=true',timeout=30))
    items=[item for item in metadata['siblings'] if item['rfilename'] in ('encoder.int8.onnx','decoder.int8.onnx','tokens.txt')]
    with ThreadPoolExecutor(max_workers=3) as pool:files=list(pool.map(compare.download,items))
    (compare.WORK/'canary-downloads.json').write_text(json.dumps(files,indent=2),encoding='utf-8')
    folder=compare.MODEL_FOLDER;started=time.perf_counter()
    asr=sherpa_onnx.OfflineRecognizer.from_nemo_canary(encoder=str(folder/'encoder.int8.onnx'),decoder=str(folder/'decoder.int8.onnx'),tokens=str(folder/'tokens.txt'),src_lang='fr',tgt_lang='fr',num_threads=4,provider='cpu')
    loaded=time.perf_counter()-started;results=[]
    for path in [compare.ROOT/'preuves/voix-small-20261011/francais.wav',compare.WORK/'parakeet/test_wavs/fr.wav']:
        with wave.open(str(path)) as source:
            rate=source.getframerate();pcm=np.frombuffer(source.readframes(source.getnframes()),dtype='<i2').astype(np.float32)/32768
        for variant,audio in [('original',pcm),('quiet',pcm*.15),('noise',np.clip(pcm+np.random.default_rng(42).normal(0,.008,len(pcm)),-1,1).astype(np.float32))]:
            started=time.perf_counter();stream=asr.create_stream();stream.accept_waveform(rate,audio);asr.decode_stream(stream)
            result={'fixture':path.name,'variant':variant,'compute_seconds':time.perf_counter()-started,'text':stream.result.text}
            results.append(result);print(json.dumps(result,ensure_ascii=True),flush=True)
    (compare.WORK/'canary-results.json').write_text(json.dumps({'loading_seconds':loaded,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
