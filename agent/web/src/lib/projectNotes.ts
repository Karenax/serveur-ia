import { agentFetch } from './agentRoutes';
import { invalidateSession, token } from './http';
import { beginActivity } from './asyncActivity';

export type NoteMark='bold'|'italic'|'underline'|'strike'|'code';
export type NoteRun={text:string;marks:NoteMark[];href:string|null;color:string|null};
export type NoteBlock={type:'paragraph';runs:NoteRun[];align:'left'|'center'|'right'}|
  {type:'heading';level:number;runs:NoteRun[]}|
  {type:'list';kind:'bullet'|'ordered'|'checklist';items:{runs:NoteRun[];checked:boolean;indent:number}[]}|
  {type:'table';header:boolean;rows:NoteRun[][][]}|
  {type:'image';attachment_id:string;caption:string};
export type NoteContent={version:1;blocks:NoteBlock[]};
export type NoteSummary={id:string;project_id:string;title:string;revision:number;version_id:string;updated_at:string;actor_id:string|null;excerpt:string};
export type NoteDetail=Omit<NoteSummary,'excerpt'>&{content:NoteContent;attachment_ids:string[];read_only:boolean;source_kind:string|null};
export type NotePage<T>={items:T[];total:number;limit:number;offset:number};
export type NotesList=NotePage<NoteSummary>&{available:boolean;can_edit?:boolean;operator_id?:string};
export type NoteCreate={command_id:string;title:string;content:NoteContent};
export type NoteSave=NoteCreate&{expected_revision:number;attachment_ids:string[]};
export type NoteRestore={command_id:string;expected_revision:number;version_id:string};
export type NotePending={kind:'create';payload:NoteCreate}|{kind:'save';payload:NoteSave}|{kind:'restore';payload:NoteRestore};
export type NoteResult={note:NoteDetail;command_id:string;command_revision:number;replayed:boolean};
export type NoteHistory={id:string;revision:number;title:string;actor_id:string|null;created_at:string;operation:string};
export type NoteVersion=NoteHistory&{project_id:string;note_id:string;value:{title:string;content:NoteContent};attachment_bindings:Record<string,string>};
export type NoteAttachment={id:string;project_id:string;note_id:string;filename:string;size_bytes:number;content_type:string;sha256:string};
export class NoteHttpError extends Error { constructor(public status:number,message:string){super(message);} }
const root=(projectId:string)=>`/api/v1/projects/${encodeURIComponent(projectId)}/notes`;
export const noteUrl=(projectId:string,noteId:string)=>`${root(projectId)}/${encodeURIComponent(noteId)}`;

