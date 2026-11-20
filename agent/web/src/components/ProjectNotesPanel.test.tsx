import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { ProjectNotesPanel } from './ProjectNotesPanel';
import { NoteContentView, readNoteRuns } from './NoteRichEditor';
import { blankNote, boundVersionContent, NoteHttpError, noteDraftKey, notesApi, readNoteDraft, validNoteContent, writeNoteDraft,
  type NoteContent, type NoteDetail, type NoteDraft, type NoteResult, type NoteVersion } from '../lib/projectNotes';

const id='11111111-1111-4111-8111-111111111111',imageId='22222222-2222-4222-8222-222222222222';
const run=(text:string)=>({text,marks:[] as [],href:null,color:null});
const content:NoteContent={version:1,blocks:[{type:'paragraph',align:'left',runs:[run('Compte rendu initial')]}]};
const head:NoteDetail={id,project_id:'p1',title:'Réunion LED',revision:2,version_id:'v2',updated_at:'2026-10-07T10:00:00Z',actor_id:'local',content,attachment_ids:[],read_only:false,source_kind:null};
const result=(note:NoteDetail,command:string):NoteResult=>({note,command_id:command,command_revision:note.revision,replayed:false});
const draft=(values:Partial<NoteDraft>={}):NoteDraft=>({format:1,project_id:'p1',note_id:id,operator_id:'local',title:'Brouillon retrouvé',content:blankNote(),attachment_ids:[],expected_revision:2,pending:null,updated_at:'2026-10-07T11:00:00Z',...values});
beforeEach(()=>{
  localStorage.clear();
  vi.spyOn(notesApi,'list').mockResolvedValue({available:true,can_edit:true,operator_id:'local',items:[{...head,excerpt:'Compte rendu initial'}],total:1,offset:0,limit:30});
  vi.spyOn(notesApi,'read').mockResolvedValue(structuredClone(head));
  vi.spyOn(notesApi,'attachments').mockResolvedValue({items:[]});
  vi.spyOn(notesApi,'history').mockResolvedValue({items:[{id:'v1',revision:1,title:'Initiale',actor_id:null,created_at:head.updated_at,operation:'create'}],total:1,offset:0,limit:20});
  vi.spyOn(notesApi,'execute').mockImplementation(async(_,__,pending)=>result({...head,revision:3,
    ...(pending.kind!=='restore'?pending.payload:{title:'Restaurée',content:blankNote()})},pending.payload.command_id));
});
afterEach(()=>{cleanup();vi.restoreAllMocks();localStorage.clear();});
async function open(){fireEvent.click(await screen.findByRole('button',{name:/Réunion LED/}));return screen.findByLabelText('Titre de la note') as Promise<HTMLInputElement>;}
it('enregistre la couleur de fond et garde le même éditeur pendant la sauvegarde',async()=>{
  render(<ProjectNotesPanel projectId="p1"/>);
  const title=await open();
  fireEvent.click(screen.getByRole('button',{name:'Fond rose'}));
  title.focus();
  const editor=screen.getByRole('textbox',{name:'Texte du bloc 1'});
  await screen.findByText('Enregistrée · version 3',{}, {timeout:3000});
  expect(screen.getByLabelText('Titre de la note')).toBe(title);
  expect(screen.getByRole('textbox',{name:'Texte du bloc 1'})).toBe(editor);
  expect(document.activeElement).toBe(title);
  expect(vi.mocked(notesApi.list)).toHaveBeenCalledTimes(1);
  expect(screen.getByRole('button',{name:/Ouvrir la note Réunion LED/}).dataset.noteBackground).toBe('pink');
});

