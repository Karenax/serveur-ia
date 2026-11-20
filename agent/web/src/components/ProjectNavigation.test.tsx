import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ProjectWindow } from '../App';
import { api, type CdcReview, type PortfolioRow, type ProjectDetail } from '../lib/api';
import { deliverableApi, type DeliverablePage, type DeliverableRow } from '../lib/projectDeliverables';
import { planningApi } from '../lib/projectPlanning';
import { identityApi, type ProjectIdentity } from '../lib/projectIdentity';
import { meetingAudio } from '../lib/meetingAudio';
import {ProjectAudioDrafts} from '../lib/projectAudioDrafts';
import { reviewApi } from '../lib/projectReviews';

vi.mock('./ProjectFolder',()=>({ProjectFolder:()=>null}));
vi.mock('./ProjectCockpit',()=>({ProjectCockpit:({onOpenDeliverable}:{onOpenDeliverable:(value:unknown)=>void})=><section aria-label="Résumé de test"><input aria-label="Recherche fictive" defaultValue=""/><select aria-label="Filtre fictif" defaultValue="all"><option value="all">Tout</option><option value="tasks">Tâches</option></select><button onClick={()=>onOpenDeliverable({deliverableId:'d1',checkId:'',milestoneId:'m1',milestoneTitle:'FAT',version:null,origin:'cockpit'})}>Ouvrir le document du résumé</button></section>}));
vi.mock('./ProjectIdentityPanel',()=>({ProjectIdentityPanel:()=> <p>Fiche et équipe chargée</p>}));
vi.mock('./ProjectNotesPanel',()=>({ProjectNotesPanel:()=> <p>Notes du projet</p>}));
vi.mock('./PlanningMilestonesPanel',()=>({PlanningMilestonesPanel:({onOpenDeliverable}:{onOpenDeliverable:(value:unknown)=>void})=><section aria-label="Échéances de test"><button onClick={()=>onOpenDeliverable({deliverableId:'d1',checkId:'c1',milestoneId:'m1',milestoneTitle:'FAT',version:null})}>Ouvrir le contrôle du jalon</button></section>}));
vi.mock('./PlanningTasksPanel',async importOriginal=>({...await importOriginal<object>(),PlanningTasksPanel:()=> <p>Tâches du projet</p>}));
vi.mock('./PlanningBaselinesPanel',()=>({PlanningBaselinesPanel:()=> <p>Comparaison du planning</p>}));
vi.mock('./PlanningTemplatesPanel',()=>({PlanningTemplatesPanel:()=> <p>Modèles du planning</p>}));
vi.mock('./PlanningHistoryPanel',()=>({PlanningHistoryPanel:()=> <p>Historique du planning</p>}));

const row={id:'p1',code:'AFF-01',title:'Affaire de test',status:'active',client_name:'Client test'} as PortfolioRow;
const project={id:'p1',tasks:[],milestones:[],deliverables:[],planning_revision:7} as unknown as ProjectDetail;
const document:DeliverableRow={id:'d1',project_id:'p1',title:'Notice',legacy_status:'todo',active:true,document_status:'draft',responsible_id:null,verifier_id:null,type_version_id:null,category:'custom',type:null,
  progress:{completed:0,total:0,percentage:0,state:'not_applicable'},transverse_progress:{completed:0,total:0,percentage:0,state:'not_applicable'},latest_version:null,milestone_ids:[]};
const page:DeliverablePage={items:[document],total:1,offset:0,limit:25,revision:7,can_edit:true};
const props={projectId:'p1',row,reloadRows:vi.fn(async()=>{}),back:vi.fn()};

