import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ProjectDocumentsPanel } from './ProjectDocumentsPanel';
import { documentApi, type DocumentDraft, type DocumentWorkspace } from '../lib/projectDocuments';

const saved:DocumentDraft={available:true,revision:3,version_id:'v3',link_id:'offpage',relative_path:'saved.docx',
  selected_link:{id:'offpage',code:'same',label:'Dossier sauvegardé hors page',path:'V:/saved',order:500},overrides:{description:'Texte enregistré'},warnings:[]};
const state:DocumentWorkspace={project_id:'p1',identity_revision:2,planning_revision:4,values_sha256:'b'.repeat(64),values:{project_code:'AIRB26LTH0205-A',description:'LED 2026'},
  origins:{},fields:{description:{label:'Description',edit_scope:'project'}},missing_fields:[],oversized_fields:[],warnings:[],overrides_scope:'one_document',read_only:true,
  templates:[{id:'ce_request',label:'Demande de CE',format:'DOCX',fields:['description'],cells:[],bookmarks:[['Desc','description']],sheet_name:null},
    {id:'user_manual',label:'Notice',format:'DOCM',fields:['description'],cells:[],bookmarks:[['Desc','description']],sheet_name:null}],
  links:{items:[{id:'l1',code:'same',label:'Lien de la page',path:'V:/page',order:1}],total:500,offset:0,limit:100},
  file_access:{status:'configured',detail:''},can_prepare_copy:true,publication:'explicit_separate_command',batch_available:false,
  search_preferences:{available:true,revision:2,version_id:'s2',items:[]}};
beforeEach(()=>{
  vi.spyOn(documentApi,'workspace').mockResolvedValue(structuredClone(state));
  vi.spyOn(documentApi,'draft').mockResolvedValue(structuredClone(saved));
  vi.spyOn(documentApi,'saveDraft').mockResolvedValue({...saved,revision:4,version_id:'v4',relative_path:'local.docx'});
  vi.spyOn(documentApi,'restoreDraft').mockResolvedValue({...saved,revision:4,version_id:'v4',relative_path:'restored.docx'});
  vi.spyOn(documentApi,'draftHistory').mockResolvedValue({items:[{id:'v2',revision:2,created_at:'2026-10-07T00:00:00+00:00',sha256:'a'.repeat(64),
    value:{actor_id:'local',choice:{link_id:'offpage',relative_path:'old.docx',overrides:{}}}}],total:21,offset:0,limit:20});
  vi.spyOn(documentApi,'preview');vi.spyOn(documentApi,'copy');vi.spyOn(documentApi,'discover');
});
afterEach(()=>{cleanup();vi.restoreAllMocks();});
const path=()=>screen.getByLabelText('Fichier de la trame dans ce lien') as HTMLInputElement;
async function loaded(){await screen.findByText('Version enregistrée : 3');await waitFor(()=>expect(path().disabled).toBe(false));}

it('relit les choix persistants hors de la page de liens sans sonder un fichier',async()=>{
  render(<ProjectDocumentsPanel projectId="p1"/>);await loaded();
  expect(path().value).toBe('saved.docx');expect((screen.getByLabelText('Dossier ou fichier du projet') as HTMLSelectElement).value).toBe('offpage');
  expect(screen.getByRole('option',{name:/Dossier sauvegardé hors page/})).toBeTruthy();
  expect((screen.getByLabelText('Description') as HTMLTextAreaElement).value).toBe('Texte enregistré');
  expect(documentApi.preview).not.toHaveBeenCalled();expect(documentApi.copy).not.toHaveBeenCalled();expect(documentApi.discover).not.toHaveBeenCalled();
});

