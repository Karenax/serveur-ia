import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { planningApi, type TemplateDefinition, type TemplateDetail, type TemplatePreview } from '../lib/projectPlanning';
import { identityApi } from '../lib/projectIdentity';
import { PlanningTemplatesPanel } from './PlanningTemplatesPanel';
import { PlanningDefinitionEditor } from './PlanningDefinitionEditor';

const definition:TemplateDefinition={name:'Cycle technique',milestones:[{code:'kom',title:'KOM',offset_workdays:0},{code:'cdr',title:'CDR',offset_workdays:5},{code:'livraison',title:'Livraison',offset_workdays:10}],tasks:[
  {key:'group',title:'Groupe BE',parent_key:null,milestone_code:null,start_offset_workdays:null,end_offset_workdays:null,planned_hours:0,priority:'normal',design:true,manufacturing:false},
  {key:'design',title:'Études',parent_key:'group',milestone_code:'cdr',start_offset_workdays:0,end_offset_workdays:5,planned_hours:8,priority:'normal',design:true,manufacturing:false}]};
const template:TemplateDetail={id:'model1',code:'STANDARD',name:'Cycle standard',typology_id:null,active:true,revision:2,latest_version:{id:'v1',number:1,sha256:'a'.repeat(64)},can_manage:true};
const info={project_id:'p1',revision:7,can_edit:true,excluded_dates:['2026-10-05'],active_template_version_id:null,task_statuses:[],workflow:[]};
const version={id:'v1',number:1,sha256:'a'.repeat(64),definition};
const preview:TemplatePreview={project_id:'p1',revision:7,version_id:'v1',preview_sha256:'b'.repeat(64),milestone_map:{kom:'m1'},task_map:{},milestones:[],tasks:[],
  inputs:{expected_revision:7,start_date:'',excluded_dates:['2026-10-05'],milestone_mapping:{},forecast_policy:'fill_empty',update_tasks:false},
  changes:{changes:[{kind:'tasks',id:'new',title:'Nouvelle tâche',field:null,severity:'high',before:null,after:{title:'Nouvelle tâche',planned_hours:8}}],planned_hours_delta:8,calendar:{before:[],after:['2026-10-05']},template_version_id:{before:null,after:'v1'}}};
