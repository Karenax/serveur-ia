import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { documentApi, DocumentHttpError, type DocumentChoice, type DocumentPreview } from './projectDocuments';
import { invalidateSession, request, token } from './http';
vi.mock('./http',()=>({request:vi.fn(),token:vi.fn(),invalidateSession:vi.fn()}));
const choice:DocumentChoice={document_id:'ce_request',link_id:'link1',relative_path:'demande.docx',overrides:{}};
const preview={document_id:'ce_request',can_prepare:true,can_prepare_copy:true,source:{project_id:'project1',link_id:'link1',relative_path:'demande.docx'},
  source_sha256:'a'.repeat(64),link_sha256:'e'.repeat(64),values_sha256:'b'.repeat(64),field_values:{identity_revision:2,planning_revision:4},output_filename:'Copie CE.docx'} as DocumentPreview;
const bytes=new TextEncoder().encode('Copie vérifiée');const output='c'.repeat(64);
function response(headers:Record<string,string>={},data:ArrayBuffer=bytes.buffer as ArrayBuffer){return new Response(data,{headers:{
  etag:'"'+output+'"','x-agent-source-sha256':preview.source_sha256,'x-agent-values-sha256':preview.values_sha256,
  'x-agent-link-sha256':preview.link_sha256,'x-agent-network-published':'false',...headers}});}
beforeEach(()=>{vi.mocked(token).mockResolvedValue('local-token');vi.stubGlobal('fetch',vi.fn().mockResolvedValue(response()));
  vi.stubGlobal('crypto',{subtle:{digest:vi.fn().mockResolvedValue(new Uint8Array(32).fill(204).buffer)}});});
afterEach(()=>{vi.restoreAllMocks();vi.clearAllMocks();vi.unstubAllGlobals();vi.useRealTimers();});

it('limite la découverte au projet et lien sélectionnés, sans transmettre de chemins ni réglages serveur',async()=>{
  vi.mocked(request).mockResolvedValue({status:'completed'});const controller=new AbortController();
  const remove=vi.spyOn(controller.signal,'removeEventListener');
  await documentApi.discover('project1','ce_request','link1',controller.signal);
  expect(request).toHaveBeenCalledWith('/api/v1/projects/project1/documents/discover',{
    method:'POST',signal:expect.any(AbortSignal),body:JSON.stringify({document_id:'ce_request',link_id:'link1'})});
  expect(remove).toHaveBeenCalledWith('abort',expect.any(Function));
});

it('ne lance aucune découverte déjà annulée',async()=>{
  const controller=new AbortController();controller.abort();
  await expect(documentApi.discover('project1','ce_request','link1',controller.signal)).rejects.toThrow('Recherche annulée');
  expect(request).not.toHaveBeenCalled();
});

it('propage une annulation de découverte au signal de la requête',async()=>{
  vi.mocked(request).mockImplementation((_url,options)=>new Promise((_resolve,reject)=>{
    options?.signal?.addEventListener('abort',()=>reject(new DOMException('Annulée','AbortError')),{once:true});}));
  const controller=new AbortController();const pending=documentApi.discover('project1','ce_request','link1',controller.signal);
  const rejected=expect(pending).rejects.toThrow('Annulée');controller.abort();await rejected;
  expect(vi.mocked(request).mock.calls[0][1]?.signal?.aborted).toBe(true);
});

it('applique le délai de 30 secondes même en présence du signal de la vue',async()=>{
  vi.useFakeTimers();vi.mocked(request).mockImplementation((_url,options)=>new Promise((_resolve,reject)=>{
    options?.signal?.addEventListener('abort',()=>reject(new DOMException('Annulée','AbortError')),{once:true});}));
  const controller=new AbortController();const pending=documentApi.discover('project1','ce_request','link1',controller.signal);
  const rejected=expect(pending).rejects.toThrow('Recherche trop longue');await vi.advanceTimersByTimeAsync(30_000);await rejected;
  expect(vi.getTimerCount()).toBe(0);expect(controller.signal.aborted).toBe(false);
});

it('libère délai et écouteur après erreur de découverte',async()=>{
  vi.useFakeTimers();vi.mocked(request).mockRejectedValue(new Error('Lien modifié'));const controller=new AbortController();
  const remove=vi.spyOn(controller.signal,'removeEventListener');
  await expect(documentApi.discover('project1','ce_request','link1',controller.signal)).rejects.toThrow('Lien modifié');
  expect(remove).toHaveBeenCalledWith('abort',expect.any(Function));expect(vi.getTimerCount()).toBe(0);
});

