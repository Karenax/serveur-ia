import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ProjectDocumentsPanel } from './ProjectDocumentsPanel';
import { documentApi, type DocumentDiscovery, type DocumentPreview, type DocumentWorkspace } from '../lib/projectDocuments';
import { documentJobApi } from '../lib/projectDocumentJobs';

const state:DocumentWorkspace={project_id:'p1',identity_revision:2,planning_revision:4,values_sha256:'b'.repeat(64),
  values:{project_code:'AIRB26LTH0205-A',description:'LED 2026'},origins:{project_code:{kind:'project',record_id:'p1',attribute:'code'},description:{kind:'project',record_id:'p1',attribute:'title'}},
  fields:{project_code:{label:"Numéro d'affaire",edit_scope:null},description:{label:'Description / désignation',edit_scope:'project'}},
  missing_fields:[],oversized_fields:[],warnings:[],overrides_scope:'one_document',read_only:true,
  templates:[{id:'ce_request',label:'Demande de CE',format:'DOCX',fields:['project_code'],cells:[],bookmarks:[['Affaire','project_code']],sheet_name:null},
    {id:'user_manual',label:"Notice d'utilisation",format:'DOCM',fields:['description'],cells:[],bookmarks:[['Désignation','description']],sheet_name:null}],
  links:{items:[{id:'l1',code:'affaire',label:'Dossier affaire',path:'V:\\Projet',order:1}],total:1,offset:0,limit:100},
  file_access:{status:'configured',detail:''},can_prepare_copy:true,publication:'explicit_separate_command',batch_available:false};
const preview:DocumentPreview={document_id:'ce_request',format:'DOCX',source_sha256:'a'.repeat(64),link_sha256:'e'.repeat(64),values_sha256:'b'.repeat(64),size_bytes:2048,
  source:{project_id:'p1',link_id:'l1',relative_path:'demande.docx',filename:'demande.docx',sha256:'a'.repeat(64)},field_values:state,
  part:'word/document.xml',sheet:null,targets:[{kind:'bookmark',target:'Affaire',field:'project_code',present:true,available:true,
    existing_value:'Ancien projet',proposed_value:'AIRB26LTH0205-A',blockers:[]}],missing_fields:[],missing_targets:[],blockers:[],
  can_prepare:true,can_prepare_copy:true,macro_parts:{},unmapped_fields:[],output_filename:'AIRB26LTH0205-A-Demande de CE.docx',output_filename_error:null};
