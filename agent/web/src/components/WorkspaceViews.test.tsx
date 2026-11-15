import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor,within } from "@testing-library/react";
import type { PortfolioRow } from "../lib/api";
import { workspaceApi, type DurableTriageJob, type WorkspaceJob, type WorkspaceKnowledge, type WorkspaceMeeting } from "../lib/workspaceApi";
import { GlobalJobsView, GlobalKnowledgeView, GlobalMeetingsView, SourceInspector } from "./WorkspaceViews";
import {meetingSessions,type MeetingSession,type SessionCapabilities} from '../lib/meetingSessions';
import {meetingCapture} from '../lib/meetingCapture';
import {notesApi,type NoteVersion} from '../lib/projectNotes';
import {fusionInsights,type FusionSettings} from '../lib/fusionInsights';

afterEach(() => {cleanup(); vi.restoreAllMocks();});

it('restaure les filtres Informations après rechargement sans modifier une autre rubrique', async()=>{
  window.history.replaceState({},'', '/app/knowledge?project=erp-a&q=capteur&offset=25');
  try {
    const load=vi.spyOn(workspaceApi,'knowledge').mockResolvedValue({items:[],total:60});
    const view=render(<GlobalKnowledgeView rows={rows} onOpenProject={vi.fn()}/>);
    await waitFor(()=>expect(load).toHaveBeenLastCalledWith(expect.objectContaining({project_id:'brain-a',q:'capteur',offset:25}),expect.any(AbortSignal)));
    fireEvent.change(screen.getByLabelText('Rechercher une information'),{target:{value:'moteur'}});
    expect(new URLSearchParams(window.location.search).get('q')).toBe('moteur');
    expect(new URLSearchParams(window.location.search).get('offset')).toBeNull();
    window.history.pushState({},'', '/app/jobs?project=erp-b');
    window.dispatchEvent(new PopStateEvent('popstate'));
    view.unmount();
    expect(window.location.search).toBe('?project=erp-b');
  } finally {window.history.replaceState({},'', '/');}
});

it('conserve la pagination des réunions à l’ouverture d’une URL enregistrée', async()=>{
  window.history.replaceState({},'', '/app/meetings?project=erp-a&offset=25&sessions_offset=25');
  try {
    const load=vi.spyOn(workspaceApi,'meetings').mockResolvedValue({items:[],total:60});
    render(<GlobalMeetingsView rows={rows} initialProjectId="erp-a" onOpenProject={vi.fn()}/>);
    await waitFor(()=>expect(load).toHaveBeenLastCalledWith(expect.objectContaining({project_id:'erp-a',offset:25}),expect.any(AbortSignal)));
    expect(new URLSearchParams(window.location.search).get('sessions_offset')).toBe('25');
  } finally {cleanup();window.history.replaceState({},'', '/');}
});

it('applique le projet du Studio dès la première lecture et après changement de route',async()=>{
  const load=vi.spyOn(workspaceApi,'meetings').mockResolvedValue({items:[],total:0});
  vi.spyOn(meetingSessions,'list').mockResolvedValue({items:[],total:0,offset:0,limit:25});
  const screenView=render(<GlobalMeetingsView rows={rows} initialProjectId="erp-a" onOpenProject={vi.fn()}/>);
  await waitFor(()=>expect(load).toHaveBeenCalledWith(expect.objectContaining({project_id:'erp-a'}),expect.any(AbortSignal)));
  expect(load.mock.calls.every(([query])=>query?.project_id==='erp-a')).toBe(true);
  screenView.rerender(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()}/>);
  await waitFor(()=>expect(load).toHaveBeenLastCalledWith(expect.objectContaining({project_id:undefined}),expect.any(AbortSignal)));
});

