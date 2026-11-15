import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { reviewApi, type ReviewDetail, type ReviewPublication } from '../lib/projectReviews';
import { identityApi, type ProjectIdentity } from '../lib/projectIdentity';
import { planningApi } from '../lib/projectPlanning';
import { deliverableApi, type DeliverableDetail } from '../lib/projectDeliverables';
import { meetingAudio, type MeetingRecording } from '../lib/meetingAudio';
import { ProjectReviewsPanel } from './ProjectReviewsPanel';

const content={meeting_date:'2026-10-10',location:'Salle projets',notes:'Notes initiales',milestone_id:null,
  participants:[{person_id:null,name:'Alice',function:'Chargée de projet',signature_required:true}],deliverable_ids:['d1'],
  items:([{id:'i1',section_code:'vigilance_points',text:'Composants disponibles'},
    {id:'i2',section_code:'expected_functions',text:'Éclairer la zone'},
    {id:'i3',section_code:'initial_constraints',text:'Qualification client'}] as const).map(item=>({...item,reviewed:true,evidence_ids:[],owner:'',due_date:''}))};
const row:ReviewDetail={id:'r1',project_id:'p1',type_code:'rlp',number:1,status:'draft',review_revision:3,previous_review_id:null,
  revision:7,can_edit:true,can_create_revision:false,content,provenance:{},created_at:'2026-10-10T09:00:00Z',updated_at:'2026-10-10T09:00:00Z',publication:null,publication_blockers:[]};
const list={items:[{id:'r1',number:1,status:'draft' as const,review_revision:3,meeting_date:'2026-10-10',participants:1,updated_at:row.updated_at}],total:1,offset:0,limit:25,revision:7,can_edit:true};
const proof={recording_id:'a1',brain_project_id:'b1',erp_project_id:'p1',source_id:'s1',revision:3,summary_model:'Local',summary_sha256:'a'.repeat(64),
  segment_id:'seg1',quote:'Essai le 20',text:'Essai le 20 puis qualification.',speaker:'Alice',start:12,end:18};
const source={id:'a1',title:'Lancement',date:'2026-10-10',revision:3,summary_model:'Local'};
const recording:MeetingRecording={id:'a1',source_id:'s1',title:'Lancement',date:'2026-10-10',filename:'recette.wav',num_speakers:1,
  segments:[{id:'seg1',text:proof.text,speaker:'spk1',start:12,end:18}],speaker_names:{spk1:'Alice'},revision:3,reviewed_revision:3,summary_revision:3,
  summary:{overview:'Synthèse de lancement',decisions:[{text:'Faire les essais',segment_id:'seg1',quote:proof.quote}]},summary_model:'Local',published_meeting_id:null,
  job_kind:'',job_status:'completed',stage:'ready',progress:100,processed_seconds:18,duration_seconds:18,cancel_requested:false,error:'',created_at:row.created_at,updated_at:row.updated_at};
const document={id:'d1',project_id:'p1',title:'Plan BE',active:true,revision:7} as DeliverableDetail;
const published:ReviewDetail={...row,status:'published',can_edit:false,can_create_revision:true,review_revision:4,revision:8,
  publication:{id:'pub1',sha256:'a'.repeat(64),pdf_sha256:'b'.repeat(64),created_at:row.created_at}};
const publication:ReviewPublication={id:'pub1',sha256:'a'.repeat(64),pdf_sha256:'b'.repeat(64),snapshot:{project:{id:'p1',code:'TEST-0001',title:'Lancement fictif'},
  team:[{person_id:'person1',name:'Nom figé',role:'responsable_projet'}],deliverables:[{id:'d1',title:'Titre figé à la publication'}],
  review:{content,provenance:{}},published_by:'local',published_at:row.created_at}};