export async function noteRequest<T>(url:string,init:RequestInit={},timeoutMs=60_000):Promise<T>{
  const finish=['GET','HEAD'].includes((init.method||'GET').toUpperCase())?()=>{}:beginActivity('Enregistrement de la note…');
  const controller=new AbortController(),cancel=()=>controller.abort();
  init.signal?.addEventListener('abort',cancel,{once:true});if(init.signal?.aborted)cancel();
  const timer=window.setTimeout(cancel,timeoutMs);
  try{
    const headers=new Headers(init.headers);if(!(init.body instanceof FormData))headers.set('Content-Type','application/json');
    if((init.method||'GET')!=='GET')headers.set('X-Agent-Token',await token());
    if(controller.signal.aborted)throw new DOMException('Requête interrompue','AbortError');
    const response=await agentFetch(url,{...init,headers,credentials:'same-origin',signal:controller.signal});
    const data=await response.json();
    if(!response.ok){if(response.status===403)invalidateSession();
      throw new NoteHttpError(response.status,typeof data.detail==='string'?data.detail:data.detail?.message||'Notes indisponibles');}
    return data as T;
  }finally{window.clearTimeout(timer);init.signal?.removeEventListener('abort',cancel);finish();}
}
const call=noteRequest;
export const notesApi={
  list:(projectId:string,query='',offset=0,signal?:AbortSignal)=>call<NotesList>(`${root(projectId)}?query=${encodeURIComponent(query)}&offset=${offset}&limit=30`,{signal}),
  read:(projectId:string,noteId:string,signal?:AbortSignal)=>call<NoteDetail>(noteUrl(projectId,noteId),{signal}),
  execute:(projectId:string,noteId:string,pending:NotePending,signal?:AbortSignal)=>call<NoteResult>(
    pending.kind==='create'?root(projectId):noteUrl(projectId,noteId)+(pending.kind==='restore'?'/restore':''),
    {method:pending.kind==='save'?'PUT':'POST',body:JSON.stringify(pending.payload),signal}),
  history:(projectId:string,noteId:string,offset=0,signal?:AbortSignal)=>call<NotePage<NoteHistory>>(`${noteUrl(projectId,noteId)}/history?offset=${offset}&limit=20`,{signal}),
  version:(projectId:string,noteId:string,versionId:string,signal?:AbortSignal)=>call<NoteVersion>(`${noteUrl(projectId,noteId)}/versions/${encodeURIComponent(versionId)}`,{signal}),
  attachments:(projectId:string,noteId:string,signal?:AbortSignal)=>call<{items:NoteAttachment[]}>(`${noteUrl(projectId,noteId)}/attachments`,{signal}),
};
export const blankNote=():NoteContent=>({version:1,blocks:[{type:'paragraph',align:'left',runs:[]}]});
export const safeNoteLink=(value:string)=>{
  if(/[\s\x00-\x1f\\]/.test(value))return false;
  try{const u=new URL(value);return ['http:','https:'].includes(u.protocol)?!!u.hostname&&!u.username&&!u.password:
    u.protocol==='mailto:'&&/^[^?@]+@[^?@]+$/.test(u.pathname)&&!u.search&&!u.hash;}catch{return false;}
};
const uuid=(value:unknown):value is string=>typeof value==='string'&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(value);
const record=(value:unknown):value is Record<string,unknown>=>!!value&&typeof value==='object'&&!Array.isArray(value);
const exact=(value:Record<string,unknown>,keys:string[])=>Object.keys(value).every(k=>keys.includes(k));
const text=(value:unknown,max:number):value is string=>typeof value==='string'&&value.length<=max&&!/[\x00-\x08\x0b-\x1f]/.test(value);
function validRuns(value:unknown,max=500):value is NoteRun[]{return Array.isArray(value)&&value.length<=max&&value.every(r=>
  record(r)&&exact(r,['text','marks','href','color'])&&text(r.text,5000)&&Array.isArray(r.marks)&&r.marks.length<=5&&
  new Set(r.marks).size===r.marks.length&&r.marks.every(m=>['bold','italic','underline','strike','code'].includes(m))&&
  (r.href===null||(typeof r.href==='string'&&r.href.length<=2048&&safeNoteLink(r.href)))&&
  (r.color===null||(typeof r.color==='string'&&/^#[0-9a-fA-F]{6}$/.test(r.color))));}
export function validNoteContent(value:unknown):value is NoteContent{
  if(!record(value)||!exact(value,['version','blocks'])||value.version!==1||!Array.isArray(value.blocks)||value.blocks.length>500)return false;
  if(new TextEncoder().encode(JSON.stringify(value)).length>2_000_000)return false;
  return value.blocks.every(b=>{
    if(!record(b))return false;
    if(b.type==='paragraph')return exact(b,['type','runs','align'])&&validRuns(b.runs)&&['left','center','right'].includes(b.align as string);
    if(b.type==='heading')return exact(b,['type','runs','level'])&&validRuns(b.runs)&&[1,2,3].includes(b.level as number);
    if(b.type==='image')return exact(b,['type','attachment_id','caption'])&&uuid(b.attachment_id)&&text(b.caption,1000);
    if(b.type==='list')return exact(b,['type','kind','items'])&&['bullet','ordered','checklist'].includes(b.kind as string)&&
      Array.isArray(b.items)&&b.items.length>=1&&b.items.length<=500&&b.items.every(i=>record(i)&&exact(i,['runs','checked','indent'])&&
        validRuns(i.runs)&&typeof i.checked==='boolean'&&(b.kind==='checklist'||!i.checked)&&Number.isInteger(i.indent)&&(i.indent as number)>=0&&(i.indent as number)<=6);
    if(b.type==='table')return exact(b,['type','header','rows'])&&typeof b.header==='boolean'&&Array.isArray(b.rows)&&b.rows.length>=1&&b.rows.length<=200&&
      b.rows.every(row=>Array.isArray(row)&&row.length>=1&&row.length<=20&&row.length===(b.rows as unknown[][])[0].length&&row.every(cell=>validRuns(cell,100)));
    return false;
  });
}
export type NoteDraft={format:1;project_id:string;note_id:string;operator_id:string;title:string;content:NoteContent;attachment_ids:string[];
  expected_revision:number;pending:NotePending|null;updated_at:string};
export const noteDraftKey=(projectId:string,noteId:string,operatorId:string)=>'agent.notes.v1.'+JSON.stringify([projectId,noteId,operatorId]);
function validDraft(value:unknown,projectId:string,noteId:string,operatorId:string):value is NoteDraft{
  if(!record(value)||value.format!==1||value.project_id!==projectId||value.note_id!==noteId||value.operator_id!==operatorId||
    !text(value.title,255)||!validNoteContent(value.content)||!Array.isArray(value.attachment_ids)||value.attachment_ids.length>20||
    !value.attachment_ids.every(uuid)||new Set(value.attachment_ids).size!==value.attachment_ids.length||
    !Number.isInteger(value.expected_revision)||(value.expected_revision as number)<0||typeof value.updated_at!=='string')return false;
  if(value.pending===null)return true;
  const p=value.pending;if(!record(p)||!record(p.payload)||!uuid(p.payload.command_id))return false;
  const payload=p.payload;
  if(p.kind==='restore')return noteId!=='new'&&exact(payload,['command_id','expected_revision','version_id'])&&uuid(payload.version_id)&&Number.isInteger(payload.expected_revision)&&(payload.expected_revision as number)>=1;
  if(!['save','create'].includes(p.kind as string)||!text(payload.title,255)||!payload.title.trim()||!validNoteContent(payload.content))return false;
  if(p.kind==='create')return noteId==='new'&&exact(payload,['command_id','title','content']);
  return noteId!=='new'&&exact(payload,['command_id','title','content','expected_revision','attachment_ids'])&&Number.isInteger(payload.expected_revision)&&
    (payload.expected_revision as number)>=1&&Array.isArray(payload.attachment_ids)&&payload.attachment_ids.length<=20&&payload.attachment_ids.every(uuid)&&new Set(payload.attachment_ids).size===payload.attachment_ids.length;
}
export function readNoteDraft(projectId:string,noteId:string,operatorId:string):{draft:NoteDraft|null;error:string}{
  try{const raw=localStorage.getItem(noteDraftKey(projectId,noteId,operatorId));if(raw===null)return{draft:null,error:''};
    if(raw.length>4_500_000)throw new Error();const value:unknown=JSON.parse(raw);
    if(!validDraft(value,projectId,noteId,operatorId))throw new Error();return{draft:value,error:''};
  }catch{return{draft:null,error:'Le brouillon local ne peut pas être lu. Il est conservé ; exportez-le avant de le remplacer.'};}
}
export function writeNoteDraft(draft:NoteDraft){
  localStorage.setItem(noteDraftKey(draft.project_id,draft.note_id,draft.operator_id),JSON.stringify(draft));
}
export const sameNote=(a:Pick<NoteDraft,'title'|'content'|'attachment_ids'>,b:Pick<NoteDraft,'title'|'content'|'attachment_ids'>)=>
  a.title===b.title&&JSON.stringify(a.content)===JSON.stringify(b.content)&&JSON.stringify(a.attachment_ids)===JSON.stringify(b.attachment_ids);
export function boundVersionContent(version:NoteVersion):NoteContent{
  const content=structuredClone(version.value.content);
  for(const block of content.blocks)if(block.type==='image'){
    const bound=version.attachment_bindings[block.attachment_id];if(!uuid(bound))throw new Error('Image historique sans liaison actuelle');block.attachment_id=bound;
  }
  return content;
}
