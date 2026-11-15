import { afterEach,beforeEach,expect,it,vi } from 'vitest';
import { request } from './http';
import { publicationApi,pendingKey,readPending,type PublicationCommand } from './projectDocumentPublications';
vi.mock('./http',()=>({request:vi.fn()}));
const command:PublicationCommand={command_id:'c1',link_id:'l1',relative_directory:'Copies',replace_existing:true,reviewed:true,
  expected_revision:9,expected_preview_sha256:'a'.repeat(64)};
const record={project_id:'p/1',job_id:'j/1',artifact_id:'a/1',command_id:'c1'};
beforeEach(()=>{vi.mocked(request).mockResolvedValue(record);localStorage.clear();});
afterEach(()=>{vi.clearAllMocks();vi.useRealTimers();localStorage.clear();});
it('envoie une commande stable avec identifiants encodés',async()=>{
  await publicationApi.publish('p/1','j/1','a/1',command);
  expect(request).toHaveBeenCalledWith('/api/v1/projects/p%2F1/documents/artifacts/a%2F1/publish',{
    method:'POST',body:JSON.stringify(command),signal:expect.any(AbortSignal)});
});
it.each(['project_id','job_id','artifact_id','command_id'])('refuse un reçu de mauvaise portée : %s',async key=>{
  vi.mocked(request).mockResolvedValue({...record,[key]:'foreign'});
  await expect(publicationApi.publish('p/1','j/1','a/1',command)).rejects.toThrow();
});
it('filtre et pagine les reçus de la copie sélectionnée',async()=>{
  vi.mocked(request).mockResolvedValue({project_id:'p/1',job_id:'j/1',items:[record],total:21,offset:20,limit:20});
  await publicationApi.list('p/1','j/1','a/1',20);
  expect(request).toHaveBeenCalledWith('/api/v1/projects/p%2F1/documents/jobs/j%2F1/publications?artifact_id=a%2F1&offset=20&limit=20',{signal:expect.any(AbortSignal)});
  vi.mocked(request).mockResolvedValue({project_id:'p/1',job_id:'j/1',items:[{...record,artifact_id:'foreign'}]});
  await expect(publicationApi.list('p/1','j/1','a/1')).rejects.toThrow();
});
it('clôture par CAS en conservant les fichiers, sans publication',async()=>{
  await publicationApi.abandon('p/1','j/1','a/1','c1',{expected_revision:10,retain_files:true,reviewed:true});
  expect(request).toHaveBeenCalledWith('/api/v1/projects/p%2F1/documents/jobs/j%2F1/publications/c1/abandon',{
    method:'POST',body:'{"expected_revision":10,"retain_files":true,"reviewed":true}',signal:expect.any(AbortSignal)});
});
it.each([['list',15000],['publish',120000]] as const)('borne %s même avec un signal parent',async(kind,delay)=>{
  vi.useFakeTimers();vi.mocked(request).mockImplementation((_url,init)=>new Promise((_resolve,reject)=>{
    init?.signal?.addEventListener('abort',()=>reject(new DOMException('Timeout','AbortError')));}));
  const parent=new AbortController();const pending=kind==='list'?publicationApi.list('p/1','j/1','a/1',0,parent.signal):publicationApi.publish('p/1','j/1','a/1',command,parent.signal);
  const rejected=expect(pending).rejects.toThrow('Timeout');await vi.advanceTimersByTimeAsync(delay);await rejected;
  expect(parent.signal.aborted).toBe(false);expect(vi.getTimerCount()).toBe(0);
});
it('n’envoie aucune requête déjà annulée',async()=>{
  const controller=new AbortController();controller.abort();
  await expect(publicationApi.publish('p/1','j/1','a/1',command,controller.signal)).rejects.toThrow('annulée');
  expect(request).not.toHaveBeenCalled();
});
it('récupère uniquement la commande figée de ce projet et cette copie',()=>{
  localStorage.setItem(pendingKey('p1','a1'),JSON.stringify(command));expect(readPending('p1','a1')).toEqual(command);
  expect(readPending('p2','a1')).toBeNull();expect(readPending('p1','a2')).toBeNull();
  localStorage.setItem(pendingKey('p1','a1'),JSON.stringify({...command,actor_id:'forged'}));expect(()=>readPending('p1','a1')).toThrow();
  localStorage.setItem(pendingKey('p1','a1'),JSON.stringify({...command,command_id:123}));expect(()=>readPending('p1','a1')).toThrow();
});
it('conserve exactement une ancienne commande v1 sans injecter de choix de remplacement',()=>{
  const {replace_existing:_unused,...legacy}=command;localStorage.setItem(pendingKey('p1','a1'),JSON.stringify(legacy));
  expect(readPending('p1','a1')).toEqual(legacy);expect(readPending('p1','a1')).not.toHaveProperty('replace_existing');
});
