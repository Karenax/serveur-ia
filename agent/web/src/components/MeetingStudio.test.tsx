import {installPublicationLocksForTest} from '../test/publicationLocks';
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { act,cleanup, fireEvent, render, screen, waitFor,within } from '@testing-library/react';
import { MeetingStudio } from './MeetingStudio';
import { meetingSessions, type MeetingSession, type SessionCapabilities,type SessionAutomaticEnhancement,type SessionChunk } from '../lib/meetingSessions';
import { blankNote,notesApi,type NoteVersion, type NoteContent } from '../lib/projectNotes';
import {fusionSources,type LibrarySource} from '../lib/fusionSources';
import {meetingCapture} from '../lib/meetingCapture';

vi.mock('./NoteRichEditor',()=>({
  NoteRichEditor:({content,onChange,disabled,draftId,onMarkdownDraftState}:{content:NoteContent;onChange:(content:NoteContent)=>void|boolean;disabled:boolean;
    draftId?:string;onMarkdownDraftState?:(state:{pending:boolean;valid:boolean})=>void})=><div data-testid="note-editor" data-draft-id={draftId}>
    <textarea aria-label="Texte des notes" disabled={disabled} value={content.blocks[0]?.type==='paragraph'?content.blocks[0].runs.map(run=>run.text).join(''):''}
      onChange={event=>onChange(note(event.target.value))}/>
    <button type="button" onClick={()=>onMarkdownDraftState?.({pending:true,valid:true})}>Simuler un brouillon Markdown valide</button>
    <button type="button" onClick={()=>onMarkdownDraftState?.({pending:true,valid:false})}>Simuler un brouillon Markdown invalide</button>
    <button type="button" onClick={()=>{if(onChange(note('Puissance 250 W non validée.'))!==false)onMarkdownDraftState?.({pending:false,valid:true});}}>Simuler appliquer Markdown</button>
  </div>,
  NoteContentView:({content}:{content:NoteContent})=><p>{content.blocks[0]?.type==='paragraph'?content.blocks[0].runs.map(run=>run.text).join(''):''}</p>,
}));
vi.mock('./MeetingAudioPanel',()=>({MeetingAudioPanel:()=> <section aria-label="Parcours audio existant"/>}));
const note=(text:string):NoteContent=>({version:1,blocks:[{type:'paragraph',align:'left',runs:[{text,marks:[],href:null,color:null}]}]});
const row:MeetingSession={id:'sid',title:'Revue mécanique',kind:'note',project_id:'erp',brain_project_id:'brain',state:'created',revision:3,
  date:'2026-10-11',recording_id:null,note_id:'note',note_revision:4,note_version_id:'note-version',
  note:{id:'note',project_id:'erp',title:'Notes mécaniques',content:note('Réserve : 55 mm à confirmer'),revision:4,version_id:'note-version',
    attachment_ids:[],read_only:false,source_kind:null,updated_at:'2026-10-11',actor_id:'local'},
  tracks:[],total_bytes:0,duration_seconds:0,issues:[],created_at:'2026-10-11',updated_at:'2026-10-11'};
const capabilities:SessionCapabilities={enabled:true,capture:{durable:true,max_upload_mb:50,max_duration_minutes:120,tracks:['mic','system'],browser_permission_required:true},
  transcription:{batch_ready:false,live_ready:false,detail:'Runtime audio absent'},notes:{staging:true,erp_projection:true}};
beforeEach(()=>{installPublicationLocksForTest();localStorage.clear();vi.spyOn(meetingSessions,'watchEvents').mockResolvedValue(undefined);vi.spyOn(meetingSessions,'get').mockResolvedValue(row);
  vi.spyOn(meetingSessions,'askHistory').mockResolvedValue({items:[]});vi.spyOn(meetingSessions,'enhancements').mockResolvedValue({items:[]});
  vi.spyOn(meetingSessions,'liveAnswers').mockResolvedValue({items:[]});});
afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks();});
function setup(value=row,caps=capabilities){vi.mocked(meetingSessions.get).mockResolvedValue(value);
  if(!localStorage.getItem('agent-meeting-layout-v2'))localStorage.setItem('agent-meeting-layout-v2','enhanced');
  return render(<MeetingStudio sessionId="sid" rows={[]} capabilities={caps} onClose={vi.fn()} onOpenProject={vi.fn()}/>);}

const retainedAnswer={id:'history-answer',query:'Quelle réserve ?',answer:'Réponse conservée avant modification',scope:'session' as const,
  citations:[],stale:false,status:'answered' as const};

it('explique les deux sources Linux avant leur autorisation',async()=>{
  document.body.dataset.kiaraLinuxSystemAudio='true';
  const snapshot={sessionId:'sid',title:'Revue',phase:'ready' as const,tracks:[],seconds:0,totalBytes:0,savedBytes:0,pending:0,error:''};
  vi.spyOn(meetingCapture,'getSnapshot').mockReturnValue(snapshot);
  vi.spyOn(meetingCapture,'subscribe').mockImplementation(()=>()=>{});
  try{
    setup({...row,kind:'meeting'});
    expect(await screen.findByText(/Le microphone et tous les sons de la sortie audio par défaut au démarrage seront enregistrés sur deux pistes/)).toBeTruthy();
    expect(screen.getByRole('button',{name:'Autoriser les sources et démarrer'})).toBeTruthy();
  }finally{delete document.body.dataset.kiaraLinuxSystemAudio;}
});

it.each([
  ['starting',false,'Ouverture audio en cours'],
  ['starting',true,'Ouverture audio en cours'],
  ['interrupted',true,'Capture interrompue · conservation à vérifier'],
  ['unknown',true,'État audio à vérifier'],
  ['paused',true,'En pause'],
] as const)('reflète la phase native %s (%s) avant sa confirmation SQL sans perdre le brouillon',async(state,alive,label)=>{
  vi.useFakeTimers();
  const pending:MeetingSession={...row,kind:'meeting',state:'recording',
    native_capture:{session_id:'sid',state,tracks:['mic'],process_alive:alive},
    transcription_admission:{policy:'direct-admission-v1',suspended:true,admitted_chunks:0,
      retained_chunks:0,recoverable_direct_chunks:0,retained_batch_only_chunks:0}};
  vi.mocked(meetingSessions.get).mockResolvedValue(pending);
  await act(async()=>{render(<MeetingStudio sessionId="sid" rows={[]} capabilities={capabilities}
    onClose={vi.fn()} onOpenProject={vi.fn()} sessionList={[pending]} onSelectSession={vi.fn()}/>);});
  expect(screen.getAllByText(`2026-10-11 · ${label}`)).toHaveLength(2);
  if(state!=='paused')expect(screen.queryByText(/L’enregistrement continue\./)).toBeNull();
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon pendant la préparation'}});
  const command=vi.spyOn(meetingSessions,'command');
  vi.mocked(meetingSessions.get).mockResolvedValue({...pending,
    native_capture:{...pending.native_capture!,state:'recording',process_alive:true}});
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  expect(screen.getAllByText('2026-10-11 · Enregistrement')).toHaveLength(2);
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Brouillon pendant la préparation');
  expect(command).not.toHaveBeenCalled();
});

it.each([
  [false,'Capture arrêtée · conservation à vérifier'],
  [null,'État audio à vérifier'],
] as const)('ne présente plus une capture native %s comme un enregistrement actif avant la mise à jour SQL',async(alive,label)=>{
  vi.useFakeTimers();
  const recording:MeetingSession={...row,kind:'meeting',state:'recording',
    native_capture:{session_id:'sid',state:'recording',tracks:['mic'],process_alive:true}};
  vi.mocked(meetingSessions.get).mockResolvedValue(recording);
  await act(async()=>{render(<MeetingStudio sessionId="sid" rows={[]} capabilities={capabilities}
    onClose={vi.fn()} onOpenProject={vi.fn()} sessionList={[recording]} onSelectSession={vi.fn()}/>);});
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Lecture humaine conservée'}});
  const command=vi.spyOn(meetingSessions,'command');
  vi.mocked(meetingSessions.get).mockResolvedValue({...recording,
    native_capture:{...recording.native_capture!,process_alive:alive}});
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  expect(screen.getAllByText(`2026-10-11 · ${label}`)).toHaveLength(2);
  expect(screen.queryByText('2026-10-11 · Enregistrement')).toBeNull();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Lecture humaine conservée');
  expect(command).not.toHaveBeenCalled();
  vi.mocked(meetingSessions.get).mockResolvedValue({...recording,state:'completed',revision:4,
    native_capture:{...recording.native_capture!,process_alive:false,state:'stopped'}});
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  expect(screen.getAllByText('2026-10-11 · Conservée')).toHaveLength(2);
  expect(screen.queryByText(`2026-10-11 · ${label}`)).toBeNull();
});

it.each([
  ['completed','Conservée'],['interrupted','Interrompue'],['paused','En pause'],
] as const)('actualise la ligne sélectionnée vers %s malgré une liste parent ancienne',async(state,label)=>{
  vi.useFakeTimers();
  const recording:MeetingSession={...row,kind:'meeting',state:'recording'};
  const other:MeetingSession={...row,id:'other',title:'Autre séance',state:'created'};
  vi.mocked(meetingSessions.get).mockResolvedValue(recording);
  await act(async()=>{render(<MeetingStudio sessionId="sid" rows={[]} capabilities={capabilities}
    onClose={vi.fn()} onOpenProject={vi.fn()} sessionList={[recording,other]} onSelectSession={vi.fn()}/>);});
  const index=screen.getByRole('complementary',{name:'Notes et séances'});
  expect(within(index).getByText('2026-10-11 · Enregistrement')).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon humain conservé'}});
  vi.mocked(meetingSessions.get).mockResolvedValue({...recording,state,revision:4,date:'2026-10-21'});
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  expect(within(index).getByText(`2026-10-21 · ${label}`)).toBeTruthy();
  expect(within(index).getByText('2026-10-11 · À préparer')).toBeTruthy();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Brouillon humain conservé');
  vi.mocked(meetingSessions.get).mockResolvedValue(recording);
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  expect(within(index).getByText(`2026-10-21 · ${label}`)).toBeTruthy();
  expect(within(index).queryByText('2026-10-11 · Enregistrement')).toBeNull();
});

it('garde la question manuelle et les notes accessibles pendant une réponse automatique lente',async()=>{
  vi.mocked(meetingSessions.liveAnswers).mockResolvedValue({items:[],automatic:{state:'pending',enabled:true,elapsed_seconds:30,delayed:true,attempt_id:7}});
  setup(row,{...capabilities,assistant:{enabled:true,ready:true}});
  fireEvent.click(await screen.findByRole('button',{name:'Assistant'}));
  fireEvent.click(await screen.findByRole('tab',{name:'Questions en direct'}));
  await screen.findByText(/La recherche automatique prend plus de temps/);
  fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Quelle réserve faut-il vérifier ?'}});
  expect(screen.getByRole('button',{name:'Poser la question'})).toHaveProperty('disabled',false);
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('disabled',false);
  expect(screen.getByRole('status',{name:'État des réponses automatiques'}).getAttribute('aria-busy')).toBe('true');
});

it('ne promet pas de réponse manuelle quand le moteur est indisponible',async()=>{
  document.body.dataset.kiaraWebConversations='true';
  try {
    setup(row);
    fireEvent.click(await screen.findByRole('button',{name:'Assistant'}));
    fireEvent.click(await screen.findByRole('tab',{name:'Questions en direct'}));
    expect(screen.queryByText(/vous pouvez demander une réponse explicitement/)).toBeNull();
    expect(screen.queryByLabelText('Question à l’assistant')).toBeNull();
    expect(screen.getByText('Le direct n’est pas qualifié.')).toBeTruthy();
    const link=screen.getByRole('link',{name:'Assistant de projet'});
    expect(link.getAttribute('href')).toBe('/app/conversations#projet=erp');
    expect(link.getAttribute('target')).toBe('_blank');
  } finally {delete document.body.dataset.kiaraWebConversations;}
});
async function openRetainedConversation(){
  vi.useFakeTimers();
  vi.mocked(meetingSessions.askHistory).mockResolvedValue({items:[retainedAnswer]});
  await act(async()=>{setup(row,{...capabilities,assistant:{enabled:true,ready:true}});});
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Assistant'}));});
  expect(within(screen.getByRole('log',{name:'Réponses de la séance'})).getByText(retainedAnswer.answer)).toBeTruthy();
}

it('enregistre puis retire l’avis sans modifier les notes ni la question en saisie',async()=>{
  await openRetainedConversation();
  const rate=vi.spyOn(meetingSessions,'rateAnswer').mockImplementation(async(_sid,kind,id,useful)=>({id,kind,useful}));
  const ask=vi.spyOn(meetingSessions,'ask'),enhance=vi.spyOn(meetingSessions,'enhance');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon humain intact'}});
  fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Question encore en saisie'}});
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Utile'}));});
  expect(rate).toHaveBeenLastCalledWith('sid','ask',retainedAnswer.id,true);
  expect(screen.getByRole('button',{name:'Utile'})).toHaveProperty('ariaPressed','true');
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Utile'}));});
  expect(rate).toHaveBeenLastCalledWith('sid','ask',retainedAnswer.id,null);
  expect(screen.getByRole('button',{name:'Utile'})).toHaveProperty('ariaPressed','false');
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Brouillon humain intact');
  expect(screen.getByLabelText('Question à l’assistant')).toHaveProperty('value','Question encore en saisie');
  expect(ask).not.toHaveBeenCalled();expect(enhance).not.toHaveBeenCalled();
});

it('un ancien contrôle d’historique ne remplace pas l’avis qui vient d’être enregistré',async()=>{
  await openRetainedConversation();
  let release!:(value:{items:typeof retainedAnswer[]})=>void;
  vi.mocked(meetingSessions.askHistory).mockReturnValue(new Promise(resolve=>{release=resolve;}));
  await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});
  vi.spyOn(meetingSessions,'rateAnswer').mockResolvedValue({id:retainedAnswer.id,kind:'ask',useful:true});
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Utile'}));});
  await act(async()=>{release({items:[retainedAnswer]});});
  expect(screen.getByRole('button',{name:'Utile'})).toHaveProperty('ariaPressed','true');
});

