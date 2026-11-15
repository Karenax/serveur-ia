import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { DocumentBatchPanel } from './DocumentBatchPanel';
import { documentApi, type DocumentChoice, type DocumentPreview, type DocumentTemplate } from '../lib/projectDocuments';
import { documentJobApi, type DocumentJob, type DocumentJobs, type BatchCommand } from '../lib/projectDocumentJobs';
import { publicationApi, type PublicationRecord, type PublicationPreview } from '../lib/projectDocumentPublications';

const templates:DocumentTemplate[]=[{id:'ce_request',label:'Demande CE',format:'DOCX',fields:[],cells:[],bookmarks:[],sheet_name:null},
  {id:'user_manual',label:'Notice',format:'DOCM',fields:[],cells:[],bookmarks:[],sheet_name:null}];
const choice:DocumentChoice={document_id:'ce_request',link_id:'l1',relative_path:'CE.docx',overrides:{description:'LED 2026'}};
const preview={document_id:'ce_request',can_prepare:true,can_prepare_copy:true,source:{project_id:'p1',link_id:'l1',relative_path:'CE.docx',filename:'CE.docx'},
  source_sha256:'a'.repeat(64),link_sha256:'b'.repeat(64),values_sha256:'c'.repeat(64),field_values:{identity_revision:2,planning_revision:4},output_filename:'Copie CE.docx'} as DocumentPreview;
const job:DocumentJob={id:'j1',project_id:'p1',actor_id:'a1',status:'failed',revision:7,total:2,processed:2,progress:1,cancel_requested:false,
  execution_blocked:false,can_cancel:false,can_retry:true,created_at:'2026-10-07T10:00:00Z',updated_at:'2026-10-07T10:00:00Z',items:[
    {id:'i1',document_id:'ce_request',position:0,status:'succeeded',last_attempt_id:'a1',artifact_id:'copy1',error:''},
    {id:'i2',document_id:'user_manual',position:1,status:'failed',last_attempt_id:'a2',artifact_id:null,error:'Source momentanément inaccessible'}]};
const jobs:DocumentJobs={available:true,worker:{state:'ready',enabled:true,running:true,can_submit:true,error:''},items:[job],total:1,offset:0,limit:20};
const base={projectId:'p1',active:true,canEdit:true,disabled:false,choice,preview,reviewed:true,templates,onBusy:vi.fn()};
beforeEach(()=>{
  vi.spyOn(documentApi,'draft').mockResolvedValue({available:true,revision:3,version_id:'d3',link_id:'l1',relative_path:'ancienne.docx',overrides:{},selected_link:null,warnings:[]});
  vi.spyOn(documentJobApi,'list').mockResolvedValue(structuredClone(jobs));vi.spyOn(documentJobApi,'detail').mockResolvedValue(structuredClone(job));
  vi.spyOn(documentJobApi,'submit').mockResolvedValue({...job,status:'queued',revision:1,processed:0});
  vi.spyOn(documentJobApi,'cancel').mockResolvedValue({...job,cancel_requested:true,revision:8});
  vi.spyOn(documentJobApi,'retry').mockResolvedValue({...job,status:'queued',revision:8,processed:1,can_retry:false});
  vi.spyOn(documentJobApi,'events').mockResolvedValue({items:[{id:'e1',revision:7,kind:'item_failed',actor_id:'a1',detail:{},created_at:job.created_at}],total:21,limit:20,offset:0});
  vi.spyOn(documentJobApi,'attempts').mockResolvedValue({items:[{id:'a2',item_id:'i2',number:2,actor_id:'a1',created_at:job.created_at,finished_at:job.updated_at,outcome:'failed',artifact_id:null,error:'Fichier absent'}],total:1,limit:20,offset:0});
  vi.spyOn(documentJobApi,'download').mockResolvedValue({url:'/api/v1/projects/p1/documents/artifacts/copy1',filename:'Copie CE.docx',sha256:'d'.repeat(64)});
  vi.spyOn(URL,'createObjectURL').mockReturnValue('blob:verified');vi.spyOn(URL,'revokeObjectURL').mockImplementation(()=>{});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.clearAllMocks();vi.useRealTimers();});
async function add(){fireEvent.click(screen.getByRole('button',{name:'Ajouter la trame vérifiée au lot'}));await screen.findByText('1 / 8 trame(s) sélectionnée(s)');}
async function open(){fireEvent.click(await screen.findByRole('button',{name:/2 \/ 2 fichier.*Échec/}));return screen.findByRole('region',{name:'Suivi du lot sélectionné'});}