it('conserve le lien vers une version de note citée même lorsque la source est projetée dans une version plus récente',async()=>{
  const version:NoteVersion={id:'v2',project_id:'erp-a',note_id:'note',revision:2,title:'Historique',actor_id:'human',created_at:'2026-10-11T15:30:00Z',operation:'save',
    value:{title:'Version historique exacte',content:{version:1,blocks:[{type:'paragraph',align:'left',runs:[{text:'Contenu ancien non validé.',marks:[],href:null,color:null}]}]}},attachment_bindings:{}};
  const load=vi.spyOn(notesApi,'version').mockResolvedValue(version);
  vi.spyOn(workspaceApi,'source').mockResolvedValue({id:'note-source',type:'document',status:'resolved',project_id:'brain-a',author:'ERP',
    metadata:{subject:'Note actuelle',origin_kind:'erp_note',erp_project_id:'erp-a',note_id:'note',note_version_id:'v3'},
    artifacts:[{id:'a3',kind:'note_text',text:'Version actuelle 3'}]} as never);
  render(<SourceInspector sourceId="note-source" onClose={vi.fn()} evidence={[{source_id:'note-source',source_url:'/api/v1/projects/erp-a/notes/note/versions/v2',
    excerpt:'Version citée 2',locator:{erp_project_id:'erp-a',note_id:'note',note_version_id:'v2',note_revision:2,block_index:0}}]} />);
  await screen.findByText('Note actuelle');
  expect(screen.getByRole('link',{name:'Ouvrir la version citée'}).getAttribute('href')).toBe('/api/v1/projects/erp-a/notes/note/versions/v2');
  expect(screen.getByRole('link',{name:/Télécharger la version actuelle de note/}).getAttribute('href')).toBe('/api/v1/workspace/sources/note-source/original');
  expect(screen.queryByRole('link',{name:/Télécharger l’original/})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Lire la version citée'}));await screen.findByText('Version historique exacte · version 2');
  expect(load).toHaveBeenCalledWith('erp-a','note','v2',expect.any(AbortSignal));
});

it.each([{type:'document',filename:'plan.pdf',locator:{physical_page:7},repere:'Page physique : 7'},
  {type:'document',filename:'devis.xlsx',locator:{sheet:'Chiffrage',range:'A2:C2'},repere:'Feuille : Chiffrage · Plage : A2:C2'},
  {type:'image',filename:'schema.png',locator:{document_part:'Schéma'},repere:'Partie du document : Schéma'},
  {type:'audio',filename:'reunion.wav',locator:{start_ms:3000,end_ms:6000},repere:'Début (ms) : 3000 · Fin (ms) : 6000'}])(
  'ouvre une source $filename depuis le Studio avec la preuve du clic et conserve les notes',async ({type,filename,locator,repere})=>{
  localStorage.clear();const content={version:1 as const,blocks:[{type:'paragraph' as const,align:'left' as const,runs:[{text:'Notes Studio conservées.',marks:[],href:null,color:null}]}]};
  const session:MeetingSession={id:'studio-source',title:'Séance de preuve',kind:'note',project_id:'erp-a',brain_project_id:'brain-a',state:'created',revision:1,
    date:'2026-10-11',recording_id:null,note_id:'note',note_revision:1,note_version_id:'v1',note:{id:'note',project_id:'erp-a',title:'Notes de preuve',content,
      revision:1,version_id:'v1',attachment_ids:[],read_only:false,source_kind:null,updated_at:'2026-10-11',actor_id:'local'},tracks:[],total_bytes:0,duration_seconds:0,issues:[],created_at:'2026-10-11',updated_at:'2026-10-11'};
  vi.spyOn(workspaceApi,'meetings').mockResolvedValue({items:[],total:0});
  vi.spyOn(meetingSessions,'capabilities').mockResolvedValue({enabled:true,capture:{durable:true,max_upload_mb:50,max_duration_minutes:120,tracks:['mic','system'],browser_permission_required:true},
    transcription:{live_ready:false,batch_ready:false,detail:'Fictif'},notes:{staging:true,erp_projection:true}});
  vi.spyOn(meetingSessions,'list').mockResolvedValue({items:[session],total:1,offset:0,limit:25});
  vi.spyOn(meetingSessions,'get').mockImplementation(async id=>({...session,id}));vi.spyOn(meetingSessions,'askHistory').mockResolvedValue({items:[]});
  vi.spyOn(meetingSessions,'enhancements').mockResolvedValue({items:[{id:'suggestion',status:'prepared',text:'Relire le document',citations:[{source_id:'source-qa',title:'Preuve exacte',
    excerpt:'Extrait industriel non validé.',source_url:'/v1/sources/source-qa',locator}]}]});vi.spyOn(meetingSessions,'liveAnswers').mockResolvedValue({items:[]});
  const load=vi.spyOn(workspaceApi,'source').mockResolvedValue({id:'source-qa',type,status:'resolved',project_id:'brain-a',author:'QA',metadata:{filename},
    artifacts:[{id:'a',kind:'document_text',text:'Contenu complet du fichier fictif.'}]});
  render(<GlobalMeetingsView rows={[]} onOpenProject={vi.fn()}/>);
  fireEvent.click(await screen.findByText('Séance de preuve'));
  await screen.findByRole('textbox',{name:'Titre de la note'});fireEvent.change(screen.getByLabelText('Titre de la note'),{target:{value:'Brouillon à garder'}});
  fireEvent.click(screen.getByRole('button',{name:'Notes enrichies'}));
  fireEvent.click(await screen.findByText('Preuve exacte'));fireEvent.click(screen.getByRole('button',{name:'Examiner la source citée'}));
  const dialog=await screen.findByRole('dialog');await within(dialog).findByText('Contenu complet du fichier fictif.');
  expect(within(dialog).getByText('Extrait industriel non validé.')).toBeTruthy();expect(within(dialog).getByText(repere)).toBeTruthy();
  expect(within(dialog).getByRole('link',{name:/Télécharger l’original/}).getAttribute('href')).toBe('/v1/sources/source-qa/raw');
  expect(load).toHaveBeenCalledWith('source-qa',expect.any(AbortSignal));
  fireEvent.click(within(dialog).getByRole('button',{name:'Fermer'}));expect(screen.getByLabelText('Titre de la note')).toHaveProperty('value','Brouillon à garder');
  fireEvent.click(screen.getByRole('button',{name:'Examiner la source citée'}));await screen.findByRole('dialog');
  fireEvent(window,new CustomEvent('agent-open-meeting-session',{detail:{sessionId:'another-session'}}));
  await waitFor(()=>expect(screen.queryByRole('dialog')).toBeNull());
});

const rows: PortfolioRow[] = [{id: "erp-a", code: "A-100", title: "Projet A", status: "active", client_name: "Client",
  jalon_en_cours: "", jalon_echeance: "", avancement: 0, raf: 0, taches: "", en_retard: 0, corrections: 0, correction_label: "",
  initial_hours: 0, consumed_hours: 0, remaining_mode: "budget_balance", overrun_hours: 0, unconfirmed: 0, open_points: 0,
  brain_project_id: "brain-a", brain_code: "A-100"}];
const meeting: WorkspaceMeeting = {id: "m1", meeting_id: "m1", recording_id: null, project_id: "erp-a", brain_project_id: "brain-a", project_code: "A-100", project_title: "Projet A", title: "Revue technique", date: "2026-10-02", participants: "Marie", decisions: "Diamètre validé à 50 mm.", actions: [{id: "a1", title: "Préparer le plan", owner: "Jean", due_date: "2026-10-09", task_id: null}], stage: "published", status: "published", created_at: "2026-10-02", recording: null};
const proposal: WorkspaceKnowledge = {id: "p1", project_id: "brain-a", brain_project_id: "brain-a", project_code: "A-100", project_name: "Projet A", erp_projects: [{id: "erp-a", code: "A-100", title: "Projet A"}], kind: "fact", subject: "Diamètre", value: "50 mm", status: "pending", citations: [{source_id: "s1", title: "Mail technique", excerpt: "Le diamètre est de 50 mm.", locator: {page: 2}}]};
const job: WorkspaceJob = {id: "j1", engine: "triage", kind: "triage", title: "Classement des mails", project_id: null, brain_project_id: null, project_code: "", project_title: "", source_id: null, status: "running", stage: "running", progress: 40, processed: 4, total: 10, unit: "mails", can_cancel: true, can_retry: false, cancel_url: "/api/v1/workspace/triage-jobs/j1/cancel", retry_url: null, error: null, created_at: "2026-10-02", updated_at: "2026-10-02"};
const triageJob: DurableTriageJob = {id: "j1", status: "running", force: false, processed: 4, total: 10, progress: 40, cancel_requested: false, result: {triaged: 4}, error: null, can_cancel: true, can_retry: false, created_at: "2026-10-02", updated_at: "2026-10-02"};

const creationCapabilities:SessionCapabilities={enabled:true,capture:{durable:true,max_upload_mb:50,max_duration_minutes:120,tracks:['mic','system'],browser_permission_required:true},
  transcription:{live_ready:false,batch_ready:false,detail:'Fictif'},notes:{staging:true,erp_projection:true}};
function creationFixture(){
  vi.spyOn(workspaceApi,'meetings').mockResolvedValue({items:[],total:0});
  vi.spyOn(meetingSessions,'list').mockResolvedValue({items:[],total:0,offset:0,limit:25});
  const create=vi.spyOn(meetingSessions,'create'),command=vi.spyOn(meetingSessions,'command'),capture=vi.spyOn(meetingCapture,'start');
  return {create,command,capture};
}
it('ouvre le formulaire demandé depuis Sources après le chargement des capacités, avec le projet accessible et sans micro',async()=>{
  const calls=creationFixture();let resolve!:(value:SessionCapabilities)=>void;
  vi.spyOn(meetingSessions,'capabilities').mockReturnValue(new Promise(value=>{resolve=value;}));
  render(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()} creationRequest={{key:1,projectId:'erp-a'}}/>);
  expect(screen.queryByRole('form',{name:'Créer une séance'})).toBeNull();
  resolve(creationCapabilities);
  const form=await screen.findByRole('form',{name:'Créer une séance'});
  expect(within(form).getByLabelText('Projet de la nouvelle séance')).toHaveProperty('value','erp-a');
  expect(within(form).getByLabelText('Préparation')).toHaveProperty('value','meeting');
  expect(calls.create).not.toHaveBeenCalled();expect(calls.command).not.toHaveBeenCalled();expect(calls.capture).not.toHaveBeenCalled();
});

