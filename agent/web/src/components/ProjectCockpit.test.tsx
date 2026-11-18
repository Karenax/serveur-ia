import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Detail } from '../App';
import { api, type CdcReview, type PortfolioRow, type ProjectDetail } from '../lib/api';
import { cockpitApi, type CockpitStructure } from '../lib/projectCockpit';
import { planningApi, type PlanningInfo, type PlanningTask } from '../lib/projectPlanning';
import { identityApi } from '../lib/projectIdentity';
import { deliverableApi, type DeliverableDetail } from '../lib/projectDeliverables';
import { ProjectCockpit } from './ProjectCockpit';
import { projectKnowledgeApi } from '../lib/projectKnowledge';

const milestone={id:'m1',title:'FAT',code:'fat',order:3,workflow_status:'open' as const,comment:'',active:true,due_date:'2026-10-15',contractual_date:'2026-10-14',forecast_date:'2026-10-15',actual_date:'',past:false,task_count:607,deliverable_count:32};
const task:PlanningTask={id:'t1',title:'Étude moteur',status:'todo',due_date:'',parent_id:null,milestone_id:'m1',responsible_id:null,template_id:null,template_key:null,priority:'normal',start_date:'',end_date:'',planned_hours:5,design:true,manufacturing:false,comment:'',active:true};
const structure:CockpitStructure={project:{id:'p1',title:'Moteur',code:'TEST-0806',status:'active',client_name:'Recette',start_date:'',planned_end_date:''},can_edit:true,
  current_milestone:milestone,tasks:{total:608,done:101,active:607,open:506,overdue:4,blocked:2},progress:17,
  hours:{initial_hours:800,consumed_hours:210,raf:590,remaining_mode:'budget_balance',overrun_hours:0},
  deliverables_total:32,milestones_total:3,unassigned_tasks:0,unassigned_deliverables:0,items:[milestone],total:1,offset:0,limit:25,revision:7};
const info:PlanningInfo={project_id:'p1',revision:7,can_edit:true,excluded_dates:[],active_template_version_id:null,task_statuses:['todo'],workflow:[{code:'fat',title:'FAT'}]};
const document:DeliverableDetail={id:'d1',project_id:'p1',title:'Plan BE',legacy_status:'todo',active:true,document_status:'draft',responsible_id:null,verifier_id:null,type_version_id:null,
  progress:{completed:0,total:0,percentage:0,state:'not_applicable'},transverse_progress:{completed:0,total:0,percentage:0,state:'not_applicable'},milestone_ids:['m1'],revision:7,comment:'Preuves accessibles',latest_version_id:null,can_edit:true,can_verify:false,checklist:[],validation_blockers:[]};
const defaults=()=>({projectId:'p1',onSaved:vi.fn(),onOpenDeliverable:vi.fn(),onOpenPlanning:vi.fn(),onOpenCdc:vi.fn()});
beforeEach(()=>{
  vi.spyOn(projectKnowledgeApi,'read').mockResolvedValue({enabled:true,status:'waiting_idle',error:null,cursor:0,total_batches:0,next_due:null,retry_after:null,interval_hours:48,stale:false,activity:{active_calls:1,waiting_calls:0,background_active:false},report:{},items:[],total:0,offset:0,limit:20});
  vi.spyOn(cockpitApi,'structure').mockResolvedValue(structure);
  vi.spyOn(cockpitApi,'tasks').mockResolvedValue({items:[task],total:607,offset:0,limit:20,revision:7});
  vi.spyOn(cockpitApi,'documents').mockResolvedValue({items:[{id:'d1',title:'Plan BE',status:'todo',document_status:'draft',milestone_ids:['m1']}],total:32,offset:0,limit:20,revision:7});
  vi.spyOn(cockpitApi,'alerts').mockResolvedValue({items:[],total:0,offset:0,limit:10,revision:7});
  vi.spyOn(planningApi,'info').mockResolvedValue(info);
  vi.spyOn(planningApi,'task').mockResolvedValue({item:task,revision:7,can_edit:true,milestone:{id:'m1',title:'FAT'}});
  vi.spyOn(planningApi,'tasks').mockResolvedValue({items:[task],total:1,offset:0,limit:50,revision:7});
  vi.spyOn(planningApi,'milestones').mockResolvedValue({items:[milestone],total:1,offset:0,limit:50,revision:7});
  vi.spyOn(planningApi,'milestone').mockResolvedValue({item:milestone,revision:7,can_edit:true});
  vi.spyOn(identityApi,'people').mockResolvedValue({items:[],total:0,offset:0,limit:50});
  vi.spyOn(deliverableApi,'detail').mockResolvedValue(document);
  vi.spyOn(deliverableApi,'milestoneGates').mockResolvedValue({items:[],total:0,offset:0,limit:25,milestone_id:'m1',revision:7,can_validate:true,checks_total:0,blocking_total:0});
});
afterEach(()=>{cleanup();vi.useRealTimers();vi.restoreAllMocks();});

