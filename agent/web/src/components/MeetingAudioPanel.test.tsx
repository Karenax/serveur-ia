import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MeetingAudioPanel } from "./MeetingAudioPanel";
import { meetingAudio, type MeetingRecording } from "../lib/meetingAudio";
import {identityApi} from '../lib/projectIdentity';
import {ProjectAudioDrafts} from '../lib/projectAudioDrafts';
import type {DurableAudioChunk} from '../lib/meetingAudioStore';

beforeEach(async () => {
  const {webcrypto} = await vi.importActual<{webcrypto:Crypto}>('node:crypto');
  vi.stubGlobal('crypto',webcrypto);
  vi.spyOn(window,'confirm').mockReturnValue(true);
  vi.spyOn(identityApi,'session').mockResolvedValue({operator:{id:'user1',role:'owner',can_edit:true,can_administer:true,project_ids:null}});
  vi.spyOn(ProjectAudioDrafts.prototype,'ready').mockResolvedValue();
  vi.spyOn(ProjectAudioDrafts.prototype,'create').mockReturnValue('capture-test');
  vi.spyOn(ProjectAudioDrafts.prototype,'list').mockResolvedValue([]);
  vi.spyOn(ProjectAudioDrafts.prototype,'append').mockResolvedValue({} as DurableAudioChunk);
  vi.spyOn(ProjectAudioDrafts.prototype,'seal').mockResolvedValue();
  vi.spyOn(ProjectAudioDrafts.prototype,'isSealed').mockReturnValue(false);
});
afterEach(() => {cleanup(); vi.restoreAllMocks();vi.unstubAllGlobals();vi.useRealTimers();});
const row: MeetingRecording = {id: "audio1", source_id: "source1", title: "Point technique", date: "2026-10-02", filename: "reunion.wav",
  num_speakers: 2, segments: [{id: "seg-1", start: 1, end: 8, speaker: "SPEAKER_01", text: "Nous validons le diamètre de 50 mm."},
    {id: "seg-2", start: 8, end: 15, speaker: "SPEAKER_02", text: "Jean prépare le plan."}],
  speaker_names: {SPEAKER_01: "Marie", SPEAKER_02: "Jean"}, revision: 2, reviewed_revision: 0, summary_revision: 0,
  summary: {}, summary_model: "", published_meeting_id: null, job_kind: "transcription", job_status: "completed", stage: "transcribed",
  progress: 100, processed_seconds: 15, duration_seconds: 15, cancel_requested: false, error: null,
  created_at: "2026-10-02T12:00:00Z", updated_at: "2026-10-02T12:00:00Z"};
function mock(record = row) {
  vi.spyOn(meetingAudio, "status").mockResolvedValue({ready: true, model: "small", device: "cpu", detail: "Prêt", max_upload_mb: 50, max_duration_minutes: 120});
  vi.spyOn(meetingAudio, "list").mockResolvedValue([record]);
  vi.spyOn(meetingAudio, "get").mockResolvedValue(record);
}
async function open() {
  fireEvent.click(await screen.findByRole("button", {name: /2026-10-02 · Point technique/}));
  await screen.findByRole("heading",{name:"Point technique",level:4});
  fireEvent.click(screen.getByRole("tab",{name:/^Transcription/}));
  await screen.findByRole("region", {name: "Phase 1 : transcription"});
}

it('suspend le suivi audio masqué et ignore la réponse tardive après reprise',async()=>{
  let hidden=false;vi.spyOn(document,'hidden','get').mockImplementation(()=>hidden);
  const running={...row,job_status:'running',stage:'transcribing'};
  mock(running);
  let resolveOld!:(value:MeetingRecording)=>void;
  vi.mocked(meetingAudio.get).mockResolvedValueOnce(running)
    .mockReturnValueOnce(new Promise(done=>{resolveOld=done;})).mockResolvedValue({...row,title:'Traitement terminé'});
  const view=render(<MeetingAudioPanel projectId="p1" initialRecordingId="audio1" onPublished={vi.fn()} viewActive/>);
  await waitFor(()=>expect(meetingAudio.get).toHaveBeenCalledTimes(2));
  const signal=vi.mocked(meetingAudio.get).mock.calls[1][2]!;
  view.rerender(<MeetingAudioPanel projectId="p1" initialRecordingId="audio1" onPublished={vi.fn()} viewActive={false}/>);
  expect(signal.aborted).toBe(true);
  vi.useFakeTimers();await act(async()=>{await vi.advanceTimersByTimeAsync(10_000);});expect(meetingAudio.get).toHaveBeenCalledTimes(2);
  hidden=true;view.rerender(<MeetingAudioPanel projectId="p1" initialRecordingId="audio1" onPublished={vi.fn()} viewActive/>);
  await act(async()=>{await vi.advanceTimersByTimeAsync(10_000);});expect(meetingAudio.get).toHaveBeenCalledTimes(2);
  hidden=false;await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});
  expect(meetingAudio.get).toHaveBeenCalledTimes(3);
  await act(async()=>resolveOld({...running,title:'Réponse périmée'}));
  expect(screen.getByRole('heading',{name:'Traitement terminé',level:4})).toBeTruthy();
  expect(screen.queryByText('Réponse périmée')).toBeNull();vi.useRealTimers();
});

