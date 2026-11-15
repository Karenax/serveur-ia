import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { planningApi, type ItemDetail, type PlanningInfo, type PlanningMilestone, type PlanningTask } from '../lib/projectPlanning';
import { identityApi, type ProjectPerson } from '../lib/projectIdentity';
import { milestoneApi } from '../lib/milestones';
import { deliverableApi, type GatePage } from '../lib/projectDeliverables';
import { PlanningTasksPanel } from './PlanningTasksPanel';
import { PlanningMilestonesPanel } from './PlanningMilestonesPanel';

const person:ProjectPerson={id:'person-1',first_name:'Alice',last_name:'Martin',email:'alice@example.test',trigram:'AMA',function:'BE',service:'Études',phone:'',agency_id:null,active:true,revision:1};
const info:PlanningInfo={project_id:'p1',revision:7,can_edit:true,excluded_dates:[],active_template_version_id:null,task_statuses:['todo','assigned','in_progress','blocked','done','cancelled'],workflow:[{code:'pdr',title:'PDR'}]};
const task:PlanningTask={id:'t1',title:'Études',status:'todo',due_date:'2026-10-09',parent_id:'group-1',milestone_id:'m1',responsible_id:person.id,template_id:null,template_key:null,priority:'normal',start_date:'2026-10-05',end_date:'2026-10-09',planned_hours:8,design:true,manufacturing:false,comment:'Commentaire existant',active:true,parent_title:'Groupe hors page',milestone_title:'FAT',responsible_name:'Alice Martin'};
const milestone:PlanningMilestone={id:'m1',title:'FAT',due_date:'2026-10-09',contractual_date:'2026-10-06',forecast_date:'2026-10-09',actual_date:'',variance_days:3,state:'scheduled',code:'pdr',order:5,workflow_status:'pending',comment:'Commentaire du jalon',active:true};
const taskDetail:ItemDetail<PlanningTask>={item:task,revision:7,can_edit:true,parent:{id:'group-1',title:'Groupe hors page'},milestone:{id:'m1',title:'FAT'},responsible:person,children_total:0};
beforeEach(()=>{
  vi.spyOn(deliverableApi,'milestoneGates').mockResolvedValue({milestone_id:'m1',revision:7,can_validate:true,checks_total:0,blocking_total:0,items:[],total:0,offset:0,limit:25});
  vi.spyOn(planningApi,'info').mockResolvedValue(info);
  vi.spyOn(planningApi,'tasks').mockResolvedValue({items:[task],total:1,offset:0,limit:25,revision:7});
  vi.spyOn(planningApi,'milestones').mockResolvedValue({items:[milestone],total:1,offset:0,limit:25,revision:7});
  vi.spyOn(planningApi,'task').mockResolvedValue(taskDetail);
  vi.spyOn(planningApi,'milestone').mockResolvedValue({item:milestone,revision:7,can_edit:true});
  vi.spyOn(identityApi,'people').mockResolvedValue({items:[person],total:1,offset:0,limit:50});
  vi.spyOn(milestoneApi,'review').mockResolvedValue({candidates:[],pending_total:0,job:null,planning_revision:7});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});