it('suspend le suivi du vrai cockpit lorsque la fiche projet est inactive puis le reprend sans perdre la saisie',async()=>{
  vi.useFakeTimers();
  vi.spyOn(api,'cdcReview').mockResolvedValue({reviewed:0,total:0} as CdcReview);
  const detailProps={current:{id:'p1',code:'TEST-0806',title:'Moteur',status:'active',client_name:'Recette'} as PortfolioRow,
    detail:{id:'p1',tasks:[],milestones:[],deliverables:[],planning_revision:7} as unknown as ProjectDetail,
    items:[],sources:[],meetings:[],tab:'pilotage' as const,setTab:vi.fn(),cdcTab:'sources' as const,setCdcTab:vi.fn(),
    analyze:vi.fn(),analyzing:false,analyzeMsg:'',aiStatus:null,jobs:[],jobsError:'',cancelJob:vi.fn(),retryJob:vi.fn(),
    editing:false,setEditing:vi.fn(),back:vi.fn(),refresh:vi.fn(async()=>{})};
  const view=render(<Detail {...detailProps} active/>);
  await act(async()=>{});
  expect(projectKnowledgeApi.read).toHaveBeenCalledTimes(1);
  const signal=vi.mocked(projectKnowledgeApi.read).mock.calls[0][2]!;
  fireEvent.change(screen.getByLabelText('Rechercher dans le projet'),{target:{value:'Recherche à conserver'}});
  view.rerender(<Detail {...detailProps} active={false}/>);
  expect(signal.aborted).toBe(true);
  await act(async()=>{await vi.advanceTimersByTimeAsync(45000);});
  expect(projectKnowledgeApi.read).toHaveBeenCalledTimes(1);
  view.rerender(<Detail {...detailProps} active/>);
  await act(async()=>{});
  expect(projectKnowledgeApi.read).toHaveBeenCalledTimes(2);
  expect((screen.getByLabelText('Rechercher dans le projet') as HTMLInputElement).value).toBe('Recherche à conserver');
});

it('affiche les compteurs complets et charge les listes indépendamment du graphe',async()=>{
  let resolve!:(value:CockpitStructure)=>void;
  vi.mocked(cockpitApi.structure).mockReturnValue(new Promise(value=>{resolve=value;}));
  render(<ProjectCockpit {...defaults()}/>);
  expect(await screen.findByRole('button',{name:/Étude moteur/})).toBeTruthy();
  expect(screen.queryByText('101 / 608 tâches terminées')).toBeNull();
  resolve(structure);expect(await screen.findByText('101 / 608 tâches terminées')).toBeTruthy();
  expect(screen.getByText('607 tâches · 32 livrables')).toBeTruthy();
  expect(within(screen.getByRole('region',{name:'Tâches liées'})).getByText('1–20 sur 607')).toBeTruthy();
});