it('envoie le jeton local et les deux empreintes puis vérifie les octets reçus',async()=>{
  const result=await documentApi.copy('project1',choice,preview);expect(result.filename).toBe('Copie CE.docx');expect(result.sha256).toBe(output);
  expect(result.blob.size).toBe(bytes.byteLength);const [url,options]=vi.mocked(fetch).mock.calls[0];expect(url).toBe('/api/v1/projects/project1/documents/prepare-copy');
  expect(options?.credentials).toBe('same-origin');expect(options?.headers).toEqual({'Content-Type':'application/json','X-Agent-Token':'local-token'});
  expect(JSON.parse(options?.body as string)).toEqual({...choice,expected_source_sha256:preview.source_sha256,expected_link_sha256:preview.link_sha256,expected_values_sha256:preview.values_sha256,
    expected_identity_revision:2,expected_planning_revision:4});expect(crypto.subtle.digest).toHaveBeenCalledWith('SHA-256',expect.any(ArrayBuffer));
});

it.each(['project','template','link','path','blocked','reader'])('refuse un aperçu différent ou interdit avant requête : %s',async(kind)=>{
  const wrong=structuredClone(preview);if(kind==='project')wrong.source.project_id='foreign';else if(kind==='template')wrong.document_id='tdao';
  else if(kind==='link')wrong.source.link_id='foreign';else if(kind==='path')wrong.source.relative_path='other.docx';
  else if(kind==='reader')wrong.can_prepare_copy=false;else wrong.can_prepare=false;
  await expect(documentApi.copy('project1',choice,wrong)).rejects.toThrow();expect(fetch).not.toHaveBeenCalled();
});

it.each(['source','link','values','publication','etag','size','empty','digest'])('refuse une copie incompatible ou altérée : %s',async(kind)=>{
  const headers:Record<string,string>={};if(kind==='source')headers['x-agent-source-sha256']='d'.repeat(64);
  if(kind==='values')headers['x-agent-values-sha256']='d'.repeat(64);if(kind==='publication')headers['x-agent-network-published']='true';
  if(kind==='link')headers['x-agent-link-sha256']='d'.repeat(64);
  if(kind==='etag')headers.etag='absent';if(kind==='size')headers['content-length']='52428801';
  if(kind==='digest')vi.mocked(crypto.subtle.digest).mockResolvedValue(new Uint8Array(32).buffer);
  vi.mocked(fetch).mockResolvedValue(response(headers,kind==='empty'?new ArrayBuffer(0):bytes.buffer as ArrayBuffer));
  await expect(documentApi.copy('project1',choice,preview)).rejects.toThrow();
});

it('préserve un conflit 409 et invalide la session seulement après refus 403',async()=>{
  vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({detail:'Contact modifié'}),{status:409}));
  await expect(documentApi.copy('project1',choice,preview)).rejects.toEqual(new DocumentHttpError(409,'Contact modifié'));
  expect(invalidateSession).not.toHaveBeenCalled();
  vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({detail:'Session expirée'}),{status:403}));
  await expect(documentApi.copy('project1',choice,preview)).rejects.toThrow('Session expirée');expect(invalidateSession).toHaveBeenCalledOnce();
});

it('annule aussi pendant la vérification cryptographique et retire les écouteurs',async()=>{
  const controller=new AbortController();const remove=vi.spyOn(controller.signal,'removeEventListener');
  let done!:(value:ArrayBuffer)=>void;vi.mocked(crypto.subtle.digest).mockReturnValue(new Promise(resolve=>{done=resolve;}));
  const result=documentApi.copy('project1',choice,preview,controller.signal);const rejected=expect(result).rejects.toThrow('Préparation annulée');
  await vi.waitFor(()=>expect(crypto.subtle.digest).toHaveBeenCalledOnce());controller.abort();done(new Uint8Array(32).fill(204).buffer);
  await rejected;expect(remove).toHaveBeenCalledWith('abort',expect.any(Function));
});

it('une annulation avant le jeton ne lance aucun téléchargement',async()=>{
  const controller=new AbortController();controller.abort();await expect(documentApi.copy('project1',choice,preview,controller.signal)).rejects.toThrow('Préparation annulée');
  expect(fetch).not.toHaveBeenCalled();
});

it('la durée maximale annule la requête même sans signal fourni',async()=>{
  vi.useFakeTimers();vi.mocked(fetch).mockImplementation((_url,options)=>new Promise((_resolve,reject)=>{
    options?.signal?.addEventListener('abort',()=>reject(new DOMException('Timeout','AbortError')),{once:true});}));
  const result=documentApi.copy('project1',choice,preview);const rejected=expect(result).rejects.toThrow('Timeout');
  await vi.advanceTimersByTimeAsync(120_000);await rejected;expect(vi.getTimerCount()).toBe(0);
});
