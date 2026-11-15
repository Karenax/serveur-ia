import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ProjectDeliverablesPanel } from './ProjectDeliverablesPanel';
import { deliverableApi, type DeliverableDetail, type DeliverablePage, type DeliverableRow } from '../lib/projectDeliverables';
import { identityApi } from '../lib/projectIdentity';
import { planningApi } from '../lib/projectPlanning';

const progress={completed:1,total:2,percentage:50,state:'pending'};
const row:DeliverableRow={id:'d1',project_id:'p1',title:'Notice',legacy_status:'done',active:true,document_status:'draft',responsible_id:null,verifier_id:null,type_version_id:null,category:'custom',type:null,progress,transverse_progress:{...progress,total:0,completed:0,percentage:0,state:'not_applicable'},latest_version:null,milestone_ids:[]};
const detail:DeliverableDetail={...row,revision:7,comment:'Initial',latest_version_id:null,can_edit:true,can_verify:true,checklist:[],validation_blockers:[]};
const page:DeliverablePage={items:[row],total:1,offset:0,limit:25,revision:7,can_edit:true};
beforeEach(()=>{
  vi.spyOn(deliverableApi,'list').mockResolvedValue(page);vi.spyOn(deliverableApi,'detail').mockResolvedValue(detail);
  vi.spyOn(identityApi,'people').mockResolvedValue({items:[],total:0,offset:0,limit:50});
  vi.spyOn(planningApi,'milestones').mockResolvedValue({items:[],total:0,offset:0,limit:50,revision:7});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function open(){fireEvent.click(await screen.findByRole('button',{name:'Consulter · Notice'}));return screen.findByRole('form',{name:'Édition du livrable'});}

it('ouvre la fiche actuelle depuis une revue sans traiter son instantané comme un visa de jalon',async()=>{
  vi.mocked(deliverableApi.detail).mockResolvedValue({...detail,latest_version_id:'v2',can_edit:false,can_verify:false});
  const handled=vi.fn();render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()} focus={{requestId:2,deliverableId:'d1',checkId:'',milestoneId:'',milestoneTitle:'Revue · Nom capturé',version:null,origin:'review'}} onFocusHandled={handled}/>);
  await screen.findByRole('region',{name:'Livrable ouvert depuis la revue'});
  expect(screen.getByText(/Cette fiche présente le livrable actuel/)).toBeTruthy();
  expect(screen.getByRole('button',{name:'Fiche'}).getAttribute('aria-pressed')).toBe('true');
  expect(screen.queryByText('Contrôle absent ou retiré depuis cette lecture.')).toBeNull();
  expect(screen.queryByRole('alert')).toBeNull();expect(handled).toHaveBeenCalledOnce();
  expect(deliverableApi.detail).toHaveBeenCalledWith('p1','d1',expect.any(AbortSignal));
  expect(screen.queryByRole('button',{name:'Enregistrer le livrable'})).toBeNull();
});

it('ouvre un livrable depuis le cockpit sans inventer un visa absent ni une version observée',async()=>{
  vi.mocked(deliverableApi.detail).mockResolvedValue({...detail,latest_version_id:'v2'});
  render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()} focus={{requestId:1,deliverableId:'d1',checkId:'',milestoneId:'m1',milestoneTitle:'FAT',version:null,origin:'cockpit'}} onFocusHandled={vi.fn()}/>);
  await screen.findByRole('region',{name:'Livrable ouvert depuis le cockpit'});
  expect(await screen.findByRole('form',{name:'Édition du livrable'})).toBeTruthy();
  expect(screen.queryByText('Contrôle absent ou retiré depuis cette lecture.')).toBeNull();
  expect(screen.queryByRole('alert')).toBeNull();
});