it('suspend le suivi de l’assistant lorsque la fenêtre est masquée et reprend sans perdre les saisies',async()=>{
  const descriptor=Object.getOwnPropertyDescriptor(document,'hidden');let hidden=false;
  Object.defineProperty(document,'hidden',{configurable:true,get:()=>hidden});
  try{
    await openRetainedConversation();
    fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Note humaine à conserver'}});
    fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Question à conserver'}});
    let release!:(value:{items:typeof retainedAnswer[]})=>void;
    vi.mocked(meetingSessions.askHistory)
      .mockReturnValueOnce(new Promise(resolve=>{release=resolve;}))
      .mockResolvedValue({items:[{...retainedAnswer,answer:'Réponse actualisée'}]});
    await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});
    const calls=vi.mocked(meetingSessions.askHistory).mock.calls;
    const previousSignal=calls[calls.length-1][3]!;
    hidden=true;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});
    expect(previousSignal.aborted).toBe(true);
    const count=vi.mocked(meetingSessions.askHistory).mock.calls.length;
    await act(async()=>{await vi.advanceTimersByTimeAsync(12000);});
    expect(meetingSessions.askHistory).toHaveBeenCalledTimes(count);
    hidden=false;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});
    expect(meetingSessions.askHistory).toHaveBeenCalledTimes(count+1);
    expect(screen.getByText('Réponse actualisée')).toBeTruthy();
    await act(async()=>{release({items:[retainedAnswer]});});
    expect(screen.getByText('Réponse actualisée')).toBeTruthy();
    expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Note humaine à conserver');
    expect(screen.getByLabelText('Question à l’assistant')).toHaveProperty('value','Question à conserver');
  }finally{
    if(descriptor)Object.defineProperty(document,'hidden',descriptor);
    else delete (document as unknown as {hidden?:boolean}).hidden;
  }
});

it('conserve l’avis précédent et la saisie quand son enregistrement échoue',async()=>{
  await openRetainedConversation();
  vi.spyOn(meetingSessions,'rateAnswer').mockRejectedValue(new Error('Avis non enregistré'));
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Réserve à conserver'}});
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Pas utile'}));});
  expect(screen.getByText('Avis non enregistré')).toBeTruthy();
  expect(screen.getByRole('button',{name:'Pas utile'})).toHaveProperty('ariaPressed','false');
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Réserve à conserver');
});

it('évalue séparément une carte du direct sans toucher à son épinglage',async()=>{
  vi.mocked(meetingSessions.liveAnswers).mockResolvedValue({items:[{...retainedAnswer,pinned:true,useful:false}]});
  const rate=vi.spyOn(meetingSessions,'rateAnswer').mockImplementation(async(_sid,kind,id,useful)=>({id,kind,useful}));
  const pin=vi.spyOn(meetingSessions,'pinAnswer');
  setup(row,{...capabilities,assistant:{enabled:true,ready:true}});
  fireEvent.click(await screen.findByRole('button',{name:'Assistant'}));
  fireEvent.click(screen.getByRole('tab',{name:'Questions en direct'}));
  fireEvent.click(await screen.findByRole('button',{name:'Utile'}));
  await waitFor(()=>expect(rate).toHaveBeenCalledWith('sid','live',retainedAnswer.id,true));
  expect(screen.getByRole('button',{name:'Désépingler la réponse'})).toHaveProperty('ariaPressed','true');
  expect(pin).not.toHaveBeenCalled();
});

it('signale une réponse devenue ancienne sans rouvrir la séance et conserve la saisie humaine',async()=>{
  await openRetainedConversation();
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon humain non enregistré'}});
  fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Question encore en saisie'}});
  vi.mocked(meetingSessions.askHistory).mockResolvedValue({items:[{...retainedAnswer,stale:true,status:'obsolete'}]});
  await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});
  expect(screen.getByText('Réponse fondée sur une ancienne version.')).toBeTruthy();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Brouillon humain non enregistré');
  expect(screen.getByLabelText('Question à l’assistant')).toHaveProperty('value','Question encore en saisie');
});

it('retire une réponse que le serveur ne permet plus de consulter sans effacer les brouillons',async()=>{
  await openRetainedConversation();
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Réserve humaine à conserver'}});
  vi.mocked(meetingSessions.askHistory).mockResolvedValue({items:[]});
  await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});
  expect(within(screen.getByRole('log',{name:'Réponses de la séance'})).queryByText(retainedAnswer.answer)).toBeNull();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Réserve humaine à conserver');
});

it('un ancien contrôle de fraîcheur ne fait pas disparaître une nouvelle réponse reçue entretemps',async()=>{
  await openRetainedConversation();
  let release!:(value:{items:typeof retainedAnswer[]})=>void;
  vi.mocked(meetingSessions.askHistory).mockReturnValue(new Promise(resolve=>{release=resolve;}));
  await act(async()=>{await vi.advanceTimersByTimeAsync(3000);});
  expect(meetingSessions.askHistory).toHaveBeenCalledTimes(2);
  vi.spyOn(meetingSessions,'ask').mockResolvedValue({...retainedAnswer,id:'new-answer',answer:'Nouvelle réponse à conserver'});
  fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Nouvelle question'}});
  await act(async()=>{fireEvent.click(screen.getByRole('button',{name:'Poser la question'}));});
  expect(screen.getByText('Nouvelle réponse à conserver')).toBeTruthy();
  await act(async()=>{release({items:[retainedAnswer]});});
  expect(screen.getByText('Nouvelle réponse à conserver')).toBeTruthy();
});

it('ouvre le parcours audio du CR par un bouton visible hors de Préparation',async()=>{
  const start=vi.spyOn(meetingCapture,'start'),enhance=vi.spyOn(meetingSessions,'enhance');
  setup({...row,kind:'meeting',state:'completed',recording_id:'audio1'});
  const button=await screen.findByRole('button',{name:'Compte rendu'});
  expect(button.closest('.meeting-preparation')).toBeNull();
  fireEvent.click(button);
  expect(screen.getByRole('region',{name:'Parcours audio existant'})).toBeTruthy();
  expect(button).toHaveProperty('ariaPressed','true');
  expect(start).not.toHaveBeenCalled();expect(enhance).not.toHaveBeenCalled();
});

it('termine explicitement une note par un bouton visible puis ouvre son CR sans audio ni publication',async()=>{
  const finalize=vi.spyOn(meetingSessions,'command').mockResolvedValue({...row,state:'completed',revision:5});
  const start=vi.spyOn(meetingCapture,'start'),publish=vi.spyOn(meetingSessions,'publishNotes');
  setup();
  const button=await screen.findByRole('button',{name:'Terminer la prise de notes'});
  expect(button.closest('details')).toBeNull();
  vi.mocked(meetingSessions.get).mockResolvedValue({...row,revision:4});
  fireEvent.click(button);
  await waitFor(()=>expect(finalize).toHaveBeenCalledWith('sid','finalize',expect.objectContaining({expected_revision:4})));
  await screen.findByRole('region',{name:'Publication du compte rendu des notes'});
  expect(screen.getByRole('button',{name:'Compte rendu'})).toHaveProperty('ariaPressed','true');
  expect(screen.queryByRole('button',{name:'Terminer la prise de notes'})).toBeNull();
  expect(start).not.toHaveBeenCalled();expect(publish).not.toHaveBeenCalled();
});

it('bloque la fin des notes pendant la préparation audio du navigateur',async()=>{
  vi.spyOn(meetingCapture,'getSnapshot').mockReturnValue({phase:'starting',sessionId:'sid',seconds:0,tracks:['mic'],pending:0,error:''} as ReturnType<typeof meetingCapture.getSnapshot>);
  const finalize=vi.spyOn(meetingSessions,'command');
  setup();
  const button=await screen.findByRole('button',{name:'Terminer la prise de notes'});
  expect(button).toHaveProperty('disabled',true);fireEvent.click(button);
  expect(finalize).not.toHaveBeenCalled();
});

it('expose le microphone et le démarrage navigateur hors de Préparation sans demander l’accès audio',async()=>{
  const enumerateDevices=vi.fn().mockResolvedValue([{kind:'audioinput',deviceId:'browser-jabra',label:'Jabra navigateur'}]);
  const getUserMedia=vi.fn(),start=vi.spyOn(meetingCapture,'start').mockResolvedValue({...row,kind:'meeting'});
  const testNavigator=Object.create(navigator);Object.defineProperty(testNavigator,'mediaDevices',{value:{enumerateDevices,getUserMedia}});
  vi.stubGlobal('navigator',testNavigator);
  try{
    setup({...row,kind:'meeting'});
    const selector=await screen.findByLabelText('Microphone du navigateur');await screen.findByRole('option',{name:'Jabra navigateur'});
    const button=screen.getByRole('button',{name:'Démarrer la réunion au microphone'});
    expect(button.closest('.meeting-preparation')).toBeNull();expect(selector.closest('.meeting-preparation')).toBeNull();
    expect(button.closest('details')?.open).toBe(true);
    fireEvent.change(selector,{target:{value:'browser-jabra'}});
    expect(start).not.toHaveBeenCalled();expect(getUserMedia).not.toHaveBeenCalled();
    fireEvent.click(button);await waitFor(()=>expect(start).toHaveBeenCalledWith('sid',expect.objectContaining({deviceId:'browser-jabra',system:false})));
    expect(getUserMedia).not.toHaveBeenCalled();
  }finally{vi.unstubAllGlobals();}
});

it('ouvre la note pleine page par défaut avec sauvegarde et outils secondaires en tête',async()=>{
  render(<MeetingStudio sessionId="sid" rows={[]} capabilities={capabilities} onClose={vi.fn()} onOpenProject={vi.fn()}/>);
  await screen.findByDisplayValue('Notes mécaniques');
  expect(document.querySelector('.meeting-layout-editor')).toBeTruthy();
  const editor=screen.getByTestId('note-editor');
  expect(screen.queryByRole('region',{name:'Notes enrichies'})).toBeNull();
  const save=screen.getByRole('button',{name:'Enregistrer la note'});
  expect(save.closest('.meeting-document-heading')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Transcription'}));
  expect(screen.getByRole('region',{name:'Transcription de la séance'})).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Notes'}));
  expect(document.querySelector('.meeting-layout-editor')).toBeTruthy();
  expect(screen.getByTestId('note-editor')).toBe(editor);
});

it('permet de démarrer le vocal depuis une note sans ouvrir le microphone au chargement',async()=>{
  const start=vi.spyOn(meetingCapture,'start').mockResolvedValue({...row,state:'recording'});
  setup(row);
  const button=await screen.findByRole('button',{name:'Démarrer la réunion au microphone'});
  expect(start).not.toHaveBeenCalled();fireEvent.click(button);
  await waitFor(()=>expect(start).toHaveBeenCalledWith('sid',expect.objectContaining({system:false})));
  await screen.findByRole('region',{name:'Transcription de la séance'});
});

it('enregistre le brouillon avant de demander une amélioration de ses notes',async()=>{
  const saved={...row,revision:4,note_revision:5,note_version_id:'v5',note:{...row.note!,revision:5,version_id:'v5',content:note('Décision rédigée maintenant')}};
  const save=vi.spyOn(meetingSessions,'saveNote').mockResolvedValue(saved);
  const enhance=vi.spyOn(meetingSessions,'enhance').mockResolvedValue({id:'proposal',session_id:'sid',kind:'enhancement',status:'pending',text:'Proposition',citations:[]} as never);
  setup(row,{...capabilities,assistant:{enabled:true,ready:true}});
  await screen.findByDisplayValue('Notes mécaniques');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Décision rédigée maintenant'}});
  vi.mocked(meetingSessions.get).mockResolvedValue(saved);
  fireEvent.click(screen.getByRole('button',{name:'Améliorer les notes'}));
  await waitFor(()=>expect(enhance).toHaveBeenCalled());
  expect(save).toHaveBeenCalledWith('sid',expect.objectContaining({content:note('Décision rédigée maintenant')}));
  expect(save.mock.invocationCallOrder[0]).toBeLessThan(enhance.mock.invocationCallOrder[0]);
});

it('expose Windows et ses périphériques avant le démarrage, avec le navigateur en option distincte',async()=>{
  const native={installed:true,ready:true,loopback_ready:false,real_test_passed:false,microphone_test_passed:false,devices:[],active:[],session:null};
  vi.spyOn(meetingSessions,'nativeStatus').mockResolvedValue(native);
  const start=vi.spyOn(meetingSessions,'native'),browser=vi.spyOn(meetingCapture,'start');
  setup({...row,kind:'meeting'},{...capabilities,native_capture:native});
  const audio=await screen.findByRole('region',{name:'Audio de la réunion'});
  expect(within(audio).getByLabelText('Sortie Windows à enregistrer')).toBeTruthy();
  expect(within(audio).getByLabelText('Microphone à utiliser')).toHaveProperty('disabled',true);
  expect(within(audio).getByRole('button',{name:'Démarrer la réunion'}).closest('details')).toBeNull();
  expect(audio.closest('.meeting-preparation')).toBeNull();
  expect(screen.getByRole('button',{name:'Enregistrer au microphone (navigateur)'}).closest('details')?.open).toBe(false);
  expect(start).not.toHaveBeenCalled();expect(browser).not.toHaveBeenCalled();
});

it('suspend le suivi de capture native lorsque la séance est quittée et garde la note au retour',async()=>{
  const native={installed:true,ready:true,loopback_ready:false,real_test_passed:false,microphone_test_passed:false,devices:[],active:[],session:null};
  const status=vi.spyOn(meetingSessions,'nativeStatus').mockResolvedValue(native);
  vi.mocked(meetingSessions.get).mockResolvedValue({...row,kind:'meeting'});
  const props={sessionId:'sid',rows:[],capabilities:{...capabilities,native_capture:native},onClose:vi.fn(),onOpenProject:vi.fn()};
  const view=render(<MeetingStudio {...props} active/>);
  await screen.findByLabelText('Texte des notes');
  await waitFor(()=>expect(status).toHaveBeenCalledTimes(2));
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Note de séance à conserver'}});
  view.rerender(<MeetingStudio {...props} active={false}/>);
  vi.useFakeTimers();
  await act(async()=>{await vi.advanceTimersByTimeAsync(11000);});
  expect(status).toHaveBeenCalledTimes(2);
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Note de séance à conserver');
  view.rerender(<MeetingStudio {...props} active/>);
  await act(async()=>{});
  expect(status).toHaveBeenCalledTimes(4);
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Note de séance à conserver');
});

function deferredSnapshot(){
  let resolve!:(value:MeetingSession)=>void;
  const promise=new Promise<MeetingSession>(finish=>{resolve=finish;});
  return {promise,resolve};
}

it.each([true,false])('garde un seul geste de conservation avec capture Windows installée=%s',async installed=>{
  const native={installed,ready:installed,loopback_ready:false,real_test_passed:false,microphone_test_passed:false,devices:[],active:[],session:null};
  let finish!:(value:typeof native)=>void;
  const inventory=new Promise<typeof native>(resolve=>{finish=resolve;});
  const status=vi.spyOn(meetingSessions,'nativeStatus').mockReturnValue(inventory);
  setup({...row,kind:'meeting',state:'interrupted',tracks:[{name:'system',mime_type:'audio/wav',filename:'kept.wav',chunks:1,total_bytes:20,duration_seconds:5,complete:true}]},
    {...capabilities,native_capture:native});
  await waitFor(()=>expect(status).toHaveBeenCalled());
  await act(async()=>{finish(native);await inventory;});
  const control=await screen.findByRole('button',{name:installed?'Conserver les fragments acquittés':'Conserver les fragments reçus et finaliser'});
  await waitFor(()=>expect(screen.queryByRole('button',{name:installed?'Conserver les fragments reçus et finaliser':'Conserver les fragments acquittés'})).toBeNull());
  await act(async()=>{await Promise.resolve();});
  expect(screen.getByRole('button',{name:installed?'Conserver les fragments acquittés':'Conserver les fragments reçus et finaliser'})).toBe(control);
});

it('course GET : conserve le segment récent et le brouillon retrouvé quand le chargement initial ancien arrive après le poll',async()=>{
  vi.useFakeTimers();
  const initial=deferredSnapshot(),poll=deferredSnapshot();
  const old={...row,event_cursor:10,segments:[]};
  const recent:MeetingSession={...row,revision:4,event_cursor:11,transcript_provisional:true,
    segments:[{id:'live-first-order',track:'mic',start_ms:0,end_ms:2000,speaker:'Voix 1',
      text:'Segment récent : ne pas valider la cote de 55 mm.',revision:1,finalized:false}]};
  const draft='Brouillon local retrouvé : cote de 55 mm à confirmer.';
  localStorage.setItem('agent.meeting-note.v1.sid',JSON.stringify({session_id:'sid',title:row.note!.title,
    content:note(draft),revision:row.revision,note_version_id:row.note_version_id,command:null}));
  vi.mocked(meetingSessions.get).mockReturnValueOnce(initial.promise).mockReturnValueOnce(poll.promise);
  setup(old);
  expect(meetingSessions.get).toHaveBeenCalledTimes(1);
  // Le poll suit son horloge réelle même si le premier GET est toujours en vol.
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  expect(meetingSessions.get).toHaveBeenCalledTimes(2);
  await act(async()=>{poll.resolve(recent);});
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText(recent.segments![0].text)).toBeTruthy();
  await act(async()=>{initial.resolve(old);});
  expect(screen.getByText('Brouillon retrouvé sur cet appareil ; votre saisie est conservée.')).toBeTruthy();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value',draft);
  expect(JSON.parse(localStorage.getItem('agent.meeting-note.v1.sid')!).content).toEqual(note(draft));
  expect(screen.getByText(recent.segments![0].text)).toBeTruthy();
});