beforeEach(()=>{
  vi.spyOn(planningApi,'info').mockResolvedValue(info);vi.spyOn(planningApi,'templates').mockResolvedValue({items:[template],total:1,offset:0,limit:25,can_manage:true});
  vi.spyOn(planningApi,'template').mockResolvedValue(template);vi.spyOn(planningApi,'versions').mockResolvedValue({items:[{...version,actor_id:'recette',created_at:'2026-10-05T10:00:00Z'}],total:1,offset:0,limit:25});
  vi.spyOn(planningApi,'version').mockResolvedValue(version);vi.spyOn(planningApi,'standard').mockResolvedValue(definition);
  vi.spyOn(planningApi,'mappingProposals').mockResolvedValue({revision:7,items:[{milestone_id:'m1',title:'Lancement du projet',suggested_code:'kom',human_confirmation_required:true,reason:'À vérifier'}]});
  vi.spyOn(planningApi,'milestones').mockResolvedValue({items:[],total:0,offset:0,limit:50,revision:7});
  vi.spyOn(planningApi,'preview').mockResolvedValue(preview);vi.spyOn(identityApi,'references').mockResolvedValue({items:[],total:0,offset:0,limit:50});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function openVersion(){fireEvent.click(await screen.findByRole('button',{name:'Ouvrir le modèle · Cycle standard'}));fireEvent.click(await screen.findByRole('button',{name:'Consulter la version 1'}));return screen.findByRole('region',{name:'Version publiée 1'});}
async function openApplication(){await openVersion();fireEvent.click(screen.getByRole('button',{name:'Préparer l’application de v1'}));return screen.findByRole('form',{name:'Application du modèle au projet'});}

it('pagine le catalogue et filtre les archivés, puis consulte la version immuable',async()=>{
  vi.mocked(planningApi.templates).mockImplementation(async(options={})=>({items:[template],total:60,offset:options.offset||0,limit:25,can_manage:true}));
  render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);await screen.findByRole('button',{name:'Créer un modèle'});
  fireEvent.click(screen.getByRole('button',{name:'Suivant'}));await waitFor(()=>expect(planningApi.templates).toHaveBeenCalledWith(expect.objectContaining({offset:25})));
  fireEvent.click(screen.getByLabelText('Inclure les modèles archivés'));await waitFor(()=>expect(planningApi.templates).toHaveBeenLastCalledWith(expect.objectContaining({include_inactive:true,offset:0})));
  const region=await openVersion();expect((within(region).getByLabelText('Charge de la tâche 2 (h)') as HTMLInputElement).disabled).toBe(true);
  expect(planningApi.version).toHaveBeenCalledWith('model1','v1');
});

it('crée une version structurée sans exposer de JSON ni modifier un projet',async()=>{
  const create=vi.spyOn(planningApi,'createTemplate').mockResolvedValue({...template,version});const apply=vi.spyOn(planningApi,'apply');
  render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Créer un modèle'}));
  await screen.findByRole('form',{name:'Création du modèle'});fireEvent.change(screen.getByLabelText('Code du modèle'),{target:{value:'TECH'}});fireEvent.change(screen.getByLabelText('Nom du modèle'),{target:{value:'Technique'}});
  fireEvent.change(screen.getByLabelText('Intitulé du jalon 1'),{target:{value:'Lancement'}});fireEvent.click(screen.getByRole('button',{name:'Créer et publier la première version'}));
  await waitFor(()=>expect(create).toHaveBeenCalledWith({code:'TECH',name:'Technique',typology_id:null,definition:expect.objectContaining({milestones:expect.arrayContaining([expect.objectContaining({title:'Lancement'})])})}));
  expect(definition.milestones[0].title).toBe('KOM');expect(apply).not.toHaveBeenCalled();expect(await screen.findByText(/Modèle créé et première version publiée/)).toBeTruthy();
});

it('publie un brouillon depuis une version sans réécrire la source ni appliquer automatiquement',async()=>{
  const publish=vi.spyOn(planningApi,'publish').mockResolvedValue({id:'v2',number:2});const apply=vi.spyOn(planningApi,'apply');
  render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);await openVersion();fireEvent.click(screen.getByRole('button',{name:'Créer une nouvelle version depuis v1'}));
  await screen.findByRole('form',{name:'Publication d’une nouvelle version'});fireEvent.change(screen.getByLabelText('Charge de la tâche 2 (h)'),{target:{value:'12'}});fireEvent.click(screen.getByRole('button',{name:'Publier cette nouvelle version'}));
  await waitFor(()=>expect(publish).toHaveBeenCalledWith(expect.objectContaining({revision:2}),expect.objectContaining({tasks:expect.arrayContaining([expect.objectContaining({planned_hours:12})])})));
  expect(definition.tasks[1].planned_hours).toBe(8);expect(apply).not.toHaveBeenCalled();
});

it('conserve le brouillon de publication après conflit et exige une reprise explicite',async()=>{
  const publish=vi.spyOn(planningApi,'publish').mockRejectedValueOnce(new Error('Révision modifiée')).mockResolvedValue({id:'v3',number:3});
  render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);await openVersion();fireEvent.click(screen.getByRole('button',{name:'Créer une nouvelle version depuis v1'}));await screen.findByRole('form',{name:'Publication d’une nouvelle version'});
  fireEvent.change(screen.getByLabelText('Nom de la version'),{target:{value:'Ma version'}});fireEvent.click(screen.getByRole('button',{name:'Publier cette nouvelle version'}));await screen.findByRole('alert');
  vi.mocked(planningApi.template).mockResolvedValue({...template,revision:3,latest_version:{id:'v2',number:2}});fireEvent.click(screen.getByRole('button',{name:'Relire le modèle sans perdre le brouillon'}));await screen.findByRole('region',{name:'Révision actuelle du modèle'});
  expect(publish).toHaveBeenCalledTimes(1);expect((screen.getByLabelText('Nom de la version') as HTMLInputElement).value).toBe('Ma version');fireEvent.click(screen.getByRole('button',{name:'Préparer la publication sur cette révision'}));fireEvent.click(screen.getByRole('button',{name:'Publier cette nouvelle version'}));
  await waitFor(()=>expect(publish).toHaveBeenLastCalledWith(expect.objectContaining({revision:3}),expect.objectContaining({name:'Ma version'})));
});

