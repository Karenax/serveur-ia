import { NOTE_ATTACHMENT_BUDGET, noteRequest, noteUrl, type NoteContent, type NoteDetail, type NoteAttachment } from './projectNotes';

export type NoteSource={kind:'upload'|'project_link';link_id:string|null;relative_path:string};
export type SourceFile={relative_path:string;size_bytes:number;sha256:string;kind?:string};
export type ImportCommand={command_id:string;planned_note_id:string;expected_preview_sha256:string;mode:'rich'|'plain';source:NoteSource};
export type ImportPreview={format:'agent-note-source-preview';version:1;kind:string;title:string;editable:boolean;read_only:boolean;
  planned_note_id:string;preview_sha256:string;can_apply:boolean;total_bytes:number;files:SourceFile[];
  versions:{source_key:string;source_actor:string|null;content:NoteContent|null;can_import_rich:boolean;issues:{path:string;message:string}[]}[];
  issues?:{path:string;message:string}[];embedded_images?:{id:string;filename:string}[]};
export type ImportResult={note:NoteDetail;command_id:string;import_id:string;replayed:boolean;source_kind:string;originals_sha256:string;
  source_descriptor:NoteSource;source_files:SourceFile[];source_metadata:Record<string,string>;
  source_versions:{source_key:string;source_actor:string|null;current_version_id:string;conversion_mode:string}[]};
export type UploadFileSelection={files:File[];inventory:SourceFile[]};
const imports=(projectId:string)=>noteUrl(projectId,'imports');
function multipart(selection:UploadFileSelection){const form=new FormData();form.set('paths',JSON.stringify(selection.inventory.map(i=>i.relative_path)));
  selection.files.forEach((file,i)=>form.append('files',file,selection.inventory[i].relative_path));return form;}
export const noteTransferApi={
  upload:(projectId:string,noteId:string,commandId:string,file:File,signal?:AbortSignal)=>{
    const form=new FormData();form.set('command_id',commandId);form.set('file',file,file.name);
    return noteRequest<{attachment:NoteAttachment;replayed:boolean}>(noteUrl(projectId,noteId)+'/attachments',{method:'POST',body:form,signal});
  },
  preview:(projectId:string,plannedId:string,mode:'rich'|'plain',source:NoteSource,selection:UploadFileSelection|null,signal?:AbortSignal)=>{
    if(source.kind==='project_link')return noteRequest<ImportPreview>(imports(projectId)+'/network/preview',
      {method:'POST',body:JSON.stringify({planned_note_id:plannedId,mode,source}),signal},120_000);
    if(!selection)throw new Error('Sélectionnez les fichiers de la note');
    const form=multipart(selection);form.set('planned_note_id',plannedId);form.set('mode',mode);
    return noteRequest<ImportPreview>(imports(projectId)+'/preview',{method:'POST',body:form,signal},120_000);
  },
  apply:(projectId:string,command:ImportCommand,selection:UploadFileSelection|null,signal?:AbortSignal)=>{
    if(command.source.kind==='project_link')return noteRequest<ImportResult>(imports(projectId)+'/network',
      {method:'POST',body:JSON.stringify(command),signal},120_000);
    if(!selection)throw new Error('Resélectionnez les mêmes fichiers pour reprendre cet import');
    const form=multipart(selection);form.set('command',JSON.stringify(command));
    return noteRequest<ImportResult>(imports(projectId),{method:'POST',body:form,signal},120_000);
  },
  replay:(projectId:string,command:ImportCommand,signal?:AbortSignal)=>noteRequest<ImportResult>(imports(projectId)+'/replay',
    {method:'POST',body:JSON.stringify(command),signal},120_000),
  source:(projectId:string,noteId:string,signal?:AbortSignal)=>noteRequest<ImportResult>(noteUrl(projectId,noteId)+'/source',{signal}),
};
export const isTransferId=(value:unknown):value is string=>typeof value==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);
const digest=(value:unknown):value is string=>typeof value==='string'&&/^[0-9a-f]{64}$/.test(value);
const object=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value);
const exact=(value:Record<string,unknown>,keys:string[])=>Object.keys(value).every(k=>keys.includes(k));
const relative=(value:unknown):value is string=>typeof value==='string'&&value.length>0&&value.length<=1024&&!/[\\:\x00-\x1f]/.test(value)&&
  !value.startsWith('/')&&value.split('/').every(p=>p&&p!=='.'&&p!=='..');
function validInventory(value:unknown):value is SourceFile[]{return Array.isArray(value)&&value.length<=200&&value.every(i=>object(i)&&exact(i,['relative_path','size_bytes','sha256','kind'])&&relative(i.relative_path)&&
  Number.isSafeInteger(i.size_bytes)&&(i.size_bytes as number)>=0&&(i.size_bytes as number)<=50*1024*1024&&digest(i.sha256))&&
  new Set(value.map(i=>i.relative_path.toLowerCase())).size===value.length&&value.reduce((sum,i)=>sum+i.size_bytes,0)<=50*1024*1024;}
