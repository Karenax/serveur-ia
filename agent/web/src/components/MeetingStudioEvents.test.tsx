import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import {MeetingStudio} from './MeetingStudio';
import {meetingSessions,type MeetingSession,type SessionCapabilities} from '../lib/meetingSessions';
import type {SessionEventOptions} from '../lib/sessionEvents';
import type {NoteContent} from '../lib/projectNotes';
import {meetingCapture} from '../lib/meetingCapture';

const note=(text:string):NoteContent=>({version:1,blocks:[{type:'paragraph',align:'left',runs:[{text,marks:[],href:null,color:null}]}]});
vi.mock('./NoteRichEditor',()=>({NoteRichEditor:({content,onChange}:{content:NoteContent;onChange:(content:NoteContent)=>void|boolean})=>
  <textarea aria-label="Note humaine" value={content.blocks[0]?.type==='paragraph'?content.blocks[0].runs.map(run=>run.text).join(''):''}
    onChange={event=>onChange(note(event.target.value))}/>,NoteContentView:()=>null}));
vi.mock('./MeetingAudioPanel',()=>({MeetingAudioPanel:()=>null}));
vi.mock('./MeetingNotePublication',()=>({MeetingNotePublication:()=>null}));
vi.mock('./MeetingCalendarContext',()=>({MeetingCalendarContext:()=>null}));

const row:MeetingSession={id:'A',title:'Séance fictive A',kind:'meeting',project_id:'erp',brain_project_id:'brain',state:'recording',revision:1,event_cursor:10,
  date:'2026-10-12',recording_id:null,note_id:'note',note_revision:1,note_version_id:'note-v1',
  note:{id:'note',project_id:'erp',title:'Note humaine',content:note('Réserve initiale non validée.'),revision:1,version_id:'note-v1',attachment_ids:[],read_only:false,source_kind:null,updated_at:'2026-10-12',actor_id:'local'},
  tracks:[],chunks:[],segments:[],total_bytes:0,duration_seconds:0,issues:[],created_at:'2026-10-12',updated_at:'2026-10-12'};
const caps:SessionCapabilities={enabled:true,capture:{durable:true,max_upload_mb:50,max_duration_minutes:120,tracks:['mic','system'],browser_permission_required:true},
  transcription:{enabled:false,batch_ready:false,live_ready:false,live_operational:false,detail:'Direct désactivé.'},notes:{staging:true,erp_projection:true}};
type Feed={id:string;options:SessionEventOptions;finish:()=>void};
let feeds:Feed[]=[],hidden=false;
let hiddenDescriptor:PropertyDescriptor|undefined;
const props=(id='A',active=true)=>({sessionId:id,active,rows:[],capabilities:caps,onClose:vi.fn(),onOpenProject:vi.fn()});
const changed=(id='A',cursor=11):MeetingSession=>({...row,id,event_cursor:cursor,segments:[{id:`segment-${id}`,track:'mic',start_ms:0,end_ms:2000,speaker:'Voix à identifier',
  text:`Segment canonique ${id} : ne pas démarrer sans consignation.`,revision:1,finalized:false}]});
async function tick(ms=0){await act(async()=>{await vi.advanceTimersByTimeAsync(ms);});}
async function emit(feed:Feed,id=11){await act(async()=>{feed.options.onEvent({id,kind:'transcript.updated',data:{text:'PAYLOAD QUI NE DOIT PAS ÊTRE APPLIQUÉ',note_version_id:'fausse-version'},revision:1,created_at:'2026-10-12T03:00:00Z'});});await tick(250);}
beforeEach(()=>{
  vi.useFakeTimers();localStorage.clear();localStorage.setItem('agent-meeting-layout-v2','complete');feeds=[];hidden=false;hiddenDescriptor=Object.getOwnPropertyDescriptor(document,'hidden');
  Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
  vi.spyOn(meetingSessions,'get').mockResolvedValue(row);
  vi.spyOn(meetingSessions,'enhancements').mockResolvedValue({items:[]});vi.spyOn(meetingSessions,'liveAnswers').mockResolvedValue({items:[]});
  vi.spyOn(meetingSessions,'askHistory').mockResolvedValue({items:[]});
  vi.spyOn(meetingSessions,'watchEvents').mockImplementation((id,options)=>new Promise(resolve=>{
    const feed={id,options,finish:resolve};feeds.push(feed);options.signal.addEventListener('abort',()=>resolve(),{once:true});
  }));
  vi.spyOn(globalThis,'fetch').mockRejectedValue(new Error('Aucun transport réel dans ce test'));
  vi.spyOn(meetingCapture,'start').mockResolvedValue(row);
});
afterEach(()=>{
  cleanup();vi.useRealTimers();vi.restoreAllMocks();localStorage.clear();
  if(hiddenDescriptor)Object.defineProperty(document,'hidden',hiddenDescriptor);else delete (document as unknown as {hidden?:boolean}).hidden;
});