it('signale l’ouverture et la fermeture réelle du Studio sans annoncer une création ni lancer la capture',async()=>{
  localStorage.clear();const calls=creationFixture(),changed=vi.fn();
  vi.spyOn(meetingSessions,'capabilities').mockResolvedValue(creationCapabilities);
  const session:MeetingSession={id:'studio-navigation',title:'Préparation fictive',kind:'note',project_id:null,brain_project_id:null,state:'created',revision:1,
    date:'2026-10-11',recording_id:null,note_id:null,tracks:[],total_bytes:0,duration_seconds:0,issues:[],created_at:'2026-10-11',updated_at:'2026-10-11'};
  vi.spyOn(meetingSessions,'get').mockResolvedValue(session);vi.spyOn(meetingSessions,'askHistory').mockResolvedValue({items:[]});
  vi.spyOn(meetingSessions,'enhancements').mockResolvedValue({items:[]});vi.spyOn(meetingSessions,'liveAnswers').mockResolvedValue({items:[]});
  render(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()} onStudioOpenChange={changed} studioNavigation={<nav aria-label="Navigation fournie">Lien conservé</nav>}/>);
  await screen.findByRole('button',{name:'Nouvelle séance'});expect(changed).toHaveBeenLastCalledWith(false);
  fireEvent(window,new CustomEvent('agent-open-meeting-session',{detail:{sessionId:session.id}}));
  await screen.findByRole('region',{name:'Séance Préparation fictive'});expect(changed).toHaveBeenLastCalledWith(true);
  expect(screen.getByRole('navigation',{name:'Navigation fournie'}).closest('.meeting-preparation')).not.toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Retour aux réunions'}));await screen.findByRole('region',{name:'Réunions'});
  expect(changed).toHaveBeenLastCalledWith(false);expect(calls.create).not.toHaveBeenCalled();expect(calls.command).not.toHaveBeenCalled();expect(calls.capture).not.toHaveBeenCalled();
});
it('écarte un projet absent ou devenu inaccessible et ne rouvre pas une demande de préparation déjà fermée',async()=>{
  creationFixture();vi.spyOn(meetingSessions,'capabilities').mockResolvedValue(creationCapabilities);
  const {rerender}=render(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()} creationRequest={{key:1,projectId:'brain-a'}}/>);
  let form=await screen.findByRole('form',{name:'Créer une séance'});
  expect(within(form).getByLabelText('Projet de la nouvelle séance')).toHaveProperty('value','');
  rerender(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()} creationRequest={{key:2,projectId:'erp-a'}}/>);
  await waitFor(()=>expect(screen.getByLabelText('Projet de la nouvelle séance')).toHaveProperty('value','erp-a'));
  rerender(<GlobalMeetingsView rows={[]} onOpenProject={vi.fn()} creationRequest={{key:2,projectId:'erp-a'}}/>);
  await waitFor(()=>expect(screen.getByLabelText('Projet de la nouvelle séance')).toHaveProperty('value',''));
  expect(screen.getByRole('alert').textContent).toContain('n’est plus accessible');
  form=screen.getByRole('form',{name:'Créer une séance'});fireEvent.click(within(form).getByRole('button',{name:'Fermer'}));
  rerender(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()} creationRequest={{key:2,projectId:'erp-a'}}/>);
  expect(screen.queryByRole('form',{name:'Créer une séance'})).toBeNull();
});
it('ouvre la préparation demandée depuis Sources avec activation explicite lorsque les réunions sont désactivées',async()=>{
  const calls=creationFixture();vi.spyOn(meetingSessions,'capabilities').mockResolvedValue({...creationCapabilities,enabled:false});
  const settings=vi.spyOn(fusionInsights,'settings'),save=vi.spyOn(fusionInsights,'save');
  render(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()} creationRequest={{key:1,projectId:'erp-a'}}/>);
  const form=await screen.findByRole('form',{name:'Créer une séance'});
  expect(within(form).getByLabelText('Projet de la nouvelle séance')).toHaveProperty('value','erp-a');
  expect(within(form).getByLabelText('Préparation')).toHaveProperty('value','meeting');
  expect(within(form).getByRole('button',{name:'Activer les réunions'})).toBeTruthy();
  fireEvent.change(within(form).getByLabelText('Titre de la séance'),{target:{value:'Revue à préparer'}});
  expect(within(form).getByRole('button',{name:'Ouvrir la séance'})).toHaveProperty('disabled',true);
  fireEvent.submit(form);
  expect(settings).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
  expect(calls.create).not.toHaveBeenCalled();expect(calls.command).not.toHaveBeenCalled();expect(calls.capture).not.toHaveBeenCalled();
});