it('ouvre le contrôle exact du jalon, recherche son code et signale une publication concurrente',async()=>{
  const check={id:'c1',code:'visa_pdr',scope_key:'m1',milestone_id:'m1',label:'Visa PDR',position:0,is_gate:true,transverse:false,contributes:true,active:true,completed:false,completed_version_id:null,completed_by:null,completed_at:null,comment:'',proof:''};vi.mocked(deliverableApi.detail).mockResolvedValue({...detail,latest_version_id:'v2',checklist:[check]});vi.spyOn(deliverableApi,'checklist').mockResolvedValue({items:[check],total:1,offset:0,limit:25,revision:7});const handled=vi.fn();render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()} focus={{requestId:1,deliverableId:'d1',checkId:'c1',milestoneId:'m1',milestoneTitle:'Revue PDR',version:{id:'v1',number:1,filename:'notice-v1.pdf',reference:'BE A'}}} onFocusHandled={handled}/>);await screen.findByRole('region',{name:'Contrôle ouvert depuis le jalon'});expect(screen.getByRole('alert').textContent).toContain('La publication a changé');await screen.findByText('Contrôle ouvert depuis le jalon',{selector:'small'});expect(deliverableApi.checklist).toHaveBeenCalledWith('p1','d1',expect.objectContaining({search:'visa_pdr'}));expect(handled).toHaveBeenCalledOnce();expect(screen.queryByRole('form',{name:'Modifier le point · Visa PDR'})).toBeNull();
});
it('garde le brouillon existant si l’ouverture ciblée est refusée',async()=>{
  vi.spyOn(window,'confirm').mockReturnValue(false);const saved=vi.fn();const view=render(<ProjectDeliverablesPanel projectId="p1" onSaved={saved}/>);await open();fireEvent.change(screen.getByLabelText('Intitulé du livrable'),{target:{value:'À conserver'}});const handled=vi.fn();view.rerender(<ProjectDeliverablesPanel projectId="p1" onSaved={saved} focus={{requestId:1,deliverableId:'d2',checkId:'c2',milestoneId:'m1',milestoneTitle:'PDR',version:null}} onFocusHandled={handled}/>);await screen.findByText('Ouverture du contrôle annulée ; votre saisie est conservée.');expect((screen.getByLabelText('Intitulé du livrable') as HTMLInputElement).value).toBe('À conserver');expect(deliverableApi.detail).toHaveBeenCalledTimes(1);expect(handled).toHaveBeenCalledOnce();
});
it('refuse une fiche cible appartenant à un autre projet',async()=>{
  vi.mocked(deliverableApi.detail).mockResolvedValue({...detail,project_id:'other'});render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()} focus={{requestId:1,deliverableId:'d1',checkId:'c1',milestoneId:'m1',milestoneTitle:'PDR',version:null}}/>);await screen.findByText('Fiche reçue pour un autre projet ou livrable.');expect(screen.queryByRole('region',{name:'Contrôle ouvert depuis le jalon'})).toBeNull();
});

