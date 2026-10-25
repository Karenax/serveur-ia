"""Time existing authenticated routes using ephemeral fictional input only."""
import json
from pathlib import Path
import sys
import time
import urllib.request
import uuid
import argparse

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'lanceur'))
from releases import profile
from validate_live_lots6_8 import get


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='gateway-latency');parser.add_argument('--transport',choices=('loopback','https'),default='loopback');args=parser.parse_args()
    state=get('/api/state');assert state['health']['loaded'] and not state['queue']['active'] and not get('/api/voice')['busy']
    paths=list((ROOT/'lanceur/clients').glob('*.exe'));assert paths,'Personal client required'
    access=profile(paths[0]);base='http://127.0.0.1:8766' if args.transport=='loopback' else 'https://ia.karenax.net';headers={'Authorization':'Bearer '+access['token'],'Content-Type':'application/json','X-Fred-Agent-Protocol':'4','User-Agent':'AccesServeurFred/3.5.41 (Windows; HTTPS)'}
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    results=[]
    for route in ('/v1/models','/v1/voice/status','/v1/chat/completions','/v1/voice/speech'):
        identifier=uuid.uuid4().hex
        body=None
        if route=='/v1/chat/completions':body={'model':state['health']['model'],'messages':[{'role':'user','content':'Bonjour Fred, est-ce que tu m’entends bien ?'}],'stream':True,'voice_conversation':True,'conversation_id':'latency-fiction-'+uuid.uuid4().hex,'turn_id':identifier,'reasoning_effort':'none'}
        if route=='/v1/voice/speech':body={'request_id':identifier,'text':'Oui, je vous entends bien.','stream':True}
        request=urllib.request.Request(base+route,data=json.dumps(body).encode() if body else None,headers={**headers,'X-Qwen-Request':identifier})
        start=time.perf_counter();first=None;first_event=None;context_info=None;sources=0;chars=0;audio=0;chunks=0
        with opener.open(request,timeout=90) as response:
            header_time=time.perf_counter()-start
            if not body:json.load(response)
            else:
                for line in response:
                    if not line.startswith(b'data: '):continue
                    raw=line[6:].strip()
                    if raw==b'[DONE]':break
                    frame=json.loads(raw)
                    if first_event is None:first_event=time.perf_counter()-start
                    if frame.get('error'):raise ValueError('Gateway or speech returned an error')
                    if frame.get('voice_context'):context_info=frame['voice_context']
                    if frame.get('workspace_sources'):sources=len(frame['workspace_sources'])
                    content=(frame.get('choices') or [{}])[0].get('delta',{}).get('content','')
                    if content:chars+=len(content)
                    if frame.get('pcm'):audio+=len(frame['pcm']);chunks+=1
                    if first is None and (content or frame.get('pcm')):first=time.perf_counter()-start
            results.append({'route':route,'response_headers_seconds':header_time,'first_event_seconds':first_event,'first_content_or_pcm_seconds':first,'complete_seconds':time.perf_counter()-start,'context':context_info,'source_count':sources,'answer_characters':chars,'audio_base64_characters':audio,'audio_chunks':chunks})
    report={'passed':True,'transport':args.transport,'route':'authenticated gateway with existing profile; no history write or new account','results':results,'limits':'Microphone and browser playback are not measured; no second WireGuard tunnel is created.'}
    (OUT/(args.label+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