it('relance seulement la branche en erreur et conserve les autres données',async()=>{
  vi.mocked(cockpitApi.documents).mockRejectedValueOnce(new Error('Réseau indisponible')).mockResolvedValue({items:[],total:0,offset:0,limit:20,revision:7});
  render(<ProjectCockpit {...defaults()}/>);
  await screen.findByText('Réseau indisponible');expect(screen.getByText('101 / 608 tâches terminées')).toBeTruthy();
  fireEvent.click(within(screen.getByRole('region',{name:'Livrables liés'})).getByRole('button',{name:'Réessayer'}));
  expect(await screen.findByText('Aucun livrable dans cette sélection.')).toBeTruthy();
  expect(cockpitApi.structure).toHaveBeenCalledTimes(1);expect(cockpitApi.tasks).toHaveBeenCalledTimes(1);
});

it('sélectionne un jalon au clavier, pagine et propage les filtres au serveur',async()=>{
  const user=userEvent.setup();render(<ProjectCockpit {...defaults()}/>);
  const node=await screen.findByRole('button',{name:'Sélectionner le jalon FAT'});node.focus();await user.keyboard('{Enter}');
  await waitFor(()=>expect(cockpitApi.tasks).toHaveBeenLastCalledWith('p1',expect.objectContaining({milestone_id:'m1',offset:0,limit:20})));
  const tasks=screen.getByRole('region',{name:'Tâches liées'});await within(tasks).findByRole('button',{name:/Étude moteur/});fireEvent.click(within(tasks).getByRole('button',{name:'Suivant'}));
  await waitFor(()=>expect(cockpitApi.tasks).toHaveBeenLastCalledWith('p1',expect.objectContaining({milestone_id:'m1',offset:20})));
  fireEvent.change(screen.getByLabelText('Rechercher dans le projet'),{target:{value:'50% écart'}});
  await waitFor(()=>expect(cockpitApi.structure).toHaveBeenLastCalledWith('p1',expect.objectContaining({search:'50% écart',offset:0})));
  fireEvent.click(screen.getByLabelText('Inclure les jalons passés'));
  await waitFor(()=>expect(cockpitApi.structure).toHaveBeenLastCalledWith('p1',expect.objectContaining({show_past:true})));
});