it('confirme la suppression avant de retirer la note sélectionnée',async()=>{
  const confirmation=vi.spyOn(window,'confirm').mockReturnValueOnce(false).mockReturnValue(true);
  const remove=vi.spyOn(notesApi,'remove').mockResolvedValue({deleted:true});
  render(<ProjectNotesPanel projectId="p1"/>);await open();
  const button=screen.getByRole('button',{name:'Supprimer la note'});
  fireEvent.click(button);expect(remove).not.toHaveBeenCalled();
  vi.mocked(notesApi.list).mockResolvedValue({available:true,can_edit:true,operator_id:'local',items:[],total:0,offset:0,limit:30});
  fireEvent.click(button);
  await waitFor(()=>expect(screen.queryByRole('button',{name:/Ouvrir la note Réunion LED/})).toBeNull());
  expect(remove).toHaveBeenCalledWith('p1',id,expect.objectContaining({expected_revision:2}),expect.any(AbortSignal));
  expect(confirmation).toHaveBeenCalledTimes(2);
});
it('bloque sauvegarde manuelle et automatique jusqu’à conversion Markdown valide',async()=>{
  render(<ProjectNotesPanel projectId="p1"/>);const title=await open();
  fireEvent.click(screen.getByRole('button',{name:'Éditer en Markdown'}));
  fireEvent.change(screen.getByLabelText('Texte Markdown'),{target:{value:'**Réserve non fermée'}});
  fireEvent.change(title,{target:{value:'Revue provisoire'}});
  expect(screen.getByRole('button',{name:'Enregistrer maintenant'})).toHaveProperty('disabled',true);
  // Wait past the real autosave debounce: the valid previous note must not be saved instead of the pending Markdown.
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,1350));});
  expect(notesApi.execute).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('Texte Markdown'),{target:{value:'Ne pas approuver : **12 Nm** provisoires.'}});
  fireEvent.click(screen.getByRole('button',{name:'Valider et revenir à l’éditeur riche'}));
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer maintenant'}));
  await waitFor(()=>expect(notesApi.execute).toHaveBeenCalledTimes(1));
  expect(notesApi.execute).toHaveBeenCalledWith('p1',id,expect.objectContaining({kind:'save',payload:expect.objectContaining({
    title:'Revue provisoire',content:{version:1,blocks:[{type:'paragraph',align:'left',runs:[run('Ne pas approuver : '),
      {...run('12 Nm'),marks:['bold']},run(' provisoires.')]}]},
  })}),expect.any(AbortSignal));
});
it('crée une note avec une commande conservée avant l’envoi, puis actualise la liste',async()=>{
  vi.mocked(notesApi.execute).mockImplementation(async(_,__,pending)=>{
    expect(readNoteDraft('p1','new','local').draft?.pending).toEqual(pending);
    return result({...head,revision:1,title:'Nouvelle réunion'},pending.payload.command_id);
  });
  render(<ProjectNotesPanel projectId="p1"/>);fireEvent.click(await screen.findByRole('button',{name:'Nouvelle note'}));
  fireEvent.change(await screen.findByLabelText('Titre de la note'),{target:{value:'Nouvelle réunion'}});
  fireEvent.click(screen.getByRole('button',{name:'Créer la note'}));await screen.findByText('Enregistrée · version 2');
  expect(notesApi.execute).toHaveBeenCalledWith('p1','new',expect.objectContaining({kind:'create'}),expect.any(AbortSignal));
  await waitFor(()=>expect(notesApi.list).toHaveBeenCalledTimes(2));expect(localStorage.getItem(noteDraftKey('p1','new','local'))).toBeNull();
});
it('enregistre automatiquement après la pause et annonce la version confirmée',async()=>{
  render(<ProjectNotesPanel projectId="p1"/>);const title=await open();fireEvent.change(title,{target:{value:'Décisions LED'}});
  expect(readNoteDraft('p1',id,'local').draft?.title).toBe('Décisions LED');
  await screen.findByText('Enregistrée · version 3',{}, {timeout:3000});
  expect(notesApi.execute).toHaveBeenCalledWith('p1',id,expect.objectContaining({kind:'save',payload:expect.objectContaining({title:'Décisions LED',expected_revision:2})}),expect.any(AbortSignal));
});
it('rattache une création rejouée à la note actuelle sans perdre la saisie devenue ancienne',async()=>{
  vi.mocked(notesApi.execute).mockImplementation(async(_,__,pending)=>({...result({...head,title:'Création modifiée ailleurs',revision:5},pending.payload.command_id),command_revision:1,replayed:true}));
  render(<ProjectNotesPanel projectId="p1"/>);fireEvent.click(await screen.findByRole('button',{name:'Nouvelle note'}));
  fireEvent.change(await screen.findByLabelText('Titre de la note'),{target:{value:'Ma création'}});fireEvent.click(screen.getByRole('button',{name:'Créer la note'}));
  await screen.findByText('Brouillon retrouvé sur cet appareil');expect(readNoteDraft('p1',id,'local').draft).toMatchObject({title:'Ma création',expected_revision:1,pending:null});
  expect(localStorage.getItem(noteDraftKey('p1','new','local'))).toBeNull();fireEvent.click(screen.getByRole('button',{name:'Reprendre ce brouillon'}));
  expect(screen.getByRole('button',{name:'Enregistrer maintenant'}).matches(':disabled')).toBe(true);expect(notesApi.execute).toHaveBeenCalledTimes(1);
});
it('garde le même identifiant de création si la sauvegarde locale échoue après la réponse',async()=>{
  const original=Storage.prototype.setItem;let fail=false;
  vi.spyOn(Storage.prototype,'setItem').mockImplementation(function(this:Storage,key,value){if(fail&&key===noteDraftKey('p1',id,'local'))throw new DOMException('Quota','QuotaExceededError');original.call(this,key,value);});
  vi.mocked(notesApi.execute).mockImplementation(async(_,__,pending)=>{fail=true;return result({...head,revision:1,title:'Création'},pending.payload.command_id);});
  render(<ProjectNotesPanel projectId="p1"/>);fireEvent.click(await screen.findByRole('button',{name:'Nouvelle note'}));
  fireEvent.change(await screen.findByLabelText('Titre de la note'),{target:{value:'Création'}});fireEvent.click(screen.getByRole('button',{name:'Créer la note'}));
  await screen.findByText(/Brouillon non conservé/);const first=vi.mocked(notesApi.execute).mock.calls[0][2];
  expect(readNoteDraft('p1','new','local').draft?.pending).toEqual(first);fail=false;
  vi.mocked(notesApi.execute).mockImplementation(async(_,__,pending)=>result({...head,revision:1,title:'Création'},pending.payload.command_id));
  fireEvent.click(screen.getByRole('button',{name:'Reprendre l’enregistrement'}));await waitFor(()=>expect(notesApi.execute).toHaveBeenCalledTimes(2));
  expect(vi.mocked(notesApi.execute).mock.calls[1][2]).toEqual(first);
});
it('conserve les nouvelles frappes pendant l’envoi puis les enregistre sur la révision confirmée',async()=>{
  let finish!:(value:NoteResult)=>void;
  vi.mocked(notesApi.execute).mockReturnValueOnce(new Promise(resolve=>{finish=resolve;}));
  render(<ProjectNotesPanel projectId="p1"/>);const title=await open();fireEvent.change(title,{target:{value:'Première saisie'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer maintenant'}));await waitFor(()=>expect(notesApi.execute).toHaveBeenCalledTimes(1));
  fireEvent.change(title,{target:{value:'Saisie plus récente'}});const pending=vi.mocked(notesApi.execute).mock.calls[0][2];
  await act(async()=>{finish(result({...head,title:'Première saisie',revision:3},pending.payload.command_id));});
  expect(title.value).toBe('Saisie plus récente');expect(readNoteDraft('p1',id,'local').draft?.expected_revision).toBe(3);
  await waitFor(()=>expect(notesApi.execute).toHaveBeenCalledTimes(2),{timeout:3000});
  expect(vi.mocked(notesApi.execute).mock.calls[1][2]).toMatchObject({payload:{title:'Saisie plus récente',expected_revision:3}});
});
it('reprend exactement la commande après une réponse perdue, y compris après rechargement',async()=>{
  vi.mocked(notesApi.execute).mockRejectedValueOnce(new TypeError('Connexion interrompue'));
  const view=render(<ProjectNotesPanel projectId="p1"/>);const title=await open();fireEvent.change(title,{target:{value:'À conserver'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer maintenant'}));await screen.findByText('Connexion interrompue');
  const first=vi.mocked(notesApi.execute).mock.calls[0][2];view.unmount();render(<ProjectNotesPanel projectId="p1"/>);await open();
  fireEvent.click(screen.getByRole('button',{name:'Reprendre ce brouillon'}));fireEvent.click(screen.getByRole('button',{name:'Reprendre l’enregistrement'}));
  await screen.findByText('Enregistrée · version 3');expect(vi.mocked(notesApi.execute).mock.calls[1][2]).toEqual(first);
});
it('garde la saisie en conflit, compare sans l’écraser puis exige une reprise explicite',async()=>{
  vi.mocked(notesApi.execute).mockRejectedValueOnce(new NoteHttpError(409,'La note a changé'));
  render(<ProjectNotesPanel projectId="p1"/>);const title=await open();fireEvent.change(title,{target:{value:'Version locale'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer maintenant'}));await screen.findByText('La note a changé');
  vi.mocked(notesApi.read).mockResolvedValue({...head,title:'Version collègue',revision:6});
  fireEvent.click(screen.getByRole('button',{name:'Comparer avec la version enregistrée'}));await screen.findByRole('region',{name:'Version enregistrée à comparer'});
  expect(title.value).toBe('Version locale');expect(notesApi.execute).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button',{name:'Reprendre ma saisie sur cette version'}));
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer maintenant'}));await waitFor(()=>expect(notesApi.execute).toHaveBeenCalledTimes(2));
  expect(vi.mocked(notesApi.execute).mock.calls[1][2]).toMatchObject({payload:{title:'Version locale',expected_revision:6}});
});
it('ne confond pas un rejeu confirmé avec une version modifiée ensuite par un autre opérateur',async()=>{
  vi.mocked(notesApi.execute).mockImplementation(async(_,__,pending)=>({...result({...head,title:'Autre modification',revision:5},pending.payload.command_id),command_revision:3,replayed:true}));
  render(<ProjectNotesPanel projectId="p1"/>);const title=await open();fireEvent.change(title,{target:{value:'Ma saisie'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer maintenant'}));await screen.findByText(/puis la note a été modifiée ailleurs/);
  expect(title.value).toBe('Ma saisie');expect(screen.getByRole('button',{name:'Enregistrer maintenant'}).matches(':disabled')).toBe(true);
  expect(readNoteDraft('p1',id,'local').draft?.title).toBe('Ma saisie');
});
it('ne lance aucune écriture lors de la découverte d’un brouillon ancien',async()=>{
  writeNoteDraft(draft({expected_revision:1}));render(<ProjectNotesPanel projectId="p1"/>);await open();
  expect(screen.getByText('Brouillon retrouvé sur cet appareil')).toBeTruthy();expect(notesApi.execute).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole('button',{name:'Reprendre ce brouillon'}));
  expect((screen.getByLabelText('Titre de la note') as HTMLInputElement).value).toBe('Brouillon retrouvé');
  expect(screen.getByRole('button',{name:'Enregistrer maintenant'}).matches(':disabled')).toBe(true);
});
it('refuse un brouillon altéré sans modifier les octets conservés',async()=>{
  const key=noteDraftKey('p1',id,'local');localStorage.setItem(key,'<script>ancien brouillon</script>');
  render(<ProjectNotesPanel projectId="p1"/>);const title=await open();await screen.findByText(/Le brouillon local ne peut pas être lu/);
  expect(title.readOnly).toBe(true);expect(localStorage.getItem(key)).toBe('<script>ancien brouillon</script>');expect(notesApi.execute).not.toHaveBeenCalled();
});
it('signale le quota local et ne transmet pas une commande non conservée',async()=>{
  render(<ProjectNotesPanel projectId="p1"/>);const title=await open();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new DOMException('Quota','QuotaExceededError');});
  fireEvent.change(title,{target:{value:'Texte à exporter'}});await screen.findByText(/Brouillon non conservé/);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer maintenant'}));expect(notesApi.execute).not.toHaveBeenCalled();expect(title.value).toBe('Texte à exporter');
});
it('conserve le brouillon quand la vue est masquée, sans enregistrement automatique en arrière-plan',async()=>{
  const view=render(<ProjectNotesPanel projectId="p1"/>);const title=await open();fireEvent.change(title,{target:{value:'En cours'}});
  view.rerender(<ProjectNotesPanel projectId="p1" active={false}/>);
  await new Promise(resolve=>setTimeout(resolve,1400));expect(notesApi.execute).not.toHaveBeenCalled();expect(readNoteDraft('p1',id,'local').draft?.title).toBe('En cours');
});
it('ignore la réponse tardive du projet précédent et conserve ses commandes pour une reprise',async()=>{
  let finish!:(value:NoteResult)=>void;vi.mocked(notesApi.execute).mockReturnValueOnce(new Promise(resolve=>{finish=resolve;}));
  const view=render(<ProjectNotesPanel projectId="p1"/>);const title=await open();fireEvent.change(title,{target:{value:'Projet 1'}});
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer maintenant'}));await waitFor(()=>expect(notesApi.execute).toHaveBeenCalledTimes(1));
  const call=vi.mocked(notesApi.execute).mock.calls[0];vi.mocked(notesApi.list).mockResolvedValue({available:true,can_edit:true,operator_id:'local',items:[],total:0,limit:30,offset:0});
  view.rerender(<ProjectNotesPanel projectId="p2"/>);expect(call[3]?.aborted).toBe(true);
  await act(async()=>finish(result({...head,title:'Projet 1',revision:3},call[2].payload.command_id)));
  expect(screen.queryByLabelText('Titre de la note')).toBeNull();expect(readNoteDraft('p1',id,'local').draft?.pending).toEqual(call[2]);expect(readNoteDraft('p2',id,'local').draft).toBeNull();
});
it('réserve les modifications aux éditeurs et garde l’historique accessible aux lecteurs',async()=>{
  vi.mocked(notesApi.list).mockResolvedValue({available:true,can_edit:false,operator_id:'reader',items:[{...head,excerpt:''}],total:1,offset:0,limit:30});
  render(<ProjectNotesPanel projectId="p1"/>);const title=await open();expect(title.readOnly).toBe(true);expect(screen.queryByRole('button',{name:'Nouvelle note'})).toBeNull();
  expect(screen.queryByRole('button',{name:'Enregistrer maintenant'})).toBeNull();fireEvent.click(screen.getByRole('button',{name:'Historique de la note'}));
  await screen.findByText('Version 1 · Initiale');expect(notesApi.execute).not.toHaveBeenCalled();
});
it('ne rend pas un Office importé modifiable',async()=>{
  vi.mocked(notesApi.read).mockResolvedValue({...head,read_only:true,source_kind:'external_office'});
  render(<ProjectNotesPanel projectId="p1"/>);const title=await open();expect(title.readOnly).toBe(true);expect(screen.queryByRole('button',{name:'Enregistrer maintenant'})).toBeNull();
  expect(screen.getByText(/Document Office en consultation/)).toBeTruthy();
});
it('consulte une version avec ses images remappées et restaure avec une nouvelle commande',async()=>{
  const oldId='33333333-3333-4333-8333-333333333333';
  const version:NoteVersion={id:'v1',revision:1,title:'Historique',actor_id:null,created_at:head.updated_at,operation:'create',project_id:'p1',note_id:id,
    value:{title:'Historique',content:{version:1,blocks:[{type:'image',attachment_id:oldId,caption:'Image historique'}]}},attachment_bindings:{[oldId]:imageId}};
  vi.spyOn(notesApi,'version').mockResolvedValue(version);
  render(<ProjectNotesPanel projectId="p1"/>);await open();fireEvent.click(screen.getByRole('button',{name:'Historique de la note'}));
  fireEvent.click(await screen.findByRole('button',{name:'Consulter la version 1'}));const preview=await screen.findByRole('region',{name:'Aperçu de la version historique'});
  expect(within(preview).getByRole('img',{name:'Image historique'}).getAttribute('src')).toContain(imageId);
  fireEvent.click(within(preview).getByRole('button',{name:'Restaurer cette version'}));await screen.findByText('Enregistrée · version 3');
  expect(notesApi.execute).toHaveBeenCalledWith('p1',id,expect.objectContaining({kind:'restore',payload:expect.objectContaining({version_id:'v1',expected_revision:2})}),expect.any(AbortSignal));
  expect(version.value.content.blocks[0]).toMatchObject({attachment_id:oldId});
});
it('garde listes, cases et cellules éditables sans convertir le contenu en texte brut',async()=>{
  vi.mocked(notesApi.read).mockResolvedValue({...head,content:{version:1,blocks:[
    {type:'list',kind:'checklist',items:[{runs:[run('Action')],checked:false,indent:2}]},
    {type:'table',header:true,rows:[[[run('Jalon')],[run('Date')]],[[run('Revue')],[run('Demain')]]]},
  ]}});
  render(<ProjectNotesPanel projectId="p1"/>);await open();fireEvent.click(screen.getByLabelText('Case 1 du bloc 1'));
  const cell=screen.getByRole('textbox',{name:'Ligne 2, colonne 2 du bloc 2'});cell.textContent='Vendredi';fireEvent.input(cell);
  fireEvent.click(screen.getByRole('button',{name:'Enregistrer maintenant'}));await screen.findByText('Enregistrée · version 3');
  expect(vi.mocked(notesApi.execute).mock.calls[0][2]).toMatchObject({payload:{content:{blocks:[
    {type:'list',items:[{checked:true,indent:2}]},{type:'table',header:true,rows:[expect.anything(),[expect.anything(),[{text:'Vendredi'}]]]},
  ]}}});
});
it('ne rend pas les liens exécutables et ignore script/image lors de la lecture du DOM',()=>{
  const element=document.createElement('div');element.innerHTML='<strong>Test</strong><script>code</script><a href="javascript:alert(1)">Lien</a><img src="https://remote.test/pixel">';
  const runs=readNoteRuns(element);expect(runs.map(r=>r.text).join('')).toBe('TestLien');expect(runs[0].marks).toEqual(['bold']);expect(runs[1].href).toBeNull();
  render(<NoteContentView content={{version:1,blocks:[{type:'paragraph',align:'left',runs:[{...run('Lien'),href:'javascript:alert(1)'}]}]}} projectId="p1" noteId={id}/>);
  expect(screen.queryByRole('link')).toBeNull();
});
it('valide les brouillons fermés et isole projets et opérateurs sans effacer les captures invalides',()=>{
  writeNoteDraft(draft());expect(readNoteDraft('p1',id,'reader').draft).toBeNull();expect(readNoteDraft('p2',id,'local').draft).toBeNull();
  expect(validNoteContent({version:true,blocks:[]})).toBe(false);
  expect(validNoteContent({version:1,blocks:[{type:'html',html:'<script>'}]})).toBe(false);
  const invalid={...draft(),pending:{kind:'save',payload:{command_id:crypto.randomUUID(),expected_revision:true,title:'Texte',content:blankNote(),attachment_ids:[]}}};
  const key=noteDraftKey('p1',id,'local');localStorage.setItem(key,JSON.stringify(invalid));expect(readNoteDraft('p1',id,'local').error).toBeTruthy();expect(localStorage.getItem(key)).toBe(JSON.stringify(invalid));
  expect(()=>boundVersionContent({value:{content:{version:1,blocks:[{type:'image',attachment_id:imageId,caption:''}]}},attachment_bindings:{}} as NoteVersion)).toThrow('liaison');
});
