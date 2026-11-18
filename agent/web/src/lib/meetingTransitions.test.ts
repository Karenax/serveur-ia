import {afterEach, expect, it, vi} from 'vitest';
import {meetingCapture} from './meetingCapture';
import {meetingSessions, type MeetingSession} from './meetingSessions';
import {createMeetingTransitions} from './meetingTransitions';

afterEach(() => {vi.restoreAllMocks(); vi.unstubAllGlobals();});
const session = {id:'session-a', revision:4} as MeetingSession;

it('permet d’annuler la demande de microphone pendant le démarrage encore en cours', async () => {
  let finishStart!: (row:MeetingSession) => void;
  const start = vi.spyOn(meetingCapture, 'start').mockReturnValue(new Promise(resolve => {finishStart = resolve;}));
  const stop = vi.spyOn(meetingCapture, 'stop').mockResolvedValue(null);
  const reload = vi.fn().mockResolvedValue(session), showTranscript = vi.fn();
  let running = false, work:Promise<void> = Promise.resolve();
  const run = (_label:string, task:()=>Promise<void>) => {
    if (running) return Promise.resolve();
    running = true;
    work = task().finally(() => {running = false;});
    return work;
  };
  const transitions = createMeetingTransitions({sessionId:session.id, captureOptions:{system:true}, maxUploadMb:1,
    reload, accept:vi.fn(), run, setNotice:vi.fn(), showTranscript, showSummary:vi.fn()});
  transitions.start();
  expect(start).toHaveBeenCalledWith(session.id, {system:true});
  expect(running).toBe(true);
  transitions.cancelStart();
  expect(stop).toHaveBeenCalledTimes(1);
  finishStart(session);
  await work;
  expect(reload).toHaveBeenCalledTimes(1);
  expect(showTranscript).toHaveBeenCalledTimes(1);
});

it('ne finalise pas un audio importé si son reçu ne correspond pas au fichier', async () => {
  const file = new File(['audio fictif'], 'audio.wav', {type:'audio/wav'});
  Object.defineProperty(file, 'arrayBuffer', {value:async () => new Uint8Array([1,2,3]).buffer});
  vi.stubGlobal('crypto', {subtle:{digest:vi.fn().mockResolvedValue(new Uint8Array([0xab]).buffer)},randomUUID:()=> 'command-id'});
  const chunk = vi.spyOn(meetingSessions, 'chunk').mockResolvedValue({acknowledged:true,session_id:session.id,
    accepted_chunk:{size_bytes:file.size,sha256:'empreinte-differente'}} as Awaited<ReturnType<typeof meetingSessions.chunk>>);
  const command = vi.spyOn(meetingSessions, 'command'), get = vi.spyOn(meetingSessions, 'get');
  const accept = vi.fn();let failure:unknown;let work:Promise<void> = Promise.resolve();
  const run = (_label:string, task:()=>Promise<void>) => {
    work = task().catch(error => {failure = error;});
    return work;
  };
  const transitions = createMeetingTransitions({sessionId:session.id,captureOptions:{},maxUploadMb:1,
    reload:async()=>session,accept,run,setNotice:vi.fn(),showTranscript:vi.fn(),showSummary:vi.fn()});
  transitions.importAudio(file);
  await work;
  expect(chunk).toHaveBeenCalledTimes(1);
  expect(failure).toEqual(new Error('L’acquittement de l’audio importé ne correspond pas au fichier.'));
  expect(command).not.toHaveBeenCalled();
  expect(get).not.toHaveBeenCalled();
  expect(accept).not.toHaveBeenCalled();
});

it.each([{track:'system',seq:0},{track:'mic',seq:1}])(
  'ne finalise pas un audio si le reçu désigne une autre piste ou séquence : $track / $seq', async accepted => {
    const file = new File(['audio fictif'], 'audio.wav', {type:'audio/wav'});
    Object.defineProperty(file, 'arrayBuffer', {value:async () => new Uint8Array([1,2,3]).buffer});
    vi.stubGlobal('crypto', {subtle:{digest:vi.fn().mockResolvedValue(new Uint8Array([0xab]).buffer)},randomUUID:()=> 'command-id'});
    vi.spyOn(meetingSessions, 'chunk').mockResolvedValue({acknowledged:true,session_id:session.id,
      accepted_chunk:{...accepted,size_bytes:file.size,sha256:'ab'}} as Awaited<ReturnType<typeof meetingSessions.chunk>>);
    const command=vi.spyOn(meetingSessions,'command'), get=vi.spyOn(meetingSessions,'get');
    let failure:unknown;let work:Promise<void>=Promise.resolve();
    const run=(_label:string,task:()=>Promise<void>)=>{work=task().catch(error=>{failure=error;});return work;};
    const transitions=createMeetingTransitions({sessionId:session.id,captureOptions:{},maxUploadMb:1,
      reload:async()=>session,accept:vi.fn(),run,setNotice:vi.fn(),showTranscript:vi.fn(),showSummary:vi.fn()});
    transitions.importAudio(file);
    await work;
    expect(failure).toEqual(new Error('L’acquittement de l’audio importé ne correspond pas au fichier.'));
    expect(get).not.toHaveBeenCalled();
    expect(command).not.toHaveBeenCalled();
  });

it('finalise après réception du fragment attendu et utilise la dernière révision', async () => {
  const file=new File(['audio fictif'],'audio.wav',{type:'audio/wav'});
  Object.defineProperty(file,'arrayBuffer',{value:async()=>new Uint8Array([1,2,3]).buffer});
  vi.stubGlobal('crypto',{subtle:{digest:vi.fn().mockResolvedValue(new Uint8Array([0xab]).buffer)},randomUUID:()=> 'command-id'});
  vi.spyOn(meetingSessions,'chunk').mockResolvedValue({acknowledged:true,session_id:session.id,
    accepted_chunk:{track:'mic',seq:0,size_bytes:file.size,sha256:'ab'}} as Awaited<ReturnType<typeof meetingSessions.chunk>>);
  const latest={...session,revision:5}, finished={...latest,state:'completed'} as MeetingSession;
  vi.spyOn(meetingSessions,'get').mockResolvedValue(latest);
  const command=vi.spyOn(meetingSessions,'command').mockResolvedValue(finished);
  const accept=vi.fn(),onChanged=vi.fn();let work:Promise<void>=Promise.resolve();
  const run=(_label:string,task:()=>Promise<void>)=>{work=task();return work;};
  const transitions=createMeetingTransitions({sessionId:session.id,captureOptions:{},maxUploadMb:1,
    reload:async()=>session,accept,run,setNotice:vi.fn(),showTranscript:vi.fn(),showSummary:vi.fn(),onChanged});
  transitions.importAudio(file);
  await work;
  expect(command).toHaveBeenCalledWith(session.id,'finalize',{command_id:'command-id',expected_revision:5});
  expect(accept).toHaveBeenCalledWith(finished);
  expect(onChanged).toHaveBeenCalledTimes(1);
});
