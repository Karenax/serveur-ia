import { afterEach, expect, it, vi } from 'vitest';
import { waitFor } from '@testing-library/react';
import { MeetingCaptureController, type DurableAudioChunk, type DurableChunkStore } from './meetingCapture';
import type {BrowserReservation} from './browserCaptureReservation';
import type { MeetingSession } from './meetingSessions';

afterEach(() => {vi.restoreAllMocks();vi.unstubAllGlobals();});
const row: MeetingSession = {id:'session-1',title:'Revue mécanique',kind:'meeting',project_id:null,brain_project_id:null,
  state:'created',revision:1,date:'2026-10-11',recording_id:null,note_id:null,tracks:[],chunks:[],total_bytes:0,duration_seconds:0,
  issues:[],created_at:'2026-10-11T10:00:00Z',updated_at:'2026-10-11T10:00:00Z'};
class MemoryChunks implements DurableChunkStore {
  items = new Map<string,DurableAudioChunk>();
  ready = vi.fn(async()=>undefined);
  put = vi.fn(async(chunk:DurableAudioChunk)=>{this.items.set(chunk.id,chunk);});
  list = vi.fn(async(sessionId?:string)=>[...this.items.values()].filter(chunk=>!sessionId||chunk.session_id===sessionId));
  acknowledge = vi.fn(async(id:string)=>{this.items.delete(id);});
}
function harness(store = new MemoryChunks(), startFailure?: Error) {
  let server: MeetingSession = {...row};
  let savedReservation: BrowserReservation | null = null;
  const reservations = {read:vi.fn(()=>savedReservation),write:vi.fn((value:BrowserReservation)=>{savedReservation=structuredClone(value);}),clear:vi.fn(()=>{savedReservation=null;})};
  const reserveReceipts=new Map<string,MeetingSession>();
  const release = vi.fn(), stopTrack = vi.fn();
  const track = {stop:stopTrack,onended:null};
  const stream = {getTracks:()=>[track],getAudioTracks:()=>[track]};
  const devices = {getUserMedia:vi.fn(async()=>stream)} as unknown as MediaDevices;
  let recorder: FakeRecorder | undefined;
  class FakeRecorder {
    state = 'inactive'; mimeType='audio/webm'; ondataavailable:((event:BlobEvent)=>void)|null=null;
    onstop:((event:Event)=>void)|null=null; onerror:((event:Event)=>void)|null=null;
    constructor(){recorder=this;}
    static isTypeSupported(){return true;}
    start(){if(startFailure)throw startFailure;this.state='recording';}
    pause(){this.state='paused';}
    resume(){this.state='recording';}
    stop(){this.state='inactive';this.onstop?.(new Event('stop'));}
    emit(text:string){this.ondataavailable?.({data:new Blob([text],{type:'audio/webm'})} as BlobEvent);}
  }
  const api = {
    get:vi.fn(async()=>server),
    commandReceipt:vi.fn(async()=>({id:'unknown',kind:'browser.reserve',status:'prepared'})),
    browserReserve:vi.fn(async(_id:string,body:{command_id:string;owner_id:string})=>{
      const previous=reserveReceipts.get(body.command_id);if(previous)return previous;
      server={...server,revision:server.revision+1,browser_capture:{owner_id:body.owner_id,state:'reserved',can_control:true}};
      reserveReceipts.set(body.command_id,server);return server;
    }),
    browserRelease:vi.fn(async(_id:string,_body:{command_id:string;expected_revision:number;owner_id:string})=>{
      server={...server,revision:server.revision+1,browser_capture:null,
        state:['recording','paused'].includes(server.state)?'interrupted':server.state};return server;
    }),
    command:vi.fn(async(_id:string,action:string,_body?:{browser_capture_owner_id?:string})=>{server={...server,revision:server.revision+1,
      state:action==='resume'?'recording':action==='pause'?'paused':'completed'};return server;}),
    chunk:vi.fn(async(id:string,name:string,seq:number,form:FormData)=>({session_id:id,acknowledged:true,replayed:false,revision:server.revision,
      accepted_chunk:{track:name,seq,sha256:String(form.get('sha256')),size_bytes:(form.get('file') as Blob).size}})),
  };
  const controller = new MeetingCaptureController({reservationStore:reservations,store,api:api as never,environment:{devices:()=>devices,
    recorder:()=>FakeRecorder as unknown as typeof MediaRecorder,lock:async()=>release,hash:async()=> 'a'.repeat(64),now:()=>2000}});
  return {controller,store,api,devices,reservations,changeRevision:()=>{server={...server,revision:server.revision+1};},release,stopTrack,recorder:()=>recorder!};
}