const props=()=>({projectId:'p1',onSaved:vi.fn()});
beforeEach(()=>{
  vi.spyOn(reviewApi,'list').mockResolvedValue(list);vi.spyOn(reviewApi,'read').mockResolvedValue(row);
  vi.spyOn(identityApi,'read').mockResolvedValue({members:[]} as unknown as ProjectIdentity);vi.spyOn(identityApi,'people').mockResolvedValue({items:[],total:0,offset:0,limit:50});
  vi.spyOn(planningApi,'milestones').mockResolvedValue({items:[],total:0,offset:0,limit:50,revision:7});
  vi.spyOn(deliverableApi,'list').mockResolvedValue({items:[],total:0,offset:0,limit:50,revision:7,can_edit:true});vi.spyOn(deliverableApi,'detail').mockResolvedValue(document);
  vi.spyOn(reviewApi,'recordings').mockResolvedValue({items:[source],total:51,offset:0,limit:25});vi.spyOn(meetingAudio,'get').mockResolvedValue(recording);
  vi.spyOn(reviewApi,'history').mockResolvedValue({items:[{id:'e1',action:'review_saved',actor_id:'local',planning_revision:7,created_at:row.created_at}],total:1,offset:0,limit:25});
  vi.spyOn(reviewApi,'event').mockResolvedValue({id:'e1',action:'review_saved',actor_id:'local',planning_revision:7,created_at:row.created_at,previous:{content:{...content,notes:'Ancienne note'}},value:{content,provenance:{}}});
  vi.spyOn(reviewApi,'publication').mockResolvedValue(publication);vi.spyOn(window,'confirm').mockReturnValue(true);
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function open(){fireEvent.click(await screen.findByRole('button',{name:/RLP · Révision 1/}));await screen.findByRole('form',{name:'Fiche RLP révision 1'});}

it('conserve les noms capturés après restauration et ouvre la relation ERP actuelle pour un lecteur',async()=>{
  const frozen=structuredClone(publication),before=structuredClone(frozen);
  frozen.bindings={erp:{d1:'restored-document'},brain:{d1:'unrelated-audio'}};
  vi.mocked(reviewApi.read).mockResolvedValue({...published,can_create_revision:false,content:{...content,deliverable_ids:['restored-document']}});
  vi.mocked(reviewApi.publication).mockResolvedValue(frozen);const navigate=vi.fn();
  const view=render(<ProjectReviewsPanel {...props()} onOpenDocument={navigate}/>);await open();
  const button=await screen.findByRole('button',{name:'Ouvrir le livrable Titre figé à la publication'});
  await waitFor(()=>expect(screen.getAllByText('Titre figé à la publication')).toHaveLength(2));
  expect(deliverableApi.detail).not.toHaveBeenCalled();fireEvent.click(button);
  expect(navigate).toHaveBeenCalledWith('restored-document','Titre figé à la publication');
  expect(frozen.snapshot).toEqual(before.snapshot);
  view.rerender(<ProjectReviewsPanel {...props()} onOpenDocument={navigate} active={false}/>);
  expect(button.matches(':disabled')).toBe(true);fireEvent.click(button);expect(navigate).toHaveBeenCalledOnce();
});

async function openRestoredHistory(){
  vi.mocked(reviewApi.read).mockResolvedValue({...row,can_edit:false});
  vi.mocked(reviewApi.event).mockResolvedValue({id:'e1',action:'review_saved',actor_id:'local',planning_revision:7,created_at:row.created_at,
    bindings:{erp:{a1:'wrong-erp-audio',d1:'current-document'},brain:{a1:'current-audio',s1:'current-source'}},previous:{},
    value:{content:{...content,notes:'a1 d1 seg1',items:[{...content.items[0],evidence_ids:['proof']}]},provenance:{proof}}});
  const view=render(<ProjectReviewsPanel {...props()}/>);await open();fireEvent.click(screen.getByRole('button',{name:'Consulter l’historique'}));
  fireEvent.click(await screen.findByRole('button',{name:'Voir l’enregistrement 7'}));await screen.findByText('a1 d1 seg1');
  fireEvent.click(screen.getByText('Source · Alice · 0:12'));
  return view;
}

it('consulte la réunion Brain restaurée et distingue sa transcription actuelle de la citation conservée',async()=>{
  const original=structuredClone(proof),save=vi.spyOn(reviewApi,'save'),publish=vi.spyOn(reviewApi,'publish');
  vi.mocked(meetingAudio.get).mockResolvedValue({...recording,id:'current-audio',source_id:'current-source',revision:4,
    segments:[{...recording.segments[0],text:'Texte corrigé après publication'}],speaker_names:{spk1:'Alice actuelle'}});
  await openRestoredHistory();expect(meetingAudio.get).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Consulter la réunion source'}));
  const source=await screen.findByRole('region',{name:'Réunion source actuelle'});await within(source).findByText('Texte corrigé après publication');
  expect(meetingAudio.get).toHaveBeenCalledWith('p1','current-audio',expect.any(AbortSignal));
  expect(within(source).getByText(/révision 4.*révision 3/)).toBeTruthy();expect(within(source).getByText('Alice actuelle · 12–18 s')).toBeTruthy();
  expect(screen.getByText('Essai le 20')).toBeTruthy();expect(screen.getByText(/Transcription conservée : Essai le 20 puis qualification/)).toBeTruthy();
  expect(screen.getByText('Livrables : current-document')).toBeTruthy();expect(proof).toEqual(original);
  expect(screen.getByLabelText('Audio de la réunion source').getAttribute('src')).toBe(meetingAudio.audioUrl('p1','current-audio'));
  expect(save).not.toHaveBeenCalled();expect(publish).not.toHaveBeenCalled();
});

it('refuse une source différente et permet de relire sans perdre la preuve publiée',async()=>{
  vi.mocked(meetingAudio.get).mockResolvedValueOnce({...recording,id:'current-audio',source_id:'foreign-source'})
    .mockResolvedValue({...recording,id:'current-audio',source_id:'current-source',revision:4,segments:[]});
  await openRestoredHistory();fireEvent.click(screen.getByRole('button',{name:'Consulter la réunion source'}));
  await screen.findByText('Source reçue différente de la réunion attendue.');expect(screen.queryByLabelText('Audio de la réunion source')).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Réessayer'}));await screen.findByText(/Ce segment n’est plus présent/);
  expect(screen.getByText('Essai le 20')).toBeTruthy();expect(meetingAudio.get).toHaveBeenCalledTimes(2);
});

it('annule la lecture source quand la vue devient inactive et ignore sa réponse tardive',async()=>{
  let resolve!:(value:MeetingRecording)=>void;vi.mocked(meetingAudio.get).mockReturnValue(new Promise(done=>{resolve=done;}));
  const view=await openRestoredHistory();fireEvent.click(screen.getByRole('button',{name:'Consulter la réunion source'}));
  await waitFor(()=>expect(meetingAudio.get).toHaveBeenCalledOnce());const signal=vi.mocked(meetingAudio.get).mock.calls[0][2];
  view.rerender(<ProjectReviewsPanel {...props()} active={false}/>);expect(signal?.aborted).toBe(true);
  resolve({...recording,id:'current-audio',source_id:'current-source',title:'Réponse tardive'});
  await waitFor(()=>expect(screen.queryByText('Réponse tardive')).toBeNull());expect(screen.queryByLabelText('Audio de la réunion source')).toBeNull();
});

it('crée le premier brouillon avec la révision projet puis rafraîchit le parent',async()=>{
  vi.mocked(reviewApi.list).mockResolvedValue({...list,items:[],total:0});const create=vi.spyOn(reviewApi,'create').mockResolvedValue(row),p=props();
  render(<ProjectReviewsPanel {...p}/>);fireEvent.click(await screen.findByRole('button',{name:'Créer la revue de lancement'}));
  await screen.findByRole('form',{name:'Fiche RLP révision 1'});expect(create).toHaveBeenCalledWith('p1',7);expect(p.onSaved).toHaveBeenCalledOnce();
});
it('préserve le brouillon entre vues, verrouille la sélection et invalide la relecture du point modifié',async()=>{
  const p=props(),save=vi.spyOn(reviewApi,'save').mockImplementation(async(_pid,_base,value)=>({...row,content:value,review_revision:4,revision:8}));
  const view=render(<ProjectReviewsPanel {...p}/>);await open();const point=within(screen.getByRole('article',{name:'Points de vigilance · Point 1'}));
  fireEvent.change(point.getByLabelText('Texte du point'),{target:{value:'Ma vigilance'}});expect((point.getByLabelText('Point relu et vérifié') as HTMLInputElement).checked).toBe(false);
  expect((screen.getByRole('button',{name:/RLP · Révision 1/}) as HTMLButtonElement).disabled).toBe(true);
  view.rerender(<ProjectReviewsPanel {...p} active={false}/>);view.rerender(<ProjectReviewsPanel {...p} active/>);
  expect((point.getByLabelText('Texte du point') as HTMLTextAreaElement).value).toBe('Ma vigilance');
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer le brouillon'}));await screen.findByText('Brouillon enregistré.');
  expect(save).toHaveBeenCalledWith('p1',row,expect.objectContaining({items:expect.arrayContaining([expect.objectContaining({text:'Ma vigilance',reviewed:false})])}));
  expect(p.onSaved).toHaveBeenCalledOnce();
});
it('compare un conflit sans perdre la saisie et exige le choix humain avant réenregistrement',async()=>{
  const save=vi.spyOn(reviewApi,'save').mockRejectedValueOnce(new Error('La revue a changé')).mockImplementation(async(_pid,_base,value)=>({...row,content:value}));
  render(<ProjectReviewsPanel {...props()}/>);await open();fireEvent.change(screen.getByLabelText('Notes de revue'),{target:{value:'Ma note'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer le brouillon'}));await screen.findByText('La revue a changé');
  vi.mocked(reviewApi.read).mockResolvedValue({...row,revision:9,review_revision:5,content:{...content,notes:'Note équipe',location:'Salle 2'}});
  fireEvent.click(screen.getByRole('button',{name:'Comparer avec la version actuelle'}));await screen.findByRole('region',{name:'Comparaison de la revue'});
  expect((screen.getByRole('button',{name:'Appliquer la comparaison au brouillon'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByLabelText('Ma saisie'));fireEvent.click(screen.getByRole('button',{name:'Appliquer la comparaison au brouillon'}));
  expect((screen.getByLabelText('Notes de revue') as HTMLTextAreaElement).value).toBe('Ma note');expect((screen.getByLabelText('Lieu') as HTMLInputElement).value).toBe('Salle 2');
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer le brouillon'}));await waitFor(()=>expect(save).toHaveBeenLastCalledWith('p1',expect.objectContaining({revision:9,review_revision:5}),expect.objectContaining({notes:'Ma note',location:'Salle 2'})));
});
it('publie seulement après sauvegarde, contrôles et confirmation puis montre les identités figées',async()=>{
  const publish=vi.spyOn(reviewApi,'publish').mockResolvedValue(published);render(<ProjectReviewsPanel {...props()}/>);await open();
  expect((screen.getByRole('button',{name:'Publier la révision'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByLabelText(/Je confirme la relecture/));fireEvent.click(screen.getByRole('button',{name:'Publier la révision'}));
  await screen.findByText('Nom figé · responsable_projet');expect(screen.getAllByText('Titre figé à la publication')).toHaveLength(2);expect(publish).toHaveBeenCalledWith('p1',row);
  expect(screen.queryByRole('button',{name:'Enregistrer le brouillon'})).toBeNull();expect(screen.getByLabelText('Notes de revue').matches(':disabled')).toBe(true);
});
it('interdit la publication incomplète et ne crée aucune révision pour un lecteur',async()=>{
  vi.mocked(reviewApi.read).mockResolvedValue({...row,can_edit:false,publication_blockers:['Équipe projet à compléter']});
  render(<ProjectReviewsPanel {...props()}/>);await open();expect(screen.queryByRole('button',{name:'Publier la révision'})).toBeNull();
  expect(screen.queryByRole('button',{name:'Créer une nouvelle révision'})).toBeNull();expect(screen.queryByRole('button',{name:'Choisir une réunion validée'})).toBeNull();
});
it('crée une nouvelle révision indépendante à partir de la publication autorisée',async()=>{
  vi.mocked(reviewApi.read).mockResolvedValue(published);const create=vi.spyOn(reviewApi,'newRevision').mockResolvedValue({...row,id:'r2',number:2,previous_review_id:'r1'});
  render(<ProjectReviewsPanel {...props()}/>);await open();fireEvent.click(screen.getByRole('button',{name:'Créer une nouvelle révision'}));
  await screen.findByRole('form',{name:'Fiche RLP révision 2'});expect(create).toHaveBeenCalledWith('p1',published);expect(published.status).toBe('published');
});
it('importe une synthèse paginée avec sa révision et laisse les points à vérifier sans publier',async()=>{
  const imported={...row,revision:8,review_revision:4,provenance:{proof},content:{...content,items:[...content.items,{id:'i4',section_code:'decisions' as const,text:'Faire les essais',reviewed:false,evidence_ids:['proof'],owner:'',due_date:''}]},publication_blockers:['Vérifier chaque point avant publication']};
  const imp=vi.spyOn(reviewApi,'importRecording').mockResolvedValue(imported),publish=vi.spyOn(reviewApi,'publish');
  render(<ProjectReviewsPanel {...props()}/>);await open();fireEvent.click(screen.getByRole('button',{name:'Choisir une réunion validée'}));
  const picker=screen.getByRole('region',{name:'Importer une réunion dans la revue'});fireEvent.click(await within(picker).findByRole('button',{name:'Suivant'}));
  await waitFor(()=>expect(reviewApi.recordings).toHaveBeenLastCalledWith('p1',25,expect.any(AbortSignal)));
  fireEvent.click(await within(picker).findByRole('button',{name:'2026-10-10 · Lancement · transcription 3'}));
  await within(picker).findByText('Alice · 12–18 s');fireEvent.click(within(picker).getByRole('button',{name:'Importer les propositions à vérifier'}));
  await screen.findByText('Propositions importées : relire chaque point et sa citation.');expect(imp).toHaveBeenCalledWith('p1',row,source);expect(publish).not.toHaveBeenCalled();
  const point=within(screen.getByRole('article',{name:'Décisions · Point 1'}));expect((point.getByLabelText('Point relu et vérifié') as HTMLInputElement).checked).toBe(false);
  expect(point.getByText('Essai le 20')).toBeTruthy();expect(point.getByText(/Transcription conservée : Essai le 20 puis qualification/)).toBeTruthy();
});
it('refuse l’import si la transcription a changé après la sélection',async()=>{
  vi.mocked(meetingAudio.get).mockResolvedValue({...recording,revision:4});render(<ProjectReviewsPanel {...props()}/>);await open();
  fireEvent.click(screen.getByRole('button',{name:'Choisir une réunion validée'}));fireEvent.click(await screen.findByRole('button',{name:'2026-10-10 · Lancement · transcription 3'}));
  await screen.findByText(/La transcription a changé/);expect((screen.getByRole('button',{name:'Importer les propositions à vérifier'}) as HTMLButtonElement).disabled).toBe(true);
});
it('affiche le contenu avant et après d’un événement borné à cette revue',async()=>{
  render(<ProjectReviewsPanel {...props()}/>);await open();fireEvent.click(screen.getByRole('button',{name:'Consulter l’historique'}));
  fireEvent.click(await screen.findByRole('button',{name:'Voir l’enregistrement 7'}));await screen.findByText('Ancienne note');
  expect(reviewApi.event).toHaveBeenCalledWith('p1','r1','e1',expect.any(AbortSignal));expect(screen.getAllByText('Composants disponibles · Relu')).toHaveLength(2);
});
it('prépare le téléchargement vérifié et permet une nouvelle tentative après erreur',async()=>{
  vi.mocked(reviewApi.read).mockResolvedValue(published);const pdf=vi.spyOn(reviewApi,'pdf').mockRejectedValueOnce(new Error('PDF indisponible')).mockResolvedValue(new Blob(['%PDF-']));
  const create=vi.spyOn(URL,'createObjectURL').mockReturnValue('blob:rlp'),revoke=vi.spyOn(URL,'revokeObjectURL').mockImplementation(()=>{});
  const view=render(<ProjectReviewsPanel {...props()}/>);await open();fireEvent.click(screen.getByRole('button',{name:'Préparer le PDF publié'}));await screen.findByText('PDF indisponible');
  fireEvent.click(screen.getByRole('button',{name:'Préparer le PDF publié'}));const link=await screen.findByRole('link',{name:'Enregistrer RLP-revision-1.pdf'});expect(link.getAttribute('href')).toBe('blob:rlp');
  expect(pdf).toHaveBeenCalledTimes(2);expect(create).toHaveBeenCalledOnce();view.unmount();expect(revoke).toHaveBeenCalledWith('blob:rlp');
});
it('reprend une lecture en erreur, conserve la liste et ignore une réponse tardive de l’ancien projet',async()=>{
  vi.mocked(reviewApi.read).mockRejectedValueOnce(new Error('Lecture interrompue')).mockResolvedValue(row);
  const p=props(),view=render(<ProjectReviewsPanel {...p}/>);fireEvent.click(await screen.findByRole('button',{name:/RLP · Révision 1/}));
  await screen.findByText('Lecture interrompue');fireEvent.click(screen.getByRole('button',{name:'Réessayer'}));await screen.findByRole('form',{name:'Fiche RLP révision 1'});
  let resolve!:(value:typeof list)=>void;vi.mocked(reviewApi.list).mockReturnValueOnce(new Promise(done=>{resolve=done;}));
  view.rerender(<ProjectReviewsPanel {...p} active={false}/>);view.rerender(<ProjectReviewsPanel {...p} active/>);
  vi.mocked(reviewApi.list).mockResolvedValue({...list,items:[],total:0});view.rerender(<ProjectReviewsPanel projectId="p2" onSaved={p.onSaved}/>);
  await screen.findByRole('button',{name:'Créer la revue de lancement'});resolve(list);await waitFor(()=>expect(screen.queryByRole('form',{name:'Fiche RLP révision 1'})).toBeNull());
});
it('ajoute un participant externe et n’envoie aucune signature électronique implicite',async()=>{
  const user=userEvent.setup();render(<ProjectReviewsPanel {...props()}/>);await open();fireEvent.click(screen.getByText('Ajouter un participant externe'));
  await user.type(screen.getByLabelText('Nom du participant externe'),'Bob Client');fireEvent.change(screen.getByLabelText('Fonction du participant externe'),{target:{value:'Qualité'}});
  fireEvent.click(screen.getByRole('button',{name:'Ajouter le participant externe'}));expect(screen.getByText('Bob Client')).toBeTruthy();
  const save=vi.spyOn(reviewApi,'save').mockImplementation(async(_pid,_row,value)=>({...row,content:value}));fireEvent.click(screen.getByRole('button',{name:'Enregistrer le brouillon'}));
  await waitFor(()=>expect(save).toHaveBeenCalledWith('p1',row,expect.objectContaining({participants:expect.arrayContaining([{person_id:null,name:'Bob Client',function:'Qualité',signature_required:true}])})));
});