function validCommand(value:unknown):value is ImportCommand{
  if(!object(value)||!exact(value,['command_id','planned_note_id','expected_preview_sha256','mode','source'])||!isTransferId(value.command_id)||!isTransferId(value.planned_note_id)||
    !digest(value.expected_preview_sha256)||!['rich','plain'].includes(value.mode as string)||!object(value.source)||!exact(value.source,['kind','link_id','relative_path']))return false;
  const s=value.source;return s.kind==='upload'?s.link_id===null&&s.relative_path==='':
    s.kind==='project_link'&&isTransferId(s.link_id)&&(s.relative_path===''||relative(s.relative_path));
}
export type UploadJournal={format:1;project_id:string;note_id:string;operator_id:string;command_id:string;filename:string;size_bytes:number;sha256:string};
export type ImportJournal={format:1;project_id:string;operator_id:string;command:ImportCommand;inventory:SourceFile[]};
export const uploadJournalKey=(pid:string,nid:string,actor:string)=>'agent.note-upload.v1.'+JSON.stringify([pid,nid,actor]);
export const importJournalKey=(pid:string,actor:string)=>'agent.note-import.v1.'+JSON.stringify([pid,actor]);
function read<T>(key:string,validate:(v:unknown)=>v is T):{value:T|null;error:string}{
  try{const raw=localStorage.getItem(key);if(raw===null)return{value:null,error:''};if(raw.length>300_000)throw new Error();
    const value:unknown=JSON.parse(raw);if(!validate(value))throw new Error();return{value,error:''};}
  catch{return{value:null,error:'Commande locale illisible : elle est conservée. Ne relancez pas une nouvelle commande avant de la vérifier.'};}
}
export const readUploadJournal=(pid:string,nid:string,actor:string)=>read<UploadJournal>(uploadJournalKey(pid,nid,actor),
  (v):v is UploadJournal=>object(v)&&exact(v,['format','project_id','note_id','operator_id','command_id','filename','size_bytes','sha256'])&&v.format===1&&v.project_id===pid&&v.note_id===nid&&v.operator_id===actor&&
    isTransferId(v.command_id)&&typeof v.filename==='string'&&v.filename.length>0&&v.filename.length<=255&&!/[\\/\x00-\x1f]/.test(v.filename)&&
    Number.isSafeInteger(v.size_bytes)&&(v.size_bytes as number)>=1&&(v.size_bytes as number)<=NOTE_ATTACHMENT_BUDGET&&digest(v.sha256));
export const readImportJournal=(pid:string,actor:string)=>read<ImportJournal>(importJournalKey(pid,actor),
  (v):v is ImportJournal=>object(v)&&exact(v,['format','project_id','operator_id','command','inventory'])&&v.format===1&&v.project_id===pid&&v.operator_id===actor&&validCommand(v.command)&&validInventory(v.inventory)&&
    (v.command.source.kind==='project_link'?v.inventory.length===0:v.inventory.length>=1));
export const saveTransfer=(key:string,value:UploadJournal|ImportJournal)=>{
  try{localStorage.setItem(key,JSON.stringify(value));}catch{throw new Error('La commande ne peut pas être conservée sur cet appareil. Libérez de l’espace ou exportez vos brouillons avant de recommencer.');}
};
export async function fileDigest(file:File){
  const bytes=await file.arrayBuffer();if(bytes.byteLength!==file.size)throw new Error('Le fichier sélectionné a changé');
  return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),v=>v.toString(16).padStart(2,'0')).join('');
}
export async function selectNoteFiles(files:File[]):Promise<UploadFileSelection>{
  if(!files.length||files.length>200||files.reduce((n,f)=>n+f.size,0)>50*1024*1024)throw new Error('Sélection limitée à 200 fichiers et 50 Mio');
  const directory=files.every(f=>!!f.webkitRelativePath),raw=files.map(f=>directory?f.webkitRelativePath:f.name);
  const roots=new Set(raw.map(p=>p.split('/')[0]));if(directory&&roots.size!==1)throw new Error('Sélectionnez un seul dossier de note');
  const paths=raw.map(p=>directory?p.split('/').slice(1).join('/'):p);
  if(paths.some(p=>!relative(p))||new Set(paths.map(p=>p.toLowerCase())).size!==paths.length)throw new Error('Noms de fichiers relatifs uniques requis');
  const inventory:SourceFile[]=[];for(let i=0;i<files.length;i++)inventory.push({relative_path:paths[i],size_bytes:files[i].size,sha256:await fileDigest(files[i])});
  return {files,inventory};
}
export const sameInventory=(a:SourceFile[],b:SourceFile[])=>a.length===b.length&&a.every(i=>b.some(j=>i.relative_path===j.relative_path&&i.size_bytes===j.size_bytes&&i.sha256===j.sha256));
