import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { documentJobApi, type BatchCommand, type DocumentJob } from './projectDocumentJobs';
import { invalidateSession, request } from './http';
vi.mock('./http',()=>({request:vi.fn(),invalidateSession:vi.fn()}));
const {webcrypto}=await vi.importActual<{webcrypto:Crypto}>('node:crypto');
const job={id:'lot/1',project_id:'p/1',revision:9} as DocumentJob;
const command:BatchCommand={command_id:'commande-1',items:[{document_id:'ce_request',link_id:'l1',relative_path:'CE.docx',overrides:{description:'LED'},
  expected_source_sha256:'a'.repeat(64),expected_link_sha256:'b'.repeat(64),expected_values_sha256:'c'.repeat(64),
  expected_identity_revision:2,expected_planning_revision:4,expected_draft_revision:7}]};
const bytes=new TextEncoder().encode('Copie documentaire vérifiée');
const sha='8232f8a372ff1d1b09f2bcec4f0583b77d3c798ca31bea7f44b70f302f1bb834';
function response(headers:Record<string,string>={},data=bytes.buffer as ArrayBuffer){return new Response(data,{headers:{etag:`"${sha}"`,
  'x-agent-network-published':'false','content-disposition':"attachment; filename*=UTF-8''Copie%20v%C3%A9rifi%C3%A9e.docx",...headers}});}
beforeEach(()=>{vi.mocked(request).mockResolvedValue(job);vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response()));vi.stubGlobal('crypto',webcrypto);});
afterEach(()=>{vi.restoreAllMocks();vi.clearAllMocks();vi.unstubAllGlobals();vi.useRealTimers();});