beforeEach(()=>{
  vi.spyOn(api,'detail').mockResolvedValue(project);vi.spyOn(api,'cdcItems').mockResolvedValue([]);vi.spyOn(api,'cdcSources').mockResolvedValue([]);vi.spyOn(api,'meetings').mockResolvedValue([]);vi.spyOn(api,'cdcJobs').mockResolvedValue([]);vi.spyOn(api,'aiStatus').mockResolvedValue({reachable:false,detail:'Test'});
  vi.spyOn(api,'cdcReview').mockResolvedValue({reviewed:0,total:0} as CdcReview);
  vi.spyOn(deliverableApi,'list').mockResolvedValue(page);
  vi.spyOn(deliverableApi,'detail').mockResolvedValue({...document,revision:7,comment:'',latest_version_id:null,can_edit:true,can_verify:false,checklist:[],validation_blockers:[]});
  vi.spyOn(deliverableApi,'checklist').mockResolvedValue({items:[],total:0,offset:0,limit:25,revision:7});
  vi.spyOn(identityApi,'people').mockResolvedValue({items:[],total:0,offset:0,limit:50});
  vi.spyOn(planningApi,'milestones').mockResolvedValue({items:[],total:0,offset:0,limit:50,revision:7});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();});

it('ne déclare libérable que la vue d’ensemble sans interaction',async()=>{
  let check!:()=>boolean;
  const register=vi.fn((_id:string,probe:()=>boolean)=>{check=probe;return()=>{};});
  render(<ProjectWindow {...props} initialTab="pilotage" registerCache={register}/>);
  await screen.findByText('Aucune tâche planifiée à traiter.');
  expect(register).toHaveBeenCalledOnce();expect(check()).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'← Tous les projets'}));
  expect(check()).toBe(true);
  fireEvent.click(screen.getByText('Options du projet'));
  expect(check()).toBe(false);
});

it('refuse la libération si un navigateur a modifié un champ sans événement',async()=>{
  let check!:()=>boolean;
  const register=vi.fn((_id:string,probe:()=>boolean)=>{check=probe;return()=>{};});
  const {container}=render(<ProjectWindow {...props} initialTab="pilotage" registerCache={register}/>);
  await screen.findByText('Aucune tâche planifiée à traiter.');expect(check()).toBe(true);
  const input=container.querySelector<HTMLInputElement>('input[aria-label="Recherche fictive"]')!;
  input.value='Saisie automatique';expect(check()).toBe(false);input.value='';expect(check()).toBe(true);
  const select=container.querySelector<HTMLSelectElement>('select[aria-label="Filtre fictif"]')!;
  select.value='tasks';expect(check()).toBe(false);
});

it('autorise la libération pendant le premier chargement sans formulaire',()=>{
  vi.mocked(api.detail).mockReturnValueOnce(new Promise(()=>{}));
  let check!:()=>boolean;
  const register=vi.fn((_id:string,probe:()=>boolean)=>{check=probe;return()=>{};});
  render(<ProjectWindow {...props} initialTab="pilotage" registerCache={register}/>);
  expect(screen.getByText('Chargement du projet…')).toBeTruthy();expect(check()).toBe(true);
});

it('protège une fiche ouverte directement sur les réunions',async()=>{
  let check!:()=>boolean;
  const register=vi.fn((_id:string,probe:()=>boolean)=>{check=probe;return()=>{};});
  render(<ProjectWindow {...props} initialTab="reviews" registerCache={register}/>);
  await screen.findByRole('tab',{name:'Comptes rendus et audio'});
  expect(check()).toBe(false);
});

it('garde une fiche protégée après avoir quitté une rubrique métier',async()=>{
  let check!:()=>boolean;
  const register=vi.fn((_id:string,probe:()=>boolean)=>{check=probe;return()=>{};});
  const view=render(<ProjectWindow {...props} initialTab="pilotage" registerCache={register}/>);
  await screen.findByText('Aucune tâche planifiée à traiter.');expect(check()).toBe(true);
  view.rerender(<ProjectWindow {...props} initialTab="reviews" registerCache={register}/>);
  await screen.findByRole('tab',{name:'Comptes rendus et audio'});expect(check()).toBe(false);
  view.rerender(<ProjectWindow {...props} initialTab="pilotage" registerCache={register}/>);
  expect(check()).toBe(false);
});

