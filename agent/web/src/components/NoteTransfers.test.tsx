import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { NoteAttachments } from './NoteAttachments';
import { NoteImportPanel } from './NoteImportPanel';
import { NoteSourcePanel } from './NoteSourcePanel';
import { api } from '../lib/api';
import { blankNote, NoteHttpError, notesApi, type NoteAttachment } from '../lib/projectNotes';
import { fileDigest, importJournalKey, noteTransferApi, readImportJournal, readUploadJournal, saveTransfer, selectNoteFiles, uploadJournalKey,
  type ImportCommand, type ImportJournal, type ImportPreview, type ImportResult, type UploadJournal } from '../lib/noteTransfers';

// Native WebCrypto in this test runner; production uses the browser's Crypto.
const {webcrypto}=(await import('node:'+'crypto')) as {webcrypto:Crypto};

const noteId='11111111-1111-4111-8111-111111111111',assetId='22222222-2222-4222-8222-222222222222',linkId='33333333-3333-4333-8333-333333333333';
const asset:NoteAttachment={id:assetId,project_id:'p1',note_id:noteId,filename:'preuve.txt',size_bytes:6,sha256:'a'.repeat(64),content_type:'text/plain'};
const source={kind:'upload' as const,link_id:null,relative_path:''};
const preview:ImportPreview={format:'agent-note-source-preview',version:1,kind:'legacy_text_note',title:'Compte rendu',editable:true,read_only:true,
  planned_note_id:noteId,preview_sha256:'b'.repeat(64),can_apply:true,total_bytes:6,files:[],versions:[{source_key:'current',source_actor:null,
    content:blankNote(),can_import_rich:true,issues:[]}],embedded_images:[],issues:[]};
const command:ImportCommand={command_id:assetId,planned_note_id:noteId,expected_preview_sha256:'b'.repeat(64),mode:'rich',source};
const imported=(c:ImportCommand):ImportResult=>({note:{id:c.planned_note_id,project_id:'p1',title:'Compte rendu',revision:1,version_id:'v1',updated_at:'2026-10-07T10:00:00Z',actor_id:'local',content:blankNote(),attachment_ids:[],read_only:false,source_kind:'legacy_text_note'},
  command_id:c.command_id,import_id:'i1',replayed:false,source_kind:'legacy_text_note',originals_sha256:'d'.repeat(64),source_descriptor:c.source,
  source_files:[{relative_path:'compte-rendu.txt',size_bytes:6,sha256:'e'.repeat(64)}],source_metadata:{},source_versions:[{source_key:'current',source_actor:null,current_version_id:'v1',conversion_mode:'source_plain'}]});