it('enregistre explicitement avec la révision attendue et ne prépare pas de fichier',async()=>{
  render(<ProjectDocumentsPanel projectId="p1"/>);await loaded();fireEvent.change(path(),{target:{value:'local.docx'}});
  expect(documentApi.saveDraft).not.toHaveBeenCalled();expect(document.querySelector('[data-workspace-dirty="true"]')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les choix'}));await screen.findByText('Choix enregistrés · version 4.');
  expect(documentApi.saveDraft).toHaveBeenCalledWith('p1','ce_request',3,{link_id:'offpage',relative_path:'local.docx',overrides:{description:'Texte enregistré'}},expect.any(AbortSignal));
  await waitFor(()=>expect(document.querySelector('[data-workspace-dirty="true"]')).toBeNull());expect(documentApi.copy).not.toHaveBeenCalled();
});

it('garde le texte et la révision en conflit puis compare sans les écraser',async()=>{
  vi.mocked(documentApi.saveDraft).mockRejectedValue(new Error('Le formulaire a changé'));
  vi.mocked(documentApi.draft).mockResolvedValueOnce(saved).mockResolvedValue({...saved,revision:5,relative_path:'server.docx'});
  vi.mocked(documentApi.draftHistory).mockResolvedValueOnce({items:[{id:'v2',revision:2,sha256:'a'.repeat(64),created_at:'2026-10-07T00:00:00+00:00',value:{actor_id:'local'}}],total:2,offset:0,limit:20})
    .mockResolvedValue({items:[{id:'v5',revision:5,sha256:'a'.repeat(64),created_at:'2026-10-07T00:00:00+00:00',value:{actor_id:'local'}}],total:5,offset:0,limit:20});
  render(<ProjectDocumentsPanel projectId="p1"/>);await loaded();fireEvent.click(screen.getByRole('button',{name:'Historique des choix'}));await screen.findByText('Version 2');
  fireEvent.change(path(),{target:{value:'local.docx'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer les choix'}));await screen.findByRole('alert');
  expect(path().value).toBe('local.docx');fireEvent.click(screen.getByRole('button',{name:'Enregistrer les choix'}));
  await waitFor(()=>expect(documentApi.saveDraft).toHaveBeenCalledTimes(2));expect(vi.mocked(documentApi.saveDraft).mock.calls.map(call=>call[2])).toEqual([3,3]);
  await waitFor(()=>expect(screen.getByRole('button',{name:'Comparer avec la version enregistrée'}).matches(':disabled')).toBe(false));
  fireEvent.click(screen.getByRole('button',{name:'Comparer avec la version enregistrée'}));await screen.findByRole('region',{name:'Version enregistrée à comparer'});
  expect(path().value).toBe('local.docx');expect(screen.getByText('Version serveur 5')).toBeTruthy();
  fireEvent.click(screen.getByRole('button',{name:'Charger cette version et remplacer ma saisie'}));expect(path().value).toBe('server.docx');
  await screen.findByText('Version 5');
  expect(document.querySelector('[data-workspace-dirty="true"]')).toBeNull();
});

it('pagine le journal et restaure sans modifier les anciennes versions',async()=>{
  render(<ProjectDocumentsPanel projectId="p1"/>);await loaded();fireEvent.click(screen.getByRole('button',{name:'Historique des choix'}));
  const history=await screen.findByRole('region',{name:'Historique documentaire'});await within(history).findByText('Version 2');
  fireEvent.click(within(history).getByRole('button',{name:'Suivant'}));await waitFor(()=>expect(documentApi.draftHistory).toHaveBeenLastCalledWith('p1','ce_request',20,expect.any(AbortSignal)));
  await waitFor(()=>expect(within(history).getByRole('button',{name:'Restaurer la version 2'}).matches(':disabled')).toBe(false));
  fireEvent.click(within(history).getByRole('button',{name:'Restaurer la version 2'}));await screen.findByText('Choix enregistrés · version 4.');
  expect(documentApi.restoreDraft).toHaveBeenCalledWith('p1','ce_request',3,'v2',expect.any(AbortSignal));expect(path().value).toBe('restored.docx');
});

it('réserve sauvegarde et restauration aux éditeurs mais laisse le journal au lecteur',async()=>{
  vi.mocked(documentApi.workspace).mockResolvedValue({...state,can_prepare_copy:false});
  render(<ProjectDocumentsPanel projectId="p1"/>);await loaded();expect(screen.queryByRole('button',{name:'Enregistrer les choix'})).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Historique des choix'}));await screen.findByText('Version 2');
  expect(screen.queryByRole('button',{name:'Restaurer la version 2'})).toBeNull();
});

it('conserve la saisie pendant la désactivation puis le retour à la vue',async()=>{
  const view=render(<ProjectDocumentsPanel projectId="p1"/>);await loaded();fireEvent.change(path(),{target:{value:'unsaved.docx'}});
  view.rerender(<ProjectDocumentsPanel projectId="p1" active={false}/>);view.rerender(<ProjectDocumentsPanel projectId="p1"/>);
  await waitFor(()=>expect(documentApi.workspace).toHaveBeenCalledTimes(2));expect(path().value).toBe('unsaved.docx');expect(documentApi.draft).toHaveBeenCalledTimes(1);
});

it('ignore le formulaire tardif du précédent projet',async()=>{
  let finish!:(value:DocumentDraft)=>void;vi.mocked(documentApi.draft).mockReturnValueOnce(new Promise(resolve=>{finish=resolve;})).mockResolvedValue({...saved,relative_path:'p2.docx'});
  const view=render(<ProjectDocumentsPanel projectId="p1"/>);await waitFor(()=>expect(documentApi.draft).toHaveBeenCalledTimes(1));
  const signal=vi.mocked(documentApi.draft).mock.calls[0][2]!;view.rerender(<ProjectDocumentsPanel projectId="p2"/>);expect(signal.aborted).toBe(true);
  await waitFor(()=>expect(path().value).toBe('p2.docx'));finish(saved);await waitFor(()=>expect(path().value).toBe('p2.docx'));
});

it('signale le lien disparu, interdit sa préparation et permet une reselection',async()=>{
  vi.mocked(documentApi.draft).mockResolvedValue({...saved,selected_link:null,warnings:['selected_link_missing']});
  render(<ProjectDocumentsPanel projectId="p1"/>);await loaded();expect(screen.getByText(/Le lien enregistré n’existe plus/)).toBeTruthy();
  expect(screen.getByRole('button',{name:'Afficher l’aperçu'}).matches(':disabled')).toBe(true);
  fireEvent.change(screen.getByLabelText('Dossier ou fichier du projet'),{target:{value:'l1'}});expect(path().value).toBe('');
  expect(screen.getByRole('button',{name:'Afficher l’aperçu'}).matches(':disabled')).toBe(false);
});

it('respecte la désactivation de recherche tout en permettant le choix manuel',async()=>{
  vi.mocked(documentApi.workspace).mockResolvedValue({...state,templates:state.templates.map(row=>({...row,search_active:false}))});
  render(<ProjectDocumentsPanel projectId="p1"/>);await loaded();expect(screen.getByRole('button',{name:'Rechercher les trames dans ce lien'}).matches(':disabled')).toBe(true);
  expect(screen.getByRole('button',{name:'Afficher l’aperçu'}).matches(':disabled')).toBe(false);
});