it('conserve le formulaire si le projet disparaît temporairement du portefeuille',async()=>{
  const view=render(<ProjectWindow {...props} initialTab="pilotage" active/>);
  fireEvent.click(await screen.findByText('Options du projet'));
  fireEvent.click(screen.getByRole('button',{name:'Modifier le projet'}));
  const title=screen.getByRole('textbox',{name:'Titre'}) as HTMLInputElement;
  fireEvent.change(title,{target:{value:'Modification à conserver'}});
  view.rerender(<ProjectWindow {...props} row={undefined} initialTab="pilotage" active/>);
  expect(screen.getByText('Projet introuvable')).toBeTruthy();
  expect(screen.queryByRole('textbox',{name:'Titre'})).toBeNull();
  expect(title.closest('[inert]')?.hasAttribute('hidden')).toBe(true);
  expect(title.isConnected).toBe(true);expect(title.value).toBe('Modification à conserver');
  view.rerender(<ProjectWindow {...props} initialTab="pilotage" active/>);
  expect(screen.getByRole('textbox',{name:'Titre'})).toBe(title);
  expect(title.value).toBe('Modification à conserver');
  await waitFor(()=>expect(api.detail).toHaveBeenCalledTimes(2));
});

it.each(['absente','autre projet','tâches invalides','tâche incomplète','liste CDC invalide','réunion invalide'])('préserve le brouillon si la réponse est %s',async failure=>{
  const view=render(<ProjectWindow {...props} initialTab="pilotage" active/>);
  fireEvent.click(await screen.findByText('Options du projet'));
  fireEvent.click(screen.getByRole('button',{name:'Modifier le projet'}));
  const title=screen.getByRole('textbox',{name:'Titre'}) as HTMLInputElement;
  fireEvent.change(title,{target:{value:'Texte intact'}});
  if(failure==='absente')vi.mocked(api.detail).mockResolvedValueOnce(null as unknown as ProjectDetail);
  if(failure==='autre projet')vi.mocked(api.detail).mockResolvedValueOnce({...project,id:'autre'});
  if(failure==='tâches invalides')vi.mocked(api.detail).mockResolvedValueOnce({...project,tasks:null} as unknown as ProjectDetail);
  if(failure==='tâche incomplète')vi.mocked(api.detail).mockResolvedValueOnce({...project,tasks:[{id:'t',title:'Tâche',status:'todo',due_date:123}]} as unknown as ProjectDetail);
  if(failure==='liste CDC invalide')vi.mocked(api.cdcItems).mockResolvedValueOnce(null as unknown as Awaited<ReturnType<typeof api.cdcItems>>);
  if(failure==='réunion invalide')vi.mocked(api.meetings).mockResolvedValueOnce([null] as unknown as Awaited<ReturnType<typeof api.meetings>>);
  view.rerender(<ProjectWindow {...props} initialTab="pilotage" active={false}/>);
  view.rerender(<ProjectWindow {...props} initialTab="pilotage" active/>);
  expect(await screen.findByText('Réponse du projet invalide. Les données et saisies affichées sont conservées.')).toBeTruthy();
  expect(screen.getByRole('textbox',{name:'Titre'})).toBe(title);expect(title.value).toBe('Texte intact');
  fireEvent.click(screen.getByRole('button',{name:'Réessayer'}));
  await waitFor(()=>expect(screen.queryByText('Réponse du projet invalide. Les données et saisies affichées sont conservées.')).toBeNull());
  expect(title.value).toBe('Texte intact');
});

