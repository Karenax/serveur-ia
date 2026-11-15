import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { planningApi, type Baseline, type PlanningInfo } from '../lib/projectPlanning';
import { PlanningBaselinesPanel } from './PlanningBaselinesPanel';
import { PlanningHistoryPanel } from './PlanningHistoryPanel';
import { DiffDetails, historyChanges, PlanningChanges } from './PlanningChanges';

const info:PlanningInfo={project_id:'p1',revision:7,can_edit:true,excluded_dates:[],active_template_version_id:null,task_statuses:[],workflow:[]};
const baseline:Baseline={id:'b1',kind:'contractual',label:'Contrat initial',capture_label:'Contrat initial',comment:'Commentaire',active:true,revision:3,metadata_revision:3,sha256:'a'.repeat(64),actor_id:'recette',created_at:'2026-10-05T10:00:00Z'};
const event={id:'h1',revision:7,actor_id:'recette',action:'task_changed',created_at:'2026-10-05T12:00:00Z'};
beforeEach(()=>{
  vi.spyOn(planningApi,'info').mockResolvedValue(info);vi.spyOn(planningApi,'baselines').mockResolvedValue({items:[baseline],total:1,offset:0,limit:25});
  vi.spyOn(planningApi,'baseline').mockResolvedValue({baseline,revision:7,can_edit:true});
  vi.spyOn(planningApi,'compare').mockResolvedValue({revision:7,baseline_revision:3,planned_hours_delta:4,changes:[
    {kind:'milestones',id:'m1',title:'FAT',field:'contractual_date',severity:'high',before:'2026-10-05',after:'2026-10-08'},
    {kind:'tasks',id:'t1',title:'Études',field:'planned_hours',severity:'normal',before:8,after:12}]});
  vi.spyOn(planningApi,'history').mockResolvedValue({items:[event],total:1,offset:0,limit:25});
  vi.spyOn(planningApi,'historyDetail').mockResolvedValue({id:'h1',revision:7,previous:{tasks:[{id:'t1',title:'Études',planned_hours:8}]},value:{tasks:[{id:'t1',title:'Études',planned_hours:12}]}});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function openMetadata(){fireEvent.click(await screen.findByRole('button',{name:'Modifier la référence · Contrat initial'}));return screen.findByRole('form',{name:'Informations du planning de référence'});}

it('capture une référence sur la révision affichée puis actualise la liste',async()=>{
  const saved=vi.fn();const create=vi.spyOn(planningApi,'createBaseline').mockResolvedValue({...baseline,id:'b2',label:'Revue KOM',kind:'review',revision:8});
  render(<PlanningBaselinesPanel projectId="p1" onSaved={saved}/>);await screen.findByRole('button',{name:'Comparer · Contrat initial'});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer le planning de référence'}));fireEvent.change(screen.getByLabelText('Nom de la référence'),{target:{value:'Revue KOM'}});
  fireEvent.change(screen.getByLabelText('Type de référence'),{target:{value:'review'}});fireEvent.click(screen.getByRole('button',{name:'Capturer l’état du planning'}));
  await waitFor(()=>expect(create).toHaveBeenCalledWith('p1',7,'review','Revue KOM'));await screen.findByText('Référence capturée : son instantané restera inchangé.');expect(saved).toHaveBeenCalledOnce();
});

it('conserve le nom et le type après conflit de capture et exige une reprise explicite',async()=>{
  const create=vi.spyOn(planningApi,'createBaseline').mockRejectedValueOnce(new Error('Planning modifié')).mockResolvedValue(baseline);
  render(<PlanningBaselinesPanel projectId="p1" onSaved={vi.fn()}/>);await screen.findByRole('button',{name:'Comparer · Contrat initial'});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer le planning de référence'}));fireEvent.change(screen.getByLabelText('Nom de la référence'),{target:{value:'Avenant 2'}});
  fireEvent.change(screen.getByLabelText('Type de référence'),{target:{value:'amendment'}});fireEvent.click(screen.getByRole('button',{name:'Capturer l’état du planning'}));await screen.findByRole('alert');
  vi.mocked(planningApi.info).mockResolvedValue({...info,revision:9});fireEvent.click(screen.getByRole('button',{name:'Relire la révision sans perdre la saisie'}));await screen.findByRole('region',{name:'Révision de la capture'});
  expect(create).toHaveBeenCalledTimes(1);expect((screen.getByRole('button',{name:'Capturer l’état du planning'}) as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(screen.getByRole('button',{name:'Préparer la capture sur cette révision'}));fireEvent.click(screen.getByRole('button',{name:'Capturer l’état du planning'}));
  await waitFor(()=>expect(create).toHaveBeenLastCalledWith('p1',9,'amendment','Avenant 2'));
});

it('archive par métadonnées sans envoyer le contenu ou l’empreinte de la capture',async()=>{
  const patch=vi.spyOn(planningApi,'patchBaseline').mockResolvedValue({revision:8,baseline:{...baseline,active:false}});
  render(<PlanningBaselinesPanel projectId="p1" onSaved={vi.fn()}/>);const form=await openMetadata();fireEvent.click(screen.getByLabelText('Référence active dans les listes'));
  expect(form.dataset.workspaceDirty).toBe('true');fireEvent.click(screen.getByRole('button',{name:'Enregistrer le nom et le commentaire'}));
  await waitFor(()=>expect(patch).toHaveBeenCalledWith('p1','b1',7,{active:false}));
});

it('reprend uniquement le nom et le commentaire saisies après une modification concurrente',async()=>{
  const patch=vi.spyOn(planningApi,'patchBaseline').mockRejectedValueOnce(new Error('Révision modifiée')).mockResolvedValue({revision:9,baseline});
  render(<PlanningBaselinesPanel projectId="p1" onSaved={vi.fn()}/>);await openMetadata();fireEvent.change(screen.getByLabelText('Nom de la référence'),{target:{value:'Mon nom'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer le nom et le commentaire'}));await screen.findByRole('alert');
  vi.mocked(planningApi.baseline).mockResolvedValue({revision:8,can_edit:true,baseline:{...baseline,comment:'Commentaire du collègue',active:false}});
  fireEvent.click(screen.getByRole('button',{name:'Relire et comparer le nom et le commentaire'}));await screen.findByRole('region',{name:'Comparaison du nom et du commentaire'});
  expect(patch).toHaveBeenCalledTimes(1);fireEvent.click(screen.getByRole('button',{name:'Préparer le nom et le commentaire sur cette révision'}));
  expect((screen.getByLabelText('Commentaire de la référence') as HTMLTextAreaElement).value).toBe('Commentaire du collègue');expect((screen.getByLabelText('Référence active dans les listes') as HTMLInputElement).checked).toBe(false);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer le nom et le commentaire'}));await waitFor(()=>expect(patch).toHaveBeenLastCalledWith('p1','b1',8,{label:'Mon nom'}));
});

it('permet au lecteur de comparer et consulter sans commande ni brouillon',async()=>{
  vi.mocked(planningApi.info).mockResolvedValue({...info,can_edit:false});vi.mocked(planningApi.baseline).mockResolvedValue({baseline,revision:7,can_edit:false});
  render(<PlanningBaselinesPanel projectId="p1" onSaved={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Consulter la référence · Contrat initial'}));
  const form=await screen.findByRole('form',{name:'Informations du planning de référence'});expect(form.dataset.workspaceDirty).toBeUndefined();expect((screen.getByLabelText('Nom de la référence') as HTMLInputElement).disabled).toBe(true);
  expect(screen.queryByRole('button',{name:'Enregistrer le nom et le commentaire'})).toBeNull();expect(screen.queryByRole('button',{name:'Enregistrer le planning de référence'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Comparer · Contrat initial'}));expect(await screen.findByRole('region',{name:'Comparaison · Contrat initial'})).toBeTruthy();
});

it('pagine et inclut les références archivées uniquement sur demande',async()=>{
  vi.mocked(planningApi.baselines).mockImplementation(async(_id,offset=0)=>({items:[baseline],total:60,offset,limit:25}));
  render(<PlanningBaselinesPanel projectId="p1" onSaved={vi.fn()}/>);await screen.findByRole('button',{name:'Comparer · Contrat initial'});
  fireEvent.click(screen.getByRole('button',{name:'Suivant'}));await waitFor(()=>expect(planningApi.baselines).toHaveBeenCalledWith('p1',25,expect.any(AbortSignal),false));
  fireEvent.click(screen.getByLabelText('Inclure les références archivées'));await waitFor(()=>expect(planningApi.baselines).toHaveBeenLastCalledWith('p1',0,expect.any(AbortSignal),true));
});

it('affiche les révisions et filtre les écarts sans changer leur compteur global ni la charge',async()=>{
  render(<PlanningBaselinesPanel projectId="p1" onSaved={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Comparer · Contrat initial'}));
  const compare=await screen.findByRole('region',{name:'Comparaison · Contrat initial'});expect(compare.textContent).toContain('Référence : révision 3 · état comparé : révision 7');
  expect(within(compare).getByText('Variation de charge : +4 h')).toBeTruthy();fireEvent.change(within(compare).getByLabelText('Sévérité'),{target:{value:'high'}});
  expect(within(compare).getByText('FAT')).toBeTruthy();expect(within(compare).queryByText('Études')).toBeNull();expect(within(compare).getByText('2 écart(s)')).toBeTruthy();
});

it('ignore une comparaison tardive du projet quitté',async()=>{
  let resolve!:(value:Awaited<ReturnType<typeof planningApi.compare>>)=>void;vi.mocked(planningApi.compare).mockReturnValue(new Promise(done=>{resolve=done;}));
  const view=render(<PlanningBaselinesPanel projectId="p1" onSaved={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Comparer · Contrat initial'}));
  view.rerender(<PlanningBaselinesPanel projectId="p2" onSaved={vi.fn()}/>);await waitFor(()=>expect(planningApi.info).toHaveBeenCalledWith('p2',expect.any(AbortSignal)));
  resolve({planned_hours_delta:0,changes:[]});await waitFor(()=>expect(screen.queryByRole('region',{name:'Comparaison · Contrat initial'})).toBeNull());
});

it('charge le détail historique seulement à la demande et montre les seuls changements',async()=>{
  render(<PlanningHistoryPanel projectId="p1"/>);const button=await screen.findByRole('button',{name:'Consulter la révision 7'});expect(planningApi.historyDetail).not.toHaveBeenCalled();fireEvent.click(button);
  const detail=await screen.findByRole('region',{name:'Détail de la révision 7'});expect(planningApi.historyDetail).toHaveBeenCalledWith('p1','h1');
  expect(within(detail).getByText('Charge (h)')).toBeTruthy();expect(within(detail).getByText('8 h')).toBeTruthy();expect(within(detail).getByText('12 h')).toBeTruthy();expect(detail.textContent).toContain('opérateur recette');
});

it('garde les ajouts/retraits et les preuves des dates dans une comparaison lisible',()=>{
  const proof={kind:'source',label:'Mail client',quote:'FAT acceptée le 8 octobre'};
  const changes=historyChanges({tasks:[{id:'old',title:'Ancienne tâche'}],milestones:[{id:'m1',title:'FAT',actual_date:''}]},
    {tasks:[{id:'new',title:'Nouvelle tâche'}],milestones:[{id:'m1',title:'FAT',actual_date:'2026-10-08',date_sources:{actual_date:proof}}]});
  render(<PlanningChanges changes={changes}/>);expect(screen.getByText('1 ajout(s)')).toBeTruthy();expect(screen.getByText('1 retrait(s)')).toBeTruthy();expect(screen.getByRole('cell',{name:'Date réelle'})).toBeTruthy();
  expect(screen.getByText('FAT acceptée le 8 octobre')).toBeTruthy();expect(changes.some(row=>row.field==='actual_date'&&row.severity==='high')).toBe(true);
});

it('pagine les grands tableaux d’écarts et l’historique serveur',async()=>{
  vi.mocked(planningApi.history).mockImplementation(async(_id,offset=0)=>({items:[event],total:60,offset,limit:25}));
  render(<PlanningHistoryPanel projectId="p1"/>);await screen.findByRole('button',{name:'Consulter la révision 7'});fireEvent.click(screen.getByRole('button',{name:'Suivant'}));
  await waitFor(()=>expect(planningApi.history).toHaveBeenCalledWith('p1',25,expect.any(AbortSignal)));
  cleanup();render(<PlanningChanges changes={Array.from({length:60},(_,index)=>({kind:'tasks',id:String(index),title:`Tâche ${index}`,field:'title',severity:'normal',before:'Avant',after:'Après'}))}/>);
  expect(screen.queryByText('Tâche 25')).toBeNull();fireEvent.click(screen.getByRole('button',{name:'Suivant'}));expect(screen.getByText('Tâche 25')).toBeTruthy();expect(screen.queryByText('Tâche 0')).toBeNull();
});

it('montre un état sans écart explicite',()=>{render(<PlanningChanges changes={[]} plannedHoursDelta={0}/>);expect(screen.getByText('Aucun écart sur les jalons et tâches comparés.')).toBeTruthy();expect(screen.getByText('Variation de charge : 0 h')).toBeTruthy();});

it('sépare les engagements projet de la charge et filtre leurs écarts',()=>{
  render(<DiffDetails diff={{baseline_revision:2,revision:4,project_comparison_available:true,project_budget_hours_delta:40,planned_hours_delta:4,changes:[
    {kind:'project',id:'p1',title:'Projet',field:'budget_hours',severity:'high',before:80,after:120},
    {kind:'tasks',id:'t1',title:'Études',field:'planned_hours',severity:'normal',before:8,after:12}]}}/>);
  expect(screen.getByText('Variation du budget d’heures : +40 h')).toBeTruthy();expect(screen.getByText('Variation de charge : +4 h')).toBeTruthy();
  fireEvent.change(screen.getByLabelText('Type d’élément'),{target:{value:'project'}});
  expect(screen.getByText('Budget d’heures du projet')).toBeTruthy();expect(screen.getByText('80 h')).toBeTruthy();expect(screen.queryByText('Études')).toBeNull();
});

it('signale les engagements absents d’une ancienne référence sans inventer une variation',()=>{
  render(<DiffDetails diff={{baseline_revision:2,revision:4,project_comparison_available:false,project_budget_hours_delta:null,planned_hours_delta:0,changes:[]}}/>);
  expect(screen.getByText(/Ancienne référence : les dates et le budget/)).toBeTruthy();expect(screen.queryByText(/Variation du budget/)).toBeNull();
});

it('montre séparément les dates projet modifiées dans le journal',()=>{
  const changes=historyChanges({project:{start_date:'2026-10-01',planned_end_date:'2026-12-01',budget_hours:80}},
    {project:{start_date:'2026-10-01',planned_end_date:'2026-12-10',budget_hours:80}});
  expect(changes).toHaveLength(1);expect(changes[0].kind).toBe('project');render(<PlanningChanges changes={changes}/>);
  expect(screen.getByText('Fin prévisionnelle du projet')).toBeTruthy();expect(screen.getByText('01/12/2026')).toBeTruthy();expect(screen.getByText('10/12/2026')).toBeTruthy();
});