it('rend Nouvelle séance visible après lecture des capacités désactivées sans activer ni enregistrer',async()=>{
  const calls=creationFixture();let resolve!:(value:SessionCapabilities)=>void;
  vi.spyOn(meetingSessions,'capabilities').mockReturnValue(new Promise(value=>{resolve=value;}));
  const settings=vi.spyOn(fusionInsights,'settings'),save=vi.spyOn(fusionInsights,'save');
  render(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()}/>);
  expect(screen.getByRole('button',{name:'Nouvelle séance'})).toHaveProperty('disabled',true);
  resolve({...creationCapabilities,enabled:false});
  await waitFor(()=>expect(screen.getByRole('button',{name:'Nouvelle séance'})).toHaveProperty('disabled',false));
  fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
  const form=screen.getByRole('form',{name:'Créer une séance'});
  expect(within(form).getByRole('button',{name:'Activer les réunions'})).toBeTruthy();
  expect(within(form).getByRole('button',{name:'Ouvrir la séance'})).toHaveProperty('disabled',true);
  expect(settings).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
  expect(calls.create).not.toHaveBeenCalled();expect(calls.command).not.toHaveBeenCalled();expect(calls.capture).not.toHaveBeenCalled();
});

it('active seulement l’espace après clic explicite et conserve les autres réglages sans créer de séance',async()=>{
  const calls=creationFixture(),disabled={...creationCapabilities,enabled:false};
  vi.spyOn(meetingSessions,'capabilities').mockResolvedValue(creationCapabilities).mockResolvedValueOnce(disabled);
  const original:FusionSettings={enabled:false,live_transcription_enabled:false,proactive_enabled:true,auto_enhancement_enabled:false,
    mode:'local',onboarding_complete:true,capabilities:disabled};
  const settings=vi.spyOn(fusionInsights,'settings').mockResolvedValue(original);
  const save=vi.spyOn(fusionInsights,'save').mockResolvedValue({...original,enabled:true,capabilities:creationCapabilities});
  const event=vi.fn();window.addEventListener('agent-fusion-settings-changed',event);
  try{
    render(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()}/>);
    await waitFor(()=>expect(screen.getByRole('button',{name:'Nouvelle séance'})).toHaveProperty('disabled',false));
    fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
    const form=screen.getByRole('form',{name:'Créer une séance'});
    fireEvent.change(within(form).getByLabelText('Titre de la séance'),{target:{value:'Revue technique préparée'}});
    fireEvent.change(within(form).getByLabelText('Projet de la nouvelle séance'),{target:{value:'erp-a'}});
    expect(save).not.toHaveBeenCalled();
    fireEvent.click(within(form).getByRole('button',{name:'Activer les réunions'}));
    await waitFor(()=>expect(save).toHaveBeenCalledWith({enabled:true,live_transcription_enabled:false,proactive_enabled:true,
      auto_enhancement_enabled:false,mode:'local',onboarding_complete:true}));
    await waitFor(()=>expect(within(form).getByRole('button',{name:'Ouvrir la séance'})).toHaveProperty('disabled',false));
    expect(settings).toHaveBeenCalledTimes(1);expect(event).toHaveBeenCalledTimes(1);
    expect(within(form).getByLabelText('Titre de la séance')).toHaveProperty('value','Revue technique préparée');
    expect(within(form).getByLabelText('Projet de la nouvelle séance')).toHaveProperty('value','erp-a');
    expect(calls.create).not.toHaveBeenCalled();expect(calls.command).not.toHaveBeenCalled();expect(calls.capture).not.toHaveBeenCalled();
  }finally{window.removeEventListener('agent-fusion-settings-changed',event);}
});