it('soumet le lot capturé avec une commande stable et des identifiants encodés',async()=>{
  await documentJobApi.submit('p/1',command);
  expect(request).toHaveBeenCalledWith('/api/v1/projects/p%2F1/documents/jobs',{
    method:'POST',body:JSON.stringify(command),signal:expect.any(AbortSignal)});
  expect(JSON.parse(vi.mocked(request).mock.calls[0][1]!.body as string)).toEqual(command);
});
it.each(['cancel','retry'] as const)('commande %s avec la révision lue, sans modifier le lot',async(kind)=>{
  await documentJobApi[kind]('p/1',job);
  expect(request).toHaveBeenCalledWith(`/api/v1/projects/p%2F1/documents/jobs/lot%2F1/${kind}`,{
    method:'POST',body:'{"expected_revision":9}',signal:expect.any(AbortSignal)});
  expect(job.revision).toBe(9);
});
it.each(['detail','submit','cancel','retry'] as const)('refuse une réponse %s appartenant à un autre projet',async(kind)=>{
  vi.mocked(request).mockResolvedValue({...job,project_id:'autre'});
  const pending=kind==='detail'?documentJobApi.detail('p/1',job.id):kind==='submit'?documentJobApi.submit('p/1',command):documentJobApi[kind]('p/1',job);
  await expect(pending).rejects.toThrow('hors du projet');
});
it('refuse une liste contenant un lot étranger',async()=>{
  vi.mocked(request).mockResolvedValue({items:[job,{...job,project_id:'autre'}]});
  await expect(documentJobApi.list('p/1')).rejects.toThrow('hors du projet');
});
it.each(['events','attempts'] as const)('borne et pagine %s',async(kind)=>{
  vi.mocked(request).mockResolvedValue({items:[],total:40,offset:20,limit:20});
  await documentJobApi[kind]('p/1',job.id,20);
  expect(request).toHaveBeenCalledWith(`/api/v1/projects/p%2F1/documents/jobs/lot%2F1/${kind}?offset=20&limit=20`,{signal:expect.any(AbortSignal)});
});
it('ne démarre aucune requête déjà annulée',async()=>{
  const controller=new AbortController();controller.abort();
  await expect(documentJobApi.submit('p/1',command,controller.signal)).rejects.toThrow('Opération annulée');
  await expect(documentJobApi.download('p/1','copie',controller.signal)).rejects.toThrow('Opération annulée');
  expect(request).not.toHaveBeenCalled();expect(fetch).not.toHaveBeenCalled();
});
it('propage l’annulation et libère le délai et l’écouteur',async()=>{
  vi.useFakeTimers();vi.mocked(request).mockImplementation((_url,options)=>new Promise((_resolve,reject)=>{
    options?.signal?.addEventListener('abort',()=>reject(new DOMException('Annulée','AbortError')),{once:true});}));
  const controller=new AbortController(),remove=vi.spyOn(controller.signal,'removeEventListener');
  const pending=documentJobApi.detail('p/1',job.id,controller.signal),rejected=expect(pending).rejects.toThrow('Annulée');
  controller.abort();await rejected;expect(remove).toHaveBeenCalledWith('abort',expect.any(Function));expect(vi.getTimerCount()).toBe(0);
});
it.each([['list',15_000],['submit',120_000]] as const)('applique le délai de %s même avec un signal parent',async(kind,ms)=>{
  vi.useFakeTimers();vi.mocked(request).mockImplementation((_url,options)=>new Promise((_resolve,reject)=>{
    options?.signal?.addEventListener('abort',()=>reject(new DOMException('Délai','AbortError')),{once:true});}));
  const controller=new AbortController();const pending=kind==='list'?documentJobApi.list('p/1',0,controller.signal):documentJobApi.submit('p/1',command,controller.signal);
  const rejected=expect(pending).rejects.toThrow('Délai');await vi.advanceTimersByTimeAsync(ms);await rejected;
  expect(controller.signal.aborted).toBe(false);expect(vi.getTimerCount()).toBe(0);
});
it('vérifie le SHA réel des octets et le nom UTF8 avant de proposer une copie',async()=>{
  const result=await documentJobApi.download('p/1','copie/1');
  expect(result.filename).toBe('Copie vérifiée.docx');expect(result.sha256).toBe(sha);
  expect(result.url).toBe('/api/v1/projects/p%2F1/documents/artifacts/copie%2F1');
  expect(fetch).toHaveBeenCalledWith('/api/v1/projects/p%2F1/documents/artifacts/copie%2F1',{credentials:'same-origin',signal:expect.any(AbortSignal)});
});
it.each(['etag','publication','filename','encoding','path','size','empty','digest'])('bloque un téléchargement invalide : %s',async(kind)=>{
  const headers:Record<string,string>={};if(kind==='etag')headers.etag='absent';if(kind==='publication')headers['x-agent-network-published']='true';
  if(kind==='filename')headers['content-disposition']='attachment; filename=CE.docx';
  if(kind==='encoding')headers['content-disposition']="attachment; filename*=UTF-8''%ZZ";
  if(kind==='path')headers['content-disposition']="attachment; filename*=UTF-8''..%2Fcopie.docx";
  if(kind==='size')headers['content-length']='52428801';if(kind==='digest')headers.etag=`"${'0'.repeat(64)}"`;
  vi.mocked(fetch).mockResolvedValue(response(headers,kind==='empty'?new ArrayBuffer(0):bytes.buffer as ArrayBuffer));
  await expect(documentJobApi.download('p/1','copie')).rejects.toThrow();
});
it('invalide une session refusée sans proposer de téléchargement',async()=>{
  vi.mocked(fetch).mockResolvedValue(new Response(JSON.stringify({detail:'Accès refusé'}),{status:403}));
  await expect(documentJobApi.download('p/1','copie')).rejects.toThrow('Accès refusé');expect(invalidateSession).toHaveBeenCalledOnce();
});
it('refuse les octets si la vue est annulée pendant leur vérification',async()=>{
  let done!:(value:ArrayBuffer)=>void;vi.stubGlobal('crypto',{subtle:{digest:vi.fn(()=>new Promise(resolve=>{done=resolve;}))}});
  const controller=new AbortController(),pending=documentJobApi.download('p/1','copie',controller.signal);
  const rejected=expect(pending).rejects.toThrow('Téléchargement annulé');
  await vi.waitFor(()=>expect(crypto.subtle.digest).toHaveBeenCalledOnce());controller.abort();
  done(new Uint8Array(sha.match(/../g)!.map(value=>parseInt(value,16))).buffer);await rejected;
});
