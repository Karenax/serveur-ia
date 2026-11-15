import { agentFetch } from './agentRoutes';
import { token, invalidateSession } from "./http";
import { withActivity } from './asyncActivity';
import type { AssistantMessage, AssistantCitation } from "../hooks/useAssistantHistory";
type Metadata = {citations:AssistantCitation[]; warnings:string[]};
export function conversationContext(messages:AssistantMessage[]) {
  const selected=messages.filter(m=>m.text && !m.text.startsWith("[Réponse interrompue]")).slice(-12)
    .map(m=>({role:m.role,content:m.text.slice(0,4000)}));
  while(selected.reduce((n,m)=>n+m.content.length,0)>12000)selected.shift();
  return selected;
}
export async function streamAssistant(query:string,projectId:string,evidence:boolean,history:AssistantMessage[],signal:AbortSignal,
  update:(answer:string,metadata:Metadata)=>void) {
  return withActivity('Recherche et rédaction de la réponse…',async()=>{
  const response=await agentFetch("/v1/projects/chat/stream",{method:"POST",credentials:"same-origin",signal,
    headers:{"Content-Type":"application/json","X-Agent-Token":await token()},
    body:JSON.stringify({query,project_id:projectId||null,include_evidence:evidence,history:conversationContext(history)})});
  if(!response.ok){if(response.status===403)invalidateSession();const data=await response.json();throw new Error(typeof data.detail==="string"?data.detail:"Réponse de l’assistant indisponible");}
  if(!response.body)throw new Error("Ce navigateur ne permet pas la lecture progressive");
  const reader=response.body.getReader(),decoder=new TextDecoder();
  let buffer="",answer="",metadata:Metadata={citations:[],warnings:[]},finished=false;
  const frame=(text:string)=>{
    let event="message";const parts:string[]=[];
    for(const line of text.split(/\r?\n/)){if(line.startsWith("event:"))event=line.slice(6).trim();if(line.startsWith("data:"))parts.push(line.slice(5).trimStart());}
    if(!parts.length)return;
    const data=JSON.parse(parts.join("\n"));
    if(event==="error")throw new Error(data.message || "Génération interrompue");
    if(event==="metadata")metadata={citations:data.citations||[],warnings:data.warnings||[]};
    if(event==="delta")answer+=data.text||"";
    if(event==="done"){finished=true;answer=data.answer;metadata={citations:data.citations||metadata.citations,warnings:data.warnings||metadata.warnings};}
    update(answer,metadata);
  };
  try{
    for(;;){const {value,done}=await reader.read();buffer+=done?decoder.decode():decoder.decode(value,{stream:true});
      let boundary;while((boundary=buffer.match(/\r?\n\r?\n/))){const index=boundary.index!;frame(buffer.slice(0,index));buffer=buffer.slice(index+boundary[0].length);}
      if(done)break;
    }
    if(!finished)throw new Error("Connexion interrompue avant la fin de la réponse");
    return {answer,...metadata};
  }finally{await reader.cancel().catch(()=>undefined);reader.releaseLock();}
  });
}
