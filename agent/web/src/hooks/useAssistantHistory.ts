import { useCallback, useEffect, useRef, useState } from "react";
import { request } from "../lib/http";

export type AssistantCitation = {project_code:string; level?:string; validation_mode?:string; reference?:string; excerpt:string; source_id?:string|null;
  source_url?:string;audio_url?:string|null;locator?:Record<string,unknown>};
export type AssistantMessage = {role:"user"|"assistant"; text:string; citations?:AssistantCitation[]; project?:string};
type Thread = {id:string; title:string; project_id:string|null; revision:number; messages:AssistantMessage[]};
type ThreadSummary = Omit<Thread,"messages"> & {message_count:number};
const endpoint = "/api/v1/workspace/assistant-threads";

/** Serialize saves and retain the local draft on conflict. A project change starts a separate thread. */
export function useAssistantHistory(enabled:boolean, messages:AssistantMessage[], projectId:string,
  restore:(messages:AssistantMessage[],projectId:string)=>void, paused=false) {
  const [threads,setThreads] = useState<ThreadSummary[]>([]);
  const [threadId,setThreadId] = useState("");
  const [status,setStatus] = useState("");
  const [error,setError] = useState("");
  const [loading,setLoading] = useState(false);
  const [saveTick,setSaveTick] = useState(0);
  const current = useRef<Thread|null>(null);
  const generation = useRef(0);
  const mounted = useRef(true);
  const serial = useRef<Promise<unknown>>(Promise.resolve());
  const latest = useRef({messages,projectId}); latest.current={messages,projectId};
  const restoring = useRef(false);
  const restoreRef = useRef(restore); restoreRef.current=restore;
  const blocked = useRef(false);
  const refresh = useCallback(async()=>{
    if(!enabled)return;
    const data=await request<{items:ThreadSummary[]}>(endpoint+"?limit=100",{},15000);
    if(mounted.current)setThreads(data.items);
  },[enabled]);
  useEffect(()=>{
    mounted.current=true;
    if(enabled)void refresh().catch(e=>{if(mounted.current)setError(String(e.message));});
    return()=>{mounted.current=false;generation.current++;};
  },[enabled,refresh]);
  const select = useCallback(async(id:string)=>{
    if(!enabled)return;
    const version=++generation.current; setLoading(true);setError("");
    try {
      await serial.current;
      const data=await request<Thread>(`${endpoint}/${encodeURIComponent(id)}`,{},15000);
      if(version!==generation.current||!mounted.current)return;
      current.current=data; blocked.current=false;restoring.current=true;setThreadId(data.id);
      restoreRef.current(data.messages,data.project_id||"");setStatus("Conversation chargée");
    } catch(e){if(version===generation.current&&mounted.current)setError(String((e as Error).message));}
    finally{if(version===generation.current&&mounted.current)setLoading(false);}
  },[enabled]);
  const newThread = useCallback(()=>{
    generation.current++;current.current=null;blocked.current=false;restoring.current=true;
    setThreadId("");setError("");setStatus("");
    restoreRef.current([],latest.current.projectId);
  },[]);
  const fork = useCallback(()=>{
    generation.current++;current.current=null;blocked.current=false;
    setThreadId("");setError("");setStatus("Copie à enregistrer");
    setSaveTick(t=>t+1);
  },[]);
  useEffect(()=>{
    if(!enabled || paused)return;
    if(restoring.current){restoring.current=false;return;}
    if(blocked.current||!messages.length)return;
    const snapshot={messages,projectId};const version=generation.current;
    setStatus("Enregistrement…");
      const save=async()=>{
        if(version!==generation.current||!mounted.current||blocked.current)return;
        try {
          let data:Thread;
          const title=(snapshot.messages.find(m=>m.role==="user")?.text||"Conversation").slice(0,100);
          if(!current.current) data=await request<Thread>(endpoint,{method:"POST",body:JSON.stringify({project_id:snapshot.projectId||null,title,messages:snapshot.messages})},15000);
          else data=await request<Thread>(`${endpoint}/${encodeURIComponent(current.current.id)}`,{method:"PUT",body:JSON.stringify({expected_revision:current.current.revision,title,messages:snapshot.messages})},15000);
          // Do not attach an old response to a newly selected conversation.
          if(version!==generation.current||!mounted.current)return;
          current.current=data;setThreadId(data.id);setStatus("Enregistrée localement");setError("");
          await refresh();
        } catch(e){if(version===generation.current&&mounted.current){blocked.current=true;setError(String((e as Error).message));setStatus("");}}
      };
      serial.current=serial.current.catch(()=>undefined).then(save);
  },[enabled,messages,projectId,saveTick,refresh,paused]);
  // Retrying keeps the draft; a conflict is resolved explicitly by reload or a copy.
  const retry=()=>{blocked.current=false;setError("");setStatus("Enregistrement à relancer");setSaveTick(t=>t+1);};
  return {threads,threadId:threadId.trim(),status,error,loading,select,newThread,fork,retry};
}