it('demande avant de remplacer un compte rendu contenant des corrections non enregistrées',async()=>{
  const draft={...row,reviewed_revision:2,summary_revision:2,summary:{overview:'Résumé initial'}};
  mock(draft);const synthesize=vi.spyOn(meetingAudio,'synthesize');const confirm=vi.spyOn(window,'confirm').mockReturnValue(false);
  render(<MeetingAudioPanel projectId="p1" initialRecordingId="audio1" onPublished={vi.fn()}/>);
  const input=await screen.findByLabelText('Résumé de la réunion');
  fireEvent.change(input,{target:{value:'Correction à conserver'}});
  fireEvent.click(screen.getByRole('button',{name:'Refaire le compte rendu'}));
  expect(confirm).toHaveBeenCalledOnce();expect(synthesize).not.toHaveBeenCalled();
  expect((input as HTMLTextAreaElement).value).toBe('Correction à conserver');
});

it('ouvre la transcription de l’audio lié sans lancer de traitement',async()=>{
  mock({...row,segments:[],revision:0,reviewed_revision:0});
  const transcribe=vi.spyOn(meetingAudio,'transcribe'),synthesize=vi.spyOn(meetingAudio,'synthesize');
  render(<MeetingAudioPanel projectId="p1" initialRecordingId="audio1" onPublished={vi.fn()}/>);
  await screen.findByRole('button',{name:'Transcrire et séparer les voix'});
  expect(screen.getByRole('tab',{name:'Transcription'})).toHaveProperty('ariaSelected','true');
  expect(transcribe).not.toHaveBeenCalled();expect(synthesize).not.toHaveBeenCalled();
});

it('passe de la relecture validée au CR en attendant un clic pour générer',async()=>{
  mock();
  vi.spyOn(meetingAudio,'review').mockResolvedValue({...row,reviewed_revision:row.revision,stage:'reviewed'});
  const synthesize=vi.spyOn(meetingAudio,'synthesize');
  render(<MeetingAudioPanel projectId="p1" initialRecordingId="audio1" onPublished={vi.fn()}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Valider la transcription'}));
  await waitFor(()=>expect(screen.getByRole('tab',{name:'Compte rendu'})).toHaveProperty('ariaSelected','true'));
  expect(screen.getByRole('button',{name:'Préparer le compte rendu'})).toHaveProperty('disabled',false);
  expect(synthesize).not.toHaveBeenCalled();
});

it.each([false,true])('écarte une validation tardive d’une autre liaison audio, retour initial=%s',async returns=>{
  mock();
  let resolve!:(value:MeetingRecording)=>void;
  const pending=new Promise<MeetingRecording>(done=>{resolve=done;});
  vi.spyOn(meetingAudio,'review').mockReturnValue(pending);
  const other={...row,id:'audio2',title:'Deuxième séance',segments:[{...row.segments[0],text:'Texte de la deuxième séance'}]};
  const recent={...row,title:'Première séance actualisée',revision:5,segments:[{...row.segments[0],text:'Correction récente à conserver'}]};
  vi.mocked(meetingAudio.get).mockResolvedValueOnce(row).mockResolvedValueOnce(other).mockResolvedValueOnce(recent);
  const published=vi.fn(),synthesize=vi.spyOn(meetingAudio,'synthesize');
  const view=render(<MeetingAudioPanel projectId="p1" initialRecordingId="audio1" onPublished={published}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Valider la transcription'}));
  view.rerender(<MeetingAudioPanel projectId="p1" initialRecordingId="audio2" onPublished={published}/>);
  await screen.findByRole('heading',{name:other.title,level:4});
  if(returns){
    view.rerender(<MeetingAudioPanel projectId="p1" initialRecordingId="audio1" onPublished={published}/>);
    await screen.findByRole('heading',{name:recent.title,level:4});
  }
  await act(async()=>{resolve({...row,reviewed_revision:2,stage:'reviewed'});await pending;});
  expect(screen.getByRole('heading',{name:returns?recent.title:other.title,level:4})).toBeTruthy();
  expect(screen.getByLabelText('Texte seg-1')).toHaveProperty('value',returns?'Correction récente à conserver':'Texte de la deuxième séance');
  expect(screen.getByRole('tab',{name:'Transcription'})).toHaveProperty('ariaSelected','true');
  expect(published).not.toHaveBeenCalled();expect(synthesize).not.toHaveBeenCalled();
});

it('ouvre uniquement l’audio de la séance et conserve cette identité pour la publication',async()=>{
  const draft={...row,reviewed_revision:2,summary_revision:2,summary:{overview:'Résumé relu',decisions:[],actions:[],open_points:[]},summary_model:'local'};
  mock(draft);vi.mocked(meetingAudio.list).mockResolvedValue([{...row,id:'another',title:'Autre séance'},draft]);
  const publish=vi.spyOn(meetingAudio,'publish').mockResolvedValue({...draft,published_meeting_id:'report'});
  render(<MeetingAudioPanel projectId="p1" initialRecordingId="audio1" onPublished={vi.fn()}/>);
  await screen.findByRole('heading',{name:'Point technique',level:4});
  expect(meetingAudio.get).toHaveBeenCalledWith('p1','audio1');
  expect(screen.queryByRole('button',{name:/Autre séance/})).toBeNull();expect(screen.queryByRole('button',{name:'Enregistrer au microphone'})).toBeNull();
  fireEvent.click(screen.getByRole('tab',{name:'Compte rendu'}));
  fireEvent.click(screen.getByRole('button',{name:'Valider et enregistrer le compte rendu'}));
  await waitFor(()=>expect(publish).toHaveBeenCalledWith('p1','audio1',2,expect.objectContaining({overview:'Résumé relu'})));
});

it("affiche le texte par interlocuteur et impose sa validation avant la synthèse", async () => {
  mock();
  const review = vi.spyOn(meetingAudio, "review").mockResolvedValue({...row, revision: 3, reviewed_revision: 3,
    segments: [{...row.segments[0], text: "Diamètre corrigé : 55 mm"}, row.segments[1]], stage: "reviewed"});
  const synthesize = vi.spyOn(meetingAudio, "synthesize").mockResolvedValue({...row, revision: 3, reviewed_revision: 3, job_kind: "synthesis", job_status: "queued", stage: "queued", progress: 0});
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()} />);
  await open();
  fireEvent.click(screen.getByText("Noms des interlocuteurs"));
  expect(screen.getByLabelText("Nom SPEAKER_01")).toHaveProperty("value", "Marie");
  expect(screen.getByLabelText("Interlocuteur seg-2")).toHaveProperty("value", "SPEAKER_02");
  expect(screen.getByRole("button", {name: "Écouter à 0:01"})).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", {name: "Compte rendu"}));
  expect(screen.getByRole("button", {name: "Préparer le compte rendu"})).toHaveProperty("disabled", true);
  fireEvent.click(screen.getByRole("tab", {name: "Transcription"}));
  fireEvent.change(screen.getByLabelText("Texte seg-1"), {target: {value: "Diamètre corrigé : 55 mm"}});
  fireEvent.click(screen.getByRole("button", {name: "Valider la transcription"}));
  await waitFor(() => expect(review).toHaveBeenCalledWith("p1", "audio1", 2,
    [{...row.segments[0], text: "Diamètre corrigé : 55 mm"}, row.segments[1]], row.speaker_names, true));
  fireEvent.click(screen.getByRole("tab", {name: "Compte rendu"}));
  await waitFor(() => expect(screen.getByRole("button", {name: "Préparer le compte rendu"})).toHaveProperty("disabled", false));
  fireEvent.click(screen.getByRole("button", {name: "Préparer le compte rendu"}));
  await waitFor(() => expect(synthesize).toHaveBeenCalledWith("p1", "audio1"));
});