it('ne mappe les suggestions qu’après choix et lie l’application à l’aperçu affiché',async()=>{
  const apply=vi.spyOn(planningApi,'apply').mockResolvedValue({revision:8});const saved=vi.fn();render(<PlanningTemplatesPanel projectId="p1" onSaved={saved}/>);await openApplication();
  fireEvent.click(screen.getByRole('button',{name:'Calculer l’aperçu des changements'}));await screen.findByRole('region',{name:'Aperçu du modèle'});
  expect(planningApi.preview).toHaveBeenLastCalledWith('p1','v1',expect.objectContaining({expected_revision:7,milestone_mapping:{},update_tasks:false}));expect(apply).not.toHaveBeenCalled();
  fireEvent.click(await screen.findByRole('button',{name:'Choisir la suggestion pour KOM'}));expect(screen.queryByRole('region',{name:'Aperçu du modèle'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Calculer l’aperçu des changements'}));await screen.findByRole('region',{name:'Aperçu du modèle'});expect(planningApi.preview).toHaveBeenLastCalledWith('p1','v1',expect.objectContaining({milestone_mapping:{kom:'m1'}}));
  fireEvent.click(screen.getByRole('button',{name:'Appliquer cet aperçu au projet'}));await waitFor(()=>expect(apply).toHaveBeenCalledWith('p1',preview));expect(saved).toHaveBeenCalledOnce();
});

it('retire l’aperçu après changement de dates, de calendrier, de politique ou de tâches',async()=>{
  render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);await openApplication();
  for(const action of [()=>fireEvent.change(screen.getByLabelText('Début de calcul des prévisions'),{target:{value:'2026-10-06'}}),
    ()=>fireEvent.change(screen.getByLabelText('Politique des dates prévisionnelles'),{target:{value:'replace'}}),
    ()=>fireEvent.click(screen.getByLabelText(/Mettre à jour les tâches actives/)),()=>fireEvent.click(screen.getByRole('button',{name:'Retirer l’exclusion 2026-10-05 du brouillon'}))]){
    fireEvent.click(screen.getByRole('button',{name:'Calculer l’aperçu des changements'}));await screen.findByRole('region',{name:'Aperçu du modèle'});action();expect(screen.queryByRole('button',{name:'Appliquer cet aperçu au projet'})).toBeNull();
  }
});

it('signale un changement de version même sans écart de tâches ou de jalons',async()=>{
  vi.mocked(planningApi.preview).mockResolvedValue({...preview,changes:{changes:[],planned_hours_delta:0,
    calendar:{before:['2026-10-05'],after:['2026-10-05']},template_version_id:{before:'old-version',after:'v1'}}});
  const apply=vi.spyOn(planningApi,'apply');render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);await openApplication();
  fireEvent.click(screen.getByRole('button',{name:'Calculer l’aperçu des changements'}));const result=await screen.findByRole('region',{name:'Aperçu du modèle'});
  expect(within(result).getByText(/Version du planning : changement de version/)).toBeTruthy();
  expect(within(result).getByText(/Calendrier : inchangé/)).toBeTruthy();expect(apply).not.toHaveBeenCalled();
  expect(within(result).getByRole('button',{name:'Appliquer cet aperçu au projet'})).toBeTruthy();
});

it('après conflit relit et prépare un nouvel aperçu, en reprenant le calendrier du collègue si inchangé',async()=>{
  const apply=vi.spyOn(planningApi,'apply').mockRejectedValue(new Error('Planning modifié'));render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);await openApplication();
  fireEvent.change(screen.getByLabelText('Début de calcul des prévisions'),{target:{value:'2026-10-06'}});fireEvent.click(screen.getByRole('button',{name:'Calculer l’aperçu des changements'}));await screen.findByRole('region',{name:'Aperçu du modèle'});fireEvent.click(screen.getByRole('button',{name:'Appliquer cet aperçu au projet'}));await screen.findByRole('alert');expect(screen.queryByRole('region',{name:'Aperçu du modèle'})).toBeNull();
  vi.mocked(planningApi.info).mockResolvedValue({...info,revision:9,excluded_dates:['2026-10-07']});fireEvent.click(screen.getByRole('button',{name:'Relire la révision du projet'}));await screen.findByRole('region',{name:'Révision actuelle du projet'});expect(apply).toHaveBeenCalledOnce();
  fireEvent.click(screen.getByRole('button',{name:'Préparer un nouvel aperçu sur cette révision'}));expect((screen.getByLabelText('Début de calcul des prévisions') as HTMLInputElement).value).toBe('2026-10-06');fireEvent.click(screen.getByRole('button',{name:'Calculer l’aperçu des changements'}));
  await waitFor(()=>expect(planningApi.preview).toHaveBeenLastCalledWith('p1','v1',expect.objectContaining({expected_revision:9,excluded_dates:['2026-10-07']})));
});

