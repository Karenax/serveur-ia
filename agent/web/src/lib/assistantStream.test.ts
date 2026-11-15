import { afterEach, expect, it, vi } from "vitest";
import { conversationContext, streamAssistant } from "./assistantStream";
vi.mock("./http",()=>({token:vi.fn().mockResolvedValue("local-test-token")}));
afterEach(()=>vi.unstubAllGlobals());
function response(text:string, chunkSize=7) {
  const bytes=new TextEncoder().encode(text);
  return {ok:true,body:new ReadableStream({start(controller){for(let offset=0;offset<bytes.length;offset+=chunkSize)controller.enqueue(bytes.slice(offset,offset+chunkSize));controller.close();}})} as Response;
}
it("reconstitue les fragments UTF-8 et attend une fin explicite",async()=>{
  const fetch=vi.fn().mockResolvedValue(response('event: metadata\ndata: {"citations":[],"warnings":["Source à confirmer"]}\n\nevent: delta\ndata: {"text":"Échéance "}\n\nevent: delta\ndata: {"text":"vendredi"}\n\nevent: done\ndata: {"answer":"Échéance vendredi"}\n\n'));
  vi.stubGlobal("fetch",fetch);const update=vi.fn();
  const result=await streamAssistant("La date ?","brain-p1",true,[],new AbortController().signal,update);
  expect(result.answer).toBe("Échéance vendredi");expect(result.warnings).toEqual(["Source à confirmer"]);
  expect(update.mock.calls.map(c=>c[0])).toContain("Échéance ");
  expect(JSON.parse(fetch.mock.calls[0][1].body).project_id).toBe("brain-p1");
  expect(fetch.mock.calls[0][1].headers["X-Agent-Token"]).toBe("local-test-token");
});
it("garde un fragment reçu mais refuse de le présenter comme réponse terminée",async()=>{
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(response('event: delta\ndata: {"text":"Partiel"}\n\n')));
  const update=vi.fn();await expect(streamAssistant("Date ?","",true,[],new AbortController().signal,update)).rejects.toThrow("avant la fin");
  expect(update).toHaveBeenCalledWith("Partiel",{citations:[],warnings:[]});
});
it("remonte une erreur SSE et exclut les fragments interrompus du contexte borné",async()=>{
  vi.stubGlobal("fetch",vi.fn().mockResolvedValue(response('event: error\ndata: {"message":"Modèle indisponible"}\n\n')));
  await expect(streamAssistant("Date ?","",true,[],new AbortController().signal,vi.fn())).rejects.toThrow("Modèle indisponible");
  const messages=Array.from({length:20},()=>({role:"user" as const,text:"x".repeat(4000)}));
  messages.push({role:"user",text:"[Réponse interrompue] ancienne erreur"});
  const selected=conversationContext(messages);
  expect(selected).toHaveLength(3);expect(selected.reduce((n,m)=>n+m.content.length,0)).toBe(12000);
});