it("permet de corriger la synthèse puis de publier explicitement le compte rendu", async () => {
  const summary = {overview: "Point technique", decisions: [{text: "Diamètre validé", segment_id: "seg-1", quote: "validons le diamètre de 50 mm"}],
    actions: [{text: "Préparer le plan", segment_id: "seg-2", quote: "Jean prépare le plan", owner: "Jean", due_date: ""}], open_points: []};
  const draft = {...row, reviewed_revision: 2, summary_revision: 2, summary, summary_model: "Modèle local", stage: "draft"};
  mock(draft);
  const onPublished = vi.fn();
  const publish = vi.spyOn(meetingAudio, "publish").mockResolvedValue({...draft, published_meeting_id: "audio1", stage: "published"});
  render(<MeetingAudioPanel projectId="p1" onPublished={onPublished} />);
  await open();
  fireEvent.click(screen.getByRole("tab", {name: "Compte rendu"}));
  expect(screen.getAllByRole("button", {name: "Écouter la source"})).toHaveLength(2);
  fireEvent.change(screen.getByLabelText("Résumé de la réunion"), {target: {value: "Compte rendu relu"}});
  fireEvent.change(screen.getByLabelText("Responsable action 1"), {target: {value: "Jean Martin"}});
  fireEvent.click(screen.getByRole("button", {name: "Valider et enregistrer le compte rendu"}));
  await waitFor(() => expect(publish).toHaveBeenCalledWith("p1", "audio1", 2, expect.objectContaining({overview: "Compte rendu relu", actions: [expect.objectContaining({owner: "Jean Martin"})]})));
  await waitFor(() => expect(onPublished).toHaveBeenCalledTimes(1));
  expect(screen.getByLabelText("Texte seg-1")).toHaveProperty("disabled", true);
  expect(screen.getByText(/Compte rendu enregistré dans les Revues/)).toBeTruthy();
});

it("montre la progression et conserve la possibilité d’interrompre le traitement", async () => {
  const running = {...row, segments: [], revision: 0, job_status: "running", stage: "speakers", progress: 21};
  mock(running);
  const cancel = vi.spyOn(meetingAudio, "cancel").mockResolvedValue({...running, cancel_requested: true});
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()} />);
  await open();
  expect(screen.getByRole("progressbar")).toHaveProperty("value", 21);
  fireEvent.click(screen.getByRole("button", {name: "Interrompre"}));
  await waitFor(() => expect(cancel).toHaveBeenCalledWith("p1", "audio1"));
  expect(await screen.findByRole("button", {name: "Annulation demandée…"})).toHaveProperty("disabled", true);
});

it("bloque la publication d’une synthèse devenue obsolète après correction du texte", async () => {
  mock({...row, revision: 3, reviewed_revision: 3, summary_revision: 2, summary: {overview: "Ancienne synthèse"}});
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()} />);
  await open();
  fireEvent.click(screen.getByRole("tab", {name: "Compte rendu"}));
  expect(screen.getByText(/La transcription a changé/)).toBeTruthy();
  expect(screen.queryByRole("button", {name: "Valider et enregistrer le compte rendu"})).toBeNull();
});

it("conserve les corrections de transcription et le compte rendu entre les onglets", async()=>{
  const draft={...row,reviewed_revision:2,summary_revision:2,summary:{overview:"Brouillon à relire"}};
  mock(draft);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();
  fireEvent.click(screen.getByRole("tab",{name:"Compte rendu"}));
  fireEvent.change(screen.getByLabelText("Résumé de la réunion"),{target:{value:"Résumé corrigé"}});
  fireEvent.click(screen.getByRole("tab",{name:"Audio"}));
  fireEvent.click(screen.getByRole("tab",{name:/^Compte rendu/}));
  expect(screen.getByLabelText("Résumé de la réunion")).toHaveProperty("value","Résumé corrigé");
  fireEvent.click(screen.getByRole("tab",{name:"Transcription"}));
  fireEvent.change(screen.getByLabelText("Texte seg-1"),{target:{value:"Texte corrigé"}});
  fireEvent.click(screen.getByRole("tab",{name:"Audio"}));
  fireEvent.click(screen.getByRole("tab",{name:/^Transcription/}));
  expect(screen.getByLabelText("Texte seg-1")).toHaveProperty("value","Texte corrigé");
  expect(screen.getByRole("button",{name:"Enregistrer les corrections"})).toHaveProperty("disabled",false);
});