it('crée une tâche sur le jalon avec la commande commune puis recharge toutes les branches',async()=>{
  const props=defaults(),create=vi.spyOn(planningApi,'createTask').mockResolvedValue({revision:8,task});
  render(<ProjectCockpit {...props}/>);fireEvent.click(await screen.findByRole('button',{name:'Sélectionner le jalon FAT'}));
  fireEvent.click(screen.getByRole('button',{name:'Créer une tâche sur ce jalon'}));
  await screen.findByRole('form',{name:'Nouvelle tâche'});
  expect((screen.getByLabelText('Jalon de rattachement') as HTMLSelectElement).value).toBe('m1');
  fireEvent.change(screen.getByLabelText('Intitulé de la tâche'),{target:{value:'Essai moteur'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la tâche'}));
  await waitFor(()=>expect(create).toHaveBeenCalledWith('p1',7,expect.objectContaining({title:'Essai moteur',milestone_id:'m1'})));
  await waitFor(()=>expect(props.onSaved).toHaveBeenCalledOnce());
  await waitFor(()=>expect(cockpitApi.structure).toHaveBeenCalledTimes(2));
  expect(cockpitApi.alerts).toHaveBeenCalledTimes(2);
});

it('conserve le brouillon lors des actualisations et du changement de vue',async()=>{
  const props=defaults(),patch=vi.spyOn(planningApi,'patchTask').mockResolvedValue({revision:9,task});
  const view=render(<ProjectCockpit {...props} revision={7}/>);
  fireEvent.click(await screen.findByRole('button',{name:/Étude moteur/}));await screen.findByRole('form',{name:'Édition de la tâche'});
  fireEvent.change(screen.getByLabelText('Intitulé de la tâche'),{target:{value:'Ma saisie'}});
  fireEvent.click(screen.getByText('Options d’affichage'));fireEvent.click(screen.getByRole('button',{name:'Actualiser la vue'}));view.rerender(<ProjectCockpit {...props} revision={8} active={false}/>);
  view.rerender(<ProjectCockpit {...props} revision={8} active/>);
  expect((screen.getByLabelText('Intitulé de la tâche') as HTMLInputElement).value).toBe('Ma saisie');
  expect((screen.getByRole('button',{name:'Réinitialiser l’affichage'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la tâche'}));
  await waitFor(()=>expect(patch).toHaveBeenCalledWith('p1','t1',7,{title:'Ma saisie'}));
});

it('ferme un inspecteur puis ouvre le bon élément sans recycler la sélection précédente',async()=>{
  const props=defaults();render(<ProjectCockpit {...props}/>);
  fireEvent.click(await screen.findByRole('button',{name:/Étude moteur/}));await screen.findByRole('form',{name:'Édition de la tâche'});
  fireEvent.click(screen.getByRole('button',{name:'Annuler le brouillon'}));
  fireEvent.click(screen.getByRole('button',{name:'Consulter le livrable Plan BE'}));
  expect(await screen.findByText('Preuves accessibles')).toBeTruthy();expect(screen.queryByRole('form',{name:'Édition de la tâche'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Ouvrir le livrable et ses preuves'}));
  expect(props.onOpenDeliverable).toHaveBeenCalledWith(expect.objectContaining({deliverableId:'d1',checkId:''}));
});

it('bloque une liste lue à une révision différente et propose une actualisation commune',async()=>{
  vi.mocked(cockpitApi.tasks).mockResolvedValue({items:[task],total:607,offset:0,limit:20,revision:8});render(<ProjectCockpit {...defaults()}/>);
  await screen.findByText('Le projet a changé entre le chargement des jalons et de cette liste.');
  expect(screen.queryByRole('button',{name:/Étude moteur/})).toBeNull();
  expect(screen.getByRole('button',{name:'Consulter le livrable Plan BE'})).toBeTruthy();
  fireEvent.click(within(screen.getByRole('region',{name:'Tâches liées'})).getByRole('button',{name:'Réessayer'}));
  await waitFor(()=>expect(cockpitApi.structure).toHaveBeenCalledTimes(2));
});

it('respecte la lecture seule et ouvre les propositions dans leur écran de validation',async()=>{
  vi.mocked(cockpitApi.structure).mockResolvedValue({...structure,can_edit:false});
  vi.mocked(cockpitApi.alerts).mockResolvedValue({items:[{kind:'date_proposal',entity_kind:'candidate',id:'c1',title:'Date SAT',severity:'normal',due_date:''},
    {kind:'cdc_review',entity_kind:'cdc',id:'c2',title:'Fonction à confirmer',severity:'normal',due_date:''}],total:2,offset:0,limit:10,revision:7});
  vi.mocked(planningApi.task).mockResolvedValue({item:task,revision:7,can_edit:false});
  const props=defaults();render(<ProjectCockpit {...props}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Date à vérifier · Date SAT'}));expect(props.onOpenPlanning).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('button',{name:'CDC à confirmer · Fonction à confirmer'}));expect(props.onOpenCdc).toHaveBeenCalledOnce();
  expect(screen.queryByRole('button',{name:/Créer une tâche/})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:/Étude moteur/}));await screen.findByRole('form',{name:'Édition de la tâche'});
  expect(screen.queryByRole('button',{name:'Enregistrer la tâche'})).toBeNull();
  expect((screen.getByLabelText('Intitulé de la tâche') as HTMLInputElement).disabled).toBe(true);
});

it('ne garde pas un chargement tardif du projet précédent',async()=>{
  let resolve!:(value:CockpitStructure)=>void;
  vi.mocked(cockpitApi.structure).mockImplementationOnce(()=>new Promise(value=>{resolve=value;})).mockResolvedValue({...structure,project:{...structure.project,id:'p2'},items:[],tasks:{...structure.tasks,total:1,done:0}});
  const props=defaults(),view=render(<ProjectCockpit {...props}/>);view.rerender(<ProjectCockpit {...props} projectId="p2"/>);
  await screen.findByText('0 / 1 tâches terminées');resolve(structure);
  await waitFor(()=>expect(screen.queryByText('101 / 608 tâches terminées')).toBeNull());
});