it('ne coupe pas le microphone si le projet disparaît temporairement du portefeuille',async()=>{
  const {webcrypto} = await vi.importActual<{webcrypto:Crypto}>('node:crypto');
  vi.stubGlobal('crypto',webcrypto);
  vi.spyOn(identityApi,'session').mockResolvedValue({operator:{id:'user1',role:'owner',can_edit:true,can_administer:true,project_ids:null}});
  vi.spyOn(ProjectAudioDrafts.prototype,'ready').mockResolvedValue();
  vi.spyOn(ProjectAudioDrafts.prototype,'list').mockResolvedValue([]);
  vi.spyOn(ProjectAudioDrafts.prototype,'create').mockReturnValue('capture-test');
  vi.spyOn(reviewApi,'list').mockResolvedValue({items:[],total:0,offset:0,limit:20,revision:1,can_edit:true});
  vi.spyOn(meetingAudio,'list').mockResolvedValue([]);
  vi.spyOn(meetingAudio,'status').mockResolvedValue({ready:true,model:'fictif',device:'cpu',detail:'Simulation',max_upload_mb:50,max_duration_minutes:120});
  const stop=vi.fn(),release=vi.fn();
  class FakeRecorder {
    state='inactive';mimeType='audio/webm';onstop:(()=>void)|null=null;ondataavailable:((event:{data:Blob})=>void)|null=null;onerror:(()=>void)|null=null;
    start(){this.state='recording';}
    stop(){this.state='inactive';stop();this.onstop?.();}
  }
  const fakeNavigator=Object.create(navigator);
  Object.defineProperty(fakeNavigator,'userAgent',{value:'Mozilla/5.0 Windows Chrome'});
  Object.defineProperty(fakeNavigator,'mediaDevices',{value:{getUserMedia:vi.fn().mockResolvedValue({getTracks:()=>[{stop:release}]})}});
  vi.stubGlobal('navigator',fakeNavigator);vi.stubGlobal('MediaRecorder',FakeRecorder);
  const view=render(<ProjectWindow {...props} initialTab="reviews" active/>);
  fireEvent.click(await screen.findByRole('tab',{name:'Comptes rendus et audio'}));
  fireEvent.click(await screen.findByRole('button',{name:'Enregistrer au microphone'}));
  await screen.findByRole('button',{name:'Arrêter l’enregistrement'});
  view.rerender(<ProjectWindow {...props} row={undefined} initialTab="reviews" active/>);
  expect(screen.getByText('Projet introuvable')).toBeTruthy();expect(stop).not.toHaveBeenCalled();expect(release).not.toHaveBeenCalled();
  view.rerender(<ProjectWindow {...props} initialTab="reviews" active/>);
  expect(screen.getByRole('button',{name:'Arrêter l’enregistrement'})).toBeTruthy();
  expect(stop).not.toHaveBeenCalled();expect(release).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Arrêter l’enregistrement'}));
  expect(stop).toHaveBeenCalledOnce();expect(release).toHaveBeenCalledOnce();
});

it('actualise la fiche au retour sans effacer une modification non enregistrée',async()=>{
  const view=render(<ProjectWindow {...props} initialTab="pilotage" active/>);
  fireEvent.click(await screen.findByText('Options du projet'));
  fireEvent.click(screen.getByRole('button',{name:'Modifier le projet'}));
  fireEvent.change(screen.getByRole('textbox',{name:'Titre'}),{target:{value:'Brouillon à conserver'}});
  expect(api.detail).toHaveBeenCalledTimes(1);
  view.rerender(<ProjectWindow {...props} initialTab="pilotage" active={false}/>);
  vi.mocked(api.detail).mockResolvedValue({...project,tasks:[{id:'t2',title:'Tâche ajoutée ailleurs',status:'todo'}]} as ProjectDetail);
  view.rerender(<ProjectWindow {...props} initialTab="pilotage" active/>);
  expect(await screen.findByText('Tâche ajoutée ailleurs')).toBeTruthy();
  expect((screen.getByRole('textbox',{name:'Titre'}) as HTMLInputElement).value).toBe('Brouillon à conserver');
  expect(api.detail).toHaveBeenCalledTimes(2);
});

it('ne remplace pas la dernière actualisation par une réponse tardive après deux retours',async()=>{
  const view=render(<ProjectWindow {...props} initialTab="pilotage" active/>);
  await screen.findByText('Aucune tâche planifiée à traiter.');
  let resolveOld!:(value:ProjectDetail)=>void;
  vi.mocked(api.detail).mockImplementationOnce(()=>new Promise(done=>{resolveOld=done;}))
    .mockResolvedValueOnce({...project,tasks:[{id:'new',title:'Tâche actuelle',status:'todo'}]} as ProjectDetail);
  view.rerender(<ProjectWindow {...props} initialTab="pilotage" active={false}/>);
  view.rerender(<ProjectWindow {...props} initialTab="pilotage" active/>);
  view.rerender(<ProjectWindow {...props} initialTab="pilotage" active={false}/>);
  view.rerender(<ProjectWindow {...props} initialTab="pilotage" active/>);
  expect(await screen.findByText('Tâche actuelle')).toBeTruthy();
  await act(async()=>resolveOld({...project,tasks:[{id:'old',title:'Tâche périmée',status:'todo'}]} as ProjectDetail));
  expect(screen.getByText('Tâche actuelle')).toBeTruthy();
  expect(screen.queryByText('Tâche périmée')).toBeNull();
});