it("affiche l’indisponibilité réelle du moteur et bloque la transcription",async()=>{
  mock({...row,segments:[],revision:0});
  vi.mocked(meetingAudio.status).mockResolvedValue({ready:false,model:"",device:"cpu",detail:"Modèle audio absent",max_upload_mb:50,max_duration_minutes:120});
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();
  expect(screen.getAllByText("Transcription indisponible sur ce poste.")).toHaveLength(2);
  expect(screen.queryByText("Modèle audio absent")).toBeNull();
  expect(screen.getByRole("button",{name:"Transcrire et séparer les voix"})).toHaveProperty("disabled",true);
  fireEvent.click(screen.getByRole("tab",{name:"Audio"}));
  fireEvent.click(screen.getByText("Importer ou enregistrer une réunion"));
  fireEvent.click(screen.getByText("Options de l’audio"));
  expect(screen.getByText(/Modèle audio absent/)).toBeTruthy();
});

it.each([["Responsable action 1","Jean Martin"],["Échéance action 1","2026-10-20"]])("protège une correction de %s avant de changer d’enregistrement",async(label,value)=>{
  const draft={...row,reviewed_revision:2,summary_revision:2,summary:{overview:"Brouillon",actions:[{text:"Préparer le plan",segment_id:"seg-2",quote:"Jean prépare le plan",owner:"Jean",due_date:""}]}};
  mock(draft);
  vi.mocked(meetingAudio.list).mockResolvedValue([draft,{...draft,id:"audio2",title:"Autre réunion"}]);
  vi.spyOn(window,"confirm").mockReturnValue(false);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();
  fireEvent.click(screen.getByRole("tab",{name:"Compte rendu"}));
  fireEvent.change(screen.getByLabelText(label),{target:{value}});
  fireEvent.click(screen.getByRole("button",{name:/Autre réunion/}));
  expect(window.confirm).toHaveBeenCalledWith("Des corrections ne sont pas enregistrées. Ouvrir un autre enregistrement ?");
  expect(meetingAudio.get).toHaveBeenCalledOnce();
  expect(screen.getByLabelText(label)).toHaveProperty("value",value);
});

it.each(["button","event"])("permet d’arrêter un microphone depuis un autre onglet par %s",async(method)=>{
  mock();
  const stop=vi.fn(),release=vi.fn();
  class FakeRecorder {
    state="inactive";mimeType="audio/webm";onstop:(()=>void)|null=null;ondataavailable:((event:{data:Blob})=>void)|null=null;onerror:(()=>void)|null=null;
    start(){this.state="recording";}
    stop(){this.state="inactive";stop();this.onstop?.();}
  }
  const fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,"userAgent",{value:"Mozilla/5.0 Windows Chrome"});
  Object.defineProperty(fakeNavigator,"mediaDevices",{value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:release}]})}});
  vi.stubGlobal("navigator",fakeNavigator);vi.stubGlobal("MediaRecorder",FakeRecorder);
  const view=render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();
  fireEvent.click(screen.getByRole("tab",{name:"Audio"}));
  fireEvent.click(screen.getByText("Importer ou enregistrer une réunion"));
  fireEvent.click(screen.getByRole("button",{name:"Enregistrer au microphone"}));
  await screen.findByRole("button",{name:"Arrêter l’enregistrement"});
  view.rerender(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()} viewActive={false}/>);
  expect(stop).not.toHaveBeenCalled();expect(release).not.toHaveBeenCalled();
  view.rerender(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()} viewActive/>);
  fireEvent.click(screen.getByRole("tab",{name:"Transcription"}));
  expect(screen.getByRole("button",{name:"Arrêter l’enregistrement"})).toBeTruthy();
  await act(async()=>window.dispatchEvent(new CustomEvent("agent-stop-recording",{detail:{projectId:"other"}})));
  expect(stop).not.toHaveBeenCalled();
  if(method==="button")fireEvent.click(screen.getByRole("button",{name:"Arrêter l’enregistrement"}));
  else {
    await act(async()=>window.dispatchEvent(new CustomEvent("agent-show-recording",{detail:{projectId:"p1"}})));
    expect(screen.getByRole("tab",{name:"Audio"})).toHaveProperty("ariaSelected","true");
    await act(async()=>window.dispatchEvent(new CustomEvent("agent-stop-recording",{detail:{projectId:"p1"}})));
  }
  await waitFor(()=>expect(stop).toHaveBeenCalledOnce());
  expect(release).toHaveBeenCalledOnce();
  expect(screen.queryByRole("button",{name:"Arrêter l’enregistrement"})).toBeNull();
});