it('sauvegarde le Blob avant le transfert et ne retire que le fragment acquitté',async()=>{
  const h=harness();await h.controller.start(row.id);
  h.api.chunk.mockImplementation(async(id,name,seq,form)=>{
    expect(h.store.items.size).toBe(1);expect(h.store.put).toHaveBeenCalledTimes(1);
    return {session_id:id,acknowledged:true,replayed:false,revision:row.revision,
      accepted_chunk:{track:name,seq,sha256:String(form.get('sha256')),size_bytes:(form.get('file') as Blob).size}};
  });
  h.recorder().emit('audio');
  await waitFor(()=>expect(h.store.acknowledge).toHaveBeenCalledTimes(1));
  const form=h.api.chunk.mock.calls[0]?.[3] as unknown as FormData;
  expect(form.get('sha256')).toBe('a'.repeat(64));
  expect(form.get('command_id')).toBeTruthy();expect(h.store.items.size).toBe(0);
  await h.controller.stop();
});

it('conserve la capture quand toutes les vues se désabonnent',async()=>{
  const h=harness();const unsubscribe=h.controller.subscribe(vi.fn());await h.controller.start(row.id);unsubscribe();
  expect(h.recorder().state).toBe('recording');expect(h.stopTrack).not.toHaveBeenCalled();
  h.recorder().emit('audio');await waitFor(()=>expect(h.api.chunk).toHaveBeenCalledTimes(1));
  await h.controller.stop();expect(h.stopTrack).toHaveBeenCalledTimes(1);expect(h.release).toHaveBeenCalledTimes(1);
});

it('garde les fragments hors réseau et les reprend avec les mêmes clés avant finalisation',async()=>{
  const h=harness();h.api.chunk.mockRejectedValue(new Error('Réseau absent'));await h.controller.start(row.id);
  h.recorder().emit('partie conservée');await waitFor(()=>expect(h.controller.getSnapshot().pending).toBe(1));
  await h.controller.stop();
  expect(h.controller.getSnapshot().phase).toBe('pending');expect(h.store.items.size).toBe(1);
  expect(h.api.command.mock.calls.some(call=>call[1]==='finalize')).toBe(false);
  const firstForm=h.api.chunk.mock.calls[0]?.[3] as unknown as FormData;
  const recovered=harness(h.store);await recovered.controller.recover();
  expect(recovered.controller.getSnapshot().sessionId).toBe(row.id);
  await recovered.controller.retryAndFinalize();
  const retriedForm=recovered.api.chunk.mock.calls[0]?.[3] as unknown as FormData;
  expect(retriedForm.get('command_id')).toBe(firstForm.get('command_id'));
  expect(recovered.store.items.size).toBe(0);expect(recovered.controller.getSnapshot().phase).toBe('completed');
});

it('refuse un second démarrage et ne demande pas un deuxième microphone',async()=>{
  const h=harness();await h.controller.start(row.id);
  await expect(h.controller.start('another')).rejects.toThrow(/déjà ouverte/);
  await h.controller.stop();
});

it('libère le microphone et le verrou quand le navigateur refuse de démarrer le Recorder',async()=>{
  const h=harness(new MemoryChunks(),new Error('Périphérique audio indisponible'));
  await expect(h.controller.start(row.id)).rejects.toThrow('Périphérique audio indisponible');
  expect(h.controller.getSnapshot()).toMatchObject({phase:'error',error:'Périphérique audio indisponible'});
  expect(h.stopTrack).toHaveBeenCalledTimes(1);expect(h.release).toHaveBeenCalledTimes(1);
  expect(h.api.command.mock.calls.map(call=>call[1])).toEqual(['resume','pause']);
  expect((await h.api.get()).state).toBe('interrupted');expect(h.api.browserRelease).toHaveBeenCalledTimes(1);expect(h.api.chunk).not.toHaveBeenCalled();
});

it('libère aussi le microphone si le serveur refuse la remise en pause après un échec de capture',async()=>{
  const h=harness(new MemoryChunks(),new Error('Format audio refusé'));
  const command=h.api.command.getMockImplementation()!;
  h.api.command.mockImplementation(async(id,action)=>{
    if(action==='pause')throw new Error('Serveur indisponible');
    return command(id,action);
  });
  await expect(h.controller.start(row.id)).rejects.toThrow('Format audio refusé');
  expect(h.stopTrack).toHaveBeenCalledTimes(1);expect(h.release).toHaveBeenCalledTimes(1);
  expect(h.controller.getSnapshot()).toMatchObject({phase:'error',error:'Format audio refusé'});
});