it('capture l’aperçu relu et la révision du formulaire sans remplacer les choix saisis',async()=>{
  const value=structuredClone(choice),view=render(<DocumentBatchPanel {...base} choice={value}/>);await add();
  value.overrides.description='Modification ultérieure';view.rerender(<DocumentBatchPanel {...base} choice={value} reviewed={false}/>);
  fireEvent.click(screen.getByRole('button',{name:'Lancer le lot de 1 fichier(s)'}));await waitFor(()=>expect(documentJobApi.submit).toHaveBeenCalledOnce());
  const submitted=vi.mocked(documentJobApi.submit).mock.calls[0][1];expect(submitted.command_id).toMatch(/^[a-z0-9-]+$/i);
  expect(submitted.items).toEqual([{...choice,expected_draft_revision:3,expected_source_sha256:'a'.repeat(64),expected_link_sha256:'b'.repeat(64),
    expected_values_sha256:'c'.repeat(64),expected_identity_revision:2,expected_planning_revision:4}]);
  await screen.findByText('0 / 8 trame(s) sélectionnée(s)');expect(base.onBusy).toHaveBeenLastCalledWith(false);
});
it('remplace explicitement une trame et retire la sélection sans soumission',async()=>{
  const view=render(<DocumentBatchPanel {...base}/>);await add();
  view.rerender(<DocumentBatchPanel {...base} choice={{...choice,overrides:{description:'Correction'}}}/>);
  fireEvent.click(screen.getByRole('button',{name:'Remplacer cette trame dans le lot'}));
  await waitFor(()=>expect(documentApi.draft).toHaveBeenCalledTimes(2));
  fireEvent.click(screen.getByRole('button',{name:'Retirer Demande CE du lot'}));await screen.findByText('0 / 8 trame(s) sélectionnée(s)');
  expect(documentJobApi.submit).not.toHaveBeenCalled();
});
it('conserve exactement la commande après une réponse perdue et après un conflit',async()=>{
  vi.mocked(documentJobApi.submit).mockRejectedValueOnce(new Error('Connexion perdue')).mockRejectedValueOnce(new Error('Révision modifiée'));
  render(<DocumentBatchPanel {...base}/>);await add();fireEvent.click(screen.getByRole('button',{name:'Lancer le lot de 1 fichier(s)'}));
  await screen.findByText('Connexion perdue');expect((screen.getByRole('button',{name:'Retirer Demande CE du lot'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Réessayer la même soumission'}));await screen.findByText('Révision modifiée');
  fireEvent.click(screen.getByRole('button',{name:'Réessayer la même soumission'}));await waitFor(()=>expect(documentJobApi.submit).toHaveBeenCalledTimes(3));
  const calls=vi.mocked(documentJobApi.submit).mock.calls;expect(calls[1][1]).toEqual(calls[0][1]);expect(calls[2][1]).toEqual(calls[0][1]);
  expect(documentApi.draft).toHaveBeenCalledOnce();
});
it('interrompt l’attente de soumission et conserve sa commande incertaine',async()=>{
  let captured!:BatchCommand;vi.mocked(documentJobApi.submit).mockImplementationOnce((_pid,command,signal)=>{
    captured=structuredClone(command);return new Promise((_resolve,reject)=>signal!.addEventListener('abort',()=>reject(new DOMException('Annulée','AbortError'))));});
  render(<DocumentBatchPanel {...base}/>);await add();fireEvent.click(screen.getByRole('button',{name:'Lancer le lot de 1 fichier(s)'}));
  fireEvent.click(await screen.findByRole('button',{name:'Interrompre l’attente'}));await screen.findByText(/Attente interrompue. Le lot peut être enregistré/);
  await waitFor(()=>expect((screen.getByRole('button',{name:'Réessayer la même soumission'}) as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(screen.getByRole('button',{name:'Réessayer la même soumission'}));await waitFor(()=>expect(documentJobApi.submit).toHaveBeenCalledTimes(2));
  expect(vi.mocked(documentJobApi.submit).mock.calls[1][1]).toEqual(captured);expect(documentJobApi.cancel).not.toHaveBeenCalled();
});
it('refuse d’ajouter une sélection différente de l’aperçu ou non relue',async()=>{
  const view=render(<DocumentBatchPanel {...base} reviewed={false}/>);
  expect((screen.getByRole('button',{name:'Ajouter la trame vérifiée au lot'}) as HTMLButtonElement).disabled).toBe(true);
  view.rerender(<DocumentBatchPanel {...base} choice={{...choice,relative_path:'autre.docx'}}/>);
  fireEvent.click(screen.getByRole('button',{name:'Ajouter la trame vérifiée au lot'}));await screen.findByText(/La sélection ne correspond plus/);
  expect(documentApi.draft).not.toHaveBeenCalled();expect(documentJobApi.submit).not.toHaveBeenCalled();
});
it('consulte les copies et le journal avec un rôle lecteur sans proposer de commandes',async()=>{
  render(<DocumentBatchPanel {...base} canEdit={false}/>);const detail=await open();
  expect(screen.queryByRole('button',{name:/Ajouter la trame/})).toBeNull();expect(screen.queryByRole('button',{name:/Reprendre les fichiers/})).toBeNull();
  expect(within(detail).getByRole('progressbar').getAttribute('value')).toBe('2');
  fireEvent.click(within(detail).getByRole('button',{name:'Ouvrir le journal du lot'}));await screen.findByText(/Notice · Essai 2 · Échec/);
  await screen.findByText('Préparation échouée');const journal=detail.querySelector('.document-job-journal')!;
  fireEvent.click(within(journal as HTMLElement).getByRole('button',{name:'Suivant'}));
  await waitFor(()=>expect(documentJobApi.events).toHaveBeenLastCalledWith('p1','j1',20,expect.any(AbortSignal)));
  expect(documentJobApi.submit).not.toHaveBeenCalled();
});
it('affiche les fichiers traités et reprend uniquement avec la révision lue',async()=>{
  render(<DocumentBatchPanel {...base}/>);const detail=await open();
  expect(within(detail).getByRole('heading',{name:'Échec · 2 / 2 fichier(s) traité(s)'})).toBeTruthy();
  fireEvent.click(within(detail).getByRole('button',{name:'Reprendre les fichiers non réussis'}));
  await waitFor(()=>expect(documentJobApi.retry).toHaveBeenCalledWith('p1',expect.objectContaining({id:'j1',revision:7}),expect.any(AbortSignal)));
  await screen.findByText('Reprise demandée ; les copies réussies sont conservées.');
  await waitFor(()=>expect(documentJobApi.detail).toHaveBeenCalledTimes(2));
  expect(screen.getByRole('heading',{name:'En attente · 1 / 2 fichier(s) traité(s)'})).toBeTruthy();
});
it('relit un conflit de reprise sans répéter la commande automatiquement',async()=>{
  vi.mocked(documentJobApi.retry).mockRejectedValue(new Error('Lot modifié'));render(<DocumentBatchPanel {...base}/>);const detail=await open();
  fireEvent.click(within(detail).getByRole('button',{name:'Reprendre les fichiers non réussis'}));await screen.findByText('Lot modifié');
  await waitFor(()=>expect(documentJobApi.detail).toHaveBeenCalledTimes(2));expect(documentJobApi.retry).toHaveBeenCalledOnce();
  expect(screen.getByText('Source momentanément inaccessible')).toBeTruthy();
});
it('permet l’arrêt d’un lot quand le worker est désactivé, sans proposer sa reprise',async()=>{
  vi.mocked(documentJobApi.list).mockResolvedValue({...jobs,worker:{...jobs.worker,state:'disabled',can_submit:false}});
  vi.mocked(documentJobApi.detail).mockResolvedValue({...job,status:'running',processed:1,can_cancel:true});
  render(<DocumentBatchPanel {...base}/>);fireEvent.click(await screen.findByRole('button',{name:/2 \/ 2 fichier.*Échec/}));
  fireEvent.click(await screen.findByRole('button',{name:'Arrêter ce lot'}));await waitFor(()=>expect(documentJobApi.cancel).toHaveBeenCalledOnce());
  expect((screen.getByRole('button',{name:'Reprendre les fichiers non réussis'}) as HTMLButtonElement).disabled).toBe(true);
  expect(vi.mocked(documentJobApi.cancel).mock.calls[0][1].revision).toBe(7);
});
it('garde consultable un historique suspendu sans boutons d’exécution',async()=>{
  vi.mocked(documentJobApi.detail).mockResolvedValue({...job,execution_blocked:true,can_cancel:false,can_retry:false});
  render(<DocumentBatchPanel {...base}/>);await open();await screen.findByText(/Historique importé ou restauré/);
  expect(screen.queryByRole('button',{name:'Arrêter ce lot'})).toBeNull();expect(screen.queryByRole('button',{name:'Reprendre les fichiers non réussis'})).toBeNull();
  expect(screen.getByRole('button',{name:'Préparer le téléchargement · Demande CE'})).toBeTruthy();
});
it('propose la route protégée après vérification sans dépendre d’un fichier temporaire du navigateur',async()=>{
  const view=render(<DocumentBatchPanel {...base}/>);await open();fireEvent.click(screen.getByRole('button',{name:'Préparer le téléchargement · Demande CE'}));
  const link=await screen.findByRole('link',{name:'Télécharger Copie CE.docx'});
  expect(link.getAttribute('href')).toBe('/api/v1/projects/p1/documents/artifacts/copy1');
  expect(link.getAttribute('download')).toBe('Copie CE.docx');expect(URL.createObjectURL).not.toHaveBeenCalled();
  expect(documentJobApi.download).toHaveBeenCalledWith('p1','copy1',expect.any(AbortSignal));view.unmount();
  expect(URL.revokeObjectURL).not.toHaveBeenCalled();
});
it('n’interroge pas un volet masqué et rejette une réponse tardive après masquage',async()=>{
  let resolve!:(value:DocumentJobs)=>void;vi.mocked(documentJobApi.list).mockReturnValue(new Promise(done=>{resolve=done;}));
  const view=render(<DocumentBatchPanel {...base} active={false}/>);expect(documentJobApi.list).not.toHaveBeenCalled();
  view.rerender(<DocumentBatchPanel {...base}/>);await waitFor(()=>expect(documentJobApi.list).toHaveBeenCalledOnce());
  view.rerender(<DocumentBatchPanel {...base} active={false}/>);expect(vi.mocked(documentJobApi.list).mock.calls[0][2]?.aborted).toBe(true);
  await act(async()=>resolve(jobs));expect(screen.queryByRole('button',{name:/2 \/ 2 fichier.*Échec/})).toBeNull();
});
it('limite le lot aux huit trames distinctes et conserve le choix explicite de remplacement',async()=>{
  const ids=['offer_lt_simple','tdao','tdsp','manufacturing_specification','user_manual','ce_request','customer_satisfaction_product','customer_satisfaction_fixed_price'] as const;
  const all=ids.map(id=>({...templates[0],id,label:id})),view=render(<DocumentBatchPanel {...base} templates={all}/>);
  for(const [index,id] of ids.entries()){
    view.rerender(<DocumentBatchPanel {...base} templates={all} choice={{...choice,document_id:id}} preview={{...preview,document_id:id}}/>);
    fireEvent.click(screen.getByRole('button',{name:'Ajouter la trame vérifiée au lot'}));await screen.findByText(`${index+1} / 8 trame(s) sélectionnée(s)`);
  }
  expect((screen.getByRole('button',{name:'Remplacer cette trame dans le lot'}) as HTMLButtonElement).disabled).toBe(false);
  fireEvent.click(screen.getByRole('button',{name:'Lancer le lot de 8 fichier(s)'}));await waitFor(()=>expect(documentJobApi.submit).toHaveBeenCalledOnce());
  expect(vi.mocked(documentJobApi.submit).mock.calls[0][1].items.map(item=>item.document_id)).toEqual(ids);
});
it('garde les copies indisponibles hors de l’interface si le téléchargement est refusé',async()=>{
  vi.mocked(documentJobApi.download).mockRejectedValue(new Error('Empreinte incorrecte'));
  render(<DocumentBatchPanel {...base}/>);await open();fireEvent.click(screen.getByRole('button',{name:'Préparer le téléchargement · Demande CE'}));
  await screen.findByText('Empreinte incorrecte');expect(URL.createObjectURL).not.toHaveBeenCalled();expect(screen.queryByRole('link',{name:/Télécharger/})).toBeNull();
});
it('interrompt la capture et refuse de remplir le lot depuis une réponse tardive',async()=>{
  let resolve!:(value:Awaited<ReturnType<typeof documentApi.draft>>)=>void;
  vi.mocked(documentApi.draft).mockReturnValue(new Promise(done=>{resolve=done;}));
  const view=render(<DocumentBatchPanel {...base}/>);fireEvent.click(screen.getByRole('button',{name:'Ajouter la trame vérifiée au lot'}));
  expect((screen.getByRole('button',{name:'Lancer le lot de 0 fichier(s)'}) as HTMLButtonElement).disabled).toBe(true);
  view.rerender(<DocumentBatchPanel {...base} active={false}/>);expect(vi.mocked(documentApi.draft).mock.calls[0][2]?.aborted).toBe(true);
  await act(async()=>resolve({available:true,revision:6,version_id:'d6',link_id:'l1',relative_path:'CE.docx',overrides:{},selected_link:null,warnings:[]}));
  expect(screen.getByText('0 / 8 trame(s) sélectionnée(s)')).toBeTruthy();expect(base.onBusy).toHaveBeenLastCalledWith(false);
});
it('actualise les fichiers en cours toutes les deux secondes puis arrête la lecture du volet masqué',async()=>{
  vi.useFakeTimers();vi.mocked(documentJobApi.list).mockResolvedValue({...jobs,items:[{...job,status:'running',processed:1}]});
  const view=render(<DocumentBatchPanel {...base}/>);await act(async()=>{});expect(documentJobApi.list).toHaveBeenCalledOnce();
  await act(async()=>vi.advanceTimersByTimeAsync(2000));expect(documentJobApi.list).toHaveBeenCalledTimes(2);
  view.rerender(<DocumentBatchPanel {...base} active={false}/>);await act(async()=>vi.advanceTimersByTimeAsync(20_000));
  expect(documentJobApi.list).toHaveBeenCalledTimes(2);expect(vi.getTimerCount()).toBe(0);
});
it('ouvre la publication de la bonne copie et bloque les commandes du lot pendant son enregistrement',async()=>{
  vi.spyOn(documentApi,'workspace').mockResolvedValue({links:{items:[{id:'l1',code:'out',label:'Sortie',path:'D:/Fictif',order:0}],total:1,offset:0,limit:100}} as Awaited<ReturnType<typeof documentApi.workspace>>);
  vi.spyOn(publicationApi,'list').mockResolvedValue({project_id:'p1',job_id:'j1',job_revision:7,execution_blocked:false,items:[],total:0,offset:0,limit:20});
  vi.spyOn(publicationApi,'preview').mockResolvedValue({project_id:'p1',job_id:'j1',artifact_id:'copy1',job_revision:7,filename:'CE.docx',destination:'D:/Fictif/CE.docx',
    directory:'D:/Fictif',directory_identity:'id',occupied:false,existing_receipt:null,link_id:'l1',relative_directory:'',replace_existing:false,version:2,
    can_publish:true,blockers:[],publication_command_available:true,preview_sha256:'f'.repeat(64)} satisfies PublicationPreview);
  let finish!:(value:PublicationRecord)=>void;vi.spyOn(publicationApi,'publish').mockImplementation(()=>new Promise(resolve=>{finish=resolve;}));
  render(<DocumentBatchPanel {...base}/>);await open();expect(publicationApi.list).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Publier ou consulter les reçus · Demande CE'}));
  fireEvent.change(await screen.findByRole('combobox',{name:'Lien de destination'}),{target:{value:'l1'}});
  fireEvent.click(screen.getByRole('button',{name:'Vérifier la destination'}));await screen.findByText('CE.docx');
  fireEvent.click(screen.getByRole('checkbox',{name:'J’ai relu la destination'}));fireEvent.click(screen.getByRole('button',{name:'Publier la copie'}));
  await waitFor(()=>expect(publicationApi.publish).toHaveBeenCalledOnce());
  expect((screen.getByRole('button',{name:'Reprendre les fichiers non réussis'}) as HTMLButtonElement).disabled).toBe(true);
  expect(vi.mocked(publicationApi.publish).mock.calls[0].slice(0,3)).toEqual(['p1','j1','copy1']);
  const command=vi.mocked(publicationApi.publish).mock.calls[0][3];
  await act(async()=>finish({project_id:'p1',job_id:'j1',artifact_id:'copy1',command_id:command.command_id,command,state:'succeeded'} as PublicationRecord));
  await waitFor(()=>expect(base.onBusy).toHaveBeenLastCalledWith(false));localStorage.clear();
});
