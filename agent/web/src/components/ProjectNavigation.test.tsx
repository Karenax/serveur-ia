import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ProjectWindow } from '../App';
import { api, type CdcReview, type PortfolioRow, type ProjectDetail } from '../lib/api';
import { deliverableApi, type DeliverablePage, type DeliverableRow } from '../lib/projectDeliverables';
import { planningApi } from '../lib/projectPlanning';
import { identityApi, type ProjectIdentity } from '../lib/projectIdentity';

vi.mock('./ProjectFolder',()=>({ProjectFolder:()=>null}));
vi.mock('./ProjectCockpit',()=>({ProjectCockpit:({onOpenDeliverable}:{onOpenDeliverable:(value:unknown)=>void})=><section aria-label="Résumé de test"><button onClick={()=>onOpenDeliverable({deliverableId:'d1',checkId:'',milestoneId:'m1',milestoneTitle:'FAT',version:null,origin:'cockpit'})}>Ouvrir le document du résumé</button></section>}));
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
afterEach(()=>{cleanup();vi.restoreAllMocks();});

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
    render(<ProjectWindow {...props} initialTab="pilotage" sidebarNavigation />);
    fireEvent.click(await screen.findByText('Options du projet'));
    fireEvent.click(screen.getByRole('button', { name: 'Sauvegarder le projet' }));
    expect((await screen.findByRole('alert')).textContent).toBe('La sauvegarde du projet a échoué.');
    expect(downloads).toEqual([]);

    fireEvent.click(screen.getByRole('button', { name: 'Réessayer la sauvegarde' }));
    await waitFor(() => expect(downloads).toEqual(['minipilot-AFF-01.json']));
    expect(screen.queryByRole('alert')).toBeNull();
    expect(exportProject.mock.calls).toEqual([['p1'], ['p1']]);
    expect(createObjectURL).toHaveBeenCalledOnce();
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:archive');
  } finally {
    vi.unstubAllGlobals();
  }
});

it('masque seulement la grande navigation dans le projet à menu latéral',async()=>{
  const view=render(<ProjectWindow {...props} initialTab="pilotage" sidebarNavigation/>);
  await screen.findByRole('region',{name:'Résumé de test'});
  expect(screen.queryByRole('navigation',{name:'Sous-modules du projet'})).toBeNull();
  view.rerender(<ProjectWindow {...props} initialTab="pilotage"/>);
  expect(within(screen.getByRole('navigation',{name:'Sous-modules du projet'})).getAllByRole('button')).toHaveLength(7);
});

it('conserve une création de document entre Notes et À remettre pendant le rechargement',async()=>{
  render(<ProjectWindow {...props} initialTab="documents" sidebarNavigation/>);
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
  fireEvent.click(within(screen.getByRole('navigation',{name:'Sous-modules du projet'})).getByRole('button',{name:'Planning'}));
  expect(change).toHaveBeenCalledWith('planification');
  expect(screen.getByRole('tab',{name:'À remettre'}).getAttribute('aria-selected')).toBe('true');
  expect((screen.getByLabelText('Intitulé du livrable') as HTMLInputElement).value).toBe('Brouillon conservé');
  expect(screen.queryByRole('region',{name:'Échéances de test'})).toBeNull();
});

it('conserve les choix du catalogue en revenant de Notes pendant une lecture en cours',async()=>{
  vi.spyOn(identityApi,'read').mockResolvedValue({project_id:'p1',typology_id:null,references:{}} as ProjectIdentity);
  vi.spyOn(deliverableApi,'types').mockResolvedValue({items:[],total:0,offset:0,limit:25,can_manage:true});
  render(<ProjectWindow {...props} initialTab="documents" sidebarNavigation/>);
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
  fireEvent.click(await screen.findByRole('button',{name:'Ouvrir le document du résumé'}));
  expect(change).toHaveBeenCalledWith('documents');expect(deliverableApi.detail).not.toHaveBeenCalled();
  view.rerender(<ProjectWindow {...props} initialTab="documents" onTabChange={change}/>);
  await screen.findByRole('button',{name:'Consulter · Notice'});
  expect(screen.queryByRole('region',{name:'Livrable ouvert depuis le cockpit'})).toBeNull();
  expect(deliverableApi.detail).not.toHaveBeenCalled();
});

it('ouvre le même panneau Documents depuis le résumé et un contrôle de jalon',async()=>{
  const view=render(<ProjectWindow {...props} initialTab="pilotage"/>);
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
  render(<ProjectWindow {...props} initialTab="planification" sidebarNavigation/>);
  const tabs=await screen.findByRole('tablist',{name:'Planification'});
  expect(within(tabs).getAllByRole('tab').map(button=>button.textContent)).toEqual(['Échéances 0','Tâches 0']);
  fireEvent.click(screen.getByText('Outils du planning'));fireEvent.click(screen.getByRole('button',{name:'Planning de référence et écarts'}));
  expect(await screen.findByText('Comparaison du planning')).toBeTruthy();
  expect(screen.getByText('Outils du planning').closest('details')?.open).toBe(false);
});