it('signale l’échec de la sauvegarde du projet et permet de réessayer', async () => {
  const exportProject = vi.spyOn(api, 'exportProject')
    .mockRejectedValueOnce(new Error('Service indisponible'))
    .mockResolvedValueOnce({ project: { code: row.code } });
  const createObjectURL = vi.fn(() => 'blob:archive');
  const revokeObjectURL = vi.fn();
  const BrowserURL = URL;
  vi.stubGlobal('URL', class extends BrowserURL {
    static createObjectURL = createObjectURL;
    static revokeObjectURL = revokeObjectURL;
  });
  const downloads: string[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
    downloads.push(this.download);
  });
  try {
    render(<ProjectWindow {...props} initialTab="pilotage" />);
    fireEvent.click(await screen.findByText('Options du projet'));
    fireEvent.click(screen.getByRole('button', { name: 'Sauvegarder le projet' }));
    expect((await screen.findByRole('alert')).textContent).toBe('La sauvegarde du projet a échoué.');
    expect(downloads).toEqual([]);

    fireEvent.click(screen.getByRole('button', { name: 'Réessayer la sauvegarde' }));
    await waitFor(() => expect(downloads).toEqual(['Kiara-Projet-AFF-01.json']));
    expect(screen.queryByRole('alert')).toBeNull();
    expect(exportProject.mock.calls).toEqual([['p1'], ['p1']]);
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:archive');
  } finally {
    vi.unstubAllGlobals();
  }
});

it('affiche les quatre rubriques de la fiche Kiara', async () => {
  render(<ProjectWindow {...props} initialTab="pilotage"/>);
  const navigation = await screen.findByRole('navigation', { name: 'Rubriques du projet' });
  expect(within(navigation).getAllByRole('button').map(button => button.textContent))
    .toEqual(['Vue d’ensemble', 'Pilotage', 'Documents', 'Réunions']);
  expect(screen.queryByRole('navigation', { name: 'Sous-modules du projet' })).toBeNull();
});

it('conserve une création de document entre Notes et À remettre pendant le rechargement',async()=>{
  render(<ProjectWindow {...props} initialTab="documents"/>);
  fireEvent.click(await screen.findByRole('button',{name:'Nouveau livrable'}));
  fireEvent.change(screen.getByLabelText('Intitulé du livrable'),{target:{value:'Notice à conserver'}});
  fireEvent.click(screen.getByRole('tab',{name:'Notes'}));await screen.findByText('Notes du projet');
  let resolve!:(value:DeliverablePage)=>void;vi.mocked(deliverableApi.list).mockReturnValueOnce(new Promise(done=>{resolve=done;}));
  fireEvent.click(screen.getByRole('tab',{name:'À remettre'}));
  await waitFor(()=>expect(deliverableApi.list).toHaveBeenCalledTimes(2));
  expect((screen.getByLabelText('Intitulé du livrable') as HTMLInputElement).value).toBe('Notice à conserver');
  expect(screen.getAllByRole('region',{name:'Livrables du projet'})).toHaveLength(1);
  resolve({...page,revision:8});await waitFor(()=>expect(screen.queryByText('Chargement des livrables')).toBeNull());
  expect((screen.getByLabelText('Intitulé du livrable') as HTMLInputElement).value).toBe('Notice à conserver');
});