function file(name='preuve.txt',body='preuve',relativePath=''){
  const value=new File([body],name,{type:'text/plain'}),bytes=new TextEncoder().encode(body);
  Object.defineProperty(value,'arrayBuffer',{value:async()=>bytes.buffer,configurable:true});
  if(relativePath)Object.defineProperty(value,'webkitRelativePath',{value:relativePath});return value;
}
beforeEach(()=>{
  localStorage.clear();vi.stubGlobal('crypto',webcrypto);
  vi.spyOn(notesApi,'attachments').mockResolvedValue({items:[]});
  vi.spyOn(noteTransferApi,'upload').mockImplementation(async(_,__,___,value)=>({attachment:{...asset,filename:value.name,size_bytes:value.size,sha256:await fileDigest(value)},replayed:false}));
  vi.spyOn(noteTransferApi,'preview').mockImplementation(async(_,id,__,___,selection)=>({...preview,planned_note_id:id,files:selection?.inventory||[]}));
  vi.spyOn(noteTransferApi,'apply').mockImplementation(async(_,c)=>imported(c));
  vi.spyOn(noteTransferApi,'replay').mockImplementation(async(_,c)=>({...imported(c),replayed:true}));
  vi.spyOn(noteTransferApi,'source').mockResolvedValue(imported(command));
  vi.spyOn(api,'networkLinks').mockResolvedValue([{id:linkId,code:'notes',libelle:'Notes du projet',chemin:'V:/Projet/Notes',ordre:1,required:false}]);
});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.unstubAllGlobals();localStorage.clear();});
const renderUpload=(onAttach=vi.fn(),extra:Partial<Parameters<typeof NoteAttachments>[0]>={})=>render(<NoteAttachments projectId="p1" noteId={noteId} operatorId="local" revision={1} active canEdit selectedIds={[]} onAttach={onAttach} onImage={vi.fn()} {...extra}/>);
function chooseUpload(value=file()){fireEvent.change(screen.getByLabelText('Ajouter une pièce jointe'),{target:{files:[value]}});}
async function upload(){fireEvent.click(screen.getByRole('button',{name:'Joindre le fichier'}));await screen.findByText(/Pièce copiée/);}
it('conserve la commande avant la copie puis associe la pièce reçue à la note',async()=>{
  const attached=vi.fn();vi.mocked(noteTransferApi.upload).mockImplementation(async(_,__,nonce,value)=>{
    expect(readUploadJournal('p1',noteId,'local').value?.command_id).toBe(nonce);
    const stored={...asset,sha256:await fileDigest(value)};vi.mocked(notesApi.attachments).mockResolvedValue({items:[stored]});
    return {attachment:stored,replayed:false};
  });renderUpload(attached);chooseUpload();await upload();expect(attached).toHaveBeenCalledWith(assetId);
  expect(localStorage.getItem(uploadJournalKey('p1',noteId,'local'))).toBeNull();expect(screen.getByRole('link',{name:'preuve.txt'}).getAttribute('href')).toContain('/download');
});
it('reprend la même copie après réponse perdue et refuse un fichier différent',async()=>{
  vi.mocked(noteTransferApi.upload).mockRejectedValueOnce(new TypeError('Connexion coupée'));const view=renderUpload();chooseUpload();
  fireEvent.click(screen.getByRole('button',{name:'Joindre le fichier'}));await screen.findByText('Connexion coupée');const first=vi.mocked(noteTransferApi.upload).mock.calls[0][2];
  view.unmount();renderUpload();await screen.findByText(/Copie à reprendre/);chooseUpload(file('autre.txt','autre'));
  fireEvent.click(screen.getByRole('button',{name:'Reprendre la copie'}));await screen.findByText(/Resélectionnez le même fichier/);expect(noteTransferApi.upload).toHaveBeenCalledTimes(1);
  chooseUpload();fireEvent.click(screen.getByRole('button',{name:'Reprendre la copie'}));await screen.findByText(/Pièce copiée/);expect(vi.mocked(noteTransferApi.upload).mock.calls[1][2]).toBe(first);
});
it('ne transmet rien si la commande de copie ne peut pas être conservée',async()=>{
  renderUpload();chooseUpload();vi.spyOn(Storage.prototype,'setItem').mockImplementation(()=>{throw new DOMException('quota');});
  fireEvent.click(screen.getByRole('button',{name:'Joindre le fichier'}));await screen.findByText(/La commande ne peut pas être conservée/);expect(noteTransferApi.upload).not.toHaveBeenCalled();
});
it('refuse les grandes pièces avant toute lecture du contenu',async()=>{
  const value=file();Object.defineProperty(value,'size',{value:5*1024*1024+1});const read=vi.spyOn(value,'arrayBuffer');renderUpload();chooseUpload(value);
  fireEvent.click(screen.getByRole('button',{name:'Joindre le fichier'}));await screen.findByText(/5 Mio requise/);expect(read).not.toHaveBeenCalled();expect(noteTransferApi.upload).not.toHaveBeenCalled();
});
it('réserve l’ajout et les images aux éditeurs, rend une ancienne pièce réassociable',async()=>{
  vi.mocked(notesApi.attachments).mockResolvedValue({items:[{...asset,content_type:'image/png'}]});const attached=vi.fn(),image=vi.fn();
  renderUpload(attached,{onImage:image});fireEvent.click(await screen.findByRole('button',{name:'Associer à cette note'}));expect(attached).toHaveBeenCalledWith(assetId);
  fireEvent.click(screen.getByRole('button',{name:'Insérer l’image dans la note'}));expect(image).toHaveBeenCalledWith(assetId,'preuve.txt');
  cleanup();renderUpload(vi.fn(),{canEdit:false});await screen.findByRole('link',{name:'preuve.txt'});expect(screen.queryByLabelText('Ajouter une pièce jointe')).toBeNull();expect(screen.queryByRole('button',{name:'Insérer l’image dans la note'})).toBeNull();
});
it('ignore une copie tardive après départ du projet et garde sa commande',async()=>{
  let finish!:(value:{attachment:NoteAttachment;replayed:boolean})=>void;vi.mocked(noteTransferApi.upload).mockReturnValueOnce(new Promise(resolve=>{finish=resolve;}));
  const attached=vi.fn(),view=renderUpload(attached),value=file();chooseUpload(value);fireEvent.click(screen.getByRole('button',{name:'Joindre le fichier'}));
  await waitFor(()=>expect(noteTransferApi.upload).toHaveBeenCalledTimes(1));const call=vi.mocked(noteTransferApi.upload).mock.calls[0];view.unmount();expect(call[4]?.aborted).toBe(true);
  finish({attachment:{...asset,sha256:await fileDigest(value)},replayed:false});await Promise.resolve();expect(attached).not.toHaveBeenCalled();expect(readUploadJournal('p1',noteId,'local').value?.command_id).toBe(call[2]);
});
const renderImport=(onImported=vi.fn(),extra:Partial<Parameters<typeof NoteImportPanel>[0]>={})=>render(<NoteImportPanel projectId="p1" operatorId="local" active canEdit onImported={onImported} {...extra}/>);
async function chooseImport(files=[file('compte-rendu.txt')],folder=false){fireEvent.change(screen.getByLabelText(folder?'Dossier d’une note XPilot':'Fichier(s) de la note'),{target:{files}});await screen.findByText(/fichier\(s\) sélectionné/);}
async function inspectImport(){fireEvent.click(screen.getByRole('button',{name:'Afficher l’aperçu de l’import'}));return screen.findByRole('region',{name:'Aperçu de l’import'});}
async function applyImport(){fireEvent.click(screen.getByLabelText('J’ai vérifié la note, ses versions et les originaux à conserver.'));fireEvent.click(screen.getByRole('button',{name:'Importer cette note dans le projet'}));}
it('affiche l’aperçu avant création et fige la sélection et la commande avant l’envoi',async()=>{
  const done=vi.fn();vi.mocked(noteTransferApi.apply).mockImplementation(async(_,c)=>{
    expect(readImportJournal('p1','local').value?.command).toEqual(c);return imported(c);
  });renderImport(done);await chooseImport();await inspectImport();expect(noteTransferApi.apply).not.toHaveBeenCalled();
  expect(screen.getByRole('button',{name:'Importer cette note dans le projet'}).matches(':disabled')).toBe(true);await applyImport();await waitFor(()=>expect(done).toHaveBeenCalledTimes(1));
  expect(localStorage.getItem(importJournalKey('p1','local'))).toBeNull();expect(vi.mocked(noteTransferApi.apply).mock.calls[0][1].source).toEqual(source);
});
it('vérifie une confirmation après réponse perdue sans resélection ni nouvel import',async()=>{
  vi.mocked(noteTransferApi.apply).mockRejectedValueOnce(new TypeError('Réponse perdue'));const view=renderImport();await chooseImport();await inspectImport();await applyImport();await screen.findByText('Réponse perdue');
  const pending=vi.mocked(noteTransferApi.apply).mock.calls[0][1];view.unmount();const done=vi.fn();renderImport(done);
  fireEvent.click(await screen.findByRole('button',{name:'Vérifier l’import déjà envoyé'}));await waitFor(()=>expect(done).toHaveBeenCalledWith(pending.planned_note_id));
  expect(noteTransferApi.replay).toHaveBeenCalledWith('p1',pending,expect.any(AbortSignal));expect(noteTransferApi.apply).toHaveBeenCalledTimes(1);
});
it('reprend un import non confirmé seulement avec les mêmes fichiers et la même commande',async()=>{
  const selected=await selectNoteFiles([file('compte-rendu.txt')]),journal:ImportJournal={format:1,project_id:'p1',operator_id:'local',command,inventory:selected.inventory};
  saveTransfer(importJournalKey('p1','local'),journal);vi.mocked(noteTransferApi.replay).mockRejectedValue(new NoteHttpError(404,'Non confirmé'));renderImport();
  fireEvent.click(await screen.findByRole('button',{name:'Vérifier l’import déjà envoyé'}));await screen.findByText(/Aucun import confirmé/);
  fireEvent.change(screen.getByLabelText('Fichier(s) de la note'),{target:{files:[file('compte-rendu.txt','différent')]}});await screen.findByText(/exactement les mêmes fichiers/);expect(noteTransferApi.apply).not.toHaveBeenCalled();
  await chooseImport();fireEvent.click(screen.getByRole('button',{name:'Reprendre le même import'}));await waitFor(()=>expect(noteTransferApi.apply).toHaveBeenCalledTimes(1));expect(vi.mocked(noteTransferApi.apply).mock.calls[0][1]).toEqual(command);
});
it('ne substitue pas le mode texte simple à un import riche incompatible sans choix humain',async()=>{
  vi.mocked(noteTransferApi.preview).mockImplementation(async(_,id,mode,__,selection)=>({...preview,planned_note_id:id,files:selection!.inventory,can_apply:mode==='plain',
    versions:[{...preview.versions[0],content:mode==='rich'?null:blankNote(),can_import_rich:mode==='plain',issues:mode==='rich'?[{path:'bloc',message:'Style non représentable'}]:[]}]}));
  renderImport();await chooseImport();await inspectImport();expect(screen.getByText('Style non représentable · bloc')).toBeTruthy();expect(screen.getByRole('button',{name:'Importer cette note dans le projet'}).matches(':disabled')).toBe(true);
  fireEvent.change(screen.getByLabelText('Mode d’import'),{target:{value:'plain'}});expect(screen.queryByRole('region',{name:'Aperçu de l’import'})).toBeNull();await inspectImport();
  expect(noteTransferApi.preview).toHaveBeenLastCalledWith('p1',expect.any(String),'plain',source,expect.anything(),expect.any(AbortSignal));expect(noteTransferApi.apply).not.toHaveBeenCalled();
});
it('conserve toutes les versions d’un dossier choisi et n’invente pas leurs auteurs',async()=>{
  vi.mocked(noteTransferApi.preview).mockImplementation(async(_,id,__,___,selection)=>({...preview,planned_note_id:id,files:selection!.inventory,kind:'xpilot_note',
    versions:[{...preview.versions[0],source_key:'20261006'}, {...preview.versions[0],source_key:'current',source_actor:'Auteur source'}]}));
  renderImport();await chooseImport([file('manifest.json','{}','Note/manifest.json'),file('content.html','<p>Courant</p>','Note/content.html'),file('content.html','<p>Avant</p>','Note/versions/20261006/content.html')],true);
  await inspectImport();fireEvent.change(screen.getByLabelText('Version source à consulter'),{target:{value:'0'}});expect(screen.getByText('Auteur source : non renseigné')).toBeTruthy();
  const selection=vi.mocked(noteTransferApi.preview).mock.calls[0][4]!;expect(selection.inventory.map(f=>f.relative_path)).toEqual(['manifest.json','content.html','versions/20261006/content.html']);
});
it('choisit explicitement un lien réseau et son chemin sans scanner lors de l’ouverture',async()=>{
  renderImport();expect(api.networkLinks).not.toHaveBeenCalled();expect(noteTransferApi.preview).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText('Source de la note'),{target:{value:'project_link'}});await screen.findByRole('option',{name:/Notes du projet/});
  fireEvent.change(screen.getByLabelText('Lien du projet'),{target:{value:linkId}});fireEvent.change(screen.getByLabelText('Fichier ou dossier de note dans ce lien'),{target:{value:'Notes/LED'}});
  await inspectImport();expect(noteTransferApi.preview).toHaveBeenCalledWith('p1',expect.any(String),'rich',{kind:'project_link',link_id:linkId,relative_path:'Notes/LED'},null,expect.any(AbortSignal));
  expect(noteTransferApi.apply).not.toHaveBeenCalled();
});
it('montre les limites d’accès réseau et préserve une commande après refus de reprise',async()=>{
  const network={...command,source:{kind:'project_link' as const,link_id:linkId,relative_path:'Notes/LED'}};
  saveTransfer(importJournalKey('p1','local'),{format:1,project_id:'p1',operator_id:'local',command:network,inventory:[]});
  vi.mocked(noteTransferApi.replay).mockRejectedValue(new NoteHttpError(409,'Commande historique restaurée'));renderImport();
  fireEvent.click(await screen.findByRole('button',{name:'Vérifier l’import déjà envoyé'}));await screen.findByText('Commande historique restaurée');
  expect(readImportJournal('p1','local').value?.command).toEqual(network);expect(noteTransferApi.apply).not.toHaveBeenCalled();
});
it('refuse un aperçu d’un autre projet préparé et n’affiche pas d’images avant acquisition gérée',async()=>{
  vi.mocked(noteTransferApi.preview).mockResolvedValue({...preview,planned_note_id:'autre'});renderImport();await chooseImport();fireEvent.click(screen.getByRole('button',{name:'Afficher l’aperçu de l’import'}));
  await screen.findByText(/Aperçu reçu différent/);expect(screen.queryByRole('region',{name:'Aperçu de l’import'})).toBeNull();
});
it('ne lit ni ne transmet les sources pour un lecteur ou une vue désactivée',async()=>{
  renderImport(vi.fn(),{canEdit:false});expect(screen.getByLabelText('Fichier(s) de la note').matches(':disabled')).toBe(true);expect(noteTransferApi.preview).not.toHaveBeenCalled();
  cleanup();renderImport(vi.fn(),{active:false});expect(screen.getByRole('button',{name:'Afficher l’aperçu de l’import'}).matches(':disabled')).toBe(true);
});
it('conserve une commande locale illisible sans l’exécuter ni la remplacer',()=>{
  const key=importJournalKey('p1','local'),raw=JSON.stringify({format:true,command:{role:'owner'}});localStorage.setItem(key,raw);renderImport();
  expect(screen.getByText(/Commande locale illisible/)).toBeTruthy();expect(localStorage.getItem(key)).toBe(raw);expect(noteTransferApi.replay).not.toHaveBeenCalled();
});
it('isole les transferts par projet et opérateur et refuse un inventaire booléen',()=>{
  const upload:UploadJournal={format:1,project_id:'p1',note_id:noteId,operator_id:'local',command_id:assetId,filename:'preuve.txt',size_bytes:6,sha256:'a'.repeat(64)};
  saveTransfer(uploadJournalKey('p1',noteId,'local'),upload);expect(readUploadJournal('p2',noteId,'local').value).toBeNull();expect(readUploadJournal('p1',noteId,'reader').value).toBeNull();
  localStorage.setItem(importJournalKey('p1','local'),JSON.stringify({format:1,project_id:'p1',operator_id:'local',command,inventory:[{relative_path:'x.txt',size_bytes:true,sha256:'a'.repeat(64)}]}));
  expect(readImportJournal('p1','local').error).toBeTruthy();
});
it('télécharge les originaux par le moteur et affiche les auteurs descriptifs sans rendre le HTML',async()=>{
  vi.mocked(noteTransferApi.source).mockResolvedValue({...imported(command),source_files:[{relative_path:'versions/avant/content.html',size_bytes:12,sha256:'a'.repeat(64)}],source_metadata:{updated_by:'Auteur source'},
    source_versions:[{source_key:'avant',source_actor:null,current_version_id:'v1',conversion_mode:'html'}]});
  render(<NoteSourcePanel projectId="p1" noteId={noteId} active/>);const link=await screen.findByRole('link',{name:'versions/avant/content.html'});
  expect(link.getAttribute('href')).toContain('relative_path=versions%2Favant%2Fcontent.html');expect(screen.getByText('Auteur source')).toBeTruthy();
  fireEvent.click(screen.getByText('Versions conservées à l’import (1)'));expect(screen.getByText(/auteur source non renseigné/)).toBeTruthy();expect(document.querySelector('iframe')).toBeNull();
});