it('course GET : conserve le segment récent et la saisie humaine quand deux polls se terminent en ordre inverse',async()=>{
  vi.useFakeTimers();
  const firstPoll=deferredSnapshot(),secondPoll=deferredSnapshot();
  const initial={...row,event_cursor:9,segments:[]},old={...row,event_cursor:10,segments:[]};
  const recent:MeetingSession={...row,revision:4,event_cursor:11,transcript_provisional:true,
    segments:[{id:'live-poll-order',track:'system',start_ms:2000,end_ms:4000,speaker:'Voix 2',
      text:'Segment récent : conserver la réserve de consignation.',revision:1,finalized:false}]};
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(initial)
    .mockReturnValueOnce(firstPoll.promise).mockReturnValueOnce(secondPoll.promise);
  setup(initial);await act(async()=>{await Promise.resolve();});
  const draft='Saisie humaine en cours : ne pas démarrer sans consignation.';
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:draft}});
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  expect(meetingSessions.get).toHaveBeenCalledTimes(3);
  await act(async()=>{secondPoll.resolve(recent);});
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText(recent.segments![0].text)).toBeTruthy();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value',draft);
  await act(async()=>{firstPoll.resolve(old);});
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value',draft);
  expect(JSON.parse(localStorage.getItem('agent.meeting-note.v1.sid')!).content).toEqual(note(draft));
  expect(screen.getByText(recent.segments![0].text)).toBeTruthy();
});

it('course GET : garde le brouillon et le conflit quand une note ERP plus récente arrive avant l’acquittement ancien de sauvegarde',async()=>{
  vi.useFakeTimers();
  const acknowledgement=deferredSnapshot();
  const initial={...row,event_cursor:10};
  const sent='Saisie envoyée : ne pas valider la puissance de 250 W.';
  const laterText='Modification ERP ultérieure : réserver la commande manuelle.';
  const acknowledged:MeetingSession={...row,revision:4,event_cursor:11,note_revision:5,note_version_id:'note-v5',
    note:{...row.note!,revision:5,version_id:'note-v5',content:note(sent)}};
  const later:MeetingSession={...row,revision:5,event_cursor:12,note_revision:6,note_version_id:'note-v6',
    note:{...row.note!,revision:6,version_id:'note-v6',content:note(laterText)}};
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(initial).mockResolvedValueOnce(later);
  const save=vi.spyOn(meetingSessions,'saveNote').mockReturnValue(acknowledgement.promise);
  setup(initial);await act(async()=>{await Promise.resolve();});
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:sent}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));
  expect(save).toHaveBeenCalledWith('sid',expect.objectContaining({content:note(sent),expected_revision:3,expected_note_revision:4}));
  // La réponse HTTP de notre sauvegarde attend alors qu'une autre version ERP est déjà courante.
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  expect(meetingSessions.get).toHaveBeenCalledTimes(2);
  expect(screen.getByText('La version enregistrée a changé. Votre saisie est conservée.')).toBeTruthy();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value',sent);
  expect(screen.getByText(laterText)).toBeTruthy();
  await act(async()=>{acknowledgement.resolve(acknowledged);});
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value',sent);
  const draft=JSON.parse(localStorage.getItem('agent.meeting-note.v1.sid')||'null');
  expect(draft).not.toBeNull();
  expect(draft.content).toEqual(note(sent));
  expect(screen.getByText('Brouillon')).toBeTruthy();
  expect(screen.getByText('La version enregistrée a changé. Votre saisie est conservée.')).toBeTruthy();
  expect(screen.getByText(laterText)).toBeTruthy();
});

it.each([false,true])('course GET : acquitte la même note malgré un transcript plus récent et protège une nouvelle saisie=%s',async newerTyping=>{
  vi.useFakeTimers();
  const acknowledgement=deferredSnapshot();
  const initial={...row,event_cursor:10};
  const sent='Note envoyée : puissance de 250 W non validée.';
  const next='Nouvelle saisie après envoi : conserver la commande manuelle.';
  const acknowledged:MeetingSession={...row,revision:4,event_cursor:11,note_revision:5,note_version_id:'note-v5',
    note:{...row.note!,revision:5,version_id:'note-v5',content:note(sent)}};
  const recent:MeetingSession={...acknowledged,event_cursor:12,transcript_provisional:true,
    segments:[{id:'live-during-save',track:'mic',start_ms:0,end_ms:2000,speaker:'Voix 1',
      text:'Segment arrivé pendant la sauvegarde.',revision:1,finalized:false}]};
  vi.mocked(meetingSessions.get).mockResolvedValueOnce(initial).mockResolvedValueOnce(recent);
  const save=vi.spyOn(meetingSessions,'saveNote').mockReturnValue(acknowledgement.promise);
  setup(initial);await act(async()=>{await Promise.resolve();});
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:sent}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText(recent.segments![0].text)).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Notes'}));
  if(newerTyping)fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:next}});
  await act(async()=>{acknowledgement.resolve(acknowledged);});
  expect(save).toHaveBeenCalledOnce();
  expect(screen.getByText(recent.segments![0].text)).toBeTruthy();
  expect(screen.queryByText('La version enregistrée a changé. Votre saisie est conservée.')).toBeNull();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value',newerTyping?next:sent);
  const draft=JSON.parse(localStorage.getItem('agent.meeting-note.v1.sid')||'null');
  if(newerTyping){
    expect(draft.content).toEqual(note(next));expect(draft.command).toBeNull();
    expect(screen.getByText('Brouillon')).toBeTruthy();
    expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',false);
  }else{
    expect(draft).toBeNull();expect(screen.getByText('Version 5')).toBeTruthy();
    expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',true);
  }
});

const automatic=(state:SessionAutomaticEnhancement['state'],extra:Partial<SessionAutomaticEnhancement>={}):SessionAutomaticEnhancement=>({enabled:state!=='disabled',state,
  detail:'Analyse des versions enregistrées après 8 secondes de stabilité.',error:null,note_version_id:'note-version',stable_seconds:8,attempt_id:'auto-attempt',...extra});
it.each([undefined,automatic('disabled')])('garde l’automatique désactivé sans opt-in explicite : %j',async state=>{
  vi.mocked(meetingSessions.enhancements).mockResolvedValue({items:[],automatic:state});const enhance=vi.spyOn(meetingSessions,'enhance');
  setup(row,{...capabilities,assistant:{ready:true}});await screen.findByText('Enrichissement automatique : Désactivé.');
  expect(enhance).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Améliorer les notes'})).toHaveProperty('disabled',false);
});

it('actualise génération puis proposition automatique via le polling sans accepter ni réécrire les notes',async()=>{
  vi.useFakeTimers();const proposal={id:'auto-proposal',status:'pending',note_revision:4,note_version_id:'note-version',text:'Ajout automatique à relire.'};
  vi.mocked(meetingSessions.enhancements).mockResolvedValueOnce({items:[],automatic:automatic('running')}).mockResolvedValue({items:[proposal],automatic:automatic('completed')});
  const enhance=vi.spyOn(meetingSessions,'enhance'),decide=vi.spyOn(meetingSessions,'decide'),save=vi.spyOn(meetingSessions,'saveNote');
  setup(row,{...capabilities,assistant:{ready:true}});await act(async()=>{await Promise.resolve();});
  expect(screen.getByText('Enrichissement automatique : Génération en cours.')).toBeTruthy();
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  expect(screen.getByText('Enrichissement automatique : Proposition disponible.')).toBeTruthy();expect(screen.getByText('Ajout automatique à relire.')).toBeTruthy();
  expect(screen.getByText('Version de note analysée : 4.')).toBeTruthy();expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Réserve : 55 mm à confirmer');
  expect(enhance).not.toHaveBeenCalled();expect(decide).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
});

it.each(['riche','Markdown'])('conserve le brouillon %s quand une proposition automatique arrive pour la version sauvegardée',async kind=>{
  vi.useFakeTimers();vi.mocked(meetingSessions.enhancements).mockResolvedValueOnce({items:[],automatic:automatic('waiting')})
    .mockResolvedValue({items:[{id:'auto-proposal',status:'pending',note_revision:4,note_version_id:'note-version',text:'Analyse de la note enregistrée.'}],automatic:automatic('completed')});
  const decide=vi.spyOn(meetingSessions,'decide'),enhance=vi.spyOn(meetingSessions,'enhance'),save=vi.spyOn(meetingSessions,'saveNote');
  setup(row,{...capabilities,assistant:{ready:true}});await act(async()=>{await Promise.resolve();});
  if(kind==='riche')fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon humain non validé à préserver'}});
  else fireEvent.click(screen.getByRole('button',{name:'Simuler un brouillon Markdown invalide'}));
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});
  expect(screen.getByText('Vos modifications non enregistrées ne participent pas à l’analyse.')).toBeTruthy();
  expect(screen.getByText('Enrichissement automatique : Proposition disponible.')).toBeTruthy();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value',kind==='riche'?'Brouillon humain non validé à préserver':'Réserve : 55 mm à confirmer');
  expect(screen.getByRole('button',{name:'Accepter comme nouvelle version'})).toHaveProperty('disabled',true);
  expect(screen.getByRole('button',{name:'Améliorer les notes'})).toHaveProperty('disabled',kind==='Markdown');
  expect(decide).not.toHaveBeenCalled();expect(enhance).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
});

it('expose l’échec automatique et permet une reprise manuelle sans retry automatique côté Studio',async()=>{
  vi.useFakeTimers();vi.mocked(meetingSessions.enhancements).mockResolvedValue({items:[],automatic:automatic('failed',{error:'Moteur occupé : budget de file dépassé'})});
  const enhance=vi.spyOn(meetingSessions,'enhance').mockResolvedValue({id:'manual',status:'pending',text:'Proposition manuelle après relecture.'});
  setup(row,{...capabilities,assistant:{ready:true}});await act(async()=>{await Promise.resolve();});
  expect(screen.getByText('Enrichissement automatique : Tentative à reprendre.')).toBeTruthy();expect(screen.getByText('Moteur occupé : budget de file dépassé')).toBeTruthy();
  await act(async()=>{await vi.advanceTimersByTimeAsync(10000);});expect(enhance).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Améliorer les notes'}));await act(async()=>{await Promise.resolve();});
  expect(enhance).toHaveBeenCalledOnce();expect(screen.getByText('Proposition manuelle après relecture.')).toBeTruthy();
});

