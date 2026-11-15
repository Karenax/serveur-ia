import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {getActivitySnapshot} from './asyncActivity';
import {streamAssistant} from './assistantStream';
import {noteRequest} from './projectNotes';
import {deliverableApi} from './projectDeliverables';
import {meetingSessions} from './meetingSessions';
import {documentJobApi} from './projectDocumentJobs';
import {workspaceApi} from './workspaceApi';
import {request} from './http';

vi.mock('./http',()=>({request:vi.fn(),token:vi.fn().mockResolvedValue('test-token'),invalidateSession:vi.fn()}));
const deferred=<T,>()=>{let resolve!:(value:T)=>void;const promise=new Promise<T>(done=>{resolve=done;});return {promise,resolve};};
beforeEach(()=>{vi.mocked(request).mockResolvedValue({items:[],project_id:'p1',job_id:'j1'});});
afterEach(()=>{expect(getActivitySnapshot()).toBeNull();vi.useRealTimers();vi.clearAllMocks();vi.unstubAllGlobals();});

it('conserve l’indicateur des notes jusqu’au décodage JSON, puis le ferme',async()=>{
  const body=deferred<{title:string}>();
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:()=>body.promise}));
  const pending=noteRequest('/api/v1/projects/p1/notes',{method:'POST',body:'{}'});
  expect(getActivitySnapshot()?.label).toBe('Enregistrement de la note…');
  await Promise.resolve();await Promise.resolve();
  expect(getActivitySnapshot()).not.toBeNull();
  body.resolve({title:'Note'});await expect(pending).resolves.toEqual({title:'Note'});
  expect(getActivitySnapshot()).toBeNull();
});

it('garde la lecture des notes silencieuse et propage un JSON invalide',async()=>{
  vi.useFakeTimers();const body=deferred<unknown>();
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,json:()=>body.promise.then(()=>{throw new SyntaxError('JSON invalide');})}));
  const pending=noteRequest('/api/v1/projects/p1/notes');const failure=expect(pending).rejects.toThrow('JSON invalide');
  expect(getActivitySnapshot()).toBeNull();await vi.advanceTimersByTimeAsync(10_000);
  expect(getActivitySnapshot()).toBeNull();
  body.resolve(null);await failure;expect(getActivitySnapshot()).toBeNull();
});

it('attend les octets du livrable après la réception des en-têtes',async()=>{
  const bytes=deferred<Blob>();vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,blob:()=>bytes.promise}));
  const pending=deliverableApi.download('p1','d1','v1','file');
  await Promise.resolve();expect(getActivitySnapshot()?.label).toBe('Téléchargement du livrable…');
  bytes.resolve(new Blob(['Contenu fictif']));await expect(pending).resolves.toBeInstanceOf(Blob);
  expect(getActivitySnapshot()).toBeNull();
});

it('suit la génération SSE jusqu’à sa fin et ferme le suivi avant toute réponse refusée',async()=>{
  let controller!:ReadableStreamDefaultController<Uint8Array>;
  const body=new ReadableStream<Uint8Array>({start(value){controller=value;}});
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:true,body}));
  const pending=streamAssistant('Question fictive','',false,[],new AbortController().signal,vi.fn());
  expect(getActivitySnapshot()?.label).toBe('Recherche et rédaction de la réponse…');
  await Promise.resolve();await Promise.resolve();
  controller.enqueue(new TextEncoder().encode('event: done\ndata: {"answer":"Réponse fictive"}\n\n'));controller.close();
  await expect(pending).resolves.toMatchObject({answer:'Réponse fictive'});
  expect(getActivitySnapshot()).toBeNull();
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:502,json:async()=>({detail:'Modèle indisponible'})}));
  await expect(streamAssistant('Question fictive','',false,[],new AbortController().signal,vi.fn())).rejects.toThrow('Modèle indisponible');
  expect(getActivitySnapshot()).toBeNull();
});

it('rend le polling silencieux tout en conservant les lectures utilisateur suivies',async()=>{
  await meetingSessions.get('s1',undefined,true);await meetingSessions.enhancements('s1',undefined,true);
  await meetingSessions.liveAnswers('s1',undefined,true);await meetingSessions.nativeStatus('s1',undefined,true);
  await documentJobApi.list('p1',0,undefined,true);await documentJobApi.detail('p1','j1',undefined,true);
  await workspaceApi.meetings({},undefined,true);await workspaceApi.jobs({},undefined,true);
  await workspaceApi.latestTriage(undefined,true);await workspaceApi.triageJob('t1',undefined,true);
  expect(vi.mocked(request).mock.calls).toHaveLength(10);
  for(const call of vi.mocked(request).mock.calls)expect(call[1]?.activity).toBe(false);
  vi.mocked(request).mockClear();await meetingSessions.get('s1');await workspaceApi.meetings();
  for(const call of vi.mocked(request).mock.calls)expect(call[1]?.activity).not.toBe(false);
});