it('ne crée la séance préparée qu’au clic Ouvrir la séance après activation et ne lance pas le microphone',async()=>{
  const calls=creationFixture(),disabled={...creationCapabilities,enabled:false};
  vi.spyOn(meetingSessions,'capabilities').mockResolvedValue(creationCapabilities).mockResolvedValueOnce(disabled);
  const original:FusionSettings={enabled:false,live_transcription_enabled:false,proactive_enabled:false,auto_enhancement_enabled:false,
    mode:'network',onboarding_complete:false,capabilities:disabled};
  vi.spyOn(fusionInsights,'settings').mockResolvedValue(original);
  vi.spyOn(fusionInsights,'save').mockResolvedValue({...original,enabled:true,capabilities:creationCapabilities});
  calls.create.mockImplementation(()=>new Promise(()=>{}));
  render(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()}/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Nouvelle séance'})).toHaveProperty('disabled',false));
  fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
  fireEvent.change(screen.getByLabelText('Titre de la séance'),{target:{value:'Revue préparée'}});
  fireEvent.click(screen.getByRole('button',{name:'Activer les réunions'}));
  await waitFor(()=>expect(screen.getByRole('button',{name:'Ouvrir la séance'})).toHaveProperty('disabled',false));
  expect(calls.create).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Ouvrir la séance'}));
  await waitFor(()=>expect(calls.create).toHaveBeenCalledWith(expect.objectContaining({title:'Revue préparée',kind:'meeting',project_id:null,command_id:expect.any(String)})));
  expect(calls.create).toHaveBeenCalledTimes(1);expect(calls.command).not.toHaveBeenCalled();expect(calls.capture).not.toHaveBeenCalled();
});