describe('Livrables : liste et fiche',()=>{
  it('distingue travail terminé, brouillon documentaire et progressions',async()=>{
    render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);
    const table=await screen.findByRole('table');expect(within(table).getByText('Brouillon')).toBeTruthy();expect(within(table).getByText('Travail : Terminé')).toBeTruthy();
    expect(within(table).getByRole('progressbar',{name:'Points vérifiés'}).getAttribute('value')).toBe('1');expect(within(table).getByText('Contrôles communs : Sans point applicable')).toBeTruthy();
  });
  it('pagine et applique les filtres sur le serveur',async()=>{
    vi.mocked(deliverableApi.list).mockImplementation(async(_id,options={})=>({...page,total:60,offset:options.offset||0}));
    render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);await screen.findByRole('button',{name:'Consulter · Notice'});
    fireEvent.click(within(screen.getByRole('group',{name:'Pages des livrables'})).getByRole('button',{name:'Suivant'}));
    await waitFor(()=>expect(deliverableApi.list).toHaveBeenLastCalledWith('p1',expect.objectContaining({offset:25,limit:25})));
    fireEvent.change(screen.getByLabelText('Rechercher un livrable'),{target:{value:'Étude'}});fireEvent.change(screen.getByLabelText('Statut documentaire'),{target:{value:'to_verify'}});fireEvent.click(screen.getByLabelText('Inclure les livrables désélectionnés'));
    await waitFor(()=>expect(deliverableApi.list).toHaveBeenLastCalledWith('p1',expect.objectContaining({search:'Étude',status:'to_verify',include_inactive:true,offset:0})));
  });
  it('crée et actualise immédiatement la liste avec une seule commande révisionnée',async()=>{
    const saved=vi.fn();const create=vi.spyOn(deliverableApi,'create').mockImplementation(async()=>{vi.mocked(deliverableApi.list).mockResolvedValue({...page,revision:8,items:[row,{...row,id:'new',title:'Rapport'}],total:2});return {id:'new',revision:8};});
    render(<ProjectDeliverablesPanel projectId="p1" onSaved={saved}/>);fireEvent.click(await screen.findByRole('button',{name:'Nouveau livrable'}));fireEvent.change(screen.getByLabelText('Intitulé du livrable'),{target:{value:'Rapport'}});fireEvent.click(screen.getByRole('button',{name:'Enregistrer le livrable'}));
    await screen.findByRole('button',{name:'Consulter · Rapport'});expect(create).toHaveBeenCalledWith('p1',7,{title:'Rapport',responsible_id:null,verifier_id:null});expect(saved).toHaveBeenCalledOnce();
  });
  it('sauvegarde les seuls champs modifiés et garde le statut historique',async()=>{
    const patch=vi.spyOn(deliverableApi,'patch').mockResolvedValue({revision:8});render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);await open();
    fireEvent.change(screen.getByLabelText('Commentaire du livrable'),{target:{value:'Mon commentaire'}});fireEvent.click(screen.getByRole('button',{name:'Enregistrer le livrable'}));
    await waitFor(()=>expect(patch).toHaveBeenCalledWith('p1','d1',7,{comment:'Mon commentaire'}));
  });
  it('compare un conflit sans réécrire le travail du collègue ni perdre le brouillon',async()=>{
    const patch=vi.spyOn(deliverableApi,'patch').mockRejectedValueOnce(new Error('Révision modifiée')).mockResolvedValue({revision:9});
    render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);const form=await open();fireEvent.change(screen.getByLabelText('Intitulé du livrable'),{target:{value:'Ma notice'}});expect(form.dataset.workspaceDirty).toBe('true');fireEvent.click(screen.getByRole('button',{name:'Enregistrer le livrable'}));await screen.findByRole('alert');
    vi.mocked(deliverableApi.detail).mockResolvedValue({...detail,revision:8,comment:'Commentaire du collègue'});fireEvent.click(screen.getByRole('button',{name:'Recharger et comparer sans perdre ma saisie'}));await screen.findByRole('region',{name:'Comparaison avec la dernière révision'});expect(patch).toHaveBeenCalledOnce();expect((screen.getByRole('button',{name:'Enregistrer le livrable'}) as HTMLButtonElement).disabled).toBe(true);
    fireEvent.click(screen.getByRole('button',{name:'Préparer mon brouillon sur cette révision'}));expect((screen.getByLabelText('Commentaire du livrable') as HTMLTextAreaElement).value).toBe('Commentaire du collègue');fireEvent.click(screen.getByRole('button',{name:'Enregistrer le livrable'}));
    await waitFor(()=>expect(patch).toHaveBeenLastCalledWith('p1','d1',8,{title:'Ma notice'}));
  });
  it('conserve une création en conflit puis prépare explicitement la nouvelle révision',async()=>{
    const create=vi.spyOn(deliverableApi,'create').mockRejectedValueOnce(new Error('Conflit')).mockResolvedValue({id:'new',revision:10});
    render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Nouveau livrable'}));fireEvent.change(screen.getByLabelText('Intitulé du livrable'),{target:{value:'Nouvelle étude'}});fireEvent.click(screen.getByRole('button',{name:'Enregistrer le livrable'}));await screen.findByRole('alert');
    vi.mocked(deliverableApi.list).mockResolvedValue({...page,revision:9});fireEvent.click(screen.getByRole('button',{name:'Recharger et comparer sans perdre ma saisie'}));await screen.findByRole('region',{name:'Comparaison avec la dernière révision'});fireEvent.click(screen.getByRole('button',{name:'Préparer mon brouillon sur cette révision'}));expect((screen.getByLabelText('Intitulé du livrable') as HTMLInputElement).value).toBe('Nouvelle étude');fireEvent.click(screen.getByRole('button',{name:'Enregistrer le livrable'}));await waitFor(()=>expect(create).toHaveBeenLastCalledWith('p1',9,expect.objectContaining({title:'Nouvelle étude'})));
  });
  it('consulte en lecture seule sans commande ni marqueur de brouillon',async()=>{
    vi.mocked(deliverableApi.list).mockResolvedValue({...page,can_edit:false});vi.mocked(deliverableApi.detail).mockResolvedValue({...detail,can_edit:false,can_verify:false});render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);const form=await open();
    expect(form.dataset.workspaceDirty).toBeUndefined();expect((screen.getByLabelText('Intitulé du livrable') as HTMLInputElement).disabled).toBe(true);expect(screen.queryByRole('button',{name:'Enregistrer le livrable'})).toBeNull();expect(screen.queryByRole('button',{name:'Nouveau livrable'})).toBeNull();expect(screen.queryByRole('button',{name:'Enregistrer le statut du travail'})).toBeNull();
  });
  it('ignore une ouverture tardive du projet quitté',async()=>{
    let resolve!:(value:DeliverableDetail)=>void;vi.mocked(deliverableApi.detail).mockReturnValue(new Promise(done=>{resolve=done;}));const view=render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);fireEvent.click(await screen.findByRole('button',{name:'Consulter · Notice'}));view.rerender(<ProjectDeliverablesPanel projectId="p2" onSaved={vi.fn()}/>);resolve(detail);await waitFor(()=>expect(deliverableApi.list).toHaveBeenCalledWith('p2',expect.anything()));expect(screen.queryByRole('form',{name:'Édition du livrable'})).toBeNull();
  });
  it('suspend les lectures d’un onglet masqué et conserve sa saisie',async()=>{
    const saved=vi.fn();const view=render(<ProjectDeliverablesPanel projectId="p1" active={false} onSaved={saved}/>);await new Promise(resolve=>setTimeout(resolve,200));expect(deliverableApi.list).not.toHaveBeenCalled();expect(identityApi.people).not.toHaveBeenCalled();
    view.rerender(<ProjectDeliverablesPanel projectId="p1" active onSaved={saved}/>);await open();fireEvent.change(screen.getByLabelText('Intitulé du livrable'),{target:{value:'Brouillon'}});view.rerender(<ProjectDeliverablesPanel projectId="p1" active={false} onSaved={saved}/>);view.rerender(<ProjectDeliverablesPanel projectId="p1" active onSaved={saved}/>);expect((screen.getByLabelText('Intitulé du livrable') as HTMLInputElement).value).toBe('Brouillon');
  });
  it('protège le brouillon lors de la fermeture et du changement de rubrique',async()=>{
    const confirm=vi.spyOn(window,'confirm').mockReturnValue(false);render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);await open();fireEvent.change(screen.getByLabelText('Intitulé du livrable'),{target:{value:'À conserver'}});fireEvent.click(screen.getByRole('button',{name:'Fermer le livrable'}));expect(confirm).toHaveBeenCalledOnce();fireEvent.click(screen.getByRole('button',{name:'Contrôles et validation'}));expect((screen.getByLabelText('Intitulé du livrable') as HTMLInputElement).value).toBe('À conserver');
  });
  it('empêche les deux formulaires de se remplacer leurs brouillons',async()=>{
    render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);await open();fireEvent.change(screen.getByLabelText('Intitulé du livrable'),{target:{value:'Brouillon'}});expect((screen.getByLabelText('Statut du travail') as HTMLSelectElement).disabled).toBe(true);fireEvent.change(screen.getByLabelText('Intitulé du livrable'),{target:{value:'Notice'}});fireEvent.change(screen.getByLabelText('Statut du travail'),{target:{value:'in_progress'}});expect((screen.getByLabelText('Intitulé du livrable') as HTMLInputElement).disabled).toBe(true);
  });
  it('conserve et compare le statut de travail en conflit sans accorder de visa',async()=>{
    const work=vi.spyOn(deliverableApi,'workStatus').mockRejectedValueOnce(new Error('Révision modifiée')).mockResolvedValue({revision:9});render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);await open();fireEvent.change(screen.getByLabelText('Statut du travail'),{target:{value:'in_progress'}});fireEvent.click(screen.getByRole('button',{name:'Enregistrer le statut du travail'}));await screen.findByRole('alert');vi.mocked(deliverableApi.detail).mockResolvedValue({...detail,revision:8,legacy_status:'todo'});fireEvent.click(screen.getByRole('button',{name:'Comparer le statut actuel'}));await screen.findByRole('region',{name:'Comparaison du statut de travail'});expect(work).toHaveBeenCalledOnce();fireEvent.click(screen.getByRole('button',{name:'Préparer ce choix sur la révision actuelle'}));fireEvent.click(screen.getByRole('button',{name:'Enregistrer le statut du travail'}));await waitFor(()=>expect(work).toHaveBeenLastCalledWith('p1','d1',8,'in_progress'));
  });
  it('verrouille fermeture et navigation pendant une commande en cours',async()=>{
    let resolve!:(value:{revision:number})=>void;vi.spyOn(deliverableApi,'patch').mockReturnValue(new Promise(done=>{resolve=done;}));
    render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);await open();fireEvent.change(screen.getByLabelText('Commentaire du livrable'),{target:{value:'À enregistrer'}});fireEvent.click(screen.getByRole('button',{name:'Enregistrer le livrable'}));
    expect((screen.getByRole('button',{name:'Fermer le livrable'}) as HTMLButtonElement).disabled).toBe(true);expect((screen.getByRole('button',{name:'Contrôles et validation'}) as HTMLButtonElement).disabled).toBe(true);
    resolve({revision:8});await waitFor(()=>expect((screen.getByRole('button',{name:'Fermer le livrable'}) as HTMLButtonElement).disabled).toBe(false));
  });
  it('protège le brouillon de checklist et verrouille toutes les rubriques pendant le visa',async()=>{
    const check={id:'c1',code:'lecture',scope_key:'',milestone_id:null,label:'Lecture',position:0,is_gate:true,transverse:false,contributes:true,active:true,completed:false,completed_version_id:null,completed_by:null,completed_at:null,comment:'',proof:''};
    vi.mocked(deliverableApi.detail).mockResolvedValue({...detail,latest_version_id:'v1',checklist:[check]});vi.spyOn(deliverableApi,'checklist').mockResolvedValue({items:[check],total:1,offset:0,limit:25,revision:7});
    let resolve!:(value:{revision:number})=>void;vi.spyOn(deliverableApi,'patchCheck').mockReturnValue(new Promise(done=>{resolve=done;}));const confirm=vi.spyOn(window,'confirm').mockReturnValue(false);
    render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);await open();fireEvent.click(screen.getByRole('button',{name:'Contrôles et validation'}));fireEvent.click(await screen.findByRole('button',{name:'Modifier · Lecture'}));fireEvent.change(screen.getByLabelText('Preuve du point'),{target:{value:'Lecture V1 effectuée'}});fireEvent.click(screen.getByRole('button',{name:'Valider le document'}));expect(confirm).toHaveBeenCalledOnce();expect(screen.getByLabelText('Preuve du point')).toBeTruthy();
    fireEvent.click(screen.getByLabelText('Je confirme ce visa humain pour la version affichée'));fireEvent.click(screen.getByRole('button',{name:'Enregistrer le point'}));expect((screen.getByRole('button',{name:'Fermer le livrable'}) as HTMLButtonElement).disabled).toBe(true);expect((screen.getByRole('button',{name:'Valider le document'}) as HTMLButtonElement).disabled).toBe(true);resolve({revision:8});await waitFor(()=>expect((screen.getByRole('button',{name:'Fermer le livrable'}) as HTMLButtonElement).disabled).toBe(false));
  });
  it('protège le fichier choisi et verrouille la navigation pendant sa publication',async()=>{
    vi.spyOn(deliverableApi,'versions').mockResolvedValue({items:[],total:0,offset:0,limit:25,revision:7});let resolve!:(value:{revision:number})=>void;vi.spyOn(deliverableApi,'upload').mockReturnValue(new Promise(done=>{resolve=done;}));const confirm=vi.spyOn(window,'confirm').mockReturnValue(false);
    render(<ProjectDeliverablesPanel projectId="p1" onSaved={vi.fn()}/>);await open();fireEvent.click(screen.getByRole('button',{name:'Fichiers'}));fireEvent.click(await screen.findByRole('button',{name:'Publier une version'}));fireEvent.change(screen.getByLabelText('Référence de la version'),{target:{value:'BE-A'}});fireEvent.change(screen.getByLabelText('Fichier à publier'),{target:{files:[new File(['preuve'],'notice.pdf')]}});fireEvent.click(screen.getByRole('button',{name:'Historique'}));expect(confirm).not.toHaveBeenCalled();expect(screen.getByRole('form',{name:'Nouvelle version de fichier'})).toBeTruthy();fireEvent.click(screen.getByLabelText('Je confirme ce fichier et la remise à zéro des visas'));fireEvent.click(screen.getByRole('button',{name:'Publier le fichier'}));expect((screen.getByRole('button',{name:'Fermer le livrable'}) as HTMLButtonElement).disabled).toBe(true);expect((screen.getByRole('button',{name:'Historique'}) as HTMLButtonElement).disabled).toBe(true);resolve({revision:8});await waitFor(()=>expect((screen.getByRole('button',{name:'Fermer le livrable'}) as HTMLButtonElement).disabled).toBe(false));
  });
});