it('ne finalise pas une séance quand la sauvegarde du fragment a échoué',async()=>{
  const h=harness();h.store.put.mockRejectedValue(new Error('Disque indisponible'));await h.controller.start(row.id);
  h.recorder().emit('audio non sauvegardé');
  await waitFor(()=>expect(h.controller.getSnapshot().phase).toBe('pending'));
  expect(h.api.chunk).not.toHaveBeenCalled();expect(h.api.command.mock.calls.some(call=>call[1]==='finalize')).toBe(false);
  expect(h.controller.getSnapshot().error).toMatch(/sauvegard|Disque/);
  h.store.put.mockImplementation(async(chunk)=>{h.store.items.set(chunk.id,chunk);});
  await h.controller.retryAndFinalize();
  expect(h.api.chunk).toHaveBeenCalledTimes(1);expect(h.controller.getSnapshot().phase).toBe('completed');
});

it('conserve le fragment si la réponse réseau acquitte un autre contenu',async()=>{
  const h=harness();h.api.chunk.mockImplementation(async(id,name,seq,form)=>({session_id:id,acknowledged:true,replayed:false,revision:1,
    accepted_chunk:{track:name,seq,sha256:'b'.repeat(64),size_bytes:(form.get('file') as Blob).size}}));
  await h.controller.start(row.id);h.recorder().emit('fragment');
  await waitFor(()=>expect(h.controller.getSnapshot().error).toMatch(/acquittement/));
  expect(h.store.items.size).toBe(1);expect(h.store.acknowledge).not.toHaveBeenCalled();
  await h.controller.stop();expect(h.controller.getSnapshot().phase).toBe('pending');
});

it('attend la réservation avant tout média',async()=>{
  const h=harness();let grant:()=>void=()=>{};
  const reserve=h.api.browserReserve.getMockImplementation()!;
  h.api.browserReserve.mockImplementation((id,body)=>new Promise(resolve=>{grant=()=>void reserve(id,body).then(resolve);}));
  const start=h.controller.start(row.id);
  await waitFor(()=>expect(h.api.browserReserve).toHaveBeenCalledTimes(1));
  expect(h.devices.getUserMedia).not.toHaveBeenCalled();grant();
  await start;expect(h.devices.getUserMedia).toHaveBeenCalledTimes(1);await h.controller.stop();
});

it('n’ouvre aucun média si Windows possède déjà la capture',async()=>{
  const h=harness();h.api.browserReserve.mockRejectedValue(new Error('Capture Windows occupée'));
  await expect(h.controller.start(row.id)).rejects.toThrow('Capture Windows occupée');
  expect(h.devices.getUserMedia).not.toHaveBeenCalled();expect(h.api.command).not.toHaveBeenCalled();
  expect(h.controller.getSnapshot().phase).toBe('pending');expect(h.reservations.read()).not.toBeNull();
});

it('garde le propriétaire en pause et ferme les pistes avant release',async()=>{
  const h=harness();await h.controller.start(row.id);await h.controller.pause();
  expect(h.api.browserRelease).not.toHaveBeenCalled();expect(h.stopTrack).not.toHaveBeenCalled();
  const owner=h.reservations.read()!.owner_id;
  expect(h.api.command.mock.calls.every(call=>(call[2] as {browser_capture_owner_id?:string}).browser_capture_owner_id===owner)).toBe(true);
  h.api.browserRelease.mockImplementation(async()=>{expect(h.stopTrack).toHaveBeenCalledTimes(1);return {...row,state:'interrupted',browser_capture:null};});
  await h.controller.stop();expect(h.reservations.read()).toBeNull();
});

it('libère après refus de permission sans finaliser',async()=>{
  const h=harness();vi.mocked(h.devices.getUserMedia).mockRejectedValue(new Error('Permission refusée'));
  await expect(h.controller.start(row.id)).rejects.toThrow('Permission refusée');
  expect(h.api.browserRelease).toHaveBeenCalledTimes(1);expect(h.api.command).not.toHaveBeenCalled();
  expect((await h.api.get()).state).toBe('created');expect(h.reservations.read()).toBeNull();
});

it('ferme une piste reçue tardivement avant de libérer une demande d’arrêt',async()=>{
  const h=harness();let resolveMedia:(value:MediaStream)=>void=()=>{};
  const original=vi.mocked(h.devices.getUserMedia).getMockImplementation()!;
  vi.mocked(h.devices.getUserMedia).mockImplementation(()=>new Promise(resolve=>{resolveMedia=resolve;}));
  const start=h.controller.start(row.id);
  await waitFor(()=>expect(h.devices.getUserMedia).toHaveBeenCalledTimes(1));
  const stop=h.controller.stop();expect(h.api.browserRelease).not.toHaveBeenCalled();
  resolveMedia(await original({audio:true}));await expect(start).rejects.toThrow('annulé');await stop;
  expect(h.stopTrack).toHaveBeenCalledTimes(1);expect(h.api.command.mock.calls.some(call=>call[1]==='resume')).toBe(false);
  expect(h.reservations.read()).toBeNull();
});