it('une notification rend le snapshot canonique avant le poll5s, sans appliquer son payload ni lancer de capture',async()=>{
  render(<MeetingStudio {...props()}/>);await tick();
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(feeds).toHaveLength(1);vi.mocked(meetingSessions.get).mockResolvedValue(changed());
  await emit(feeds[0]);
  expect(screen.getByText(changed().segments![0].text)).toBeTruthy();
  expect(screen.queryByText('PAYLOAD QUI NE DOIT PAS ÊTRE APPLIQUÉ')).toBeNull();
  expect(meetingCapture.start).not.toHaveBeenCalled();expect(fetch).not.toHaveBeenCalled();
});
it('un GET ancien tardif ne retire ni segment reçu par événement ni brouillon humain',async()=>{
  let finish!:(value:MeetingSession)=>void;const slow=new Promise<MeetingSession>(resolve=>{finish=resolve;});
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(row).mockReturnValueOnce(slow).mockResolvedValue(changed());
  render(<MeetingStudio {...props()}/>);await tick();
  fireEvent.change(screen.getByLabelText('Note humaine'),{target:{value:'Ne pas valider la puissance : brouillon humain.'}});
  await tick(5000); // A slow fallback read is in flight while the notification arrives.
  await emit(feeds[0]);
  await act(async()=>{finish(row);});await tick();
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText(changed().segments![0].text)).toBeTruthy();
  expect(screen.getByLabelText('Note humaine')).toHaveProperty('value','Ne pas valider la puissance : brouillon humain.');
});
it('retour visible reprend par un snapshot frais et aucun callback ancien ne touche la séance B',async()=>{
  const view=render(<MeetingStudio {...props()}/>);await tick();const old=feeds[0];
  hidden=true;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});await tick();
  expect(old.options.signal.aborted).toBe(true);
  const next={...row,id:'B',title:'Séance fictive B',event_cursor:20};vi.mocked(meetingSessions.get).mockResolvedValue(next);
  view.rerender(<MeetingStudio {...props('B')}/>);await tick();
  const before=vi.mocked(meetingSessions.get).mock.calls.length;
  await emit(old);expect(vi.mocked(meetingSessions.get).mock.calls).toHaveLength(before);
  hidden=false;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});await tick();
  expect(feeds[feeds.length-1]?.id).toBe('B');expect(feeds[feeds.length-1]?.options.after).toBe(20);
  expect(screen.getByLabelText('Note humaine')).toHaveProperty('value','Réserve initiale non validée.');
});
it('navigation inactive arrête le flux et conserve les notes ; retour actif lit la version récente',async()=>{
  const view=render(<MeetingStudio {...props()}/>);await tick();const feed=feeds[0];
  fireEvent.change(screen.getByLabelText('Note humaine'),{target:{value:'Saisie conservée pendant navigation.'}});
  view.rerender(<MeetingStudio {...props('A',false)}/>);await tick();expect(feed.options.signal.aborted).toBe(true);
  const count=feeds.length;await tick(10_000);expect(feeds).toHaveLength(count);
  vi.mocked(meetingSessions.get).mockResolvedValue(changed('A',30));
  view.rerender(<MeetingStudio {...props()}/>);await tick();
  expect(feeds.length).toBeGreaterThan(count);expect(screen.getByLabelText('Note humaine')).toHaveProperty('value','Saisie conservée pendant navigation.');
});
it('la révocation terminale garde le brouillon et ne présente jamais le payload comme contenu',async()=>{
  render(<MeetingStudio {...props()}/>);await tick();
  fireEvent.change(screen.getByLabelText('Note humaine'),{target:{value:'Texte humain conservé après révocation.'}});
  vi.mocked(meetingSessions.get).mockRejectedValue(new Error('Séance introuvable'));
  await act(async()=>{feeds[0].options.onError?.({message:'Accès séance révoqué.',status:404,retryable:false});feeds[0].finish();});await tick();
  expect(screen.getByLabelText('Note humaine')).toHaveProperty('value','Texte humain conservé après révocation.');
  expect(screen.queryByText('PAYLOAD QUI NE DOIT PAS ÊTRE APPLIQUÉ')).toBeNull();expect(fetch).not.toHaveBeenCalled();
});
it('un événement n’attend pas le GET initial suspendu et restaure le brouillon sans régression tardive',async()=>{
  let finish!:(value:MeetingSession)=>void;const initial=new Promise<MeetingSession>(resolve=>{finish=resolve;});
  const human='Brouillon restauré : ne pas accepter cette cote.';
  localStorage.setItem('agent.meeting-note.v1.A',JSON.stringify({session_id:'A',content:note(human),title:'Note humaine',revision:1,note_version_id:'note-v1',command:null}));
  vi.mocked(meetingSessions.get).mockReturnValueOnce(initial).mockResolvedValue(changed());
  render(<MeetingStudio {...props()}/>);await tick();expect(feeds).toHaveLength(1);
  await emit(feeds[0]);fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText(changed().segments![0].text)).toBeTruthy();
  await act(async()=>{finish(row);});await tick();
  expect(screen.getByText(changed().segments![0].text)).toBeTruthy();expect(screen.getByLabelText('Note humaine')).toHaveProperty('value',human);
});
it('coalesce la rafale en attente et ignore les IDs doublonnés ou anciens',async()=>{
  render(<MeetingStudio {...props()}/>);await tick();
  let finish!:(value:MeetingSession)=>void;const pending=new Promise<MeetingSession>(resolve=>{finish=resolve;});
  vi.mocked(meetingSessions.get).mockReturnValueOnce(pending).mockResolvedValue(changed('A',13));
  const before=vi.mocked(meetingSessions.get).mock.calls.length;
  await emit(feeds[0],11);
  await act(async()=>{for(const id of [12,13,13,10])feeds[0].options.onEvent({id,kind:'transcript.updated',revision:1,data:{}});});
  expect(vi.mocked(meetingSessions.get).mock.calls).toHaveLength(before+1);
  await act(async()=>{finish(changed('A',13));});await tick(500);
  expect(vi.mocked(meetingSessions.get).mock.calls).toHaveLength(before+2);
  const after=vi.mocked(meetingSessions.get).mock.calls.length;
  await emit(feeds[0],12);await emit(feeds[0],13);expect(vi.mocked(meetingSessions.get).mock.calls).toHaveLength(after);
});
it('garde le wake-up après une lecture échouée et une reconnexion demande aussi le snapshot frais',async()=>{
  render(<MeetingStudio {...props()}/>);await tick();
  vi.mocked(meetingSessions.get).mockRejectedValueOnce(new Error('Lecture temporairement indisponible')).mockResolvedValue(changed());
  await emit(feeds[0]);await tick(500);
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));expect(screen.getByText(changed().segments![0].text)).toBeTruthy();
  const before=vi.mocked(meetingSessions.get).mock.calls.length;
  await act(async()=>{feeds[0].options.onConnected?.();});await tick();
  expect(vi.mocked(meetingSessions.get).mock.calls.length).toBeGreaterThan(before);
});
it('le fallback5s fonctionne quand le transport SSE est indisponible et reste muet après démontage',async()=>{
  vi.mocked(meetingSessions.watchEvents).mockRejectedValue(new Error('Transport SSE indisponible'));
  const view=render(<MeetingStudio {...props()}/>);await tick();
  const before=vi.mocked(meetingSessions.get).mock.calls.length;vi.mocked(meetingSessions.get).mockResolvedValue(changed());
  await tick(5000);expect(vi.mocked(meetingSessions.get).mock.calls.length).toBeGreaterThan(before);
  view.unmount();const after=vi.mocked(meetingSessions.get).mock.calls.length;
  await tick(10_000);expect(vi.mocked(meetingSessions.get).mock.calls).toHaveLength(after);expect(fetch).not.toHaveBeenCalled();
});
it('le contrôle de secours borne les lectures, les annule au masquage et conserve la note',async()=>{
  let finish!:(value:MeetingSession)=>void;const slow=new Promise<MeetingSession>(resolve=>{finish=resolve;});
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(row).mockReturnValueOnce(slow).mockReturnValueOnce(slow).mockResolvedValue(changed());
  render(<MeetingStudio {...props()}/>);await tick();
  fireEvent.change(screen.getByLabelText('Note humaine'),{target:{value:'Brouillon conservé pendant le masquage.'}});
  await tick(5000);
  const calls=vi.mocked(meetingSessions.get).mock.calls,firstSignal=calls[calls.length-1][1]!;
  await tick(10_000);const before=calls.length;expect(before).toBe(3);const secondSignal=calls[calls.length-1][1]!;
  hidden=true;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});expect(firstSignal.aborted).toBe(true);expect(secondSignal.aborted).toBe(true);
  await tick(10_000);expect(meetingSessions.get).toHaveBeenCalledTimes(before);
  hidden=false;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});await tick();
  expect(vi.mocked(meetingSessions.get).mock.calls.length).toBeGreaterThan(before);
  await act(async()=>{finish(row);});await tick();
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText(changed().segments![0].text)).toBeTruthy();
  expect(screen.getByLabelText('Note humaine')).toHaveProperty('value','Brouillon conservé pendant le masquage.');
});
it('le flux reprend immédiatement même si une lecture annulée ne se termine pas',async()=>{
  let finish!:(value:MeetingSession)=>void;const slow=new Promise<MeetingSession>(resolve=>{finish=resolve;});
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(row).mockReturnValueOnce(slow).mockResolvedValue(changed());
  render(<MeetingStudio {...props()}/>);await tick();
  await emit(feeds[0]);
  const calls=vi.mocked(meetingSessions.get).mock.calls,oldSignal=calls[calls.length-1][1]!;
  hidden=true;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});expect(oldSignal.aborted).toBe(true);
  hidden=false;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});await tick();
  const before=vi.mocked(meetingSessions.get).mock.calls.length;
  await act(async()=>{feeds[feeds.length-1].options.onConnected?.();});await tick();
  expect(vi.mocked(meetingSessions.get).mock.calls.length).toBeGreaterThan(before);
  await act(async()=>{finish(row);});await tick();
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText(changed().segments![0].text)).toBeTruthy();
});
it('la reprise explicite utilise la dernière révision et conserve le brouillon humain sans réenregistrer l’audio',async()=>{
  const failed={...row,chunks:[{id:'failed',track:'mic' as const,sequence:0,sha256:'a'.repeat(64),size_bytes:32044,start_ms:0,duration_ms:1000,
    created_at:'2026-10-12T03:00:00Z',speech_status:'failed' as const,speech_error:'Échec fictif'}]};
  vi.mocked(meetingSessions.get).mockResolvedValue(failed);
  const retry=vi.spyOn(meetingSessions,'retryTranscription').mockResolvedValue({session:{...failed,revision:3,event_cursor:12,
    chunks:[{...failed.chunks[0],speech_status:'pending'}]},retried_chunks:1,chunk_ids:['failed']});
  const capture=vi.spyOn(meetingSessions,'chunk');
  render(<MeetingStudio {...props()} capabilities={{...caps,transcription:{...caps.transcription,enabled:true}}}/>);await tick();
  fireEvent.change(screen.getByLabelText('Note humaine'),{target:{value:'Correction humaine à garder pendant reprise.'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));vi.mocked(meetingSessions.get).mockResolvedValue({...failed,revision:2});
  fireEvent.click(screen.getByRole('button',{name:'Reprendre un lot de transcription'}));await tick();
  expect(retry).toHaveBeenCalledExactlyOnceWith('A',expect.objectContaining({expected_revision:2,command_id:expect.any(String)}));
  expect(screen.getByText('1 fragment(s) admis pour transcription ; audio et corrections conservés.')).toBeTruthy();
  expect(screen.getByLabelText('Note humaine')).toHaveProperty('value','Correction humaine à garder pendant reprise.');
  expect(capture).not.toHaveBeenCalled();expect(meetingCapture.start).not.toHaveBeenCalled();
});

it('une lecture initiale échouée disparaît après le snapshot réussi du poll',async()=>{
  vi.mocked(meetingSessions.get).mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValue(row);
  render(<MeetingStudio {...props()}/>);await tick();
  expect(screen.getByRole('alert').textContent).toBe('Failed to fetch');
  await tick(5000);
  expect(screen.getByLabelText('Note humaine')).toHaveProperty('value','Réserve initiale non validée.');
  expect(screen.queryByText(/Failed to fetch/)).toBeNull();
  expect(meetingCapture.start).not.toHaveBeenCalled();
});

it('un échec de GET ancien ne restaure pas l’erreur après un snapshot plus récent réussi',async()=>{
  let reject!:(error:Error)=>void;const old=new Promise<MeetingSession>((_,failed)=>{reject=failed;});
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(row).mockReturnValueOnce(old).mockResolvedValue(changed());
  render(<MeetingStudio {...props()}/>);await tick();await tick(5000);
  await emit(feeds[0]);
  await act(async()=>{reject(new TypeError('Ancienne lecture échouée'));});await tick();
  expect(screen.queryByText(/Ancienne lecture échouée/)).toBeNull();
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText(changed().segments![0].text)).toBeTruthy();
});