it('garde la rubrique active lorsque le changement de navigation est refusé',async()=>{
  const change=vi.fn(()=>false);render(<ProjectWindow {...props} initialTab="documents" onTabChange={change}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Nouveau livrable'}));
  fireEvent.change(screen.getByLabelText('Intitulé du livrable'),{target:{value:'Brouillon conservé'}});
  fireEvent.click(within(screen.getByRole('navigation',{name:'Rubriques du projet'})).getByRole('button',{name:'Pilotage'}));
  expect(change).toHaveBeenCalledWith('planification');
  expect(screen.getByRole('tab',{name:'À remettre'}).getAttribute('aria-selected')).toBe('true');
  expect((screen.getByLabelText('Intitulé du livrable') as HTMLInputElement).value).toBe('Brouillon conservé');
  expect(screen.queryByRole('region',{name:'Échéances de test'})).toBeNull();
});

it('conserve les choix du catalogue en revenant de Notes pendant une lecture en cours',async()=>{
  vi.spyOn(identityApi,'read').mockResolvedValue({project_id:'p1',typology_id:null,references:{}} as ProjectIdentity);
  vi.spyOn(deliverableApi,'types').mockResolvedValue({items:[],total:0,offset:0,limit:25,can_manage:true});
  render(<ProjectWindow {...props} initialTab="documents"/>);
  fireEvent.click(await screen.findByRole('button',{name:'Ajouter depuis les modèles'}));
  const form=await screen.findByRole('form',{name:'Sélection des livrables'});
  const label='Désélectionner les types absents de mes choix, en conservant leurs données';
  fireEvent.click(screen.getByLabelText(label));
  fireEvent.click(screen.getByRole('tab',{name:'Notes'}));
  let resolve!:(value:DeliverablePage)=>void;vi.mocked(deliverableApi.list).mockReturnValueOnce(new Promise(done=>{resolve=done;}));
  fireEvent.click(screen.getByRole('tab',{name:'À remettre'}));
  await waitFor(()=>expect(deliverableApi.list).toHaveBeenCalledTimes(2));
  expect(screen.getByRole('form',{name:'Sélection des livrables'})).toBe(form);
  expect((screen.getByLabelText(label) as HTMLInputElement).checked).toBe(true);
  resolve(page);
});

it('ne prépare pas une ouverture ciblée lorsque la navigation vers Documents est refusée',async()=>{
  const change=vi.fn(()=>false),view=render(<ProjectWindow {...props} initialTab="pilotage" onTabChange={change}/>);
  fireEvent.click(await screen.findByText('Suivi détaillé du projet'));
  fireEvent.click(await screen.findByRole('button',{name:'Ouvrir le document du résumé'}));
  expect(change).toHaveBeenCalledWith('documents');expect(deliverableApi.detail).not.toHaveBeenCalled();
  view.rerender(<ProjectWindow {...props} initialTab="documents" onTabChange={change}/>);
  await screen.findByRole('button',{name:'Consulter · Notice'});
  expect(screen.queryByRole('region',{name:'Livrable ouvert depuis le cockpit'})).toBeNull();
  expect(deliverableApi.detail).not.toHaveBeenCalled();
});

it('ouvre le même panneau Documents depuis le résumé et un contrôle de jalon',async()=>{
  const view=render(<ProjectWindow {...props} initialTab="pilotage"/>);
  fireEvent.click(await screen.findByText('Suivi détaillé du projet'));
  fireEvent.click(await screen.findByRole('button',{name:'Ouvrir le document du résumé'}));
  await screen.findByRole('region',{name:'Livrable ouvert depuis le cockpit'});
  expect(screen.getByRole('tab',{name:'À remettre'}).getAttribute('aria-selected')).toBe('true');
  view.rerender(<ProjectWindow {...props} initialTab="planification"/>);
  await screen.findByRole('region',{name:'Échéances de test'});
  fireEvent.click(screen.getByRole('button',{name:'Ouvrir le contrôle du jalon'}));
  await screen.findByRole('region',{name:'Contrôle ouvert depuis le jalon'});
  expect(screen.getByRole('button',{name:'Contrôles et validation'}).getAttribute('aria-pressed')).toBe('true');
  expect(window.document.querySelectorAll('.deliverables-panel')).toHaveLength(1);
  expect(deliverableApi.detail).toHaveBeenLastCalledWith('p1','d1',expect.any(AbortSignal));
});

it('conserve les outils de planning sans les présenter comme des onglets quotidiens',async()=>{
  render(<ProjectWindow {...props} initialTab="planification"/>);
  const tabs=await screen.findByRole('tablist',{name:'Planification'});
  expect(within(tabs).getAllByRole('tab').map(button=>button.textContent)).toEqual(['Échéances 0','Tâches 0']);
  fireEvent.click(screen.getByText('Outils du planning'));fireEvent.click(screen.getByRole('button',{name:'Planning de référence et écarts'}));
  expect(await screen.findByText('Comparaison du planning')).toBeTruthy();
  expect(screen.getByText('Outils du planning').closest('details')?.open).toBe(false);
});