it('libère le microphone si l’enregistreur ne démarre pas et conserve le fichier déjà choisi', async () => {
  mock();
  const release=vi.fn();
  const fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,'userAgent',{value:'Mozilla/5.0 Windows Chrome'});
  Object.defineProperty(fakeNavigator,'mediaDevices',{value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:release}]})}});
  class BrokenRecorder {constructor(){throw new Error('indisponible');}}
  vi.stubGlobal('navigator',fakeNavigator);vi.stubGlobal('MediaRecorder',BrokenRecorder);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();fireEvent.click(screen.getByRole('tab',{name:'Audio'}));
  const previous=new File(['audio fictif'],'existant.wav',{type:'audio/wav'});
  fireEvent.change(screen.getByLabelText('Fichier audio'),{target:{files:[previous]}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer au microphone'}));
  await screen.findByText(/Microphone indisponible/);
  expect(release).toHaveBeenCalledOnce();
  expect(screen.getByText(/existant\.wav/)).toBeTruthy();
});

it('signale un enregistrement vide sans remplacer le fichier déjà choisi', async () => {
  mock();
  const release=vi.fn();
  const fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,'userAgent',{value:'Mozilla/5.0 Windows Chrome'});
  Object.defineProperty(fakeNavigator,'mediaDevices',{value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:release}]})}});
  class EmptyRecorder {
    state='inactive';mimeType='audio/webm';onstop:(()=>void)|null=null;ondataavailable:((event:{data:Blob})=>void)|null=null;onerror:(()=>void)|null=null;
    start(){this.state='recording';} stop(){this.state='inactive';this.onstop?.();}
  }
  vi.stubGlobal('navigator',fakeNavigator);vi.stubGlobal('MediaRecorder',EmptyRecorder);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();fireEvent.click(screen.getByRole('tab',{name:'Audio'}));
  fireEvent.change(screen.getByLabelText('Fichier audio'),{target:{files:[new File(['audio fictif'],'existant.wav',{type:'audio/wav'})]}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer au microphone'}));
  fireEvent.click(await screen.findByRole('button',{name:'Arrêter l’enregistrement'}));
  expect(await screen.findByText(/Aucun son n’a été enregistré/)).toBeTruthy();
  expect(screen.getByText(/existant\.wav/)).toBeTruthy();expect(release).toHaveBeenCalledOnce();
});

it('ne demande le microphone qu’une fois pendant son ouverture', async () => {
  mock();
  let resolveMedia!:(media:unknown)=>void;
  const requested=vi.fn().mockReturnValue(new Promise(resolve=>{resolveMedia=resolve;}));
  const release=vi.fn(), fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,'userAgent',{value:'Mozilla/5.0 Windows Chrome'});
  Object.defineProperty(fakeNavigator,'mediaDevices',{value:{getUserMedia:requested}});
  class FakeRecorder {
    state='inactive';mimeType='audio/webm';onstop:(()=>void)|null=null;ondataavailable:((event:{data:Blob})=>void)|null=null;onerror:(()=>void)|null=null;
    start(){this.state='recording';} stop(){this.state='inactive';this.onstop?.();}
  }
  vi.stubGlobal('navigator',fakeNavigator);vi.stubGlobal('MediaRecorder',FakeRecorder);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();fireEvent.click(screen.getByRole('tab',{name:'Audio'}));
  const start=screen.getByRole('button',{name:'Enregistrer au microphone'});
  fireEvent.click(start);fireEvent.click(start);await waitFor(()=>expect(requested).toHaveBeenCalledOnce());
  await act(async()=>resolveMedia({getTracks:()=>[{stop:release}]}));
  fireEvent.click(await screen.findByRole('button',{name:'Arrêter l’enregistrement'}));
  expect(release).toHaveBeenCalledOnce();
});

it.each([false,true])('conserve l’audio déjà reçu en cas d’erreur, arrêt impossible : %s', async stopThrows => {
  mock();
  const release=vi.fn(), fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,'userAgent',{value:'Mozilla/5.0 Windows Chrome'});
  Object.defineProperty(fakeNavigator,'mediaDevices',{value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:release}]})}});
  let current!:FakeRecorder;
  class FakeRecorder {
    state='inactive';mimeType='audio/webm';onstop:(()=>void)|null=null;ondataavailable:((event:{data:Blob})=>void)|null=null;onerror:(()=>void)|null=null;
    constructor(){current=this;}
    start(){this.state='recording';}
    stop(){if(stopThrows)throw new Error('arrêt indisponible');this.state='inactive';this.onstop?.();}
  }
  vi.stubGlobal('navigator',fakeNavigator);vi.stubGlobal('MediaRecorder',FakeRecorder);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();fireEvent.click(screen.getByRole('tab',{name:'Audio'}));
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer au microphone'}));
  await screen.findByRole('button',{name:'Arrêter l’enregistrement'});
  act(()=>{current.ondataavailable?.({data:new Blob(['audio fictif'],{type:'audio/webm'})});current.onerror?.();});
  expect(await screen.findByText(/Enregistrement interrompu. Vérifiez l’audio récupéré/)).toBeTruthy();
  expect(screen.getByText(/reunion-.*\.webm/)).toBeTruthy();expect(release).toHaveBeenCalledOnce();
});

it('signale immédiatement une erreur avant le fichier partiel reçu plus tard', async () => {
  mock();
  const release=vi.fn(), fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,'userAgent',{value:'Mozilla/5.0 Windows Chrome'});
  Object.defineProperty(fakeNavigator,'mediaDevices',{value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:release}]})}});
  let current!:FakeRecorder;
  class FakeRecorder {
    state='inactive';mimeType='audio/webm';onstop:(()=>void)|null=null;ondataavailable:((event:{data:Blob})=>void)|null=null;onerror:(()=>void)|null=null;
    constructor(){current=this;} start(){this.state='recording';} stop(){this.state='inactive';}
  }
  vi.stubGlobal('navigator',fakeNavigator);vi.stubGlobal('MediaRecorder',FakeRecorder);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();fireEvent.click(screen.getByRole('tab',{name:'Audio'}));
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer au microphone'}));
  await screen.findByRole('button',{name:'Arrêter l’enregistrement'});
  act(()=>{current.ondataavailable?.({data:new Blob(['audio fictif'],{type:'audio/webm'})});current.onerror?.();});
  expect(await screen.findByText('Enregistrement interrompu par le navigateur.')).toBeTruthy();
  expect(release).toHaveBeenCalledOnce();
  act(()=>current.onstop?.());
  expect(await screen.findByText(/Enregistrement interrompu. Vérifiez l’audio récupéré/)).toBeTruthy();
  expect(screen.getByText(/reunion-.*\.webm/)).toBeTruthy();expect(release).toHaveBeenCalledOnce();
});

