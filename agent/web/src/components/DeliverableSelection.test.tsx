import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { DeliverableSelection } from './DeliverableSelection';
import { deliverableApi, type CatalogueRow, type DeliverableRow, type SelectionPreview, type TypeVersionDetail } from '../lib/projectDeliverables';
import { identityApi, type ProjectIdentity } from '../lib/projectIdentity';
import { planningApi, type PlanningInfo } from '../lib/projectPlanning';

const head:CatalogueRow={id:'type1',code:'notice',label:'Notice',active:true,revision:3,latest_version:{id:'type-v2',number:2,sha256:'a'.repeat(64),position:0}};
const version:TypeVersionDetail={id:'type-v2',type_id:'type1',number:2,sha256:'a'.repeat(64),definition:{category:'studies',design:true,position:0,checklist:[{code:'notice_visa',label:'Vérifier',milestone_code:'pdr',active:true,is_gate:true,transverse:false,contributes:true,typology_codes:[]}]},published_definition:{}};
const identity:ProjectIdentity={project_id:'p1',code:'QA-001',title:'Recette',status:'active',legacy_client_name:'Client',offer_number:'',revision:1,actual_closure_date:'',members:[],roles:[],responsible:null,client_id:null,agency_id:null,business_unit_id:null,family_id:null,typology_id:'typ1',responsible_id:null,description:'',client_reference:'',client_site:'',client_contact:'',equipment_number:'',quantity:null,start_date:'',planned_end_date:'',standby:false,references:{typ1:{id:'typ1',kind:'typology',code:'machine',label:'Machine',active:true,revision:1}},can_edit:true};
const result:SelectionPreview={project_id:'p1',revision:7,can_edit:true,sha256:'b'.repeat(64),changes:1,operations:[{operation:'create',type_id:'type1',version_id:'type-v2',deliverable_id:null,label:'Notice'}],blockers:[],warnings:[]};
beforeEach(()=>{
  vi.spyOn(identityApi,'read').mockResolvedValue(identity);vi.spyOn(identityApi,'people').mockResolvedValue({items:[],total:0,offset:0,limit:50});
  vi.spyOn(deliverableApi,'types').mockResolvedValue({items:[head],total:1,offset:0,limit:25,can_manage:true});
  vi.spyOn(deliverableApi,'typeVersion').mockImplementation(async(_type,id)=>({...version,id,number:id==='type-v1'?1:2}));
  vi.spyOn(deliverableApi,'typeVersions').mockResolvedValue({items:[{id:'type-v2',number:2,sha256:'a'.repeat(64)},{id:'type-v1',number:1,sha256:'c'.repeat(64)}],total:2,offset:0,limit:25});
  vi.spyOn(deliverableApi,'list').mockResolvedValue({items:[],total:0,offset:0,limit:50,revision:7,can_edit:true});
  vi.spyOn(deliverableApi,'previewSelection').mockResolvedValue(result);vi.spyOn(deliverableApi,'applySelection').mockResolvedValue({revision:8,changed:result.operations,warnings:[]});
  vi.spyOn(planningApi,'info').mockResolvedValue({revision:8,can_edit:true} as PlanningInfo);
  vi.spyOn(planningApi,'milestones').mockResolvedValue({items:[],total:0,offset:0,limit:50,revision:7});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
function view(canEdit=true,active=true){return render(<DeliverableSelection projectId="p1" revision={7} canEdit={canEdit} active={active} onSaved={vi.fn()} onCancel={vi.fn()} onBusy={vi.fn()}/>);}
async function choose(){fireEvent.click(await screen.findByRole('button',{name:'Choisir Notice · V2'}));await screen.findByText('Notice · notice · V2');await waitFor(()=>expect((screen.getByRole('button',{name:'Calculer l’aperçu de la sélection'}) as HTMLButtonElement).disabled).toBe(false));}
async function preview(){await waitFor(()=>expect((screen.getByRole('button',{name:'Calculer l’aperçu de la sélection'}) as HTMLButtonElement).disabled).toBe(false));fireEvent.click(screen.getByRole('button',{name:'Calculer l’aperçu de la sélection'}));return screen.findByRole('region',{name:'Aperçu de la sélection'});}

describe('Sélection des livrables avec aperçu lié',()=>{
  it('applique seulement les paramètres capturés et l’empreinte confirmée',async()=>{
    const saved=vi.fn();render(<DeliverableSelection projectId="p1" revision={7} canEdit active onSaved={saved} onCancel={vi.fn()} onBusy={vi.fn()}/>);await choose();
    expect(screen.getByText(/Typologie projet : Machine/)).toBeTruthy();fireEvent.click(screen.getByLabelText('Exclure explicitement le jalon pdr et ses contrôles'));const region=await preview();
    expect(within(region).getByText('Jalons et contrôles explicitement exclus : pdr.')).toBeTruthy();expect(deliverableApi.applySelection).not.toHaveBeenCalled();fireEvent.click(within(region).getByLabelText('Je confirme les changements de cet aperçu'));fireEvent.click(within(region).getByRole('button',{name:'Appliquer la sélection confirmée'}));
    await waitFor(()=>expect(saved).toHaveBeenCalledOnce());expect(deliverableApi.applySelection).toHaveBeenCalledWith('p1',expect.objectContaining({expected_revision:7,type_version_ids:['type-v2'],typology_id:'typ1',excluded_milestone_codes:['pdr'],milestone_mapping:{}}),'b'.repeat(64));
  });
  it('retire l’aperçu et sa confirmation dès qu’un choix change',async()=>{
    view();await choose();const region=await preview();fireEvent.click(within(region).getByLabelText('Je confirme les changements de cet aperçu'));fireEvent.click(screen.getByLabelText('Désélectionner les types absents de mes choix, en conservant leurs données'));
    expect(screen.queryByRole('region',{name:'Aperçu de la sélection'})).toBeNull();await preview();expect((screen.getByLabelText('Je confirme les changements de cet aperçu') as HTMLInputElement).checked).toBe(false);expect(deliverableApi.applySelection).not.toHaveBeenCalled();
  });
  it('consulte les blocages et vigilances sans autoriser une application',async()=>{
    vi.mocked(deliverableApi.previewSelection).mockResolvedValue({...result,blockers:[{type_id:'type1',code:'pdr',message:'Rattacher ou exclure explicitement ce jalon'}],warnings:[{type_id:'type1',message:'Version projet conservée',retained_version_id:'old-version'}]});view();await choose();await preview();
    expect(screen.getByRole('region',{name:'Blocages de la sélection'}).textContent).toContain('Notice · pdr');expect(screen.getByRole('region',{name:'Vigilances de la sélection'}).textContent).toContain('Version projet conservée');expect((screen.getByRole('button',{name:'Appliquer la sélection confirmée'}) as HTMLButtonElement).disabled).toBe(true);expect(deliverableApi.applySelection).not.toHaveBeenCalled();
  });
  it('permet une version ancienne précise sans substituer la dernière publication',async()=>{
    view();fireEvent.click(await screen.findByRole('button',{name:'Toutes les versions de Notice'}));fireEvent.click(await screen.findByRole('button',{name:'Choisir Notice · publication V1'}));await screen.findByText('Notice · notice · V1');await preview();
    expect(deliverableApi.previewSelection).toHaveBeenCalledWith('p1',expect.objectContaining({type_version_ids:['type-v1']}),expect.any(AbortSignal));expect(deliverableApi.applySelection).not.toHaveBeenCalled();
  });
  it('rattache explicitement le jalon et retire l’exclusion opposée',async()=>{
    vi.mocked(planningApi.milestones).mockResolvedValue({items:[{id:'m1',title:'Revue client',active:true} as never],total:1,offset:0,limit:50,revision:7});view();await choose();fireEvent.click(screen.getByLabelText('Exclure explicitement le jalon pdr et ses contrôles'));fireEvent.click(screen.getByLabelText('Exclure explicitement le jalon pdr et ses contrôles'));await screen.findByRole('option',{name:'Revue client'});
    fireEvent.change(screen.getByLabelText('Jalon projet pour pdr'),{target:{value:'m1'}});const region=await preview();expect(within(region).getByText('pdr → Revue client')).toBeTruthy();expect(deliverableApi.previewSelection).toHaveBeenCalledWith('p1',expect.objectContaining({milestone_mapping:{pdr:'m1'},excluded_milestone_codes:[]}),expect.any(AbortSignal));
  });
  it('conserve les choix après conflit puis exige comparaison, nouvel aperçu et reconfirmation',async()=>{
    vi.mocked(deliverableApi.applySelection).mockRejectedValueOnce(new Error('Aperçu périmé'));view();await choose();fireEvent.click(screen.getByLabelText('Exclure explicitement le jalon pdr et ses contrôles'));await preview();fireEvent.click(screen.getByLabelText('Je confirme les changements de cet aperçu'));fireEvent.click(screen.getByRole('button',{name:'Appliquer la sélection confirmée'}));await screen.findByRole('alert');
    expect(screen.queryByRole('region',{name:'Aperçu de la sélection'})).toBeNull();expect(screen.getByText('Notice · notice · V2')).toBeTruthy();fireEvent.click(screen.getByRole('button',{name:'Relire et comparer le projet'}));await screen.findByRole('region',{name:'Comparaison de la sélection'});fireEvent.click(screen.getByRole('button',{name:'Préparer mes choix sur cette révision'}));vi.mocked(deliverableApi.previewSelection).mockResolvedValue({...result,revision:8});await preview();
    expect(deliverableApi.previewSelection).toHaveBeenLastCalledWith('p1',expect.objectContaining({expected_revision:8,type_version_ids:['type-v2'],excluded_milestone_codes:['pdr']}),expect.any(AbortSignal));expect((screen.getByLabelText('Je confirme les changements de cet aperçu') as HTMLInputElement).checked).toBe(false);expect(deliverableApi.applySelection).toHaveBeenCalledOnce();
  });
  it('permet l’aperçu lecteur sans commande ni marqueur de brouillon',async()=>{
    vi.mocked(deliverableApi.previewSelection).mockResolvedValue({...result,can_edit:false});view(false);await choose();await preview();expect(screen.queryByRole('button',{name:'Appliquer la sélection confirmée'})).toBeNull();expect(screen.getByRole('form',{name:'Sélection des livrables'}).dataset.workspaceDirty).toBeUndefined();expect(deliverableApi.applySelection).not.toHaveBeenCalled();
  });
  it('borne et pagine le catalogue sans perdre une version déjà choisie',async()=>{
    vi.mocked(deliverableApi.types).mockImplementation(async(options={})=>({items:[head],total:60,offset:options.offset||0,limit:25,can_manage:true}));view();await choose();fireEvent.click(within(screen.getByRole('group',{name:'Pages du catalogue de sélection'})).getByRole('button',{name:'Suivant'}));await waitFor(()=>expect(deliverableApi.types).toHaveBeenLastCalledWith(expect.objectContaining({offset:25,limit:25,typology_id:'typ1'})));expect(screen.getByText('Notice · notice · V2')).toBeTruthy();
  });
  it('refuse une réponse d’aperçu liée à un autre projet ou une autre révision',async()=>{
    vi.mocked(deliverableApi.previewSelection).mockResolvedValue({...result,project_id:'other'});view();await choose();fireEvent.click(screen.getByRole('button',{name:'Calculer l’aperçu de la sélection'}));await screen.findByRole('alert');expect(screen.queryByRole('region',{name:'Aperçu de la sélection'})).toBeNull();expect(deliverableApi.applySelection).not.toHaveBeenCalled();
  });
  it('annule la lecture de version tardive à la fermeture',async()=>{
    let resolve!:(value:TypeVersionDetail)=>void;let signal:AbortSignal|undefined;vi.mocked(deliverableApi.typeVersion).mockImplementation((_type,_version,input)=>{signal=input;return new Promise(done=>{resolve=done;});});const rendered=view();fireEvent.click(await screen.findByRole('button',{name:'Choisir Notice · V2'}));rendered.unmount();expect(signal?.aborted).toBe(true);resolve(version);expect(deliverableApi.previewSelection).not.toHaveBeenCalled();
  });
  it('adopte une cible explicite et interdit les fiches déjà rattachées à un autre type',async()=>{
    const manual={id:'manual1',title:'Notice client existante',active:true,type:null,document_status:'draft'} as DeliverableRow;
    const other={...manual,id:'other1',title:'Autre pièce',type:{id:'other-type',code:'other',label:'Autre type'}};
    vi.mocked(deliverableApi.list).mockResolvedValue({items:[manual,other],total:2,offset:0,limit:50,revision:7,can_edit:true});view();await choose();
    fireEvent.click(screen.getByText('Associer une fiche existante (facultatif)'));await screen.findByRole('option',{name:'Notice client existante · Personnalisé · Brouillon'});expect((screen.getByRole('option',{name:'Autre pièce · Autre type · Brouillon'}) as HTMLOptionElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText('Fiche existante pour Notice'),{target:{value:'manual1'}});await preview();expect(deliverableApi.previewSelection).toHaveBeenCalledWith('p1',expect.objectContaining({existing_mapping:{type1:'manual1'}}),expect.any(AbortSignal));
  });
  it('annule un aperçu tardif lorsque le panneau devient inactif',async()=>{
    let resolve!:(value:SelectionPreview)=>void;let signal:AbortSignal|undefined;vi.mocked(deliverableApi.previewSelection).mockImplementation((_id,_inputs,input)=>{signal=input;return new Promise(done=>{resolve=done;});});const rendered=view();await choose();fireEvent.click(screen.getByRole('button',{name:'Calculer l’aperçu de la sélection'}));
    rendered.rerender(<DeliverableSelection projectId="p1" revision={7} canEdit active={false} onSaved={vi.fn()} onCancel={vi.fn()} onBusy={vi.fn()}/>);expect(signal?.aborted).toBe(true);resolve(result);await waitFor(()=>expect(screen.queryByRole('region',{name:'Aperçu de la sélection'})).toBeNull());expect(deliverableApi.applySelection).not.toHaveBeenCalled();
  });
  it('ne lit rien tant que le panneau est inactif',()=>{view(true,false);expect(identityApi.read).not.toHaveBeenCalled();expect(deliverableApi.types).not.toHaveBeenCalled();});
});