it('reprend la même clé après réponse reserve perdue sans réouvrir',async()=>{
  const h=harness();const reserve=h.api.browserReserve.getMockImplementation()!;
  h.api.browserReserve.mockImplementationOnce(async(id,body)=>{await reserve(id,body);throw new Error('Réponse perdue');});
  await expect(h.controller.start(row.id)).rejects.toThrow('Réponse perdue');
  const original=h.api.browserReserve.mock.calls[0];await h.controller.retryAndFinalize();
  expect(h.api.browserReserve.mock.calls[0]).toEqual(original);expect(h.api.browserReserve).toHaveBeenCalledTimes(1);expect(h.devices.getUserMedia).not.toHaveBeenCalled();
  expect(h.reservations.read()).toBeNull();
});

it('attend un clic frais avant le partage système',async()=>{
  const h=harness();const track={stop:vi.fn()};
  const display=vi.fn(async()=>({getTracks:()=>[track],getAudioTracks:()=>[track]} as unknown as MediaStream));
  Object.assign(h.devices,{getDisplayMedia:display});
  vi.stubGlobal('MediaStream',class {constructor(private tracks:MediaStreamTrack[]){}getAudioTracks(){return this.tracks;}});
  await h.controller.start(row.id,{system:true});
  expect(h.controller.getSnapshot().phase).toBe('ready');expect(display).not.toHaveBeenCalled();expect(h.devices.getUserMedia).not.toHaveBeenCalled();
  const start=h.controller.activatePrepared();expect(display).toHaveBeenCalledTimes(1);expect(h.devices.getUserMedia).not.toHaveBeenCalled();
  await start;await h.controller.stop();
});

it('annule le partage préparé sans média ni publication',async()=>{
  const h=harness();await h.controller.start(row.id,{system:true});await h.controller.cancelPrepared();
  expect(h.devices.getUserMedia).not.toHaveBeenCalled();expect(h.api.command).not.toHaveBeenCalled();
  expect(h.controller.getSnapshot().phase).toBe('idle');expect(h.reservations.read()).toBeNull();
});

it('refuse la libération récupérée si un autre onglet tient encore ses pistes',async()=>{
  const h=harness();await h.controller.start(row.id);
  const other=new MeetingCaptureController({store:h.store,api:h.api as never,reservationStore:h.reservations,
    environment:{lock:async()=>{throw new Error('Autre onglet actif');}}});
  await other.recover();await other.stop();
  expect(h.api.browserRelease).not.toHaveBeenCalled();expect(h.recorder().state).toBe('recording');expect(h.stopTrack).not.toHaveBeenCalled();
  expect(other.getSnapshot()).toMatchObject({phase:'pending',error:'Autre onglet actif'});await h.controller.stop();
});

it('n’écrase pas une capture active avec une récupération tardive d’une autre séance',async()=>{
  const h=harness();let resolveList:(value:DurableAudioChunk[])=>void=()=>{};
  h.store.list.mockImplementationOnce(()=>new Promise(resolve=>{resolveList=resolve;}));
  const recovering=h.controller.recover();await h.controller.start(row.id);
  resolveList([{session_id:'other-session'} as DurableAudioChunk]);await recovering;
  expect(h.controller.getSnapshot()).toMatchObject({sessionId:row.id,phase:'recording'});await h.controller.stop();
});

it('reprend release avec un nouveau UUID seulement après une révision supérieure du même propriétaire',async()=>{
  const h=harness();await h.controller.start(row.id);
  h.api.browserRelease.mockImplementationOnce(async()=>{h.changeRevision();throw new Error('Révision différente');});
  await h.controller.stop();
  const [first,second]=h.api.browserRelease.mock.calls.map(call=>call[1]);
  expect(second.command_id).not.toBe(first.command_id);expect(second.owner_id).toBe(first.owner_id);
  expect(second.expected_revision).toBeGreaterThan(first.expected_revision);expect(h.reservations.read()).toBeNull();
});

it('oublie uniquement une réserve dont le rejet du UUID exact est confirmé',async()=>{
  const h=harness();h.api.browserReserve.mockRejectedValue(new Error('Capture Windows occupée'));
  await expect(h.controller.start(row.id)).rejects.toThrow('Capture Windows occupée');
  h.api.commandReceipt.mockResolvedValue({id:h.reservations.read()!.reserve.command_id,kind:'browser.reserve',status:'rejected'});
  await h.controller.retryAndFinalize();
  expect(h.api.browserRelease).not.toHaveBeenCalled();expect(h.devices.getUserMedia).not.toHaveBeenCalled();expect(h.reservations.read()).toBeNull();
});