it('refuse une proposition dont la version de base est ancienne même si un poll ancien l’annonce disponible',async()=>{
  const newer={...row,note_version_id:'v5',note_revision:5,note:{...row.note!,version_id:'v5',revision:5,content:note('Note humaine courante')}};
  vi.mocked(meetingSessions.enhancements).mockResolvedValue({items:[{id:'old',status:'pending',note_revision:4,note_version_id:'note-version',text:'Ancien ajout à écarter'}],automatic:automatic('completed')});
  const decide=vi.spyOn(meetingSessions,'decide');setup(newer,{...capabilities,assistant:{ready:true}});
  await screen.findByText('Enrichissement automatique : Proposition à régénérer.');
  expect(screen.getByRole('button',{name:'Accepter comme nouvelle version'})).toHaveProperty('disabled',true);
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Note humaine courante');expect(decide).not.toHaveBeenCalled();
});

it('montre l’erreur de lecture d’état sans annoncer un worker désactivé puis reprend au poll suivant',async()=>{
  vi.useFakeTimers();vi.mocked(meetingSessions.enhancements).mockRejectedValueOnce(new Error('Lecture API indisponible')).mockResolvedValue({items:[],automatic:automatic('waiting')});
  setup();await act(async()=>{await Promise.resolve();});
  expect(screen.getByText('Lecture des données de séance indisponible : Lecture API indisponible')).toBeTruthy();
  expect(screen.queryByText('Enrichissement automatique : Désactivé.')).toBeNull();
  await act(async()=>{await vi.advanceTimersByTimeAsync(5000);});expect(screen.getByText('Enrichissement automatique : En attente de stabilité.')).toBeTruthy();
  expect(screen.queryByText('Lecture des données de séance indisponible : Lecture API indisponible')).toBeNull();
});

it('ignore un ancien poll de propositions qui termine après une amélioration manuelle',async()=>{
  let finish!:(value:Awaited<ReturnType<typeof meetingSessions.enhancements>>)=>void;
  vi.mocked(meetingSessions.enhancements).mockResolvedValueOnce({items:[],automatic:automatic('failed')})
    .mockReturnValueOnce(new Promise(resolve=>{finish=resolve;}));
  vi.spyOn(meetingSessions,'enhance').mockResolvedValue({id:'manual-new',status:'pending',note_revision:4,note_version_id:'note-version',text:'Nouvelle proposition conservée'});
  setup(row,{...capabilities,assistant:{ready:true}});await screen.findByText('Enrichissement automatique : Tentative à reprendre.');
  fireEvent.click(screen.getByRole('button',{name:'Améliorer les notes'}));await screen.findByText('Nouvelle proposition conservée');
  await act(async()=>{finish({items:[],automatic:automatic('failed')});});
  expect(screen.getByText('Nouvelle proposition conservée')).toBeTruthy();
});

it.each([true,false])('bloque les mutations de notes avant application du brouillon Markdown valid=%s',async valid=>{
  const save=vi.spyOn(meetingSessions,'saveNote'),enhance=vi.spyOn(meetingSessions,'enhance'),decide=vi.spyOn(meetingSessions,'decide'),publish=vi.spyOn(meetingSessions,'publishNotes');
  vi.mocked(meetingSessions.enhancements).mockResolvedValue({items:[{id:'proposal',status:'prepared',text:'Proposition à relire'}]});
  setup({...row,state:'completed'},{...capabilities,assistant:{ready:true}});await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  expect(screen.getByTestId('note-editor').getAttribute('data-draft-id')).toBe('sid');
  await waitFor(()=>expect(screen.getByRole('button',{name:'Accepter comme nouvelle version'})).toHaveProperty('disabled',false));
  expect(screen.getByRole('button',{name:'Améliorer les notes'})).toHaveProperty('disabled',false);
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});fireEvent.click(screen.getByRole('tab',{name:'Compte rendu'}));
  fireEvent.change(screen.getByLabelText('Synthèse relue'),{target:{value:'Cote à confirmer.'}});fireEvent.click(screen.getByLabelText(/J’ai relu la synthèse/));
  expect(screen.getByRole('button',{name:'Publier le compte rendu relu'})).toHaveProperty('disabled',false);
  fireEvent.click(screen.getByRole('button',{name:'Notes'}));
  fireEvent.click(screen.getByRole('button',{name:`Simuler un brouillon Markdown ${valid?'valide':'invalide'}`}));
  expect(screen.getByText(valid?'Brouillon Markdown à appliquer avant d’enregistrer, d’améliorer ou de publier la note.':
    'Brouillon Markdown invalide : corrigez-le et appliquez-le avant d’enregistrer, d’améliorer ou de publier la note.')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Compte rendu'}));
  expect(screen.getByRole('button',{name:'Publier le compte rendu relu'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Publier le compte rendu relu'}));
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'enhanced'}});
  expect(screen.getByRole('button',{name:'Améliorer les notes'})).toHaveProperty('disabled',true);
  expect(screen.getByRole('button',{name:'Accepter comme nouvelle version'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Améliorer les notes'}));fireEvent.click(screen.getByRole('button',{name:'Accepter comme nouvelle version'}));
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Ancien contenu riche corrigé'}});
  expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));
  expect(save).not.toHaveBeenCalled();expect(enhance).not.toHaveBeenCalled();expect(decide).not.toHaveBeenCalled();expect(publish).not.toHaveBeenCalled();
});

it('enregistre le contenu converti explicitement sur la même note canonique',async()=>{
  const converted=note('Puissance 250 W non validée.');
  const save=vi.spyOn(meetingSessions,'saveNote').mockResolvedValue({...row,revision:4,note_revision:5,note_version_id:'v5',note:{...row.note!,revision:5,version_id:'v5',content:converted}});
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.click(screen.getByRole('button',{name:'Simuler un brouillon Markdown valide'}));
  expect(screen.getByRole('button',{name:'Terminer la prise de notes'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Simuler appliquer Markdown'}));
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Puissance 250 W non validée.');
  expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',false);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));
  await waitFor(()=>expect(save).toHaveBeenCalledWith('sid',expect.objectContaining({content:converted,expected_note_revision:4,expected_note_version_id:'note-version'})));
  expect(screen.queryByText(/Brouillon Markdown à appliquer/)).toBeNull();
  expect(JSON.parse(localStorage.getItem('agent.meeting-note.v1.sid')||'null')).toBeNull();
});

it('protège le départ et garde le Markdown pending lorsque le brouillon converti ne peut pas être conservé',async()=>{
  const onClose=vi.fn(),confirm=vi.spyOn(window,'confirm').mockReturnValue(false);
  render(<MeetingStudio sessionId="sid" rows={[]} capabilities={capabilities} onClose={onClose} onOpenProject={vi.fn()}/>);
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');fireEvent.click(screen.getByRole('button',{name:'Simuler un brouillon Markdown valide'}));
  const event=new Event('beforeunload',{cancelable:true});window.dispatchEvent(event);expect(event.defaultPrevented).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Retour aux réunions'}));expect(confirm).toHaveBeenCalledWith('Un brouillon Markdown reste à appliquer à la note. Revenir à la liste ?');expect(onClose).not.toHaveBeenCalled();
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new Error('Quota fictif');});
  fireEvent.click(screen.getByRole('button',{name:'Simuler appliquer Markdown'}));
  expect(screen.getByText('Brouillon non conservé sur cet appareil. Enregistrez la note avant de quitter.')).toBeTruthy();
  expect(screen.getByText('Brouillon Markdown à appliquer avant d’enregistrer, d’améliorer ou de publier la note.')).toBeTruthy();
  expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',true);
  expect(screen.queryByText('Brouillon conservé sur cet appareil')).toBeNull();
});

it.each(['recording','pending'] as const)('laisse arrêt ou drain audio accessible avec un brouillon Markdown (%s)',async phase=>{
  const snapshot={sessionId:'sid',title:row.title,phase,tracks:['mic' as const],seconds:30,totalBytes:500,savedBytes:250,pending:1,error:''};
  vi.spyOn(meetingCapture,'getSnapshot').mockReturnValue(snapshot);
  const stop=vi.spyOn(meetingCapture,'stop').mockResolvedValue(null),drain=vi.spyOn(meetingCapture,'retryAndFinalize').mockResolvedValue(null);
  setup({...row,kind:'meeting',state:phase==='recording'?'recording':'interrupted'});await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.click(screen.getByRole('button',{name:'Simuler un brouillon Markdown invalide'}));
  const button=screen.getByRole('button',{name:phase==='recording'?'Arrêter':'Synchroniser les fragments conservés'});
  expect(button.closest('.meeting-preparation')).toBeNull();
  expect(button).toHaveProperty('disabled',false);fireEvent.click(button);
  await waitFor(()=>expect(phase==='recording'?stop:drain).toHaveBeenCalledOnce());
});

it('recharge la discussion conservée par séance au retour A B A même sans moteur de génération',async()=>{
  const b={...row,id:'sid-b',title:'Séance B'};
  vi.mocked(meetingSessions.get).mockImplementation(async id=>id==='sid-b'?b:row);
  vi.mocked(meetingSessions.askHistory).mockImplementation(async id=>({items:[{id:id+'-answer',query:'Réserve ?',answer:id==='sid'?'Réponse A conservée':'Réponse B conservée'}]}));
  const props={rows:[],capabilities,onClose:vi.fn(),onOpenProject:vi.fn()};localStorage.setItem('agent-meeting-layout-v2','assistant');
  const view=render(<MeetingStudio key="sid" sessionId="sid" {...props}/>);
  await screen.findByText('Réponse A conservée');expect(screen.queryByRole('button',{name:'Poser la question'})).toBeNull();
  view.rerender(<MeetingStudio key="sid-b" sessionId="sid-b" {...props}/>);
  await screen.findByText('Réponse B conservée');expect(screen.queryByText('Réponse A conservée')).toBeNull();
  view.rerender(<MeetingStudio key="sid" sessionId="sid" {...props}/>);
  await screen.findByText('Réponse A conservée');expect(screen.queryByText('Réponse B conservée')).toBeNull();
  expect(meetingSessions.askHistory).toHaveBeenLastCalledWith('sid','session',[],expect.any(AbortSignal));
});

it('partitionne l’historique par sélection de sources et ignore une lecture du contexte précédent',async()=>{
  let finish!:(value:{items:{query:string;answer:string}[]})=>void;
  vi.mocked(meetingSessions.askHistory).mockImplementation(async (_id,scope,ids)=>scope==='sources'&&ids?.length===1?
    new Promise(resolve=>{finish=resolve;}):{items:scope==='sources'?[{query:'Deux sources',answer:'Contexte deux sources'}]:[]});
  vi.spyOn(fusionSources,'list').mockResolvedValue({items:[{id:'a',source_id:'a',title:'Source A',project_code:'QA'},{id:'b',source_id:'b',title:'Source B',project_code:'QA'}] as LibrarySource[],
    total:2,offset:0,limit:50,has_next:false,labels:[]});
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.change(screen.getByLabelText('Périmètre de la question'),{target:{value:'sources'}});
  fireEvent.click(await screen.findByRole('checkbox',{name:/Source A/}));
  await waitFor(()=>expect(meetingSessions.askHistory).toHaveBeenLastCalledWith('sid','sources',['a'],expect.any(AbortSignal)));
  fireEvent.click(screen.getByRole('checkbox',{name:/Source B/}));await screen.findByText('Contexte deux sources');
  finish({items:[{query:'A',answer:'Ancien contexte A'}]});
  await waitFor(()=>expect(screen.queryByText('Ancien contexte A')).toBeNull());
  expect(JSON.parse(localStorage.getItem('agent.meeting-discussion-context.v1.sid')!)).toEqual({scope:'sources',sourceIds:['a','b']});
});

it('refuse une réponse lancée avant un changement de périmètre sans effacer la nouvelle saisie',async()=>{
  let finish!:(value:{answer:string})=>void;
  const ask=vi.spyOn(meetingSessions,'ask').mockReturnValue(new Promise(resolve=>{finish=resolve;}));
  setup(row,{...capabilities,assistant:{ready:true}});await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Réserve séance ?'}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Poser la question'})).toHaveProperty('disabled',false));
  fireEvent.click(screen.getByRole('button',{name:'Poser la question'}));await waitFor(()=>expect(ask).toHaveBeenCalledOnce());
  fireEvent.change(screen.getByLabelText('Périmètre de la question'),{target:{value:'project'}});
  fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Nouvelle question projet'}});
  finish({answer:'Réponse du précédent contexte'});
  await screen.findByText(/La réponse est conservée dans son contexte d’origine/);
  expect(screen.queryByText('Réponse du précédent contexte')).toBeNull();
  expect(screen.getByLabelText('Question à l’assistant')).toHaveProperty('value','Nouvelle question projet');
});

it('affiche une erreur de lecture d’historique puis permet sa reprise explicite',async()=>{
  vi.mocked(meetingSessions.askHistory).mockRejectedValueOnce(new Error('Historique réseau indisponible')).mockResolvedValue({items:[{query:'Question sauvegardée',answer:'Réponse sauvegardée'}]});
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  await screen.findByText('Historique réseau indisponible');fireEvent.click(screen.getByRole('button',{name:'Relire l’historique'}));
  await screen.findByText('Réponse sauvegardée');expect(screen.queryByText('Historique réseau indisponible')).toBeNull();
});

