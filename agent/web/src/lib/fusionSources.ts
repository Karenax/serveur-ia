import { request } from './http';
export type LibrarySource = {id:string;source_id:string|null;kind:string;title:string;project_id:string;project_code?:string|null;
  erp_project_id?:string|null;note_id?:string|null;labels:string[];status:string;current:boolean;date:string;mime_type?:string|null;file_format?:FileFormat|null;
  extraction_status:string;index_status:string;provider?:string|null;version_id?:string|null;source_url?:string};
export type SourcePage = {items:LibrarySource[];total:number;offset:number;limit:number;has_next:boolean;labels:string[]};
export type FileFormat = 'pdf'|'png'|'jpeg'|'webp'|'txt'|'md'|'csv'|'docx'|'doc'|'xlsx'|'xls'|'xlsm'|'pptx'|'ppt'|'html'|'wav'|'mp3'|'m4a'|'webm'|'ogg'|'eml';
export const FILE_FORMATS:Record<FileFormat,string>={pdf:'PDF',png:'PNG',jpeg:'JPEG',webp:'WebP',txt:'TXT',md:'Markdown',csv:'CSV',
  docx:'DOCX',doc:'DOC',xlsx:'XLSX',xls:'XLS',xlsm:'XLSM',pptx:'PPTX',ppt:'PPT',html:'HTML',wav:'WAV',mp3:'MP3',m4a:'M4A',webm:'WebM',ogg:'OGG',eml:'EML'};
export type SourceFilters = {query?:string;project_id?:string;source_type?:string;file_format?:FileFormat|'all'|'unknown';label?:string;status?:string;
  sort?:'title_asc'|'title_desc'|'date_asc'|'date_desc';offset?:number;limit?:number};
export type SourceImportResult = {source_id?:string;id?:string;replayed?:boolean;unchanged?:boolean;extraction_error?:string|null;status?:string;
  reinterpreted?:boolean;extraction_version_id?:string};
export type SourceGraph = {nodes:{id:string;label:string;kind:'project'|'source'|'knowledge'|'session';project_id:string;source_id?:string}[];
  edges:{id:string;source:string;target:string;kind:'belongs_to'|'cites'|'session_source';inferred:false}[];truncated:boolean;
  offset?:number;limit?:number;total?:number;has_next?:boolean;page_provenance_complete?:boolean};
export type DriveConnection = {enabled?:boolean;configured:boolean;last_import?:string|null;connection_scope?:string;token_expiry?:string};
export type CalendarEvent = {uid:string;summary?:string;dtstart?:string;dtend?:string;description?:string;location?:string;attendees?:{value:string;parameters:string[]}[]};
export type SourceSearchHit = {id:string;source_id:string;project_id:string;modality:string;text:string;excerpt:string;locator:Record<string,unknown>;score:number;source_url:string;profile_key:string};
const root='/api/v1/workspace/sources';
export const fusionSources={
  list:(filters:SourceFilters={},signal?:AbortSignal)=>{
    const query=new URLSearchParams();Object.entries({...filters,limit:filters.limit??25}).forEach(([key,value])=>{
      if(value!==undefined&&value!=='')query.set(key,String(value));});
    return request<SourcePage>(`${root}?${query}`,{signal},30_000);
  },
  graph:(projectId?:string,signal?:AbortSignal,offset=0)=>request<SourceGraph>(`/api/v1/workspace/source-graph?limit=200&offset=${offset}${projectId?`&project_id=${encodeURIComponent(projectId)}`:''}`,{signal}),
  labels:(sourceId:string,labels:string[])=>request<{source_id:string;labels:string[]}>(`${root}/${encodeURIComponent(sourceId)}/labels`,{method:'PUT',body:JSON.stringify({labels})}),
  ocr:(sourceId:string)=>request<{source_id:string;recognized_pages:number;empty_pages:number;extraction_status:string;current:boolean}>(`${root}/${encodeURIComponent(sourceId)}/ocr`,{method:'POST',activity:'Reconnaissance du texte du scan'},0),
  cancelOcr:(sourceId:string)=>request<{cancel_requested:boolean}>(`${root}/${encodeURIComponent(sourceId)}/ocr/cancel`,{method:'POST'}),
  file:(projectId:string,file:File,folder=false)=>{
    const form=new FormData();form.append('project_id',projectId);form.append('file',file);
    form.append('provider',folder?'folder':'file');form.append('provider_key',folder?file.webkitRelativePath||file.name:file.name);
    return request<SourceImportResult>(`${root}/imports/file`,{method:'POST',body:form});
  },
  url:(projectId:string,url:string)=>request<SourceImportResult>(`${root}/imports/url`,{method:'POST',body:JSON.stringify({project_id:projectId,url})}),
  drive:(projectId:string,fileId:string)=>request<SourceImportResult>(`${root}/imports/drive`,{method:'POST',body:JSON.stringify({project_id:projectId,file_id:fileId})}),
  driveStatus:()=>request<DriveConnection>(`${root}/connectors/drive`),
  connectDrive:(accessToken:string)=>request<DriveConnection>(`${root}/connectors/drive`,{method:'PUT',body:JSON.stringify({access_token:accessToken})}),
  calendar:(file:File)=>{const form=new FormData();form.append('file',file);return request<{events:CalendarEvent[];sha256:string;context_only:true;dates_are_imported_metadata:true}>(`${root}/calendar/preview`,{method:'POST',body:form});},
  passages:(id:string,signal?:AbortSignal)=>request<{source_id:string;version_id:string|null;passages:{id:string;text:string;locator:Record<string,unknown>}[]}>(`${root}/${encodeURIComponent(id)}/passages`,{signal}),
  original:(id:string)=>`${root}/${encodeURIComponent(id)}/original`,
  search:(query:string,projectId?:string,sourceIds:string[]=[])=>request<{items:SourceSearchHit[];issues?:{source_id:string;error:string}[]}>(`${root}/search?${new URLSearchParams({query,...(projectId?{project_id:projectId}:{}),source_ids:sourceIds.join(',')})}`),
};