beforeEach(()=>{
  vi.spyOn(documentApi,'workspace').mockResolvedValue(structuredClone(state));
  vi.spyOn(documentApi,'preview').mockResolvedValue(structuredClone(preview));
  vi.spyOn(documentApi,'copy').mockResolvedValue({blob:new Blob(['copie']),filename:preview.output_filename!,sha256:'c'.repeat(64)});
  vi.spyOn(documentApi,'discover').mockResolvedValue(structuredClone(discovered));
  vi.spyOn(documentJobApi,'list').mockResolvedValue({available:true,worker:{state:'ready',enabled:true,running:true,can_submit:true,error:''},items:[],total:0,offset:0,limit:20});
  vi.spyOn(URL,'createObjectURL').mockReturnValue('blob:document');vi.spyOn(URL,'revokeObjectURL').mockImplementation(()=>{});
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
async function choose(){await screen.findByRole('radio',{name:/Demande de CE/});
  fireEvent.change(screen.getByLabelText('Dossier ou fichier du projet'),{target:{value:'l1'}});
  fireEvent.change(screen.getByLabelText('Fichier de la trame dans ce lien'),{target:{value:'demande.docx'}});}
async function inspect(){await choose();fireEvent.click(screen.getByRole('button',{name:'Afficher l’aperçu'}));
  await screen.findByRole('region',{name:'Aperçu des informations à remplir'});}
const confirm=()=>fireEvent.click(screen.getByLabelText('J’ai vérifié les informations proposées pour cette copie.'));

it('ne consulte aucun lot avant l’activation du schéma documentaire',async()=>{
  render(<ProjectDocumentsPanel projectId="p1"/>);await choose();
  expect(screen.queryByRole('region',{name:'Préparation par lot'})).toBeNull();expect(documentJobApi.list).not.toHaveBeenCalled();
});
it('raccorde le lot à la relecture de l’aperçu et fige les choix du bon projet',async()=>{
  vi.mocked(documentApi.workspace).mockResolvedValue({...state,batch_available:true});
  vi.spyOn(documentApi,'draft').mockResolvedValue({available:true,revision:6,version_id:'d6',link_id:'l1',relative_path:'autre.docx',overrides:{},selected_link:null,warnings:[]});
  render(<ProjectDocumentsPanel projectId="p1"/>);await inspect();const batch=screen.getByRole('region',{name:'Préparation par lot'});
  const add=within(batch).getByRole('button',{name:'Ajouter la trame vérifiée au lot'}) as HTMLButtonElement;
  expect(add.disabled).toBe(true);confirm();expect(add.disabled).toBe(false);fireEvent.click(add);
  await within(batch).findByText('1 / 8 trame(s) sélectionnée(s)');
  expect(documentApi.draft).toHaveBeenCalledWith('p1','ce_request',expect.any(AbortSignal));
  expect((screen.getByLabelText('Fichier de la trame dans ce lien') as HTMLInputElement).value).toBe('demande.docx');
  expect(documentJobApi.list).toHaveBeenCalledWith('p1',0,expect.any(AbortSignal));expect(documentApi.copy).not.toHaveBeenCalled();
});
const discovered:DocumentDiscovery={project_id:'p1',link_id:'l1',document_id:'ce_request',rule_sha256:'f'.repeat(64),
  rule:{relative_paths:['04 qualite/06 ce'],filename_patterns:['fiche demande declaration ce'],excluded_tokens:['old'],preferred_version:10},
  status:'completed',examined:{entries:8,files:4,directories:3},total:null,bounds:[],skipped:{},ambiguous:false,
  recommended_path:'04 Qualité/06 CE/Fiche demande déclaration CE V10.docx',elapsed_seconds:.5,read_only:true,requires_manual_choice:true,
  candidates:[{relative_path:'04 Qualité/06 CE/Fiche demande déclaration CE V10.docx',filename:'Fiche demande déclaration CE V10.docx',
    size_bytes:2048,modified_ns:1,matched_paths:['04 qualite/06 ce'],matched_patterns:['fiche demande declaration ce'],version:10,
    version_origin:'explicit',rank:0,direct_file_link:false,requires_preview:true}]};

async function search(){fireEvent.click(screen.getByRole('button',{name:'Rechercher les trames dans ce lien'}));
  return screen.findByRole('region',{name:'Trames trouvées dans le lien projet'});}

it('montre les correspondances sans choisir automatiquement et impose un nouvel aperçu après le choix',async()=>{
  render(<ProjectDocumentsPanel projectId="p1"/>);await inspect();confirm();fireEvent.click(screen.getByRole('button',{name:'Préparer la copie'}));
  await screen.findByRole('link',{name:/Télécharger AIRB26/});const results=await search();
  expect(documentApi.discover).toHaveBeenCalledWith('p1','ce_request','l1',expect.any(AbortSignal));
  expect(within(results).getByText(/1 candidat.*4 fichier.*3 dossier/)).toBeTruthy();
  expect(within(results).getByText(/Indice 10 indiqué dans le nom/)).toBeTruthy();
  expect((screen.getByLabelText('Fichier de la trame dans ce lien') as HTMLInputElement).value).toBe('demande.docx');
  expect(screen.queryByRole('link',{name:/Télécharger/})).toBeNull();expect(URL.revokeObjectURL).toHaveBeenCalled();
  fireEvent.click(within(results).getByRole('button',{name:/Choisir la trame/}));
  expect((screen.getByLabelText('Fichier de la trame dans ce lien') as HTMLInputElement).value).toBe(discovered.candidates[0].relative_path);
  expect(screen.queryByRole('region',{name:'Aperçu des informations à remplir'})).toBeNull();
  expect(screen.getByText('Trame sélectionnée. Affichez l’aperçu pour vérifier son contenu.')).toBeTruthy();
  vi.mocked(documentApi.preview).mockResolvedValue({...preview,source:{...preview.source,relative_path:discovered.candidates[0].relative_path}});
  fireEvent.click(screen.getByRole('button',{name:'Afficher l’aperçu'}));await screen.findByRole('region',{name:'Aperçu des informations à remplir'});
  expect(documentApi.preview).toHaveBeenLastCalledWith('p1',expect.objectContaining({relative_path:discovered.candidates[0].relative_path}),expect.any(AbortSignal));
});

it('explique une recherche partielle et les rangs ambigus sans inventer de pourcentage',async()=>{
  vi.mocked(documentApi.discover).mockResolvedValue({...discovered,status:'limited',bounds:['entries'],ambiguous:true,recommended_path:null,
    candidates:[discovered.candidates[0],{...discovered.candidates[0],relative_path:'copie.docx',filename:'Copie.docx',version_origin:'name_numbers'}]});
  render(<ProjectDocumentsPanel projectId="p1"/>);await choose();const results=await search();
  expect(within(results).getByText(/limite de nombre d’entrées atteinte/)).toBeTruthy();
  expect(within(results).getByText(/Plusieurs correspondances possibles/)).toBeTruthy();
  expect(within(results).getByText(/Indice 10 déduit des nombres du nom/)).toBeTruthy();
  expect(within(results).queryByText(/Meilleure correspondance/)).toBeNull();
  expect(within(results).queryByRole('progressbar')).toBeNull();
});

it('propose la saisie manuelle lorsqu’aucune trame ne correspond',async()=>{
  vi.mocked(documentApi.discover).mockResolvedValue({...discovered,candidates:[],recommended_path:null});
  render(<ProjectDocumentsPanel projectId="p1"/>);await choose();const results=await search();
  expect(within(results).getByText(/Aucune trame correspondante/)).toBeTruthy();
  expect(within(results).queryByRole('button',{name:/Choisir la trame/})).toBeNull();
  expect((screen.getByLabelText('Fichier de la trame dans ce lien') as HTMLInputElement).value).toBe('demande.docx');
});

it('annule la recherche, ignore une réponse tardive et rend le formulaire disponible',async()=>{
  let done!:(value:DocumentDiscovery)=>void;vi.mocked(documentApi.discover).mockReturnValue(new Promise(resolve=>{done=resolve;}));
  render(<ProjectDocumentsPanel projectId="p1"/>);await choose();fireEvent.click(screen.getByRole('button',{name:'Rechercher les trames dans ce lien'}));
  expect(screen.getByText(/Le nombre total de fichiers est encore inconnu/)).toBeTruthy();
  expect(screen.getByLabelText('Dossier ou fichier du projet').matches(':disabled')).toBe(true);
  const signal=vi.mocked(documentApi.discover).mock.calls[0][3]!;
  fireEvent.click(screen.getByRole('button',{name:'Annuler l’opération'}));expect(signal.aborted).toBe(true);
  done(discovered);await waitFor(()=>expect(screen.getByText('Opération annulée.')).toBeTruthy());
  expect(screen.queryByRole('region',{name:'Trames trouvées dans le lien projet'})).toBeNull();
  expect(screen.getByLabelText('Dossier ou fichier du projet').matches(':disabled')).toBe(false);
});

it('refuse une réponse de découverte d’un autre projet ou lien',async()=>{
  vi.mocked(documentApi.discover).mockResolvedValue({...discovered,link_id:'foreign'});
  render(<ProjectDocumentsPanel projectId="p1"/>);await choose();fireEvent.click(screen.getByRole('button',{name:'Rechercher les trames dans ce lien'}));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent','Résultats reçus différents du projet, du lien ou de la trame sélectionnés');
  expect(screen.queryByRole('region',{name:'Trames trouvées dans le lien projet'})).toBeNull();
});

it('retire les résultats après changement de trame ou relecture des liens',async()=>{
  render(<ProjectDocumentsPanel projectId="p1"/>);await choose();await search();
  fireEvent.click(screen.getByRole('radio',{name:/Notice d'utilisation/}));
  expect(screen.queryByRole('region',{name:'Trames trouvées dans le lien projet'})).toBeNull();
  fireEvent.click(screen.getByRole('radio',{name:/Demande de CE/}));await search();
  fireEvent.click(screen.getByRole('button',{name:'Actualiser les informations'}));
  await waitFor(()=>expect(documentApi.workspace).toHaveBeenCalledTimes(2));
  expect(screen.queryByRole('region',{name:'Trames trouvées dans le lien projet'})).toBeNull();
});

it('garde la découverte accessible au lecteur autorisé',async()=>{
  vi.mocked(documentApi.workspace).mockResolvedValue({...state,can_prepare_copy:false});
  render(<ProjectDocumentsPanel projectId="p1"/>);await choose();await search();
  expect(documentApi.discover).toHaveBeenCalledOnce();expect(documentApi.copy).not.toHaveBeenCalled();
});

it('conserve la saisie après erreur de recherche et permet un nouvel essai',async()=>{
  vi.mocked(documentApi.discover).mockRejectedValueOnce(new Error('Partage indisponible'));
  render(<ProjectDocumentsPanel projectId="p1"/>);await choose();fireEvent.click(screen.getByRole('button',{name:'Rechercher les trames dans ce lien'}));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent','Partage indisponible');
  expect((screen.getByLabelText('Fichier de la trame dans ce lien') as HTMLInputElement).value).toBe('demande.docx');
  await search();expect(documentApi.discover).toHaveBeenCalledTimes(2);
});

it('montre les origines, vérifie la trame puis exige une relecture avant téléchargement',async()=>{
  const view=render(<ProjectDocumentsPanel projectId="p1"/>);await inspect();
  const region=screen.getByRole('region',{name:'Aperçu des informations à remplir'});
  expect(within(region).getByText('Ancien projet')).toBeTruthy();expect(within(region).getByText('Projet')).toBeTruthy();
  const prepare=screen.getByRole('button',{name:'Préparer la copie'});expect(prepare.matches(':disabled')).toBe(true);
  expect((screen.getByLabelText("Numéro d'affaire") as HTMLTextAreaElement).readOnly).toBe(true);
  confirm();fireEvent.click(prepare);const download=await screen.findByRole('link',{name:/Télécharger AIRB26/});
  expect(documentApi.copy).toHaveBeenCalledWith('p1',{document_id:'ce_request',link_id:'l1',relative_path:'demande.docx',overrides:{}},preview,expect.any(AbortSignal));
  expect(download.getAttribute('href')).toBe('blob:document');expect(download.getAttribute('download')).toBe(preview.output_filename);
  expect(URL.revokeObjectURL).not.toHaveBeenCalled();view.unmount();expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:document');
});

it('normalise les chemins Windows et conserve une sélection hors de sa page',async()=>{
  vi.mocked(documentApi.workspace).mockResolvedValue({...state,links:{...state.links,total:101}});
  render(<ProjectDocumentsPanel projectId="p1"/>);await choose();
  fireEvent.change(screen.getByLabelText('Fichier de la trame dans ce lien'),{target:{value:'Trames\\demande.docx'}});
  vi.mocked(documentApi.preview).mockResolvedValue({...preview,source:{...preview.source,relative_path:'Trames/demande.docx'}});
  fireEvent.click(screen.getByRole('button',{name:'Afficher l’aperçu'}));await screen.findByRole('region',{name:'Aperçu des informations à remplir'});
  expect(documentApi.preview).toHaveBeenCalledWith('p1',expect.objectContaining({relative_path:'Trames/demande.docx'}),expect.any(AbortSignal));
  vi.mocked(documentApi.workspace).mockResolvedValue({...state,links:{items:[],total:101,offset:100,limit:100}});
  fireEvent.click(screen.getByRole('button',{name:'Suivant'}));await screen.findByRole('option',{name:'Dossier affaire · sélection conservée'});
  expect((screen.getByLabelText('Dossier ou fichier du projet') as HTMLSelectElement).value).toBe('l1');
  expect(screen.queryByRole('region',{name:'Aperçu des informations à remplir'})).toBeNull();
});

it('invalide aperçu et copie au changement de fichier et libère les octets téléchargés',async()=>{
  render(<ProjectDocumentsPanel projectId="p1"/>);await inspect();confirm();fireEvent.click(screen.getByRole('button',{name:'Préparer la copie'}));
  await screen.findByRole('link',{name:/Télécharger AIRB26/});fireEvent.change(screen.getByLabelText('Fichier de la trame dans ce lien'),{target:{value:'autre.docx'}});
  expect(screen.queryByRole('region',{name:'Aperçu des informations à remplir'})).toBeNull();expect(screen.queryByRole('link',{name:/Télécharger/})).toBeNull();
  expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:document');
});

it('conserve les corrections locales après conflit et impose un nouvel aperçu',async()=>{
  vi.mocked(documentApi.preview).mockResolvedValue({...preview,document_id:'user_manual',format:'DOCM',field_values:{...state,values:{...state.values,description:'Texte local'},
    origins:{...state.origins,description:{kind:'document_override',record_id:null,attribute:'description'}}},targets:[{...preview.targets[0],target:'Désignation',field:'description',proposed_value:'Texte local'}]});
  vi.mocked(documentApi.copy).mockRejectedValue(new Error('Données métier modifiées depuis l’aperçu'));
  const view=render(<ProjectDocumentsPanel projectId="p1"/>);await choose();fireEvent.click(screen.getByRole('radio',{name:/Notice d'utilisation/}));
  fireEvent.change(screen.getByLabelText('Description / désignation'),{target:{value:'Texte local'}});
  expect(view.container.querySelector('[data-workspace-dirty="true"]')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Afficher l’aperçu'}));await screen.findByRole('region',{name:'Aperçu des informations à remplir'});confirm();
  fireEvent.click(screen.getByRole('button',{name:'Préparer la copie'}));await screen.findByRole('alert');
  expect((screen.getByLabelText('Description / désignation') as HTMLTextAreaElement).value).toBe('Texte local');
  expect(screen.queryByRole('button',{name:'Préparer la copie'})).toBeNull();expect(screen.queryByRole('link',{name:/Télécharger/})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Revenir à la donnée projet · Description / désignation'}));
  expect((screen.getByLabelText('Description / désignation') as HTMLTextAreaElement).value).toBe('LED 2026');
});

it('réserve la préparation aux éditeurs et garde l’aperçu accessible en lecture seule',async()=>{
  vi.mocked(documentApi.workspace).mockResolvedValue({...state,can_prepare_copy:false});
  vi.mocked(documentApi.preview).mockResolvedValue({...preview,can_prepare_copy:false});render(<ProjectDocumentsPanel projectId="p1"/>);await inspect();
  expect(screen.getByText(/Lecture seule :/)).toBeTruthy();expect(screen.getByRole('button',{name:'Préparer la copie'}).matches(':disabled')).toBe(true);
  expect(screen.getByLabelText('J’ai vérifié les informations proposées pour cette copie.').matches(':disabled')).toBe(true);expect(documentApi.copy).not.toHaveBeenCalled();
});

it('montre les champs manquants et les protections sans préparer un fichier bloqué',async()=>{
  vi.mocked(documentApi.preview).mockResolvedValue({...preview,can_prepare:false,missing_fields:['description'],blockers:['document_protected'],
    targets:[{...preview.targets[0],available:false,blockers:['bookmark_missing']}],macro_parts:{'word/vbaProject.bin':'d'.repeat(64)}});
  render(<ProjectDocumentsPanel projectId="p1"/>);await inspect();expect(screen.getByText('À compléter : Description / désignation.')).toBeTruthy();
  expect(screen.getByText('Le document Word est protégé.')).toBeTruthy();expect(screen.getByText('Signet absent.')).toBeTruthy();
  expect(screen.getByText(/Les macros existantes sont conservées/)).toBeTruthy();expect(screen.getByRole('button',{name:'Préparer la copie'}).matches(':disabled')).toBe(true);
});

it('n’explore pas le réseau quand les racines sont désactivées',async()=>{
  vi.mocked(documentApi.workspace).mockResolvedValue({...state,file_access:{status:'disabled',detail:'Racines documentaires à configurer'}});
  render(<ProjectDocumentsPanel projectId="p1"/>);await choose();expect(screen.getByText(/Contactez l’administrateur/)).toBeTruthy();
  expect(screen.getByRole('button',{name:'Afficher l’aperçu'}).matches(':disabled')).toBe(true);expect(documentApi.preview).not.toHaveBeenCalled();
});

it('ignore les réponses tardives et annule la lecture quand le projet devient inactif',async()=>{
  let done!:(value:DocumentPreview)=>void;vi.mocked(documentApi.preview).mockReturnValue(new Promise(resolve=>{done=resolve;}));
  const view=render(<ProjectDocumentsPanel projectId="p1"/>);await choose();fireEvent.click(screen.getByRole('button',{name:'Afficher l’aperçu'}));
  const signal=vi.mocked(documentApi.preview).mock.calls[0][2];view.rerender(<ProjectDocumentsPanel projectId="p1" active={false}/>);
  expect(signal?.aborted).toBe(true);done(preview);await waitFor(()=>expect(screen.queryByRole('region',{name:'Aperçu des informations à remplir'})).toBeNull());
  expect(URL.createObjectURL).not.toHaveBeenCalled();
});

it('annule la préparation et ignore un résultat tardif sans afficher de lien',async()=>{
  let done!:(value:{blob:Blob;filename:string;sha256:string})=>void;vi.mocked(documentApi.copy).mockReturnValue(new Promise(resolve=>{done=resolve;}));
  render(<ProjectDocumentsPanel projectId="p1"/>);await inspect();confirm();fireEvent.click(screen.getByRole('button',{name:'Préparer la copie'}));
  fireEvent.click(screen.getByRole('button',{name:'Annuler l’opération'}));expect(vi.mocked(documentApi.copy).mock.calls[0][3]?.aborted).toBe(true);
  done({blob:new Blob(['late']),filename:'late.docx',sha256:'d'.repeat(64)});await screen.findByText('Opération annulée.');
  expect(screen.queryByRole('link',{name:/Télécharger/})).toBeNull();expect(URL.createObjectURL).not.toHaveBeenCalled();
});

it('recharge les références sans écraser la correction locale et réinitialise le projet suivant',async()=>{
  const view=render(<ProjectDocumentsPanel projectId="p1"/>);await choose();fireEvent.click(screen.getByRole('radio',{name:/Notice d'utilisation/}));
  fireEvent.change(screen.getByLabelText('Description / désignation'),{target:{value:'Texte local'}});
  vi.mocked(documentApi.workspace).mockResolvedValue({...state,values:{...state.values,description:'Nouveau projet'}});
  fireEvent.click(screen.getByRole('button',{name:'Actualiser les informations'}));await waitFor(()=>expect(documentApi.workspace).toHaveBeenCalledTimes(2));
  expect((screen.getByLabelText('Description / désignation') as HTMLTextAreaElement).value).toBe('Texte local');
  view.rerender(<ProjectDocumentsPanel projectId="p2"/>);await waitFor(()=>expect(documentApi.workspace).toHaveBeenLastCalledWith('p2',0,expect.any(AbortSignal)));
  expect((screen.getByLabelText('Dossier ou fichier du projet') as HTMLSelectElement).value).toBe('');expect(screen.queryByLabelText('Description / désignation')).toBeNull();
});

it('permet de réessayer un chargement échoué sans envoyer de commande documentaire',async()=>{
  vi.mocked(documentApi.workspace).mockRejectedValueOnce(new Error('Projet indisponible')).mockResolvedValue(state);
  render(<ProjectDocumentsPanel projectId="p1"/>);await screen.findByText('Projet indisponible');fireEvent.click(screen.getByRole('button',{name:'Réessayer'}));
  await screen.findByRole('radio',{name:/Demande de CE/});expect(documentApi.preview).not.toHaveBeenCalled();
});