it('borne le contexte chargé à six échanges et douze mille caractères sans couper une paire',async()=>{
  vi.mocked(meetingSessions.askHistory).mockResolvedValue({items:Array.from({length:10},(_,index)=>({id:String(index),query:'Q'.repeat(2000),answer:'A'.repeat(5000)}))});
  const ask=vi.spyOn(meetingSessions,'ask').mockResolvedValue({answer:'Nouvelle réponse'});
  setup(row,{...capabilities,assistant:{ready:true}});await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Nouvelle question'}});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Poser la question'})).toHaveProperty('disabled',false));
  fireEvent.click(screen.getByRole('button',{name:'Poser la question'}));await waitFor(()=>expect(ask).toHaveBeenCalledOnce());
  const history=ask.mock.calls[0][1].history;
  expect(history.reduce((total,item)=>total+item.content.length,0)).toBeLessThanOrEqual(12000);
  expect(history.map(item=>item.role)).toEqual(['user','assistant','user','assistant']);
});

it('épingle une réponse persistée, trie les épinglées en premier et recharge son état',async()=>{
  let pinned=false;
  vi.mocked(meetingSessions.liveAnswers).mockImplementation(async()=>({items:[{id:'new',query:'Question récente',answer:'Réponse récente',pinned},
    {id:'old',query:'Question épinglée',answer:'Réponse ancienne',pinned:true}]}));
  const pin=vi.spyOn(meetingSessions,'pinAnswer').mockImplementation(async (_sid,id,value)=>{pinned=value;return {id,pinned:value};});
  const view=setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});fireEvent.click(screen.getByRole('tab',{name:'Questions en direct'}));
  await screen.findByText('Réponse ancienne');
  expect(within(screen.getByRole('log')).getAllByRole('heading',{level:3})[0].textContent).toBe('Question épinglée');
  fireEvent.click(screen.getByRole('button',{name:'Épingler la réponse'}));
  await waitFor(()=>expect(screen.getAllByRole('button',{name:'Désépingler la réponse'})).toHaveLength(2));
  expect(pin).toHaveBeenCalledWith('sid','new',true);view.unmount();
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');fireEvent.click(screen.getByRole('tab',{name:'Questions en direct'}));
  await waitFor(()=>expect(screen.getAllByRole('button',{name:'Désépingler la réponse'})).toHaveLength(2));
});

it('conserve l’état non épinglé après refus et rejoue le même choix au clic suivant',async()=>{
  vi.mocked(meetingSessions.liveAnswers).mockResolvedValue({items:[{id:'answer',query:'Question',answer:'Réponse',pinned:false}]});
  const pin=vi.spyOn(meetingSessions,'pinAnswer').mockRejectedValueOnce(new Error('Droit de modification requis')).mockResolvedValueOnce({id:'answer',pinned:true});
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Questions en direct'}));fireEvent.click(await screen.findByRole('button',{name:'Épingler la réponse'}));
  await screen.findByText('Droit de modification requis');expect(screen.getByRole('button',{name:'Épingler la réponse'}).getAttribute('aria-pressed')).toBe('false');
  fireEvent.click(screen.getByRole('button',{name:'Épingler la réponse'}));await screen.findByRole('button',{name:'Désépingler la réponse'});
  expect(pin.mock.calls.map(call=>call.slice(0,3))).toEqual([['sid','answer',true],['sid','answer',true]]);
});

it('annonce la finalisation requise après enregistrement de la note sans inventer des corrections',async()=>{
  const saved={...row,revision:4,note_revision:5,note_version_id:'v5',note:{...row.note!,content:note('Contrôle enregistré'),revision:5,version_id:'v5'}};
  vi.spyOn(meetingSessions,'saveNote').mockResolvedValue(saved);
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Contrôle enregistré'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',true));
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Compte rendu'}));
  expect(screen.getByText('Note enregistrée : version 5')).toBeTruthy();
  expect(screen.getByText(/Terminez la prise de notes avant de publier/)).toBeTruthy();
  expect(screen.queryByText(/corrections à enregistrer/)).toBeNull();
  expect(screen.queryByText(/La note a changé depuis la préparation/)).toBeNull();
  expect(screen.getByRole('button',{name:'Terminer la prise de notes'})).toHaveProperty('disabled',false);
  expect(screen.getByRole('button',{name:'Publier le compte rendu relu'})).toHaveProperty('disabled',true);
});

it('signale les vraies corrections sur une séance terminée',async()=>{
  setup({...row,state:'completed'});await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Correction en brouillon'}});
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Compte rendu'}));
  expect(screen.getByText(/corrections à enregistrer/)).toBeTruthy();
  expect(screen.queryByText(/Terminez la prise de notes avant de publier/)).toBeNull();
  expect(screen.getByRole('button',{name:'Publier le compte rendu relu'})).toHaveProperty('disabled',true);
});

it('conserve le formulaire Action entier avant ajout après Synthèse, Transcription et retour',async()=>{
  const publish=vi.spyOn(meetingSessions,'publishNotes');
  setup({...row,state:'completed'});await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Compte rendu'}));
  fireEvent.change(screen.getByLabelText('Synthèse relue'),{target:{value:'Réserve dimensionnelle à confirmer.'}});
  fireEvent.change(screen.getByLabelText('Élément du compte rendu'),{target:{value:'actions'}});
  fireEvent.change(screen.getByLabelText('Formulation'),{target:{value:'Contrôler la cote'}});
  fireEvent.change(screen.getByLabelText('Bloc cité'),{target:{value:'0'}});
  fireEvent.change(screen.getByLabelText('Extrait exact de la note'),{target:{value:'55 mm à confirmer'}});
  fireEvent.change(screen.getByLabelText('Responsable'),{target:{value:'Paul'}});
  fireEvent.change(screen.getByLabelText('Échéance'),{target:{value:'2026-10-23'}});
  fireEvent.click(screen.getByLabelText(/J’ai relu la synthèse/));
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.queryByRole('button',{name:'Ajouter au compte rendu'})).toBeNull();
  fireEvent.click(screen.getByRole('tab',{name:'Compte rendu'}));
  expect(screen.getByLabelText('Synthèse relue')).toHaveProperty('value','Réserve dimensionnelle à confirmer.');
  expect(screen.getByLabelText('Élément du compte rendu')).toHaveProperty('value','actions');
  expect(screen.getByLabelText('Formulation')).toHaveProperty('value','Contrôler la cote');
  expect(screen.getByLabelText('Bloc cité')).toHaveProperty('value','0');
  expect(screen.getByLabelText('Extrait exact de la note')).toHaveProperty('value','55 mm à confirmer');
  expect(screen.getByLabelText('Responsable')).toHaveProperty('value','Paul');
  expect(screen.getByLabelText('Échéance')).toHaveProperty('value','2026-10-23');
  expect(screen.getByLabelText(/J’ai relu la synthèse/)).toHaveProperty('checked',true);
  expect(screen.getByRole('button',{name:'Ajouter au compte rendu'})).toHaveProperty('disabled',false);
  expect(publish).not.toHaveBeenCalled();
});

it('numérote les blocs cités à partir de 1 sans transformer les autres localisateurs',async()=>{
  vi.spyOn(meetingSessions,'enhancements').mockResolvedValue({items:[{id:'enhancement',status:'prepared',text:'Contrôler la cote.',
    citations:[{title:'Note mécanique',quote:'Réserve : 55 mm à confirmer',locator:{block_index:0,note_revision:4,start_ms:3000}}]}]});
  vi.spyOn(meetingSessions,'liveAnswers').mockResolvedValue({items:[]});
  setup(row,{...capabilities,assistant:{enabled:true,ready:true}});
  const citation=await screen.findByText('Note mécanique');fireEvent.click(citation);
  expect(screen.getByText('Bloc: 1 · Version de note: 4 · Début (ms): 3000')).toBeTruthy();
  expect(screen.queryByText(/Bloc: 0/)).toBeNull();
});

it('ouvre les preuves de note et de transcription sans source_id en conservant version, piste et timecode',async()=>{
  const noteUrl='/api/v1/projects/erp/notes/note/versions/old-version';
  const load=vi.spyOn(notesApi,'version').mockResolvedValue({id:'old-version',project_id:'erp',note_id:'note',revision:2,title:'Note conservée exacte',actor_id:'human',created_at:'2026-10-11T15:30:00Z',operation:'save',
    value:{title:'Note conservée exacte',content:note('Puissance ancienne 250 W non validée.')},attachment_bindings:{}} as NoteVersion);
  const audioUrl='/api/v1/meeting-sessions/sid/audio?track=system#t=3';
  vi.spyOn(meetingSessions,'enhancements').mockResolvedValue({items:[{id:'enhancement',status:'prepared',text:'Relire.',citations:[
    {title:'Note conservée',quote:'55 mm à confirmer',source_url:noteUrl,locator:{note_id:'note',note_version_id:'old-version',erp_project_id:'erp',block:0}},
    {title:'Passage audio',excerpt:'Puissance non validée.',source_url:'/api/v1/meeting-sessions/sid/segments',audio_url:audioUrl,locator:{segment_id:'segment',track:'system',start_ms:3000,end_ms:6000}},
  ]}]});
  vi.spyOn(meetingSessions,'liveAnswers').mockResolvedValue({items:[]});
  setup(row,{...capabilities,assistant:{enabled:true,ready:true}});
  fireEvent.click(await screen.findByText('Note conservée'));
  expect(screen.getByRole('link',{name:'Ouvrir la version citée'}).getAttribute('href')).toBe(noteUrl);
  expect(screen.getByText(/Bloc: 1/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));await screen.findByText('Note conservée exacte · version 2');
  expect(load).toHaveBeenCalledWith('erp','note','old-version',expect.any(AbortSignal));
  fireEvent.click(screen.getByText('Passage audio'));
  expect(screen.getByRole('link',{name:'Consulter la source citée'}).getAttribute('href')).toBe('/api/v1/meeting-sessions/sid/segments');
  expect(screen.getByLabelText('Audio de la citation').getAttribute('src')).toBe(audioUrl);
});

it('conserve le brouillon Notes dans sa séance après ouverture B puis retour A',async()=>{
  const b={...row,id:'sid-b',title:'Séance B',note_id:'note-b',note_version_id:'version-b',note:{...row.note!,id:'note-b',version_id:'version-b',content:note('Texte B')}};
  vi.mocked(meetingSessions.get).mockImplementation(async id=>id==='sid-b'?b:row);
  const props={rows:[],capabilities,onClose:vi.fn(),onOpenProject:vi.fn()};
  const view=render(<MeetingStudio key="sid" sessionId="sid" {...props}/>);
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon A à conserver'}});
  view.rerender(<MeetingStudio key="sid-b" sessionId="sid-b" {...props}/>);
  await screen.findByDisplayValue('Texte B');
  expect(screen.queryByDisplayValue('Brouillon A à conserver')).toBeNull();
  view.rerender(<MeetingStudio key="sid" sessionId="sid" {...props}/>);
  await screen.findByDisplayValue('Brouillon A à conserver');
  expect(screen.getByText(/Brouillon retrouvé sur cet appareil/)).toBeTruthy();
  expect(JSON.parse(localStorage.getItem('agent.meeting-note.v1.sid')!)).toMatchObject({session_id:'sid',note_version_id:'note-version'});
});