it.each(['sans WebM','absent'])('enregistre en WAV PCM sous WebKit Linux lorsque MediaRecorder est %s', async availability => {
  mock();
  const release=vi.fn(), disconnect=vi.fn();
  const processor={connect:vi.fn(),disconnect,onaudioprocess:null as ((event:AudioProcessingEvent)=>void)|null};
  const node=()=>({connect:vi.fn(),disconnect:vi.fn()});
  class FakeAudioContext {
    sampleRate=16000;destination=node();
    createMediaStreamSource(){return node();}
    createScriptProcessor(){return processor;}
    createGain(){return {...node(),gain:{value:1}};}
    resume(){return Promise.resolve();}
    close(){return Promise.resolve();}
  }
  class UnsupportedRecorder {static isTypeSupported(){return false;} constructor(){throw new Error('Ne doit pas être utilisé');}}
  const fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,'userAgent',{value:'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 Safari/605.1.15'});
  Object.defineProperty(fakeNavigator,'mediaDevices',{value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:release}]})}});
  vi.stubGlobal('navigator',fakeNavigator);vi.stubGlobal('MediaRecorder',availability==='absent'?undefined:UnsupportedRecorder);vi.stubGlobal('AudioContext',FakeAudioContext);
  const upload=vi.spyOn(meetingAudio,'upload').mockResolvedValue(row);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();fireEvent.click(screen.getByRole('tab',{name:'Audio'}));
  fireEvent.change(screen.getByLabelText('Titre de la réunion'),{target:{value:'Réunion fictive'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer au microphone'}));
  await screen.findByText('Enregistrement au microphone en cours');
  act(()=>processor.onaudioprocess?.({inputBuffer:{getChannelData:()=>new Float32Array([0.5,-0.5,1])}} as unknown as AudioProcessingEvent));
  fireEvent.click(screen.getByRole('button',{name:'Arrêter l’enregistrement'}));
  await screen.findByText(/reunion-.*\.wav/);
  expect(release).toHaveBeenCalledOnce();
  await waitFor(()=>expect(screen.getByRole('button',{name:'Importer l’audio'})).toHaveProperty('disabled',false));
  expect(ProjectAudioDrafts.prototype.seal).toHaveBeenCalledWith('user1','p1','capture-test');
  fireEvent.click(screen.getByRole('button',{name:'Importer l’audio'}));
  await waitFor(()=>expect(upload).toHaveBeenCalledOnce());
  const audio=vi.mocked(upload).mock.calls[0][1].get('file') as File;
  expect(audio.type).toBe('audio/wav');expect(audio.size).toBe(50);
  const bytes=await new Promise<ArrayBuffer>((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result as ArrayBuffer);reader.onerror=()=>reject(reader.error);reader.readAsArrayBuffer(audio);});
  const view=new DataView(bytes);
  expect(String.fromCharCode(...new Uint8Array(bytes,0,4))).toBe('RIFF');
  expect(view.getUint32(24,true)).toBe(16000);expect(view.getUint32(40,true)).toBe(6);
  expect(view.getInt16(44,true)).toBe(16384);
});

it('arrête le microphone si la sauvegarde échoue et conserve le fichier en mémoire', async () => {
  mock();
  vi.mocked(ProjectAudioDrafts.prototype.append).mockRejectedValue(new Error('quota'));
  const release=vi.fn(), fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,'userAgent',{value:'Mozilla/5.0 Windows Chrome'});
  Object.defineProperty(fakeNavigator,'mediaDevices',{value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:release}]})}});
  let current!:FakeRecorder;
  class FakeRecorder {
    state='inactive';mimeType='audio/webm';onstop:(()=>void)|null=null;ondataavailable:((event:{data:Blob})=>void)|null=null;onerror:(()=>void)|null=null;
    constructor(){current=this;} start(){this.state='recording';} stop(){this.state='inactive';this.onstop?.();}
  }
  vi.stubGlobal('navigator',fakeNavigator);vi.stubGlobal('MediaRecorder',FakeRecorder);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();fireEvent.click(screen.getByRole('tab',{name:'Audio'}));
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer au microphone'}));
  await screen.findByRole('button',{name:'Arrêter l’enregistrement'});
  act(()=>current.ondataavailable?.({data:new Blob(['fragment fictif'],{type:'audio/webm'})}));
  expect(await screen.findByText(/sauvegarde locale a échoué/)).toBeTruthy();
  expect(await screen.findByText(/reunion-.*\.webm/)).toBeTruthy();
  expect(release).toHaveBeenCalledOnce();
  expect(ProjectAudioDrafts.prototype.seal).not.toHaveBeenCalled();
});

