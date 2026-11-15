import {afterEach, expect, it, vi} from 'vitest';
import {subscribeSessionEvents, type SessionEvent} from './sessionEvents';

afterEach(()=>{vi.unstubAllGlobals();vi.useRealTimers();});
function response(text:string,chunkSize=3) {
  const bytes=new TextEncoder().encode(text);
  return new Response(new ReadableStream<Uint8Array>({start(controller){
    for(let offset=0;offset<bytes.length;offset+=chunkSize)controller.enqueue(bytes.slice(offset,offset+chunkSize));
    controller.close();
  }}),{headers:{'Content-Type':'text/event-stream; charset=utf-8'}});
}
const frame=(id:number|string,text='échéance',kind='transcript.updated')=>`id: ${id}\r\nevent: ${kind}\r\ndata: {"kind":"${kind}","data":{"text":"${text}"},\r\ndata: "revision":4,"created_at":"2026-10-12T03:00:00Z"}\r\n\r\n`;

it('découpe UTF8/CRLF, données multilignes et événements nommés sans changer leur contenu',async()=>{
  const fetch=vi.fn().mockResolvedValue(response(': ready\r\n\r\nretry: 500\r\n\r\n'+frame(8,'Échéance : ne pas valider 250 W.')));
  vi.stubGlobal('fetch',fetch);const controller=new AbortController(),events:SessionEvent[]=[],connected=vi.fn();
  await subscribeSessionEvents('sid/projet',{after:7,signal:controller.signal,onConnected:connected,onEvent:event=>{events.push(event);controller.abort();}});
  expect(events).toEqual([{id:8,kind:'transcript.updated',revision:4,created_at:'2026-10-12T03:00:00Z',data:{text:'Échéance : ne pas valider 250 W.'}}]);
  expect(connected).toHaveBeenCalledOnce();
  expect(fetch).toHaveBeenCalledExactlyOnceWith('/api/v1/meeting-sessions/sid%2Fprojet/events?follow=true&after=7',expect.objectContaining({method:'GET',credentials:'same-origin',headers:{Accept:'text/event-stream'}}));
});
it('ignore les rejeux et IDs anciens, conserve une notification inconnue sans appliquer son payload',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(frame(8)+frame(7)+frame(9,'suggestion','future.notification'))));
  const controller=new AbortController(),events:SessionEvent[]=[];
  await subscribeSessionEvents('sid',{after:8,signal:controller.signal,onEvent:event=>{events.push(event);controller.abort();}});
  expect(events.map(event=>[event.id,event.kind])).toEqual([[9,'future.notification']]);
});
it('reprend après EOF au dernier ID livré sans requête ou notification après abort',async()=>{
  vi.useFakeTimers();const fetch=vi.fn().mockResolvedValueOnce(response(frame(1))).mockResolvedValueOnce(response(frame(1)+frame(2)));
  vi.stubGlobal('fetch',fetch);const controller=new AbortController(),events:number[]=[],connected=vi.fn();
  const task=subscribeSessionEvents('sid',{after:0,signal:controller.signal,onConnected:connected,onEvent:event=>{events.push(event.id);if(event.id===2)controller.abort();}});
  await vi.advanceTimersByTimeAsync(500);await task;
  expect(events).toEqual([1,2]);expect(connected).toHaveBeenCalledTimes(2);
  expect(fetch.mock.calls[1][0]).toContain('after=1');
  await vi.advanceTimersByTimeAsync(35_000);expect(fetch).toHaveBeenCalledTimes(2);
});
it('annule une lecture bloquée et ferme son reader, sans callback ancien ni reconnexion',async()=>{
  vi.useFakeTimers();const cancel=vi.fn();const body=new ReadableStream<Uint8Array>({cancel});
  const fetch=vi.fn().mockResolvedValue(new Response(body,{headers:{'Content-Type':'text/event-stream'}}));
  vi.stubGlobal('fetch',fetch);const controller=new AbortController(),event=vi.fn(),error=vi.fn();
  const task=subscribeSessionEvents('A',{after:0,signal:controller.signal,onEvent:event,onError:error});
  await vi.advanceTimersByTimeAsync(0);controller.abort();await task;
  await vi.advanceTimersByTimeAsync(40_000);
  expect(cancel).toHaveBeenCalledOnce();expect(event).not.toHaveBeenCalled();expect(error).not.toHaveBeenCalled();expect(fetch).toHaveBeenCalledOnce();
});
it('un abort avant connexion ne lit rien',async()=>{
  const fetch=vi.fn();vi.stubGlobal('fetch',fetch);const controller=new AbortController();controller.abort();
  await subscribeSessionEvents('sid',{after:0,signal:controller.signal,onEvent:vi.fn()});expect(fetch).not.toHaveBeenCalled();
});
it.each([403,404,422])('remonte HTTP %s terminal sans retry et sans altérer le curseur',async status=>{
  const fetch=vi.fn().mockResolvedValue(new Response(JSON.stringify({detail:'Séance introuvable'}),{status,headers:{'Content-Type':'application/json'}}));
  vi.stubGlobal('fetch',fetch);const error=vi.fn();
  await subscribeSessionEvents('sid',{after:8,signal:new AbortController().signal,onEvent:vi.fn(),onError:error});
  expect(error).toHaveBeenCalledExactlyOnceWith({message:'Séance introuvable',status,retryable:false});expect(fetch).toHaveBeenCalledOnce();
});
it.each([403,404])('reconnaît stream.denied %s sans ID comme révocation terminale',async status=>{
  const fetch=vi.fn().mockResolvedValue(response(`event: stream.denied\ndata: {"status":${status}}\n\n`));
  vi.stubGlobal('fetch',fetch);const event=vi.fn(),error=vi.fn();
  await subscribeSessionEvents('sid',{after:8,signal:new AbortController().signal,onEvent:event,onError:error});
  expect(event).not.toHaveBeenCalled();expect(error).toHaveBeenCalledExactlyOnceWith({message:'L’accès à cette séance n’est plus autorisé.',status,retryable:false});
  expect(fetch).toHaveBeenCalledOnce();
});
it('borne retry serveur et conserve un HTTP503 explicite avant récupération',async()=>{
  vi.useFakeTimers();const controller=new AbortController(),error=vi.fn();
  const fetch=vi.fn().mockResolvedValueOnce(new Response('Maintenance',{status:503}))
    .mockResolvedValueOnce(response('retry: 1\n\n'+frame(1)))
    .mockResolvedValueOnce(response(frame(2)));
  vi.stubGlobal('fetch',fetch);
  const task=subscribeSessionEvents('sid',{after:0,signal:controller.signal,onError:error,onEvent:event=>{if(event.id===2)controller.abort();}});
  await vi.advanceTimersByTimeAsync(1000);
  expect(fetch).toHaveBeenCalledTimes(2);expect(error).toHaveBeenCalledWith(expect.objectContaining({status:503,retryable:true}));
  await vi.advanceTimersByTimeAsync(499);expect(fetch).toHaveBeenCalledTimes(2);
  await vi.advanceTimersByTimeAsync(1);await task;expect(fetch).toHaveBeenCalledTimes(3);
});
it.each(['9007199254740992','-1','8abc'])('refuse l’ID %s hors safeint avant livraison',async id=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(frame(id))));const event=vi.fn(),error=vi.fn();
  await subscribeSessionEvents('sid',{after:0,signal:new AbortController().signal,onEvent:event,onError:error});
  expect(event).not.toHaveBeenCalled();expect(error).toHaveBeenCalledWith(expect.objectContaining({retryable:false}));
});
it('annule le délai de reconnexion hors ligne sans lancer de nouvelle séance',async()=>{
  vi.useFakeTimers();const fetch=vi.fn().mockRejectedValue(new TypeError('offline'));vi.stubGlobal('fetch',fetch);
  const controller=new AbortController(),error=vi.fn();
  const task=subscribeSessionEvents('sid',{after:5,signal:controller.signal,onError:error,onEvent:vi.fn()});
  await vi.advanceTimersByTimeAsync(0);controller.abort();await task;
  await vi.advanceTimersByTimeAsync(50_000);expect(fetch).toHaveBeenCalledOnce();expect(error).toHaveBeenCalledOnce();
});
it('une connexion qui dépasse sa borne est annulée et signale la reprise sans faux événement',async()=>{
  vi.useFakeTimers();const controller=new AbortController(),cancel=vi.fn(),event=vi.fn();
  const fetch=vi.fn().mockResolvedValue(new Response(new ReadableStream({cancel}),{headers:{'Content-Type':'text/event-stream'}}));
  vi.stubGlobal('fetch',fetch);const error=vi.fn(()=>controller.abort());
  const task=subscribeSessionEvents('sid',{after:0,signal:controller.signal,onEvent:event,onError:error});
  await vi.advanceTimersByTimeAsync(35_000);await task;
  expect(error).toHaveBeenCalledWith(expect.objectContaining({retryable:true,message:expect.stringContaining('expiré')}));
  expect(cancel).toHaveBeenCalledOnce();expect(event).not.toHaveBeenCalled();expect(fetch).toHaveBeenCalledOnce();
});
it('refuse UTF8 corrompu sans boucle de reprise ni payload transformé',async()=>{
  const body=new ReadableStream<Uint8Array>({start(controller){controller.enqueue(new Uint8Array([0xc3,0x28]));controller.close();}});
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(body,{headers:{'Content-Type':'text/event-stream'}})));
  const event=vi.fn(),error=vi.fn();
  await subscribeSessionEvents('sid',{after:0,signal:new AbortController().signal,onEvent:event,onError:error});
  expect(event).not.toHaveBeenCalled();expect(error).toHaveBeenCalledWith(expect.objectContaining({retryable:false,message:expect.stringContaining('Encodage')}));
});
it('borne aussi le retry serveur excessif au lieu de bloquer la reprise pendant une durée arbitraire',async()=>{
  vi.useFakeTimers();const controller=new AbortController();
  const fetch=vi.fn().mockResolvedValueOnce(response('retry: 999999999\n\n')).mockResolvedValueOnce(response(frame(1)));
  vi.stubGlobal('fetch',fetch);
  const task=subscribeSessionEvents('sid',{after:0,signal:controller.signal,onEvent:()=>controller.abort()});
  await vi.advanceTimersByTimeAsync(4999);expect(fetch).toHaveBeenCalledOnce();
  await vi.advanceTimersByTimeAsync(1);await task;expect(fetch).toHaveBeenCalledTimes(2);
});
it('accepte un seul read regroupant plusieurs événements valides dont la somme dépasse la borne par frame',async()=>{
  const large='x'.repeat(600_000),body=frame(1,large)+frame(2,large);
  expect(body.length).toBeGreaterThan(1024*1024);
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(body,body.length)));
  const controller=new AbortController(),events:SessionEvent[]=[],error=vi.fn();
  await subscribeSessionEvents('sid',{after:0,signal:controller.signal,onError:error,onEvent:event=>{events.push(event);if(event.id===2)controller.abort();}});
  expect(events.map(event=>event.id)).toEqual([1,2]);expect(events.every(event=>event.data.text===large)).toBe(true);expect(error).not.toHaveBeenCalled();
});
it.each([500_000,2_000_000])('refuse un événement individuel trop gros reçu par morceaux ou en un seul read (%s)',async chunkSize=>{
  const text=frame(1,'x'.repeat(1024*1024+1));vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response(text,chunkSize)));
  const event=vi.fn(),error=vi.fn();
  await subscribeSessionEvents('sid',{after:0,signal:new AbortController().signal,onEvent:event,onError:error});
  expect(event).not.toHaveBeenCalled();expect(error).toHaveBeenCalledWith(expect.objectContaining({retryable:false,message:expect.stringContaining('trop volumineux')}));
});
it('une frame à la borne reste valable quand CRLFCRLF est fragmenté au milieu du délimiteur',async()=>{
  const limit=1024*1024;
  const empty=frame(1,'');const text=frame(1,'x'.repeat(limit-(empty.length-4)));
  expect(text.indexOf('\r\n\r\n')).toBe(limit);
  const bytes=new TextEncoder().encode(text);
  const body=new ReadableStream<Uint8Array>({start(controller){controller.enqueue(bytes.slice(0,limit+3));controller.enqueue(bytes.slice(limit+3));controller.close();}});
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(body,{headers:{'Content-Type':'text/event-stream'}})));
  const controller=new AbortController(),event=vi.fn(()=>controller.abort()),error=vi.fn();
  await subscribeSessionEvents('sid',{after:0,signal:controller.signal,onEvent:event,onError:error});
  expect(event).toHaveBeenCalledOnce();expect(error).not.toHaveBeenCalled();
});