it('rend les liens exacts des citations de la discussion ordinaire',async()=>{
  vi.spyOn(meetingSessions,'enhancements').mockResolvedValue({items:[]});vi.spyOn(meetingSessions,'liveAnswers').mockResolvedValue({items:[]});
  let finishHistory!:(value:{items:[]})=>void;
  vi.mocked(meetingSessions.askHistory).mockReturnValue(new Promise(resolve=>{finishHistory=resolve;}));
  const url='/api/v1/projects/erp/notes/note/versions/note-version';
  const ask=vi.spyOn(meetingSessions,'ask').mockResolvedValue({answer:'Réserve à confirmer [C1].',citations:[{title:'Note réponse',source_url:url,
    excerpt:'55 mm à confirmer',locator:{note_version_id:'note-version',block_index:0}}]});
  setup(row,{...capabilities,assistant:{enabled:true,ready:true}});await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.change(screen.getByLabelText('Question à l’assistant'),{target:{value:'Quelle réserve ?'}});
  expect(screen.getByRole('button',{name:'Poser la question'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByRole('button',{name:'Poser la question'}));expect(ask).not.toHaveBeenCalled();
  await act(async()=>{finishHistory({items:[]});});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Poser la question'})).toHaveProperty('disabled',false));
  fireEvent.click(screen.getByRole('button',{name:'Poser la question'}));
  fireEvent.click(await screen.findByText('Note réponse'));
  expect(screen.getByRole('link',{name:'Ouvrir la version citée'}).getAttribute('href')).toBe(url);
  expect(ask).toHaveBeenCalledWith('sid',expect.objectContaining({scope:'session',history:[]}));
});

it('écoute la piste du segment live et conserve son timecode',async()=>{
  const play=vi.spyOn(HTMLMediaElement.prototype,'play').mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype,'load').mockImplementation(()=>undefined);
  setup({...row,state:'completed',kind:'meeting',tracks:[{name:'system',mime_type:'audio/wav',filename:'fictif.wav',chunks:1,total_bytes:1,duration_seconds:10,complete:true}],
    segments:[{id:'seg',track:'system',start_ms:3000,end_ms:5000,speaker:'UNKNOWN',text:'Devis non validé',revision:1,finalized:false}]});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  fireEvent.click(screen.getByRole('button',{name:'0:03–0:05'}));
  expect(screen.getByLabelText('Audio de la séance').closest('.meeting-preparation')).toBeNull();
  expect(screen.getByLabelText('Audio de la séance').closest('details')).toHaveProperty('open',true);
  expect(screen.getByLabelText('Audio de la séance').closest('[role="tabpanel"]')).toHaveProperty('id','meeting-sid-transcript-panel');
  expect(play).not.toHaveBeenCalled();
  fireEvent.loadedMetadata(screen.getByLabelText('Audio de la séance'));
  expect(screen.getByLabelText('Audio de la séance').getAttribute('src')).toBe('/api/v1/meeting-sessions/sid/audio?track=system');
  expect(screen.getByLabelText('Audio de la séance')).toHaveProperty('currentTime',3);expect(play).toHaveBeenCalledOnce();
});

it('garde uniquement le dernier repère demandé avant le chargement des métadonnées audio',async()=>{
  const play=vi.spyOn(HTMLMediaElement.prototype,'play').mockResolvedValue();
  vi.spyOn(HTMLMediaElement.prototype,'load').mockImplementation(()=>undefined);
  setup({...row,state:'completed',kind:'meeting',tracks:[{name:'mic',mime_type:'audio/wav',filename:'fictif.wav',chunks:1,total_bytes:1,duration_seconds:10,complete:true}],
    segments:[{id:'first',track:'mic',start_ms:2000,end_ms:4000,speaker:'MIC',text:'Premier',revision:1,finalized:true},
      {id:'last',track:'mic',start_ms:7000,end_ms:9000,speaker:'MIC',text:'Dernier',revision:1,finalized:true}]});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  fireEvent.click(screen.getByRole('button',{name:'0:02–0:04'}));
  fireEvent.click(screen.getByRole('button',{name:'0:07–0:09'}));
  expect(play).not.toHaveBeenCalled();
  const player=screen.getByLabelText('Audio de la séance');
  fireEvent.loadedMetadata(player);
  expect(player).toHaveProperty('currentTime',7);
  expect(play).toHaveBeenCalledOnce();
  fireEvent.loadedMetadata(player);
  expect(play).toHaveBeenCalledOnce();
});

it('isole une erreur de sauvegarde tardive après changement de séance et retrouve les deux brouillons',async()=>{
  const b={...row,id:'sid-b',title:'Séance B',note_id:'note-b',note_version_id:'version-b',note:{...row.note!,id:'note-b',version_id:'version-b',content:note('Texte B')}};
  vi.mocked(meetingSessions.get).mockImplementation(async id=>id==='sid-b'?b:row);
  let fail!:(reason:Error)=>void;
  const save=vi.spyOn(meetingSessions,'saveNote').mockReturnValueOnce(new Promise((_resolve,reject)=>{fail=reject;}))
    .mockResolvedValueOnce({...row,revision:4,note_revision:5,note_version_id:'v5',note:{...row.note!,revision:5,version_id:'v5',content:note('Brouillon A à conserver')}});
  const props={rows:[],capabilities,onClose:vi.fn(),onOpenProject:vi.fn()};
  const view=render(<MeetingStudio key="sid" sessionId="sid" {...props}/>);
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon A à conserver'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));
  expect(save).toHaveBeenCalledTimes(1);
  view.rerender(<MeetingStudio key="sid-b" sessionId="sid-b" {...props}/>);
  await screen.findByDisplayValue('Texte B');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon B à conserver'}});
  await act(async()=>{fail(new Error('Erreur tardive de la séance A'));});
  expect(screen.queryByText('Erreur tardive de la séance A')).toBeNull();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Brouillon B à conserver');
  view.rerender(<MeetingStudio key="sid" sessionId="sid" {...props}/>);
  await screen.findByDisplayValue('Brouillon A à conserver');
  fireEvent.click(screen.getByRole('button',{name:'Reprendre l’enregistrement'}));
  await waitFor(()=>expect(save).toHaveBeenCalledTimes(2));
  expect(save.mock.calls[1][1].command_id).toBe(save.mock.calls[0][1].command_id);
  view.rerender(<MeetingStudio key="sid-b" sessionId="sid-b" {...props}/>);
  await screen.findByDisplayValue('Brouillon B à conserver');
});

it('sauvegarde la version de note ERP attendue et conserve la saisie arrivée pendant l’enregistrement',async()=>{
  let finish!:(value:MeetingSession)=>void;
  const save=vi.spyOn(meetingSessions,'saveNote').mockReturnValue(new Promise(resolve=>{finish=resolve;}));
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Premier texte'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));
  await waitFor(()=>expect(save).toHaveBeenCalledWith('sid',expect.objectContaining({expected_revision:3,expected_note_revision:4,expected_note_version_id:'note-version'})));
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Nouvelle correction pendant sauvegarde'}});
  const newer={...row,revision:4,note_revision:5,note_version_id:'v5',note:{...row.note!,content:note('Premier texte'),revision:5,version_id:'v5'}};
  finish(newer);
  await screen.findByText('Commande précédente enregistrée. Les nouvelles corrections restent à enregistrer.');
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Nouvelle correction pendant sauvegarde');
  expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',false);
});

it('ne lance pas deux enregistrements de note pendant le même traitement React',async()=>{
  let finish!:(value:MeetingSession)=>void;
  const save=vi.spyOn(meetingSessions,'saveNote').mockReturnValue(new Promise(resolve=>{finish=resolve;}));
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Correction à conserver'}});
  const button=screen.getByRole('button',{name:'Enregistrer la note'});
  act(()=>{fireEvent.click(button);fireEvent.click(button);});
  expect(save).toHaveBeenCalledTimes(1);
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Correction à conserver');
  await act(async()=>{finish({...row,revision:4});});
});

it('reprend un enregistrement réseau interrompu avec la même clé et sans perdre le brouillon',async()=>{
  const save=vi.spyOn(meetingSessions,'saveNote').mockRejectedValueOnce(new Error('Réseau absent')).mockResolvedValueOnce({...row,revision:4});
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Correction conservée'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));
  await screen.findByText('Réseau absent');
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Correction conservée');
  fireEvent.click(screen.getByRole('button',{name:'Reprendre l’enregistrement'}));
  await waitFor(()=>expect(save).toHaveBeenCalledTimes(2));
  expect(save.mock.calls[1][1].command_id).toBe(save.mock.calls[0][1].command_id);
});

it('expose la version concurrente et bloque l’écrasement jusqu’à résolution explicite',async()=>{
  const save=vi.spyOn(meetingSessions,'saveNote').mockRejectedValue(new Error('La note a changé'));
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  vi.mocked(meetingSessions.get).mockResolvedValue({...row,note_revision:5,note_version_id:'other',note:{...row.note!,revision:5,version_id:'other',content:note('Autre opérateur')}});
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Ma saisie'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la note'}));
  await screen.findByText('La version enregistrée a changé. Votre saisie est conservée.');
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Ma saisie');
  expect(screen.getByRole('button',{name:'Reprendre l’enregistrement'})).toHaveProperty('disabled',true);
  fireEvent.click(screen.getByText('Comparer la version enregistrée'));expect(screen.getByText('Autre opérateur')).toBeTruthy();expect(save).toHaveBeenCalledTimes(1);
});

it('conserve les notes lors du changement entre les deux dispositions référencées',async()=>{
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'À conserver'}});
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  expect(screen.getByRole('tab',{name:'Transcription'})).toBeTruthy();
  fireEvent.click(screen.getByRole('tab',{name:'Compte rendu'}));
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'enhanced'}});
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','À conserver');
});

it('montre notes et enrichissement dans le même groupe gauche avec l’assistant simultanément',async()=>{
  vi.mocked(meetingSessions.enhancements).mockResolvedValue({items:[{id:'proposal',status:'pending',text:'Proposition sourcée à relire.'}]});
  vi.mocked(meetingSessions.askHistory).mockResolvedValue({items:[{id:'answer',query:'Quelle réserve ?',answer:'Réponse conservée : cote à confirmer.'}]});
  const enhance=vi.spyOn(meetingSessions,'enhance'),ask=vi.spyOn(meetingSessions,'ask'),save=vi.spyOn(meetingSessions,'saveNote');
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'complete'}});
  const notes=screen.getByRole('region',{name:'Notes de séance'}),enriched=screen.getByRole('region',{name:'Notes enrichies'}),assistant=screen.getByRole('region',{name:'Assistant de la séance'});
  expect(notes.parentElement).toBe(enriched.parentElement);
  expect(notes.parentElement?.classList.contains('meeting-notes-stack')).toBe(true);
  expect(notes.parentElement?.parentElement).toBe(assistant.parentElement);
  expect(assistant.parentElement?.classList.contains('meeting-layout-complete')).toBe(true);
  expect(screen.getAllByRole('region',{name:'Notes enrichies',hidden:true})).toHaveLength(1);
  expect(within(enriched).getByText('Proposition sourcée à relire.')).toBeTruthy();
  await within(assistant).findByText('Réponse conservée : cote à confirmer.');
  expect(within(assistant).getByRole('tab',{name:'Discussion'})).toBeTruthy();
  expect(enhance).not.toHaveBeenCalled();expect(ask).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
});

it('garde les mêmes nœuds de l’éditeur et de l’enrichissement avec le brouillon à travers les trois dispositions',async()=>{
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  const editor=screen.getByTestId('note-editor'),input=screen.getByLabelText('Texte des notes') as HTMLTextAreaElement;
  const enriched=screen.getByRole('region',{name:'Notes enrichies'});
  fireEvent.change(input,{target:{value:'Brouillon humain non validé à conserver'}});input.setSelectionRange(3,12);
  fireEvent.click(screen.getByRole('button',{name:'Simuler un brouillon Markdown invalide'}));
  for(const value of ['complete','assistant','enhanced','complete']){
    fireEvent.change(screen.getByLabelText('Disposition'),{target:{value}});
    expect(screen.getByTestId('note-editor')).toBe(editor);expect(screen.getByLabelText('Texte des notes')).toBe(input);
    expect(document.querySelector('.meeting-enhanced-pane')).toBe(enriched);
    expect(input.value).toBe('Brouillon humain non validé à conserver');expect(input.selectionStart).toBe(3);expect(input.selectionEnd).toBe(12);
    expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',true);
    expect(screen.getByText(/Brouillon Markdown invalide : corrigez-le/)).toBeTruthy();
  }
  expect(JSON.parse(localStorage.getItem('agent.meeting-note.v1.sid')!).content).toEqual(note('Brouillon humain non validé à conserver'));
  expect(localStorage.getItem('agent-meeting-layout-v2')).toBe('complete');
});

it('conserve l’onglet, la question et l’historique lorsque la disposition masque puis remonte l’assistant',async()=>{
  localStorage.setItem('agent-meeting-layout-v2','complete');
  vi.mocked(meetingSessions.askHistory).mockResolvedValue({items:[{id:'history',query:'Réserve ?',answer:'Historique de séance inchangé.'}]});
  vi.mocked(meetingSessions.liveAnswers).mockResolvedValue({items:[{id:'live',query:'Question conservée',answer:'Réponse en direct conservée.',pinned:true}]});
  setup(row,{...capabilities,assistant:{ready:true}});await screen.findByText('Historique de séance inchangé.');
  const assistant=screen.getByRole('region',{name:'Assistant de la séance'}),history=screen.getByText('Historique de séance inchangé.');
  const question=screen.getByLabelText('Question à l’assistant');fireEvent.change(question,{target:{value:'Question non envoyée à conserver'}});
  const historyReads=vi.mocked(meetingSessions.askHistory).mock.calls.length;
  for(const value of ['assistant','enhanced','complete']){
    fireEvent.change(screen.getByLabelText('Disposition'),{target:{value}});
    expect(document.querySelector('.meeting-assistant-pane')).toBe(assistant);
    expect(screen.getByText('Historique de séance inchangé.')).toBe(history);
  }
  expect(screen.getByLabelText('Question à l’assistant')).toBe(question);expect(question).toHaveProperty('value','Question non envoyée à conserver');
  expect(meetingSessions.askHistory).toHaveBeenCalledTimes(historyReads);
  fireEvent.click(screen.getByRole('tab',{name:'Questions en direct'}));await screen.findByText('Réponse en direct conservée.');
  const pinned=screen.getByRole('button',{name:'Désépingler la réponse'});
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'enhanced'}});
  expect(screen.queryByRole('tab',{name:'Questions en direct'})).toBeNull();
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'complete'}});
  expect(screen.getByRole('tab',{name:'Questions en direct'}).getAttribute('aria-selected')).toBe('true');
  expect(screen.getByRole('button',{name:'Désépingler la réponse'})).toBe(pinned);
});

it.each(['enhanced','assistant','complete'] as const)('restaure la disposition enregistrée %s après réouverture sans changer les préférences existantes',async value=>{
  localStorage.setItem('agent-meeting-layout-v2',value);
  const first=setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  expect(screen.getByLabelText('Disposition')).toHaveProperty('value',value);
  first.unmount();setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  expect(screen.getByLabelText('Disposition')).toHaveProperty('value',value);
  expect(!!screen.queryByRole('region',{name:'Notes enrichies'})).toBe(value!=='assistant');
  expect(!!screen.queryByRole('region',{name:'Assistant de la séance'})).toBe(value!=='enhanced');
  expect(localStorage.getItem('agent-meeting-layout-v2')).toBe(value);
});

it('retrouve la nouvelle disposition et le brouillon humain après démontage et réouverture',async()=>{
  const first=setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'complete'}});
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon complet à retrouver'}});
  first.unmount();setup();await screen.findByDisplayValue('Brouillon complet à retrouver');
  expect(screen.getByLabelText('Disposition')).toHaveProperty('value','complete');
  expect(screen.getByRole('region',{name:'Notes enrichies'})).toBeTruthy();expect(screen.getByRole('region',{name:'Assistant de la séance'})).toBeTruthy();
  expect(screen.getByText('Brouillon retrouvé sur cet appareil ; votre saisie est conservée.')).toBeTruthy();
});