it('affiche le refus d’activation et conserve le formulaire sans créer ni démarrer de séance',async()=>{
  const calls=creationFixture();vi.spyOn(meetingSessions,'capabilities').mockResolvedValue({...creationCapabilities,enabled:false});
  vi.spyOn(fusionInsights,'settings').mockRejectedValue(new Error('Action réservée au propriétaire.'));
  const save=vi.spyOn(fusionInsights,'save');
  render(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()}/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Nouvelle séance'})).toHaveProperty('disabled',false));
  fireEvent.click(screen.getByRole('button',{name:'Nouvelle séance'}));
  fireEvent.change(screen.getByLabelText('Titre de la séance'),{target:{value:'Brouillon conservé'}});
  fireEvent.click(screen.getByRole('button',{name:'Activer les réunions'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Action réservée au propriétaire.');
  expect(screen.getByLabelText('Titre de la séance')).toHaveProperty('value','Brouillon conservé');
  expect(screen.getByRole('button',{name:'Ouvrir la séance'})).toHaveProperty('disabled',true);
  expect(save).not.toHaveBeenCalled();expect(calls.create).not.toHaveBeenCalled();expect(calls.command).not.toHaveBeenCalled();expect(calls.capture).not.toHaveBeenCalled();
});

it("exige un projet explicite pour ouvrir le parcours réunion et pagine côté serveur", async () => {
  const load = vi.spyOn(workspaceApi, "meetings").mockResolvedValue({items: [meeting], total: 26});
  const open = vi.fn();
  render(<GlobalMeetingsView rows={rows} onOpenProject={open} />);
  await screen.findByText("Revue technique");
  expect(screen.queryByRole("button", {name: "Revues du projet"})).toBeNull();
  expect(open).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", {name: "Suivants"}));
  await waitFor(() => expect(load).toHaveBeenLastCalledWith(expect.objectContaining({offset: 25, project_id: undefined}), expect.any(AbortSignal)));
  fireEvent.change(screen.getByLabelText("Projet"), {target: {value: "erp-a"}});
  await waitFor(() => expect(load).toHaveBeenLastCalledWith(expect.objectContaining({offset: 0, project_id: "erp-a"}), expect.any(AbortSignal)));
  fireEvent.click(screen.getByRole("button", {name: "Revues du projet"}));
  expect(open).toHaveBeenCalledWith("erp-a", "reviews");
});

it("affiche les décisions et les responsables existants sans recréer de compte rendu", async () => {
  vi.spyOn(workspaceApi, "meetings").mockResolvedValue({items: [meeting], total: 1});
  render(<GlobalMeetingsView rows={rows} onOpenProject={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", {name: "Revue technique"}));
  expect(screen.getByRole("dialog", {name: "Revue technique"})).toBeTruthy();
  expect(screen.getByRole('link',{name:'Exporter en PDF'}).getAttribute('href')).toBe('/api/v1/projects/erp-a/meetings/m1/pdf');
  expect(screen.getByText("Diamètre validé à 50 mm.")).toBeTruthy();
  expect(screen.getByText(/Jean · 9 oct/)).toBeTruthy();
  fireEvent.keyDown(screen.getByRole("dialog"), {key: "Escape"});
  expect(screen.queryByRole("dialog")).toBeNull();
});

it("envoie la recherche et le projet Brain au serveur et distingue les faits validés", async () => {
  vi.spyOn(workspaceApi, "proposals").mockResolvedValue({items: [proposal], total: 1});
  const facts = vi.spyOn(workspaceApi, "knowledge").mockResolvedValue({items: [{...proposal, status: "validated", version: 2, validated_at: "2026-10-02"}], total: 1});
  render(<GlobalKnowledgeView rows={rows} onOpenProject={vi.fn()} />);
  await screen.findByText("Diamètre");
  fireEvent.change(screen.getByLabelText("Projet"), {target: {value: "erp-a"}});
  fireEvent.click(screen.getByRole("button", {name: "Informations retenues"}));
  fireEvent.change(screen.getByLabelText("Rechercher une information"), {target: {value: "diamètre"}});
  await waitFor(() => expect(facts).toHaveBeenLastCalledWith(expect.objectContaining({q: "diamètre", project_id: "brain-a", status: "validated"}), expect.any(AbortSignal)));
  expect(screen.queryByRole("button", {name: "Examiner et corriger"})).toBeNull();
  expect(screen.getByText("Retenue")).toBeTruthy();
});

it("permet de corriger une proposition avant validation et conserve le brouillon en cas d'erreur", async () => {
  vi.spyOn(workspaceApi, "proposals").mockResolvedValue({items: [proposal], total: 1});
  vi.spyOn(workspaceApi, "knowledge").mockResolvedValue({items: [], total: 0});
  const save = vi.spyOn(workspaceApi, "decide").mockRejectedValueOnce(new Error("La connaissance a changé : relire la version")).mockResolvedValue({status: "validated"});
  render(<GlobalKnowledgeView rows={rows} onOpenProject={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", {name: "À vérifier"}));
  fireEvent.click(await screen.findByRole("button", {name: "Examiner et corriger"}));
  fireEvent.change(screen.getByLabelText("Valeur"), {target: {value: "52 mm après contrôle"}});
  fireEvent.click(screen.getByRole("button", {name: "Valider l’information"}));
  await screen.findByRole("alert");
  expect((screen.getByLabelText("Valeur") as HTMLTextAreaElement).value).toBe("52 mm après contrôle");
  expect(save).toHaveBeenCalledWith("p1", "edit-and-accept", expect.objectContaining({subject: "Diamètre", value: "52 mm après contrôle"}));
  fireEvent.click(screen.getByRole("button", {name: "Valider l’information"}));
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
});

it("protège les corrections contre une fermeture et n'efface pas le brouillon", async () => {
  vi.spyOn(workspaceApi, "proposals").mockResolvedValue({items: [proposal], total: 1});
  vi.spyOn(workspaceApi, "knowledge").mockResolvedValue({items: [], total: 0});
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  render(<GlobalKnowledgeView rows={rows} onOpenProject={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", {name: "À vérifier"}));
  fireEvent.click(await screen.findByRole("button", {name: "Examiner et corriger"}));
  fireEvent.change(screen.getByLabelText("Sujet"), {target: {value: "Diamètre nominal"}});
  fireEvent.click(screen.getByRole("button", {name: "Fermer"}));
  expect(confirm).toHaveBeenCalled();
  expect((screen.getByLabelText("Sujet") as HTMLInputElement).value).toBe("Diamètre nominal");
  expect(screen.getByRole("dialog").getAttribute("data-workspace-dirty")).toBe("true");
});

it("ouvre la preuve dans un inspecteur et affiche la source complète", async () => {
  vi.spyOn(workspaceApi, "knowledge").mockResolvedValue({items: [{...proposal, status: "validated"}], total: 1});
  vi.spyOn(workspaceApi, "source").mockResolvedValue({id: "s1", type: "email", status: "resolved", project_id: "brain-a", author: "Marie", metadata: {subject: "Mail technique original"}, artifacts: [{id: "art1", kind: "body_text", text: "Texte complet du mail, conservé avec les preuves."}]});
  render(<GlobalKnowledgeView rows={rows} onOpenProject={vi.fn()} />);
  fireEvent.click(await screen.findByRole("button", {name: "Mail technique"}));
  await screen.findByText("Texte complet du mail, conservé avec les preuves.");
  expect(screen.getByText("Le diamètre est de 50 mm.")).toBeTruthy();
  expect(screen.getByText("Page : 2")).toBeTruthy();
  expect(screen.getByRole("link", {name: "Télécharger l’original"}).getAttribute("href")).toBe("/v1/sources/s1/raw");
});

it("ignore une réponse source obsolète après sélection d'une autre citation", async () => {
  let resolveOld: (value: any) => void = () => {};
  vi.spyOn(workspaceApi, "source").mockImplementation(id => id === "old" ? new Promise(resolve => {resolveOld = resolve;}) : Promise.resolve({id: "new", type: "email", status: "resolved", project_id: "brain-a", author: "", metadata: {subject: "Nouvelle source"}, artifacts: []}));
  const view = render(<SourceInspector sourceId="old" onClose={vi.fn()} />);
  view.rerender(<SourceInspector sourceId="new" onClose={vi.fn()} />);
  await screen.findByText("Nouvelle source");
  resolveOld({id: "old", type: "email", status: "resolved", metadata: {subject: "Ancienne source"}, artifacts: []});
  await waitFor(() => expect(screen.queryByText("Ancienne source")).toBeNull());
});

it("affiche les localisateurs documentaires conservés sans inventer une page à partir de l'ordinal", async () => {
  vi.spyOn(workspaceApi, "source").mockResolvedValue({id: "pdf", type: "document", status: "resolved", project_id: "brain-a", author: "", metadata: {filename: "Plan industriel.pdf"}, artifacts: [{id: "a-pdf", kind: "document_page", text: "Plan annoté à 250 W."}]});
  render(<SourceInspector sourceId="pdf" onClose={vi.fn()} evidence={[{source_id: "pdf", locator: {physical_page: 7, printed_page: "B-3", ordinal: 1, path: "C:/private/plan.pdf", profile_key: "private-profile"}}]} />);
  await screen.findByText("Plan annoté à 250 W.");
  expect(screen.getByRole("heading", {name: "Texte du document"})).toBeTruthy();
  expect(screen.getByText("Page physique : 7 · Page imprimée : B-3")).toBeTruthy();
  expect(screen.queryByText(/ordinal|private-profile|C:\/private/)).toBeNull();
  expect(screen.queryByText("Page : 1")).toBeNull();
});

it("rend les repères de tableur, audio et version de note consultables", async () => {
  vi.spyOn(workspaceApi, "source").mockResolvedValue({id: "repere", type: "document", status: "resolved", project_id: "brain-a", author: "", metadata: {filename: "Sources localisées"}, artifacts: []});
  render(<SourceInspector sourceId="repere" onClose={vi.fn()} evidence={[{source_id: "repere", locator: {sheet: "Chiffrage", range: "A4:C4", start_ms: 5000, end_ms: 10000, note_revision: 2, block_index: 3}}]} />);
  await screen.findByText("Sources localisées");
  expect(screen.getByText("Feuille : Chiffrage · Plage : A4:C4 · Début (ms) : 5000 · Fin (ms) : 10000 · Version de note : 2 · Bloc : 4")).toBeTruthy();
});

it("affiche les compteurs réels et propose seulement les commandes garanties par le moteur", async () => {
  vi.spyOn(workspaceApi, "jobs").mockResolvedValue({items: [job], total: 1});
  const action = vi.spyOn(workspaceApi, "jobAction").mockResolvedValue(job);
  const open = vi.fn();
  render(<GlobalJobsView rows={rows} onOpenProject={open} active={false} />);
  await screen.findByText("4 / 10 mails");
  expect(screen.getByRole("progressbar").getAttribute("value")).toBe("40");
  expect(screen.queryByRole("button", {name: "Reprendre"})).toBeNull();
  expect(screen.queryByRole("button", {name: "Ouvrir le projet"})).toBeNull();
  fireEvent.click(screen.getByRole("button", {name: "Annuler"}));
  await waitFor(() => expect(action).toHaveBeenCalledWith("/api/v1/workspace/triage-jobs/j1/cancel"));
  expect(open).not.toHaveBeenCalled();
});

it("lance une ré-analyse globale explicite même quand la vue est filtrée par projet", async () => {
  vi.spyOn(workspaceApi, "jobs").mockResolvedValue({items: [], total: 0});
  const start = vi.spyOn(workspaceApi, "startTriage").mockResolvedValue(triageJob);
  render(<GlobalJobsView rows={rows} onOpenProject={vi.fn()} active={false} />);
  await screen.findByText("Aucun traitement enregistré");
  fireEvent.change(screen.getByLabelText("Projet"), {target: {value: "erp-a"}});
  fireEvent.click(screen.getByLabelText("Ré-analyser les mails à classer ayant déjà une proposition"));
  fireEvent.click(screen.getByRole("button", {name: "Analyser les mails"}));
  await waitFor(() => expect(start).toHaveBeenCalledWith(true));
});

it("ne remplace pas silencieusement un projet délié par toutes les connaissances", async () => {
  const load = vi.spyOn(workspaceApi, "knowledge").mockResolvedValue({items: [{...proposal, status: "validated"}], total: 1});
  const view = render(<GlobalKnowledgeView rows={rows} onOpenProject={vi.fn()} />);
  await screen.findByText("Diamètre");
  fireEvent.change(screen.getByLabelText("Projet"), {target: {value: "erp-a"}});
  await waitFor(() => expect(load).toHaveBeenLastCalledWith(expect.objectContaining({project_id: "brain-a"}), expect.any(AbortSignal)));
  const before = load.mock.calls.length;
  view.rerender(<GlobalKnowledgeView rows={[{...rows[0], brain_project_id: null}]} onOpenProject={vi.fn()} />);
  await screen.findByText(/Ce projet n’est plus lié/);
  expect(load.mock.calls.length).toBe(before);
});

it("bloque la validation d'une proposition sans projet et ne recherche aucune version globale à remplacer", async () => {
  vi.spyOn(workspaceApi, "proposals").mockResolvedValue({items: [{...proposal, project_id: null, brain_project_id: null, erp_projects: []}], total: 1});
  const facts = vi.spyOn(workspaceApi, "knowledge").mockResolvedValue({items: [], total: 0});
  const save = vi.spyOn(workspaceApi, "decide");
  render(<GlobalKnowledgeView rows={rows} onOpenProject={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", {name: "À vérifier"}));
  fireEvent.click(await screen.findByRole("button", {name: "Examiner et corriger"}));
  expect((screen.getByRole("button", {name: "Valider l’information"}) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText(/Cette proposition n’a pas de projet/)).toBeTruthy();
  expect(facts).toHaveBeenCalledTimes(1);
  expect(save).not.toHaveBeenCalled();
});


it("retient par défaut, déclasse puis permet un rétablissement avec les sources", async () => {
  const load = vi.spyOn(workspaceApi, "knowledge").mockImplementation(async filters => ({items: [{...proposal, status: filters?.status || "validated", validation_mode: "default"}], total: 1}));
  const change = vi.spyOn(workspaceApi, "changeKnowledge").mockResolvedValue({id: "p1", status: "invalidated"});
  render(<GlobalKnowledgeView rows={rows} onOpenProject={vi.fn()} />);
  await screen.findByText(/Retenue par défaut/);
  fireEvent.click(screen.getByRole("button", {name: "Déclasser"}));
  await waitFor(() => expect(change).toHaveBeenCalledWith("brain-a", "p1", "invalidate"));
  fireEvent.click(screen.getByRole("button", {name: "Déclassées"}));
  await screen.findByRole("button", {name: "Rétablir"});
  expect(load).toHaveBeenLastCalledWith(expect.objectContaining({status: "invalidated"}), expect.any(AbortSignal));
  expect(screen.getByRole("button", {name: "Mail technique"})).toBeTruthy();
  fireEvent.click(screen.getByRole("button", {name: "Rétablir"}));
  await waitFor(() => expect(change).toHaveBeenCalledWith("brain-a", "p1", "restore"));
});


it('affiche une seule version HTML originale dans la source mail',async()=>{
  vi.spyOn(workspaceApi,'source').mockResolvedValue({id:'mail-original',type:'email',status:'resolved',project_id:'brain-a',author:'Alice',metadata:{subject:'Mail original'},body_html:'<p style="color:red">Présentation originale</p>',artifacts:[{id:'plain',kind:'body_text',text:'Alternative simplifiée'}]});
  render(<SourceInspector sourceId="mail-original" onClose={vi.fn()}/>);
  const frame=await screen.findByTitle('Contenu du message');
  expect(frame.getAttribute('srcdoc')).toContain('style="color:red"');
  expect(screen.getAllByTitle('Contenu du message')).toHaveLength(1);
  expect(screen.queryByText('Alternative simplifiée')).toBeNull();
});