it('montre le visa bloquant et garde la date réelle indépendante de la validation du workflow',async()=>{
  const gates:GatePage={milestone_id:'m1',revision:7,can_validate:false,checks_total:1,blocking_total:1,total:1,offset:0,limit:25,items:[{id:'g1',label:'Visa plan',deliverable_id:'d1',deliverable_title:'Plan BE',version_id:'v1',version:{id:'v1',number:1,filename:'plan.pdf',reference:'Plan A'},ready:false,reason:'Visa humain requis pour la dernière version',responsible_id:null,responsible_name:null,verifier_id:'u1',verifier_name:'Alice Martin'}]};
  vi.mocked(deliverableApi.milestoneGates).mockResolvedValue(gates);const patch=vi.spyOn(planningApi,'patchMilestone').mockResolvedValue({revision:8,milestone});render(<PlanningMilestonesPanel projectId="p1" onSaved={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Modifier · FAT'}));await screen.findByText('Visa plan');fireEvent.change(screen.getByLabelText('Date réelle'),{target:{value:'2026-10-06'}});fireEvent.change(screen.getByLabelText('État du jalon'),{target:{value:'validated'}});expect((screen.getByRole('button',{name:'Enregistrer le jalon'}) as HTMLButtonElement).disabled).toBe(true);expect((screen.getByLabelText('Date réelle') as HTMLInputElement).value).toBe('2026-10-06');expect(patch).not.toHaveBeenCalled();fireEvent.change(screen.getByLabelText('État du jalon'),{target:{value:'pending'}});fireEvent.click(screen.getByRole('button',{name:'Enregistrer le jalon'}));await waitFor(()=>expect(patch).toHaveBeenCalledWith('p1','m1',7,{actual_date:'2026-10-06'}));
});
it('ouvre les visas depuis la liste et transmet la cible exacte du contrôle sans modifier le jalon',async()=>{
  const open=vi.fn();const gate={id:'g1',label:'Visa plan',deliverable_id:'d1',deliverable_title:'Plan BE',version_id:null,version:null,ready:false,reason:'Publier une version',responsible_id:null,responsible_name:null,verifier_id:null,verifier_name:null};vi.mocked(deliverableApi.milestoneGates).mockResolvedValue({milestone_id:'m1',revision:7,can_validate:false,checks_total:1,blocking_total:1,items:[gate],total:1,offset:0,limit:25});render(<PlanningMilestonesPanel projectId="p1" onSaved={vi.fn()} onOpenDeliverable={open}/>);fireEvent.click(await screen.findByLabelText('Options du jalon FAT'));fireEvent.click(screen.getByRole('button',{name:'Visas de livrables · FAT'}));fireEvent.click(await screen.findByRole('button',{name:'Ouvrir Plan BE · Visa plan'}));expect(open).toHaveBeenCalledWith({deliverableId:'d1',checkId:'g1',milestoneId:'m1',milestoneTitle:'FAT',version:null});expect(screen.queryByRole('form',{name:'Édition du jalon'})).toBeNull();
});
async function editTask(){fireEvent.click(await screen.findByRole('button',{name:'Modifier · Études'}));return screen.findByRole('form',{name:'Édition de la tâche'});}

it('sauvegarde les seuls champs modifiés avec la révision et conserve les sélections hors page',async()=>{
  const patch=vi.spyOn(planningApi,'patchTask').mockResolvedValue({revision:8,task:{...task,planned_hours:12}});const saved=vi.fn();
  render(<PlanningTasksPanel projectId="p1" onSaved={saved}/>);const form=await editTask();
  expect(within(screen.getByLabelText('Tâche parente')).getByRole('option',{name:'Groupe hors page'})).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Charge prévue (h)'),{target:{value:'12'}});
  expect(form.dataset.workspaceDirty).toBe('true');fireEvent.click(screen.getByRole('button',{name:'Enregistrer la tâche'}));
  await waitFor(()=>expect(patch).toHaveBeenCalledWith('p1','t1',7,{planned_hours:12}));await screen.findByText('Tâche enregistrée.');expect(saved).toHaveBeenCalledOnce();
});

it('compare un conflit sans perdre la saisie puis ne réécrit pas les champs changés par un collègue',async()=>{
  const patch=vi.spyOn(planningApi,'patchTask').mockRejectedValueOnce(new Error('Révision modifiée')).mockResolvedValue({revision:9,task});
  render(<PlanningTasksPanel projectId="p1" onSaved={vi.fn()}/>);await editTask();
  fireEvent.change(screen.getByLabelText('Intitulé de la tâche'),{target:{value:'Mon étude'}});fireEvent.click(screen.getByRole('button',{name:'Enregistrer la tâche'}));
  await screen.findByRole('alert');expect((screen.getByLabelText('Intitulé de la tâche') as HTMLInputElement).value).toBe('Mon étude');
  vi.mocked(planningApi.task).mockResolvedValue({...taskDetail,revision:8,item:{...task,comment:'Commentaire du collègue',planned_hours:10}});
  fireEvent.click(screen.getByRole('button',{name:'Recharger et comparer sans perdre ma saisie'}));await screen.findByRole('region',{name:'Comparaison avec la dernière révision'});
  expect(patch).toHaveBeenCalledTimes(1);expect((screen.getByRole('button',{name:'Enregistrer la tâche'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Préparer mon brouillon sur cette révision'}));
  expect((screen.getByLabelText('Commentaire de la tâche') as HTMLTextAreaElement).value).toBe('Commentaire du collègue');
  expect((screen.getByLabelText('Charge prévue (h)') as HTMLInputElement).value).toBe('10');
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la tâche'}));await waitFor(()=>expect(patch).toHaveBeenLastCalledWith('p1','t1',8,{title:'Mon étude'}));
});

it('crée une tâche structurée et recharge la liste après la sauvegarde',async()=>{
  const saved=vi.fn();const created={...task,id:'new-task',title:'Contrôle final',parent_id:null,milestone_id:null,responsible_id:null,planned_hours:4};
  const create=vi.spyOn(planningApi,'createTask').mockImplementation(async()=>{vi.mocked(planningApi.tasks).mockResolvedValue({items:[task,created],total:2,offset:0,limit:25,revision:8});return {revision:8,task:created};});
  render(<PlanningTasksPanel projectId="p1" onSaved={saved}/>);await screen.findByRole('button',{name:'Modifier · Études'});
  fireEvent.click(screen.getByRole('button',{name:'Nouvelle tâche'}));fireEvent.change(screen.getByLabelText('Intitulé de la tâche'),{target:{value:'Contrôle final'}});fireEvent.change(screen.getByLabelText('Charge prévue (h)'),{target:{value:'4'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la tâche'}));await waitFor(()=>expect(create).toHaveBeenCalledWith('p1',7,expect.objectContaining({title:'Contrôle final',planned_hours:4,active:true,parent_task_id:null})));
  expect(await screen.findByRole('button',{name:'Modifier · Contrôle final'})).toBeTruthy();expect(saved).toHaveBeenCalledOnce();
});

it('reprend une création en conflit sans effacer la nouvelle tâche',async()=>{
  const create=vi.spyOn(planningApi,'createTask').mockRejectedValueOnce(new Error('Planning modifié')).mockResolvedValue({revision:10,task});
  render(<PlanningTasksPanel projectId="p1" onSaved={vi.fn()}/>);await screen.findByRole('button',{name:'Modifier · Études'});
  fireEvent.click(screen.getByRole('button',{name:'Nouvelle tâche'}));fireEvent.change(screen.getByLabelText('Intitulé de la tâche'),{target:{value:'Ma nouvelle tâche'}});
  fireEvent.change(screen.getByLabelText('Charge prévue (h)'),{target:{value:'6'}});fireEvent.click(screen.getByRole('button',{name:'Enregistrer la tâche'}));
  await screen.findByRole('alert');vi.mocked(planningApi.info).mockResolvedValue({...info,revision:9});
  fireEvent.click(screen.getByRole('button',{name:'Recharger et comparer sans perdre ma saisie'}));await screen.findByRole('region',{name:'Comparaison avec la dernière révision'});
  expect(create).toHaveBeenCalledTimes(1);fireEvent.click(screen.getByRole('button',{name:'Préparer mon brouillon sur cette révision'}));
  expect((screen.getByLabelText('Intitulé de la tâche') as HTMLInputElement).value).toBe('Ma nouvelle tâche');expect((screen.getByLabelText('Charge prévue (h)') as HTMLInputElement).value).toBe('6');
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer la tâche'}));await waitFor(()=>expect(create).toHaveBeenLastCalledWith('p1',9,expect.objectContaining({title:'Ma nouvelle tâche',planned_hours:6})));
});

it('bloque les dates et heures propres des groupes et garde les erreurs de hiérarchie',async()=>{
  vi.mocked(planningApi.task).mockResolvedValue({...taskDetail,children_total:2});const patch=vi.spyOn(planningApi,'patchTask').mockRejectedValue(new Error('Cycle de tâches interdit'));
  render(<PlanningTasksPanel projectId="p1" onSaved={vi.fn()}/>);await editTask();
  expect((screen.getByLabelText('Charge prévue (h)') as HTMLInputElement).disabled).toBe(true);expect((screen.getByLabelText('Début de la tâche') as HTMLInputElement).disabled).toBe(true);
  fireEvent.change(screen.getByLabelText('Commentaire de la tâche'),{target:{value:'Brouillon de contrôle'}});fireEvent.click(screen.getByRole('button',{name:'Enregistrer la tâche'}));
  expect((await screen.findByRole('alert')).textContent).toContain('Cycle');expect((screen.getByLabelText('Commentaire de la tâche') as HTMLTextAreaElement).value).toBe('Brouillon de contrôle');
  expect(patch).toHaveBeenCalledWith('p1','t1',7,{comment:'Brouillon de contrôle'});
});

it('affiche une consultation pour le lecteur sans commande ni brouillon de navigation',async()=>{
  vi.mocked(planningApi.info).mockResolvedValue({...info,can_edit:false});vi.mocked(planningApi.task).mockResolvedValue({...taskDetail,can_edit:false});
  render(<PlanningTasksPanel projectId="p1" onSaved={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Consulter · Études'}));
  const form=await screen.findByRole('form',{name:'Édition de la tâche'});expect(form.dataset.workspaceDirty).toBeUndefined();
  expect((screen.getByLabelText('Intitulé de la tâche') as HTMLInputElement).disabled).toBe(true);expect(screen.queryByRole('button',{name:'Enregistrer la tâche'})).toBeNull();expect(screen.queryByRole('button',{name:'Nouvelle tâche'})).toBeNull();
});

it('pagine et filtre la liste sur le serveur',async()=>{
  vi.mocked(planningApi.tasks).mockImplementation(async(_id,options={})=>({items:[task],total:60,offset:options.offset||0,limit:25,revision:7}));
  render(<PlanningTasksPanel projectId="p1" onSaved={vi.fn()}/>);await screen.findByRole('button',{name:'Modifier · Études'});fireEvent.click(screen.getByRole('button',{name:'Suivant'}));
  await waitFor(()=>expect(planningApi.tasks).toHaveBeenCalledWith('p1',expect.objectContaining({offset:25,include_inactive:false})));
  fireEvent.change(screen.getByLabelText('Rechercher une tâche'),{target:{value:'Contrôle'}});fireEvent.click(screen.getByLabelText('Inclure les tâches archivées'));
  await waitFor(()=>expect(planningApi.tasks).toHaveBeenCalledWith('p1',expect.objectContaining({search:'Contrôle',offset:0,include_inactive:true})));
});

it('ignore une ouverture tardive du projet quitté',async()=>{
  let resolve!:(value:ItemDetail<PlanningTask>)=>void;vi.mocked(planningApi.task).mockReturnValue(new Promise(done=>{resolve=done;}));
  const view=render(<PlanningTasksPanel projectId="p1" onSaved={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Modifier · Études'}));
  view.rerender(<PlanningTasksPanel projectId="p2" onSaved={vi.fn()}/>);await waitFor(()=>expect(planningApi.info).toHaveBeenCalledWith('p2',expect.any(AbortSignal)));
  resolve(taskDetail);await waitFor(()=>expect(screen.queryByRole('form',{name:'Édition de la tâche'})).toBeNull());
});

it('conserve le brouillon lorsque la rubrique devient masquée puis revient',async()=>{
  const saved=vi.fn();const view=render(<PlanningTasksPanel projectId="p1" onSaved={saved}/>);await editTask();fireEvent.change(screen.getByLabelText('Intitulé de la tâche'),{target:{value:'Brouillon conservé'}});
  view.rerender(<PlanningTasksPanel projectId="p1" active={false} onSaved={saved}/>);view.rerender(<PlanningTasksPanel projectId="p1" active onSaved={saved}/>);
  expect((screen.getByLabelText('Intitulé de la tâche') as HTMLInputElement).value).toBe('Brouillon conservé');
});

it('modifie le workflow sans inventer une date réelle',async()=>{
  const patch=vi.spyOn(planningApi,'patchMilestone').mockResolvedValue({revision:8,milestone:{...milestone,workflow_status:'validated'}});const saved=vi.fn();
  render(<PlanningMilestonesPanel projectId="p1" onSaved={saved}/>);fireEvent.click(await screen.findByRole('button',{name:'Modifier · FAT'}));await screen.findByRole('form',{name:'Édition du jalon'});
  fireEvent.change(screen.getByLabelText('État du jalon'),{target:{value:'validated'}});expect((screen.getByLabelText('Date réelle') as HTMLInputElement).value).toBe('');
  const save=screen.getByRole('button',{name:'Enregistrer le jalon'}) as HTMLButtonElement;
  // Le formulaire s’ouvre avant le contrôle asynchrone des visas ; attendre son autorisation de validation.
  await waitFor(()=>expect(save.disabled).toBe(false),{timeout:3_000});fireEvent.click(save);
  await waitFor(()=>expect(patch).toHaveBeenCalledWith('p1','m1',7,{workflow_status:'validated'}));expect(saved).toHaveBeenCalledOnce();
});

it('garde la date saisie en conflit et consulte l’historique des dates',async()=>{
  vi.spyOn(planningApi,'patchMilestone').mockRejectedValue(new Error('Modification concurrente'));vi.spyOn(milestoneApi,'history').mockResolvedValue([{id:'h1',field:'forecast_date',previous:'2026-10-06',value:'2026-10-09',evidence:{kind:'manual',label:'Saisie manuelle'},created_at:'2026-10-05T10:00:00Z'}]);
  render(<PlanningMilestonesPanel projectId="p1" onSaved={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Modifier · FAT'}));await screen.findByLabelText('Date prévisionnelle');
  fireEvent.change(screen.getByLabelText('Date prévisionnelle'),{target:{value:'2026-10-12'}});fireEvent.click(screen.getByRole('button',{name:'Enregistrer le jalon'}));await screen.findByRole('alert');expect((screen.getByLabelText('Date prévisionnelle') as HTMLInputElement).value).toBe('2026-10-12');
  fireEvent.click(screen.getByRole('button',{name:'Annuler le brouillon'}));fireEvent.click(screen.getByLabelText('Options du jalon FAT'));fireEvent.click(screen.getByRole('button',{name:'Historique des dates · FAT'}));expect(await screen.findByRole('region',{name:'Historique des dates · FAT'})).toBeTruthy();
});

it('valide une proposition pour un jalon hors page avec la valeur et la révision affichées',async()=>{
  vi.mocked(planningApi.milestones).mockResolvedValue({items:[],total:30,offset:0,limit:25,revision:7});
  vi.mocked(milestoneApi.review).mockResolvedValue({planning_revision:7,pending_total:1,job:null,candidates:[{id:'c1',title:'FAT',date_type:'forecast_date',date:'2026-10-12',quote:'FAT le 12 octobre',evidence:{kind:'manual',label:'Note recette'},confidence:1,current_value:'2026-10-09',conflict:true,milestone_id:'m1'}]});
  const decide=vi.spyOn(milestoneApi,'decide').mockResolvedValue({});render(<PlanningMilestonesPanel projectId="p1" onSaved={vi.fn()}/>);
  const button=await screen.findByRole('button',{name:'Valider le remplacement'});await waitFor(()=>expect((button as HTMLButtonElement).disabled).toBe(false));
  fireEvent.click(button);await waitFor(()=>expect(decide).toHaveBeenCalledWith('p1','c1',{decision:'accept',expected_value:'2026-10-09',milestone_id:'m1',expected_revision:7}));
});

it('masque les commandes de recherche et de validation pour le lecteur',async()=>{
  vi.mocked(planningApi.info).mockResolvedValue({...info,can_edit:false});render(<PlanningMilestonesPanel projectId="p1" onSaved={vi.fn()}/>);
  await screen.findByRole('button',{name:'Consulter · FAT'});expect(screen.queryByRole('button',{name:'Créer le jalon'})).toBeNull();expect(screen.queryByRole('button',{name:'Rechercher les dates'})).toBeNull();
});