it('adapte la hauteur disponible des trois dispositions au viewport sans remonter l’éditeur puis libère la hauteur sur mobile',async()=>{
  vi.stubGlobal('innerWidth',850);vi.stubGlobal('innerHeight',479);vi.stubGlobal('scrollY',0);
  let top=80;let onResize:()=>void=()=>undefined;
  const disconnect=vi.fn();
  vi.stubGlobal('ResizeObserver',class{constructor(callback:ResizeObserverCallback){onResize=()=>callback([],this as unknown as ResizeObserver);}observe(){}disconnect=disconnect;});
  vi.spyOn(HTMLElement.prototype,'getBoundingClientRect').mockImplementation(function(this:HTMLElement){return {top:this.classList.contains('meeting-studio')?top:0} as DOMRect;});
  try{
    localStorage.setItem('agent-meeting-layout-v2','complete');const first=setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
    const studio=screen.getByRole('region',{name:'Séance Revue mécanique'}),editor=screen.getByTestId('note-editor');
    fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon conservé pendant le redimensionnement'}});
    expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('391px');
    top=100;act(()=>onResize());expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('371px');
    vi.stubGlobal('innerWidth',670);fireEvent(window,new Event('resize'));
    expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('');
    expect(screen.getByTestId('note-editor')).toBe(editor);expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Brouillon conservé pendant le redimensionnement');
    vi.stubGlobal('innerWidth',850);vi.stubGlobal('innerHeight',600);fireEvent(window,new Event('resize'));
    expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('492px');
    for(const value of ['assistant','enhanced','complete']){
      fireEvent.change(screen.getByLabelText('Disposition'),{target:{value}});expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('492px');
    }
    expect(screen.getByTestId('note-editor')).toBe(editor);
    first.unmount();expect(disconnect).toHaveBeenCalled();
  }finally{vi.unstubAllGlobals();}
});

it('garde les commandes secondaires montées dans Préparation et les alertes visibles hors du panneau replié',async()=>{
  localStorage.setItem('agent-meeting-layout-v2','complete');
  vi.mocked(meetingSessions.enhancements).mockResolvedValue({items:[],automatic:automatic('failed',{error:'Tentative échouée ; la note enregistrée est conservée.'})});
  setup({...row,issues:['Vérifier la valeur avant validation.']});await screen.findByText('Tentative échouée ; la note enregistrée est conservée.');
  const commands=screen.getByRole('region',{name:'Commandes et état de la séance'}),selector=screen.getByLabelText('Disposition');
  const editor=screen.getByTestId('note-editor'),alert=screen.getByRole('alert');
  expect(screen.getByRole('button',{name:'Terminer la prise de notes'}).closest('.meeting-preparation')).toBeNull();
  expect(within(commands).getByRole('link',{name:'Exporter et récupérer la séance'})).toBeTruthy();
  expect(screen.getByText('Vérifier la valeur avant validation.').closest('.meeting-preparation')).toBeNull();
  for(const value of ['enhanced','assistant','complete']){
    fireEvent.change(selector,{target:{value}});
    expect(screen.getByRole('region',{name:'Commandes et état de la séance'})).toBe(commands);
    expect(screen.getByRole('alert')).toBe(alert);expect(alert.closest('.meeting-preparation')).toBeNull();expect(alert.closest('[hidden]')).toBeNull();expect(screen.getByTestId('note-editor')).toBe(editor);
  }
  expect(commands.getAttribute('tabindex')).toBe('0');
  expect(screen.getByRole('region',{name:'Notes de séance'}).getAttribute('tabindex')).toBe('0');
  expect(screen.getByRole('region',{name:'Notes enrichies'}).getAttribute('tabindex')).toBe('0');
  expect(screen.getByRole('tabpanel').getAttribute('tabindex')).toBe('0');
  expect(screen.getAllByTestId('note-editor')).toHaveLength(1);
});

it('emploie le même seuil CSS de la vue complète même lorsque innerWidth arrondit différemment la largeur',async()=>{
  const desktop={matches:true,addEventListener:vi.fn(),removeEventListener:vi.fn()};
  const matchMedia=vi.fn().mockReturnValue(desktop);
  vi.stubGlobal('innerWidth',670);vi.stubGlobal('innerHeight',479);vi.stubGlobal('scrollY',0);vi.stubGlobal('matchMedia',matchMedia);
  try{
    localStorage.setItem('agent-meeting-layout-v2','complete');const first=setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
    const studio=screen.getByRole('region',{name:'Séance Revue mécanique'}),editor=screen.getByTestId('note-editor');
    expect(matchMedia).toHaveBeenCalledWith('(min-width:671px)');expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('471px');
    const size=desktop.addEventListener.mock.calls[0][1] as ()=>void;
    desktop.matches=false;vi.stubGlobal('innerWidth',671);act(()=>size());
    expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('');expect(screen.getByTestId('note-editor')).toBe(editor);
    desktop.matches=true;act(()=>size());expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('471px');
    expect(screen.getAllByTestId('note-editor')).toHaveLength(1);
    first.unmount();expect(desktop.removeEventListener).toHaveBeenCalledWith('change',size);
  }finally{vi.unstubAllGlobals();}
});

it('affiche les indisponibilités réelles et ne propose pas une amélioration active',async()=>{
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  expect(screen.getByText(/Transcription en direct indisponible/)).toBeTruthy();
  expect(screen.getByRole('button',{name:'Améliorer les notes'})).toHaveProperty('disabled',true);
});

it('utilise les millisecondes des segments live et leur statut sans créer un faux compte rendu',async()=>{
  setup({...row,recording_id:null,transcript_provisional:true,segments:[{id:'live-1',track:'system',start_ms:65000,end_ms:71000,
    speaker:'Voix 2',text:'Ne pas engager la fabrication.',revision:2,finalized:false}]});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByRole('button',{name:'1:05–1:11'})).toHaveProperty('disabled',true);
  expect(screen.getByText('Ne pas engager la fabrication.')).toBeTruthy();
  expect(screen.queryByRole('region',{name:'Parcours audio existant'})).toBeNull();
});

it('conserve une correction live non enregistrée à travers les onglets et les dispositions',async()=>{
  setup({...row,segments:[{id:'segment',track:'mic',start_ms:0,end_ms:2000,speaker:'Voix 1',text:'Texte original',revision:1,finalized:false}]});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  fireEvent.click(screen.getByRole('button',{name:'Corriger ce passage'}));fireEvent.change(screen.getByLabelText('Texte corrigé'),{target:{value:'Correction humaine à conserver'}});
  fireEvent.click(screen.getByRole('tab',{name:'Discussion'}));fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'enhanced'}});
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByLabelText('Texte corrigé')).toHaveProperty('value','Correction humaine à conserver');
});

it('ouvre et ferme Préparation au clavier sans changer le brouillon ni lancer une commande',async()=>{
  const command=vi.spyOn(meetingSessions,'command'),capture=vi.spyOn(meetingCapture,'start');
  setup();await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  const editor=screen.getByTestId('note-editor'),details=document.querySelector('details.meeting-preparation') as HTMLDetailsElement;
  const summary=details.querySelector('summary')!;
  expect(details.open).toBe(false);details.open=true;
  fireEvent.change(screen.getByLabelText('Texte des notes'),{target:{value:'Brouillon humain conservé dans la disposition compacte'}});
  fireEvent.click(screen.getByRole('button',{name:'Simuler un brouillon Markdown invalide'}));
  fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'complete'}});
  const selector=screen.getByLabelText('Disposition');selector.focus();
  fireEvent.keyDown(selector,{key:'Escape'});
  expect(details.open).toBe(false);expect(document.activeElement).toBe(summary);
  expect(screen.getByTestId('note-editor')).toBe(editor);
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Brouillon humain conservé dans la disposition compacte');
  expect(screen.getByRole('button',{name:'Enregistrer la note'})).toHaveProperty('disabled',true);
  details.open=true;fireEvent.click(screen.getByRole('button',{name:'Fermer la préparation'}));
  expect(details.open).toBe(false);expect(document.activeElement).toBe(summary);
  expect(command).not.toHaveBeenCalled();expect(capture).not.toHaveBeenCalled();
});

it.each(['enhanced','assistant','complete'] as const)('soustrait le padding bas réel pour la hauteur de la disposition %s',async layout=>{
  vi.stubGlobal('innerWidth',850);vi.stubGlobal('innerHeight',479);vi.stubGlobal('scrollY',0);
  vi.spyOn(HTMLElement.prototype,'getBoundingClientRect').mockImplementation(()=>({top:56}) as DOMRect);
  try{
    localStorage.setItem('agent-meeting-layout-v2',layout);
    const view=render(<main className="workspace-main" style={{paddingBottom:20}}><MeetingStudio sessionId="sid" rows={[]} capabilities={capabilities} onClose={vi.fn()} onOpenProject={vi.fn()}/></main>);
    await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
    expect(screen.getByRole('region',{name:'Séance Revue mécanique'}).style.getPropertyValue('--meeting-studio-height')).toBe('403px');
    view.unmount();
  }finally{vi.unstubAllGlobals();}
});

it('réduit la hauteur disponible quand une barre de capture apparaît au-dessus sans resize du viewport',async()=>{
  vi.stubGlobal('innerWidth',850);vi.stubGlobal('innerHeight',479);vi.stubGlobal('scrollY',0);let top=56;
  vi.spyOn(HTMLElement.prototype,'getBoundingClientRect').mockImplementation(()=>({top}) as DOMRect);
  try{
    const view=render(<main className="workspace-main" style={{paddingBottom:8}}><MeetingStudio sessionId="sid" rows={[]} capabilities={capabilities} onClose={vi.fn()} onOpenProject={vi.fn()}/></main>);
    await screen.findByDisplayValue('Réserve : 55 mm à confirmer');const studio=screen.getByRole('region',{name:'Séance Revue mécanique'});
    expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('415px');
    const bar=document.createElement('section');bar.className='meeting-capture-bar';bar.textContent='Capture active simulée';top+=70;studio.parentElement!.prepend(bar);
    await waitFor(()=>expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('345px'));
    top-=70;bar.remove();await waitFor(()=>expect(studio.style.getPropertyValue('--meeting-studio-height')).toBe('415px'));
    expect(screen.getAllByTestId('note-editor')).toHaveLength(1);view.unmount();
  }finally{vi.unstubAllGlobals();}
});

it.each(['recording','paused'] as const)('laisse les commandes Windows %s hors Préparation avec le brouillon Markdown',async state=>{
  const item={session_id:'sid',state,tracks:['system' as const]};
  const native={installed:true,ready:true,loopback_ready:true,real_test_passed:true,microphone_test_passed:false,devices:[],active:[item],session:item};
  vi.spyOn(meetingSessions,'nativeStatus').mockResolvedValue(native);
  const control=vi.spyOn(meetingSessions,'native').mockResolvedValue({...row,kind:'meeting',state:'completed'});
  setup({...row,kind:'meeting',state},{...capabilities,native_capture:native});await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  fireEvent.click(screen.getByRole('button',{name:'Simuler un brouillon Markdown invalide'}));
  const stop=screen.getByRole('button',{name:'Arrêter Windows et conserver la séance'});
  const pause=screen.getByRole('button',{name:state==='paused'?'Reprendre la capture Windows':'Mettre Windows en pause'});
  expect(stop.closest('.meeting-preparation')).toBeNull();expect(pause.closest('.meeting-preparation')).toBeNull();
  expect(stop).toHaveProperty('disabled',false);expect(pause).toHaveProperty('disabled',false);
  expect(stop.closest('details')).toBeNull();expect(pause.closest('details')).toBeNull();
  const diagnostics=screen.getByText('État des périphériques').closest('details')!;
  expect(diagnostics.open).toBe(false);stop.focus();fireEvent.click(stop);
  await waitFor(()=>expect(control).toHaveBeenCalledWith('sid','stop',expect.objectContaining({expected_revision:3})));
});

const speechChunk=(state:NonNullable<SessionChunk['speech_status']>,track:SessionChunk['track']='system',duration=5000):SessionChunk=>({id:`${track}-fragment`,track,sequence:0,
  sha256:'fictive-hash',size_bytes:20,start_ms:0,duration_ms:duration,speech_status:state,speech_error:state==='failed'?'Moteur indisponible : essai fictif.':null});
it('sépare le travail admis de l’audio archivé sans l’exécuter ni le déclarer terminé',async()=>{
  const retry=vi.spyOn(meetingSessions,'retryTranscription'),batch=vi.spyOn(meetingSessions,'batchTranscription');
  setup({...row,kind:'meeting',state:'recording',chunks:[speechChunk('pending','mic'),speechChunk('retained','system')],segments:[],
    transcript_processing_complete:true,transcription_admission:{policy:'direct-admission-v1',suspended:false,admitted_chunks:1,
      retained_chunks:1,retained_batch_only_chunks:0,recoverable_direct_chunks:1}});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  const status=screen.getByRole('status',{name:'État du traitement STT'});
  expect(within(status).getByText('Microphone : 5 s dans la file du direct sur cette piste.')).toBeTruthy();
  expect(within(status).getByText('Audio partagé : 5 s sauvegardées hors du direct sur cette piste.')).toBeTruthy();
  expect(within(status).queryByRole('alert')).toBeNull();expect(screen.queryByText(/Traitement STT terminé/)).toBeNull();
  expect(retry).not.toHaveBeenCalled();expect(batch).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Réserve : 55 mm à confirmer');
});

it('signale la suspension du direct hors Préparation et conserve la saisie des notes',async()=>{
  setup({...row,state:'recording',transcription_admission:{policy:'direct-admission-v1',suspended:true,reason:'capacity',admitted_chunks:24,
    retained_chunks:1,retained_batch_only_chunks:0,recoverable_direct_chunks:1}});
  const banner=await screen.findByText(/L’enregistrement continue\. La transcription directe est suspendue/);
  expect(banner.closest('.meeting-preparation')).toBeNull();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('disabled',false);
  expect(screen.queryByText(/latence qualifiée|P95/)).toBeNull();
});

it.each([1,0])('distingue le direct suspendu des derniers fragments admis (%s) sans reprise automatique',async admitted=>{
  const retry=vi.spyOn(meetingSessions,'retryTranscription'),batch=vi.spyOn(meetingSessions,'batchTranscription'),capture=vi.spyOn(meetingCapture,'start');
  setup({...row,state:'recording',chunks:[...(admitted?[speechChunk('pending','mic')]:[]),speechChunk('retained','system')],
    transcription_admission:{policy:'direct-admission-v1',suspended:true,reason:'capacity',admitted_chunks:admitted,
      retained_chunks:1,retained_batch_only_chunks:0,recoverable_direct_chunks:1}});
  await screen.findByText(/L’enregistrement continue\. La transcription directe est suspendue/);
  fireEvent.click(screen.getByRole('button',{name:'Transcription'}));
  expect(screen.getByText(admitted?'Transcription des passages en attente':'Direct suspendu')).toBeTruthy();
  expect(screen.queryByText('Suivi du direct')).toBeNull();
  expect(screen.getByText(admitted?/Les derniers passages en attente sont encore traités/:/Les passages restants sont conservés pour une transcription ultérieure/)).toBeTruthy();
  expect(retry).not.toHaveBeenCalled();expect(batch).not.toHaveBeenCalled();expect(capture).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Réserve : 55 mm à confirmer');
});

