import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MeetingAudioPanel } from "./MeetingAudioPanel";
import { meetingAudio, type MeetingRecording } from "../lib/meetingAudio";

afterEach(() => {cleanup(); vi.restoreAllMocks();vi.unstubAllGlobals();});
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
  Object.defineProperty(fakeNavigator,"mediaDevices",{value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:release}]})}});
  vi.stubGlobal("navigator",fakeNavigator);vi.stubGlobal("MediaRecorder",FakeRecorder);
  render(<MeetingAudioPanel projectId="p1" onPublished={vi.fn()}/>);
  await open();
  fireEvent.click(screen.getByRole("tab",{name:"Audio"}));
  fireEvent.click(screen.getByText("Importer ou enregistrer une réunion"));
  fireEvent.click(screen.getByRole("button",{name:"Enregistrer au microphone"}));
  await screen.findByRole("button",{name:"Arrêter l’enregistrement"});
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