it('demande avant de remplacer le fichier sélectionné par une capture locale', async () => {
  mock();
  const NativeURL=URL, revoke=vi.fn();
  vi.stubGlobal('URL',class extends NativeURL {static createObjectURL(){return 'blob:audio-fictif';} static revokeObjectURL=revoke;});
  vi.mocked(ProjectAudioDrafts.prototype.list).mockResolvedValue([{sessionId:'capture-test',count:2}]);
  const read=vi.spyOn(ProjectAudioDrafts.prototype,'read').mockResolvedValue({blob:new Blob(['audio'],{type:'audio/webm'}),createdAt:'2026-11-18T08:00:00Z',count:2});
  vi.mocked(window.confirm).mockReturnValue(false);
  const view=render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();fireEvent.click(screen.getByRole('tab',{name:'Audio'}));
  fireEvent.change(screen.getByLabelText('Fichier audio'),{target:{files:[new File(['existant'],'existant.wav',{type:'audio/wav'})]}});
  fireEvent.click(await screen.findByRole('button',{name:/Récupérer la capture 1/}));
  expect(read).not.toHaveBeenCalled();expect(screen.getByText(/existant\.wav/)).toBeTruthy();
  vi.mocked(window.confirm).mockReturnValue(true);
  fireEvent.click(screen.getByRole('button',{name:/Récupérer la capture 1/}));
  expect(await screen.findByText(/Audio récupéré : il peut être incomplet/)).toBeTruthy();
  expect(read).toHaveBeenCalledWith('user1','p1','capture-test');
  expect(screen.getByText(/reunion-recuperee-.*\.webm/)).toBeTruthy();
  expect(screen.getByLabelText('Écouter le fichier avant import').getAttribute('src')).toBe('blob:audio-fictif');
  view.unmount();expect(revoke).toHaveBeenCalledWith('blob:audio-fictif');
});

it('affiche la limite audio annoncée par le serveur', async () => {
  mock();
  vi.mocked(meetingAudio.status).mockResolvedValue({ready:true,model:'fictif',device:'cpu',detail:'Prêt',max_upload_mb:256,max_duration_minutes:120});
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  expect(await screen.findByText(/256 Mio maximum/)).toBeTruthy();
});

it('signale un inventaire local indisponible et permet de le relancer', async () => {
  mock();
  vi.mocked(ProjectAudioDrafts.prototype.list).mockRejectedValueOnce(new Error('stockage indisponible'))
    .mockResolvedValue([{sessionId:'capture-test',count:2}]);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  expect(await screen.findByText(/captures locales ne peuvent pas être vérifiées/)).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Réessayer'}));
  expect(await screen.findByRole('button',{name:/Récupérer la capture 1/})).toBeTruthy();
  expect(screen.queryByText(/captures locales ne peuvent pas être vérifiées/)).toBeNull();
});

it('ignore un ancien inventaire arrivé après la fin d’une capture', async () => {
  mock();
  let resolveOld!:(value:{sessionId:string;count:number}[])=>void;
  vi.mocked(ProjectAudioDrafts.prototype.list).mockReturnValueOnce(new Promise(resolve=>{resolveOld=resolve;}))
    .mockResolvedValue([{sessionId:'capture-test',count:1}]);
  const fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,'userAgent',{value:'Mozilla/5.0 Windows Chrome'});
  Object.defineProperty(fakeNavigator,'mediaDevices',{value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:vi.fn()}]})}});
  let current!:FakeRecorder;
  class FakeRecorder {
    state='inactive';mimeType='audio/webm';onstop:(()=>void)|null=null;ondataavailable:((event:{data:Blob})=>void)|null=null;onerror:(()=>void)|null=null;
    constructor(){current=this;} start(){this.state='recording';} stop(){this.state='inactive';this.onstop?.();}
  }
  vi.stubGlobal('navigator',fakeNavigator);vi.stubGlobal('MediaRecorder',FakeRecorder);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await waitFor(()=>expect(ProjectAudioDrafts.prototype.list).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer au microphone'}));
  fireEvent.click(await screen.findByRole('button',{name:'Arrêter l’enregistrement'}));
  await screen.findByRole('button',{name:/Récupérer la capture 1/});
  await act(async()=>resolveOld([]));
  expect(screen.getByRole('button',{name:/Récupérer la capture 1/})).toBeTruthy();
  expect(current.state).toBe('inactive');
});

async function prepareImportedCapture(sealed:boolean) {
  mock();
  vi.mocked(ProjectAudioDrafts.prototype.list).mockResolvedValue([{sessionId:'capture-test',count:1}]);
  vi.mocked(ProjectAudioDrafts.prototype.isSealed).mockReturnValue(sealed);
  vi.spyOn(ProjectAudioDrafts.prototype,'read').mockResolvedValue({blob:new Blob(['audio'],{type:'audio/webm'}),createdAt:'2026-11-18T08:00:00Z',count:1});
  vi.spyOn(meetingAudio,'upload').mockResolvedValue(row);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();fireEvent.click(screen.getByRole('tab',{name:'Audio'}));
  fireEvent.change(screen.getByLabelText('Titre de la réunion'),{target:{value:'Réunion fictive'}});
  fireEvent.click(await screen.findByRole('button',{name:/Récupérer la capture 1/}));
  await screen.findByText(/reunion-recuperee-.*\.webm/);
  fireEvent.click(screen.getByRole('button',{name:'Importer l’audio'}));
  await waitFor(()=>expect(meetingAudio.upload).toHaveBeenCalledOnce());
}