it('permet au lecteur un aperçu sans commandes de publication ni application',async()=>{
  vi.mocked(planningApi.info).mockResolvedValue({...info,can_edit:false});vi.mocked(planningApi.templates).mockResolvedValue({items:[template],total:1,offset:0,limit:25,can_manage:false});vi.mocked(planningApi.template).mockResolvedValue({...template,can_manage:false});
  render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);await openApplication();expect(screen.queryByRole('button',{name:'Créer un modèle'})).toBeNull();expect(screen.queryByRole('button',{name:'Modifier les métadonnées du modèle'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Calculer l’aperçu des changements'}));await screen.findByRole('region',{name:'Aperçu du modèle'});expect(screen.queryByRole('button',{name:'Appliquer cet aperçu au projet'})).toBeNull();expect(screen.getByRole('form',{name:'Application du modèle au projet'}).dataset.workspaceDirty).toBeUndefined();
});

it('archive le modèle par un patch minimal et conserve les versions et projets',async()=>{
  const patch=vi.spyOn(planningApi,'patchTemplate').mockResolvedValue({...template,active:false,revision:3});render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);await openVersion();fireEvent.click(screen.getByRole('button',{name:'Modifier les métadonnées du modèle'}));await screen.findByRole('form',{name:'Métadonnées du modèle'});
  fireEvent.click(screen.getByLabelText('Modèle actif'));fireEvent.click(screen.getByRole('button',{name:'Enregistrer les métadonnées du modèle'}));await waitFor(()=>expect(patch).toHaveBeenCalledWith(expect.objectContaining({revision:2}),{active:false}));
});

it('ne propose pas d’appliquer ou republier un modèle archivé',async()=>{
  vi.mocked(planningApi.template).mockResolvedValue({...template,active:false});render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);await openVersion();expect(screen.queryByRole('button',{name:'Préparer l’application de v1'})).toBeNull();expect(screen.queryByRole('button',{name:'Créer une nouvelle version depuis v1'})).toBeNull();
});

it('ignore une ouverture tardive du projet quitté',async()=>{
  let resolve!:(value:TemplateDetail)=>void;vi.mocked(planningApi.template).mockReturnValue(new Promise(done=>{resolve=done;}));const view=render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);
  fireEvent.click(await screen.findByRole('button',{name:'Ouvrir le modèle · Cycle standard'}));view.rerender(<PlanningTemplatesPanel projectId="p2" onSaved={vi.fn()}/>);await waitFor(()=>expect(planningApi.info).toHaveBeenCalledWith('p2',expect.any(AbortSignal)));resolve(template);
  await waitFor(()=>expect(screen.queryByRole('region',{name:'Versions du modèle · Cycle standard'})).toBeNull());
});

it('pagine la définition complète et empêche de publier un cycle de tâches',async()=>{
  const value={...definition,milestones:Array.from({length:25},(_,index)=>({code:`jalon_${index}`,title:`Jalon ${index}`,offset_workdays:null}))};const change=vi.fn();render(<PlanningDefinitionEditor value={value} onChange={change}/>);
  expect(screen.queryByLabelText('Intitulé du jalon 11')).toBeNull();fireEvent.click(within(screen.getByRole('region',{name:'Définition structurée du modèle'})).getAllByRole('button',{name:'Suivant'})[0]);expect(screen.getByLabelText('Intitulé du jalon 11')).toBeTruthy();cleanup();
  render(<PlanningTemplatesPanel projectId="p1" onSaved={vi.fn()}/>);await openVersion();fireEvent.click(screen.getByRole('button',{name:'Créer une nouvelle version depuis v1'}));await screen.findByRole('form',{name:'Publication d’une nouvelle version'});
  fireEvent.change(screen.getByLabelText('Clé du parent de la tâche 1'),{target:{value:'design'}});expect(screen.getAllByText(/cycle de parents interdit/)).toHaveLength(2);expect((screen.getByRole('button',{name:'Publier cette nouvelle version'}) as HTMLButtonElement).disabled).toBe(true);
});