it.each([true,false])('après arrêt distingue les 1341 fragments conservés du direct avec moteur différé disponible=%s',async installed=>{
  const retry=vi.spyOn(meetingSessions,'retryTranscription'),batch=vi.spyOn(meetingSessions,'batchTranscription'),capture=vi.spyOn(meetingCapture,'start');
  const chunks=Array.from({length:1440},(_,index)=>({...speechChunk(index<99?'completed':'retained',index%2?'mic':'system'),
    id:`kept-${index}`,sequence:Math.floor(index/2),start_ms:Math.floor(index/2)*5000}));
  setup({...row,state:'completed',chunks,transcript_processing_complete:false,
    transcription_admission:{policy:'direct-admission-v1',suspended:true,reason:'capacity',admitted_chunks:0,
      retained_chunks:1341,retained_batch_only_chunks:0,recoverable_direct_chunks:1341}},
    {...capabilities,transcription:{...capabilities.transcription,enabled:false,session_batch_ready:installed}});
  await screen.findByText(/L’enregistrement est terminé et conservé\. La transcription directe a été suspendue/);
  fireEvent.click(screen.getByRole('button',{name:'Transcription'}));
  expect(screen.queryByText(/L’enregistrement continue/)).toBeNull();expect(screen.queryByText('Suivi du direct')).toBeNull();
  expect(screen.getByText(/1341 conservés hors direct.*99 traités/)).toBeTruthy();
  expect(screen.getByRole('button',{name:'Transcrire l’audio conservé'})).toHaveProperty('disabled',!installed);
  expect(screen.queryByText(/Traitement STT terminé/)).toBeNull();
  expect(retry).not.toHaveBeenCalled();expect(batch).not.toHaveBeenCalled();expect(capture).not.toHaveBeenCalled();
});

it.each(['retained','pending'] as const)('permet le traitement complet explicite d’un audio personnel %s inconnu sans activer le direct',async state=>{
  const personal={...row,project_id:null,brain_project_id:null,note_id:null,note:null,staged_note:{title:'Notes mécaniques',content:note('Note personnelle conservée'),revision:1},
    state:'completed' as const,chunks:[speechChunk(state,'mic',0)],transcription_admission:{policy:'direct-admission-v1',suspended:false,
      admitted_chunks:0,retained_chunks:1,retained_batch_only_chunks:1,recoverable_direct_chunks:0}};
  const admitted={command_id:'batch-command',state:'admitted' as const,selected_chunks:1,completed_chunks:0,error:null};
  const batch=vi.spyOn(meetingSessions,'batchTranscription').mockResolvedValue({session:{...personal,transcription_batch:admitted},batch:admitted});
  const retry=vi.spyOn(meetingSessions,'retryTranscription'),capture=vi.spyOn(meetingCapture,'start');
  setup(personal,{...capabilities,transcription:{...capabilities.transcription,enabled:false,session_batch_ready:true}});
  await screen.findByDisplayValue('Note personnelle conservée');fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  expect(screen.getByLabelText('État de l’audio').textContent).toContain('Durée inconnue');
  expect(screen.getByLabelText('État de l’audio').textContent).not.toContain('0:00');
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(batch).not.toHaveBeenCalled();expect(screen.queryByRole('button',{name:'Reprendre un lot de transcription'})).toBeNull();
  const button=screen.getByRole('button',{name:'Transcrire l’audio conservé'});expect(button).toHaveProperty('disabled',false);
  fireEvent.click(button);await waitFor(()=>expect(batch).toHaveBeenCalledWith('sid',expect.objectContaining({expected_revision:3})));
  expect(retry).not.toHaveBeenCalled();expect(capture).not.toHaveBeenCalled();
  await screen.findByRole('button',{name:'Annuler le traitement complet'});
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Note personnelle conservée');
});

it('annule explicitement le traitement complet tout en gardant notes et texte déjà reçus',async()=>{
  const active={command_id:'batch-command',state:'running' as const,selected_chunks:2,completed_chunks:1,error:null};
  const session={...row,state:'completed' as const,chunks:[speechChunk('batch_running')],transcription_batch:active};
  const cancelling={...active,state:'cancelling' as const};
  const cancel=vi.spyOn(meetingSessions,'cancelBatchTranscription').mockResolvedValue({session:{...session,transcription_batch:cancelling},batch:cancelling});
  setup(session);await screen.findByDisplayValue('Réserve : 55 mm à confirmer');fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  const status=screen.getByRole('status',{name:'État du traitement complet'});
  expect(status.textContent).toContain('1 / 2 fragment(s) traités');expect(cancel).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Annuler le traitement complet'}));
  await waitFor(()=>expect(cancel).toHaveBeenCalledWith('sid',expect.objectContaining({expected_revision:3})));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Annuler le traitement complet'})).toHaveProperty('disabled',true));
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Réserve : 55 mm à confirmer');
});

it.each(['pending','running','failed'] as const)('montre le traitement %s même avant le premier segment sans changer les notes',async state=>{
  const save=vi.spyOn(meetingSessions,'saveNote');setup({...row,kind:'meeting',state:'recording',segments:[],chunks:[speechChunk(state)],transcript_processing_complete:false,transcript_provisional:true});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  const status=screen.getByRole('status',{name:'État du traitement STT'});
  expect(within(status).getByText(`Fragments STT : ${state==='pending'?1:0} en attente · ${state==='running'?1:0} en cours · 0 conservés hors direct · ${state==='failed'?1:0} à reprendre · 0 traités.`)).toBeTruthy();
  expect(within(status).getByText('Aucun segment disponible pour le moment.')).toBeTruthy();
  if(state==='failed')expect(within(status).getByRole('alert').textContent).toContain('Moteur indisponible : essai fictif.');
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Réserve : 55 mm à confirmer');expect(save).not.toHaveBeenCalled();
  expect(screen.queryByText(/5 secondes|P95|latence qualifiée/)).toBeNull();
});

it('distingue une STT terminée sans parole de l’attente avant le premier segment',async()=>{
  setup({...row,kind:'meeting',state:'completed',segments:[],chunks:[speechChunk('completed')],transcript_processing_complete:true,transcript_provisional:false});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});
  fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText('Traitement STT terminé ; aucun segment de parole disponible.')).toBeTruthy();
  expect(screen.queryByText('Aucun segment disponible pour le moment.')).toBeNull();expect(screen.queryByText('Segments consolidés.')).toBeNull();
});

it('ne présente pas le traitement fini comme une validation du texte provisoire',async()=>{
  setup({...row,kind:'meeting',state:'completed',chunks:[speechChunk('completed')],transcript_processing_complete:true,transcript_provisional:false,
    segments:[{id:'live',track:'system',start_ms:0,end_ms:5000,speaker:'Voix à identifier',text:'Puissance non validée.',revision:1,finalized:false}]});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText('Traitement STT terminé ; le texte reste soumis à consolidation et relecture.')).toBeTruthy();
  expect(screen.getByText('Texte provisoire ; la consolidation finale reste nécessaire.')).toBeTruthy();expect(screen.queryByText('Segments consolidés.')).toBeNull();
});

it('présente les deux pistes en attente séparément sans fabriquer dix secondes de retard mural',async()=>{
  setup({...row,kind:'meeting',state:'recording',segments:[],chunks:[speechChunk('pending','mic'),speechChunk('running','system')]});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');fireEvent.change(screen.getByLabelText('Disposition'),{target:{value:'assistant'}});fireEvent.click(screen.getByRole('tab',{name:'Transcription'}));
  expect(screen.getByText('Microphone : 5 s dans la file du direct sur cette piste.')).toBeTruthy();
  expect(screen.getByText('Audio partagé : 5 s dans la file du direct sur cette piste.')).toBeTruthy();
  expect(screen.queryByText(/10 s|retard mural|P95/)).toBeNull();
});

it('expose le direct en essai et son détail même lorsque la transcription batch est prête',async()=>{
  setup(row,{...capabilities,transcription:{live_ready:false,live_operational:true,qualified_live_latency:false,industrial_quality_qualified:false,batch_ready:true,
    detail:'Qualité et latence industrielles non qualifiées ; relecture nécessaire.'}});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  const banner=screen.getByText(/Direct en essai, non qualifié/);
  expect(banner.textContent).toContain('Transcription de l’audio conservé disponible.');
  expect(banner.textContent).toContain('Qualité et latence industrielles non qualifiées ; relecture nécessaire.');
  expect(screen.queryByText('Transcription en direct disponible.')).toBeNull();
});

it.each([
  {enabled:true,installed:true,live_operational:false,message:'Direct activé en essai, non qualifié. Relecture nécessaire.'},
  {enabled:false,installed:true,live_operational:true,message:'Transcription en direct désactivée.'},
  {enabled:true,installed:false,live_operational:false,message:'Transcription en direct indisponible.'},
])('distingue le runtime installé, l’accord de direct et la qualification : $message',async({message,...status})=>{
  const start=vi.spyOn(meetingSessions,'command');
  setup(row,{...capabilities,transcription:{...status,live_ready:false,batch_ready:true,detail:'Profil installé, performances non qualifiées.'}});
  await screen.findByDisplayValue('Réserve : 55 mm à confirmer');
  const banner=screen.getByText(content=>content.startsWith(message));
  expect(banner.textContent).toContain('Transcription de l’audio conservé disponible.');
  expect(screen.queryByText('Transcription en direct disponible.')).toBeNull();
  expect(start).not.toHaveBeenCalled();
});

// Append to the isolated copy of MeetingStudio.test.tsx; uses its existing fixtures.
it('affiche une réponse vide comme aucun ajout utile sans acceptation ni erreur',async()=>{
  const enhance=vi.spyOn(meetingSessions,'enhance').mockResolvedValue({id:'empty-proposal',status:'pending',
    note_revision:4,note_version_id:'note-version',text:'',citations:[],content:{version:1,blocks:[]}});
  const decide=vi.spyOn(meetingSessions,'decide'),save=vi.spyOn(meetingSessions,'saveNote');
  setup(row,{...capabilities,assistant:{ready:true}});await screen.findByDisplayValue('Notes mécaniques');
  fireEvent.click(screen.getByRole('button',{name:'Améliorer les notes'}));
  expect(await screen.findByText('Aucun ajout utile à proposer pour cette note.')).toBeTruthy();
  const pane=screen.getByRole('region',{name:'Notes enrichies'});
  expect(within(pane).queryByRole('button',{name:'Accepter comme nouvelle version'})).toBeNull();
  expect(within(pane).queryByRole('button',{name:'Écarter'})).toBeNull();
  expect(screen.queryByRole('alert')).toBeNull();expect(enhance).toHaveBeenCalledTimes(1);
  expect(decide).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
  expect(screen.getByLabelText('Texte des notes')).toHaveProperty('value','Réserve : 55 mm à confirmer');
});

it('décrit une analyse automatique sans ajout sans annoncer une proposition disponible',async()=>{
  vi.mocked(meetingSessions.enhancements).mockResolvedValue({items:[{id:'empty-auto',status:'pending',text:'',
    note_revision:4,note_version_id:'note-version',citations:[],content:{version:1,blocks:[]}}],
    automatic:automatic('completed',{detail:'Suggestion à valider.'})});
  const decide=vi.spyOn(meetingSessions,'decide'),save=vi.spyOn(meetingSessions,'saveNote');
  setup(row,{...capabilities,assistant:{ready:true}});
  expect(await screen.findByText('Enrichissement automatique : Aucun ajout utile.')).toBeTruthy();
  expect(screen.getByText('Les notes existantes sont conservées.')).toBeTruthy();
  expect(screen.queryByText('Suggestion à valider.')).toBeNull();
  expect(screen.queryByText('Enrichissement automatique : Proposition disponible.')).toBeNull();
  expect(screen.queryByRole('button',{name:'Accepter comme nouvelle version'})).toBeNull();
  expect(decide).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
});


it('conserve l’état obsolète d’une analyse vide et ne le présente pas comme une analyse actuelle',async()=>{
  vi.mocked(meetingSessions.enhancements).mockResolvedValue({items:[{id:'old-empty',status:'obsolete',text:'',
    note_revision:4,note_version_id:'note-version',citations:[],content:{version:1,blocks:[]}}]});
  setup(row,{...capabilities,assistant:{ready:true}});
  expect(await screen.findByText('Cette analyse sans ajout concerne un ancien contexte de la séance.')).toBeTruthy();
  expect(screen.getByText(/Ancienne analyse · révision/)).toBeTruthy();
  expect(screen.queryByText(/Analyse terminée · révision/)).toBeNull();
  expect(screen.queryByRole('button',{name:'Accepter comme nouvelle version'})).toBeNull();
});

it('ignore une ancienne analyse vide pour le libellé de la nouvelle proposition automatique',async()=>{
  vi.mocked(meetingSessions.enhancements).mockResolvedValue({items:[
    {id:'old-empty',status:'obsolete',note_version_id:'note-version',text:'',content:{version:1,blocks:[]}},
    {id:'current-addition',status:'pending',note_version_id:'note-version',text:'Contrôle supplémentaire à relire.'}],
    automatic:automatic('completed')});
  setup(row,{...capabilities,assistant:{ready:true}});
  expect(await screen.findByText('Enrichissement automatique : Proposition disponible.')).toBeTruthy();
  expect(screen.queryByText('Enrichissement automatique : Aucun ajout utile.')).toBeNull();
});