it('un succès de GET ancien ne masque pas l’échec d’une lecture plus récente',async()=>{
  let finish!:(value:MeetingSession)=>void;const old=new Promise<MeetingSession>(resolve=>{finish=resolve;});
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(row).mockReturnValueOnce(old)
    .mockRejectedValueOnce(new TypeError('Lecture récente échouée')).mockResolvedValue(changed('A',12));
  render(<MeetingStudio {...props()}/>);await tick();await tick(5000);
  await emit(feeds[0]);
  expect(screen.getByText(/Lecture récente échouée/)).toBeTruthy();
  await act(async()=>{finish(row);});await tick();
  expect(screen.getByText(/Lecture récente échouée/)).toBeTruthy();
  await tick(500);
  expect(screen.queryByText(/Lecture récente échouée/)).toBeNull();
});

it('le poll réussi garde l’échec de sauvegarde et le brouillon humain',async()=>{
  const save=vi.spyOn(meetingSessions,'saveNote').mockRejectedValue(new Error('Sauvegarde refusée : version concurrente.'));
  render(<MeetingStudio {...props()}/>);await tick();
  fireEvent.change(screen.getByLabelText('Note humaine'),{target:{value:'Correction humaine encore à enregistrer.'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));await tick();
  expect(save).toHaveBeenCalledTimes(1);
  expect(screen.getByText('Sauvegarde refusée : version concurrente.')).toBeTruthy();
  await tick(5000);
  expect(screen.getByText('Sauvegarde refusée : version concurrente.')).toBeTruthy();
  expect(screen.getByLabelText('Note humaine')).toHaveProperty('value','Correction humaine encore à enregistrer.');
  expect(save).toHaveBeenCalledTimes(1);
});

it('le poll réussi ne masque pas un brouillon local illisible et conserve sa copie',async()=>{
  localStorage.setItem('agent.meeting-note.v1.A','{brouillon invalide');
  render(<MeetingStudio {...props()}/>);await tick();
  const message='Un brouillon local ne peut pas être relu. Il reste conservé sur cet appareil.';
  expect(screen.getByText(message)).toBeTruthy();
  await tick(5000);
  expect(screen.getByText(message)).toBeTruthy();
  expect(localStorage.getItem('agent.meeting-note.v1.A')).toBe('{brouillon invalide');
});

it('une lecture annexe reprise efface son alerte sans laisser une erreur globale',async()=>{
  vi.mocked(meetingSessions.enhancements).mockRejectedValueOnce(new TypeError('État IA temporairement illisible')).mockResolvedValue({items:[]});
  render(<MeetingStudio {...props()}/>);await tick();
  expect(screen.getByText('Lecture des données de séance indisponible : État IA temporairement illisible')).toBeTruthy();
  await tick(5000);
  expect(screen.queryByText(/État IA temporairement illisible/)).toBeNull();
  expect(screen.getByLabelText('Note humaine')).toHaveProperty('value','Réserve initiale non validée.');
});

it('une lecture de l’ancienne séance rejetée après navigation ne pose aucune erreur sur la nouvelle',async()=>{
  let reject!:(error:Error)=>void;const old=new Promise<MeetingSession>((_,failed)=>{reject=failed;});
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(row).mockReturnValueOnce(old).mockResolvedValue({...row,id:'B',title:'Séance fictive B'});
  const view=render(<MeetingStudio {...props()}/>);await tick();await tick(5000);
  view.rerender(<MeetingStudio {...props('B')}/>);await tick();
  await act(async()=>{reject(new TypeError('Lecture de A échouée'));});await tick();
  expect(screen.queryByText(/Lecture de A échouée/)).toBeNull();
  expect(screen.getByRole('heading',{name:'Séance fictive B'})).toBeTruthy();
});

it('un GET préalable échoué ne lance aucun lot et sa reprise ne laisse aucune erreur de mutation',async()=>{
  const retained={...row,chunks:[{id:'retained',track:'mic' as const,sequence:0,sha256:'a'.repeat(64),size_bytes:32044,start_ms:0,duration_ms:1000,
    created_at:'2026-10-12T03:00:00Z',speech_status:'retained' as const,speech_error:null}]};
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(retained).mockRejectedValueOnce(new TypeError('Failed to fetch')).mockResolvedValue(retained);
  const retry=vi.spyOn(meetingSessions,'retryTranscription');
  render(<MeetingStudio {...props()} capabilities={{...caps,transcription:{...caps.transcription,enabled:true}}}/>);await tick();
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  fireEvent.click(screen.getByRole('button',{name:'Reprendre un lot de transcription'}));await tick();
  expect(screen.getByText('Lecture de la séance indisponible : Failed to fetch')).toBeTruthy();
  expect(retry).not.toHaveBeenCalled();
  await tick(5000);
  expect(screen.queryByText(/Failed to fetch/)).toBeNull();
  expect(retry).not.toHaveBeenCalled();expect(meetingCapture.start).not.toHaveBeenCalled();
});

it('un arrêt simulé confirmé suivi d’un GET échoué garde seulement l’alerte de lecture jusqu’à sa reprise',async()=>{
  const snapshot={sessionId:'A',title:'Capture fictive',phase:'recording' as const,tracks:['mic' as const],seconds:7,
    totalBytes:0,savedBytes:0,pending:0,error:''};
  vi.spyOn(meetingCapture,'getSnapshot').mockReturnValue(snapshot);
  const stop=vi.spyOn(meetingCapture,'stop').mockResolvedValue(null);
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(row).mockRejectedValueOnce(new TypeError('Lecture après arrêt interrompue'))
    .mockResolvedValue({...row,state:'completed'});
  render(<MeetingStudio {...props()}/>);await tick();
  fireEvent.click(screen.getByRole('button',{name:'Arrêter'}));await tick();
  expect(stop).toHaveBeenCalledTimes(1);
  expect(screen.getByText('Lecture de la séance indisponible : Lecture après arrêt interrompue')).toBeTruthy();
  await tick(5000);
  expect(screen.queryByText(/Lecture après arrêt interrompue/)).toBeNull();
  expect(stop).toHaveBeenCalledTimes(1);expect(meetingCapture.start).not.toHaveBeenCalled();
});