it('ne libère la copie locale qu’après vérification explicite de la copie serveur', async () => {
  const receipt={recording_id:'audio1',source_id:'source1',sha256:'a'.repeat(64),size:5};
  const integrity=vi.spyOn(meetingAudio,'integrity').mockResolvedValue(receipt);
  const release=vi.spyOn(ProjectAudioDrafts.prototype,'releaseVerified').mockImplementation(async(...args)=>{await args[6]();});
  await prepareImportedCapture(true);
  expect(release).not.toHaveBeenCalled();
  fireEvent.click(await screen.findByRole('button',{name:'Libérer la copie locale'}));
  await waitFor(()=>expect(release).toHaveBeenCalledWith('user1','p1','capture-test',receipt,'audio1','source1',expect.any(Function)));
  await waitFor(()=>expect(screen.queryByRole('button',{name:'Libérer la copie locale'})).toBeNull());
  expect(screen.getByText(/Copie locale libérée/)).toBeTruthy();
  expect(integrity).toHaveBeenCalledTimes(2);expect(integrity).toHaveBeenCalledWith('p1','audio1');
});

it('conserve la copie locale si le serveur change pendant la vérification', async () => {
  const receipt={recording_id:'audio1',source_id:'source1',sha256:'a'.repeat(64),size:5};
  vi.spyOn(meetingAudio,'integrity').mockResolvedValueOnce(receipt).mockResolvedValueOnce({...receipt,sha256:'b'.repeat(64)});
  vi.spyOn(ProjectAudioDrafts.prototype,'releaseVerified').mockImplementation(async(...args)=>{await args[6]();});
  await prepareImportedCapture(true);
  fireEvent.click(await screen.findByRole('button',{name:'Libérer la copie locale'}));
  expect(await screen.findByText(/copie sur le serveur a changé/)).toBeTruthy();
  expect(screen.getByRole('button',{name:'Libérer la copie locale'})).toBeTruthy();
});

it('conserve la copie locale si la vérification serveur échoue', async () => {
  vi.spyOn(meetingAudio,'integrity').mockRejectedValue(new Error('Copie serveur indisponible'));
  const release=vi.spyOn(ProjectAudioDrafts.prototype,'releaseVerified').mockResolvedValue();
  await prepareImportedCapture(true);
  fireEvent.click(await screen.findByRole('button',{name:'Libérer la copie locale'}));
  expect(await screen.findByText('Copie serveur indisponible')).toBeTruthy();
  expect(release).not.toHaveBeenCalled();expect(screen.getByRole('button',{name:'Libérer la copie locale'})).toBeTruthy();
});

it('conserve la copie locale si le compte change pendant la vérification', async () => {
  const receipt={recording_id:'audio1',source_id:'source1',sha256:'a'.repeat(64),size:5};
  vi.spyOn(meetingAudio,'integrity').mockImplementation(async()=>{
    vi.mocked(identityApi.session).mockResolvedValueOnce({operator:{id:'autre',role:'owner',can_edit:true,can_administer:true,project_ids:null}});
    return receipt;
  });
  const release=vi.spyOn(ProjectAudioDrafts.prototype,'releaseVerified').mockResolvedValue();
  await prepareImportedCapture(true);
  fireEvent.click(await screen.findByRole('button',{name:'Libérer la copie locale'}));
  expect(await screen.findByText(/Le compte ou l’accès au projet a changé/)).toBeTruthy();expect(release).not.toHaveBeenCalled();
});

it('conserve la copie locale si l’accès au projet est retiré pendant la vérification', async () => {
  const receipt={recording_id:'audio1',source_id:'source1',sha256:'a'.repeat(64),size:5};
  vi.spyOn(meetingAudio,'integrity').mockImplementation(async()=>{
    vi.mocked(identityApi.session).mockResolvedValueOnce({operator:{id:'user1',role:'owner',can_edit:true,can_administer:false,project_ids:['autre']}});
    return receipt;
  });
  const release=vi.spyOn(ProjectAudioDrafts.prototype,'releaseVerified').mockResolvedValue();
  await prepareImportedCapture(true);
  fireEvent.click(await screen.findByRole('button',{name:'Libérer la copie locale'}));
  expect(await screen.findByText(/l’accès au projet a changé/)).toBeTruthy();expect(release).not.toHaveBeenCalled();
});

it('ne propose pas la libération pour une capture dont la fin est inconnue', async () => {
  const release=vi.spyOn(ProjectAudioDrafts.prototype,'releaseVerified').mockResolvedValue();
  await prepareImportedCapture(false);
  await waitFor(()=>expect(vi.mocked(meetingAudio.list).mock.calls.length).toBeGreaterThanOrEqual(3));
  expect(screen.queryByRole('button',{name:'Libérer la copie locale'})).toBeNull();expect(release).not.toHaveBeenCalled();
  expect(screen.getByText(/fin de cette capture n’a pas été confirmée/)).toBeTruthy();
});

it('ne lance pas le microphone si le panneau a changé de projet pendant la préparation', async () => {
  mock();
  let resolveSession!:(value:Awaited<ReturnType<typeof identityApi.session>>)=>void;
  const session={operator:{id:'user1',role:'owner' as const,can_edit:true,can_administer:true,project_ids:null}};
  const getUserMedia=vi.fn();
  const fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,'userAgent',{value:'Mozilla/5.0 Windows Chrome'});
  Object.defineProperty(fakeNavigator,'mediaDevices',{value:{getUserMedia}});
  vi.stubGlobal('navigator',fakeNavigator);vi.stubGlobal('MediaRecorder',class {});
  const view=render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();fireEvent.click(screen.getByRole('tab',{name:'Audio'}));
  vi.mocked(identityApi.session).mockReturnValueOnce(new Promise(resolve=>{resolveSession=resolve;}));
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer au microphone'}));
  view.rerender(<MeetingAudioPanel projectId="p2" onPublished={vi.fn()}/>);
  await act(async()=>resolveSession(session));
  expect(getUserMedia).not.toHaveBeenCalled();
});
