/** Keep canonical version and scope pointers supplied by Agent; never open external URLs. */
export type CitationTarget={source_id?:string|null;source_url?:string;audio_url?:string|null;locator?:Record<string,unknown>};
const id='[A-Za-z0-9_-]+';
export const noteVersionUrl=(project:string,note:string,version:string)=>`/api/v1/projects/${encodeURIComponent(project)}/notes/${encodeURIComponent(note)}/versions/${encodeURIComponent(version)}`;
const notePattern=new RegExp(`^/api/v1/projects/(${id})/notes/(${id})/versions/(${id})$`);
const stagedPattern=new RegExp(`^/api/v1/meeting-sessions/(${id})/note-versions/(${id})$`);
export const isNoteVersionUrl=(url:string|null|undefined)=>!!url&&(notePattern.test(url)||stagedPattern.test(url));
export function noteVersionIdentity(url:string|null|undefined){
  const match=url?notePattern.exec(url):null;
  return match?{projectId:match[1],noteId:match[2],versionId:match[3]}:null;
}
export function stagedNoteVersionIdentity(url:string|null|undefined){
  const match=url?stagedPattern.exec(url):null;
  return match?{sessionId:match[1],versionId:match[2]}:null;
}
export function citationSourceUrl(citation:CitationTarget):string|null{
  const locator=citation.locator||{};
  const identity=['erp_project_id','note_id','note_version_id'].map(key=>locator[key]);
  const url=citation.source_url;
  const noteIdentity=identity.every(value=>typeof value==='string'&&new RegExp(`^${id}$`).test(value));
  if(url){
    const note=notePattern.exec(url);
    if(note){
      if(identity.some((value,index)=>value!=null&&value!==note[index+1]))return null;
      return url;
    }
    const staging=stagedPattern.exec(url);
    if(staging){
      if((locator.session_id!=null&&locator.session_id!==staging[1])||
        ['staged_note_version_id','note_version_id'].some(key=>locator[key]!=null&&locator[key]!==staging[2]))return null;
      return url;
    }
    const source=new RegExp(`^/v1/sources/(${id})(?:/raw)?$`).exec(url);
    if(source){
      if(citation.source_id&&citation.source_id!==source[1])return null;
      return noteIdentity?noteVersionUrl(...identity as [string,string,string]):url;
    }
    const session=new RegExp(`^/api/v1/meeting-sessions/(${id})(?:/segments)?$`).exec(url);
    if(session){
      if(locator.session_id&&locator.session_id!==session[1])return null;
      const staged=locator.staged_note_version_id;
      if(typeof staged==='string'&&new RegExp(`^${id}$`).test(staged)&&!url.endsWith('/segments')){
        if(locator.note_version_id!=null&&locator.note_version_id!==staged)return null;
        return `/api/v1/meeting-sessions/${session[1]}/note-versions/${staged}`;
      }
      return url;
    }
    if(new RegExp(`^/v1/projects/${id}/knowledge$`).test(url))return url;
  }
  if(noteIdentity)
    return noteVersionUrl(...identity as [string,string,string]);
  return citation.source_id?`/v1/sources/${encodeURIComponent(citation.source_id)}`:null;
}
/** Human-readable source viewer; retain exact note versions and other evidence targets. */
export function citationReaderUrl(citation:CitationTarget):string|null{
  const url=citationSourceUrl(citation);
  const source=url?new RegExp(`^/v1/sources/(${id})$`).exec(url):null;
  return source?`/app/sources?source=${encodeURIComponent(source[1])}`:url;
}
export function citationAudioUrl(citation:CitationTarget):string|null{
  const url=citation.audio_url;
  if(!url)return null;
  const session=new RegExp(`^/api/v1/meeting-sessions/(${id})/audio\\?track=(mic|system)`).exec(url);
  if(session&&((citation.locator?.session_id&&citation.locator.session_id!==session[1])||
    (citation.locator?.track&&citation.locator.track!==session[2])))return null;
  return new RegExp(`^/api/v1/(?:meeting-sessions/${id}/audio\\?track=(?:mic|system)|projects/${id}/recordings/${id}/audio)(?:#t=\\d+(?:\\.\\d+)?)?$`).test(url)?url:null;
}
export function citationLocatorText(locator:Record<string,unknown>,separator=': '){
  const names:Record<string,string>={page:'Page',physical_page:'Page physique',printed_page:'Page imprimée',document_part:'Partie du document',
    sheet:'Feuille',range:'Plage',start:'Début',end:'Fin',start_ms:'Début (ms)',end_ms:'Fin (ms)',start_seconds:'Début (s)',end_seconds:'Fin (s)',
    block:'Bloc',block_index:'Bloc',speaker:'Intervenant',track:'Piste',segment_id:'Segment',segment_revision:'Révision du segment',
    revision:'Révision',note_revision:'Version de note',note_version_id:'Identifiant de version de note',mode:'Repérage'};
  return Object.entries(locator).filter(([key,value])=>key in names&&value!=null).map(([key,value])=>
    `${names[key]}${separator}${String(['block','block_index'].includes(key)&&typeof value==='number'&&Number.isInteger(value)&&value>=0?value+1:value)}`).join(' · ');
}
