import { agentPath } from '../lib/agentRoutes';
import { useEffect, useMemo, useRef, useState } from "react";
import { api, type PortfolioRow } from "../lib/api";
import { Glyph, P } from "../os/icons";
import { ChatMarkdown } from "./ChatMarkdown";
import { useAssistantHistory, type AssistantMessage } from "../hooks/useAssistantHistory";
import { streamAssistant } from "../lib/assistantStream";
import "../assistant.css";
import {citationSourceUrl,citationReaderUrl,citationAudioUrl,citationLocatorText,isNoteVersionUrl} from '../lib/citationLinks';
import {NoteVersionPreview} from './NoteVersionPreview';
import {AsyncDownloadLink} from './AsyncDownloadLink';

type Citation = { project_code: string; level?: string; validation_mode?: string; reference?: string; excerpt: string; source_id?: string | null };
type Message = AssistantMessage;
type StreamRequest = { controller: AbortController; stopReason: DOMException | null };
const SPARK = "m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z";

function Reply({ message, onSourceOpen }: { message: Message; onSourceOpen?: (id:string,title?:string)=>void }) {
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const [selected, setSelected] = useState("");
  const [copyState, setCopyState] = useState("");
  const citations = message.citations || [];
  const sourceRef = useRef<HTMLDivElement>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => () => { if (timerRef.current) clearTimeout(timerRef.current); }, []);
  useEffect(() => {
    if (selected) sourceRef.current?.querySelector(`[data-reference="${selected}"]`)?.scrollIntoView?.({ block: "nearest", behavior: "smooth" });
  }, [selected, sourcesOpen]);
  const copy = async () => {
    try { await navigator.clipboard.writeText(message.text); setCopyState("Copié"); }
    catch { setCopyState("Copie indisponible"); }
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setCopyState(""), 2000);
  };
  return <article className="chat-msg assistant">
    <div className="chat-message-label"><Glyph d={SPARK} size={13} /> Assistant</div>
    <div className="chat-bubble">
      <ChatMarkdown text={message.text} references={citations.map((c) => c.reference || "")}
        onReference={(reference) => { setSelected(reference); setSourcesOpen(true); }} />
    </div>
    <div className="chat-reply-actions">
      {citations.length > 0 && <button type="button" className="chat-text-button" aria-expanded={sourcesOpen}
        onClick={() => { setSourcesOpen(!sourcesOpen); setSelected(""); }}>
        <Glyph d={P.folder} size={14} /> {citations.length} source{citations.length > 1 ? "s" : ""}
        <span className={`chat-chevron${sourcesOpen ? " open" : ""}`}><Glyph d={P.chevR} size={12} /></span>
      </button>}
      <button type="button" className="chat-text-button chat-copy" onClick={() => void copy()} aria-label="Copier la réponse">
        <Glyph d={["M8 8h12v12H8z", "M16 8V4H4v12h4"]} size={13} /> {copyState || "Copier"}
      </button>
    </div>
    {sourcesOpen && <div className="chat-sources" ref={sourceRef}>
      {citations.map((c, i) => {const url=citationSourceUrl(c),audio=citationAudioUrl(c);return <details key={i} data-reference={c.reference}
        open={selected === c.reference ? true : undefined} className={selected === c.reference ? "selected" : ""}
        onToggle={(e) => { if (!e.currentTarget.open && selected === c.reference) setSelected(""); }}>
        <summary><span className={`chat-reference ${c.level === "validated" ? "validated" : "proposed"}`}>{c.reference || i + 1}</span>
          <span>{c.level === "validated" ? (c.validation_mode === "default" ? "Retenue par défaut" : c.validation_mode === "human" ? "Confirmation humaine" : "Information retenue") : "Source à confirmer"}<small>{c.project_code}</small></span>
        </summary>
        <p>{c.excerpt}</p>
        {c.locator&&<p>{citationLocatorText(c.locator)}</p>}
        {url&&<a className="chat-source-download" href={agentPath(citationReaderUrl(c)!)} target="_blank" rel="noreferrer"
          onClick={event=>{if(onSourceOpen&&c.source_id&&citationReaderUrl(c)!==url&&!event.ctrlKey&&!event.metaKey&&!event.shiftKey&&!event.altKey){event.preventDefault();onSourceOpen(c.source_id,c.reference);}}}>{isNoteVersionUrl(url)?'Ouvrir la version citée':'Consulter la source citée'}</a>}
        <NoteVersionPreview citation={c}/>
        {c.source_id && onSourceOpen && <button type="button" className="chat-text-button" onClick={()=>onSourceOpen(c.source_id!,c.reference)}>Examiner la preuve</button>}
        {c.source_id && !isNoteVersionUrl(url) && <AsyncDownloadLink className="chat-source-download" href={agentPath(`/v1/sources/${encodeURIComponent(c.source_id)}/raw`)}>
          <Glyph d={P.download} size={13} /> Télécharger la source originale</AsyncDownloadLink>}
        {audio&&<audio aria-label="Audio de la citation" controls preload="metadata" src={agentPath(audio)}/>}
      </details>;})}
    </div>}
  </article>;
}

export function AssistantPanel({ onClose, persistHistory=false, suggestedProjectId, suggestedErpProjectId, portfolio, onProjectsChanged, onSourceOpen }: {
  onClose: () => void; persistHistory?:boolean; suggestedProjectId?:string|null; onSourceOpen?:(id:string,title?:string)=>void;
  portfolio?:PortfolioRow[]; suggestedErpProjectId?:string|null; onProjectsChanged?:()=>Promise<void>;
}) {
  const [knowledgeProjects, setKnowledgeProjects] = useState<{ id: string; code: string; name: string }[]>([]);
  const [resolvedLinks,setResolvedLinks] = useState<Record<string,string>>({});
  const [resolvingProject,setResolvingProject] = useState(false);
  const mounted = useRef(true);
  const projects=useMemo(()=>{
    if(!portfolio)return knowledgeProjects;
    const represented=new Set<string>();
    const targets=portfolio.map(row=>{const id=row.brain_project_id||resolvedLinks[row.id]||`erp:${row.id}`;represented.add(id);return {id,code:row.code,name:row.title};});
    return [...targets,...knowledgeProjects.filter(row=>!represented.has(row.id))];
  },[portfolio,knowledgeProjects,resolvedLinks]);
  const suggested=portfolio?.find(row=>row.id===suggestedErpProjectId);
  const suggestedTarget=suggested?(suggested.brain_project_id||resolvedLinks[suggested.id]||`erp:${suggested.id}`):suggestedProjectId;
  const [projectId, setProjectId] = useState("");
  const [includeEvidence, setIncludeEvidence] = useState(true);
  const [ephemeral, setEphemeral] = useState(true);
  const keepHistory = persistHistory && !ephemeral;
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [warnings, setWarnings] = useState<string[]>([]);
  const [failedRequest, setFailedRequest] = useState<{ query: string; projectId: string; evidence: boolean; partial?:boolean } | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const sending = useRef(false);
  const streamController = useRef<StreamRequest|null>(null);
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;streamController.current?.controller.abort();};},[]);
  const stopResponse = () => {
    const stream = streamController.current;
    if (!stream || stream.controller.signal.aborted) return;
    stream.stopReason = new DOMException("Réponse arrêtée à votre demande", "AbortError");
    stream.controller.abort(stream.stopReason);
  };
  const history = useAssistantHistory(keepHistory,messages,projectId,(saved,scope)=>{
    setMessages(saved);setProjectId(scope);setInput("");setWarnings([]);setError("");setFailedRequest(null);
  },busy);
  const saving = keepHistory && history.status === "Enregistrement…";
  useEffect(()=>{
    const protect=(event:BeforeUnloadEvent)=>{if(input.trim() || busy || saving || history.error){event.preventDefault();event.returnValue="";}};
    window.addEventListener("beforeunload",protect);return()=>window.removeEventListener("beforeunload",protect);
  },[input,busy,saving,history.error]);
  const changeProject = async (id:string)=>{
    if(resolvingProject)return;
    if(persistHistory)history.newThread();
    setProjectId(id);setWarnings([]);
    if(persistHistory)setFailedRequest(null);
    if(!id.startsWith("erp:"))return;
    setResolvingProject(true);setError("");
    try {
      // Choosing this ERP project is explicit. Only an actual persisted link
      // can select a knowledge scope; a matching display code never grants it.
      const erpId=id.slice(4);const link=await api.ensureBrainLink(erpId);
      if(!link.linked||!link.brain_project_id)throw new Error("Projet non relié à la connaissance.");
      if(!mounted.current)return;
      setResolvedLinks(previous=>({...previous,[erpId]:link.brain_project_id!}));
      setProjectId(link.brain_project_id);
      if(onProjectsChanged)await onProjectsChanged();
    }catch(e){if(mounted.current)setError(e instanceof Error?e.message:String(e));}
    finally{if(mounted.current)setResolvingProject(false);}
  };
  useEffect(() => {
    let cancelled=false;
    api.brainProjects().then(rows=>{if(!cancelled)setKnowledgeProjects(rows);}).catch(() => {if(!cancelled)setError("Impossible de charger la liste des projets de connaissance.");});
    return()=>{cancelled=true;};
  }, [portfolio]);
  useEffect(() => { if(messages.length || busy)bottomRef.current?.scrollIntoView?.({ behavior: "smooth", block: "end" }); }, [messages, busy]);
  useEffect(() => {
    const field = inputRef.current;
    if (field) {
      field.style.height = "32px";
      if (input) field.style.height = `${Math.max(32, Math.min(field.scrollHeight, 128))}px`;
    }
  }, [input]);

  const send = async (query: string, retry = false) => {
    const q = query.trim();
    if (q.length < 2 || sending.current || history.loading || resolvingProject) return;
    sending.current = true;
    const target = retry && failedRequest ? failedRequest.projectId : projectId;
    if(target.startsWith("erp:")){setError("Ce projet n’est pas encore relié à la connaissance. Choisissez-le à nouveau ou établissez sa liaison dans Connaissance.");return;}
    const evidence = retry && failedRequest ? failedRequest.evidence : includeEvidence;
    const project = projects.find((p) => p.id === target)?.code || "Tous les projets";
    const previous=retry && failedRequest?.partial ? messages.slice(0,-1) : messages;
    const context=previous.filter(m=>m.text);
    const replyIndex=previous.length+(retry?0:1);
    let partial="";
    setError(""); setWarnings([]); setFailedRequest(null);
    if(persistHistory)setMessages([...previous,...(!retry?[{role:"user" as const,text:q,project}]:[]),{role:"assistant",text:"",citations:[]}]);
    else if (!retry) setMessages((m) => [...m, { role: "user", text: q, project }]);
    if(!retry)setInput("");
    setBusy(true);
    const stream: StreamRequest | null = persistHistory ? { controller: new AbortController(), stopReason: null } : null;
    if (stream) streamController.current = stream;
    try {
      const result = stream ? await streamAssistant(q,target,evidence,context,
        stream.controller.signal,(answer,metadata)=>{
          partial=answer;setMessages(m=>m.map((item,i)=>i===replyIndex?{role:"assistant",text:answer,citations:metadata.citations}:item));
        }) : await api.brainChat(q, target || null, evidence);
      if(!persistHistory)setMessages((m) => [...m, { role: "assistant", text: result.answer, citations: result.citations || [] }]);
      setWarnings(result.warnings || []);
    } catch (e: unknown) {
      const stopped = stream !== null && stream.stopReason !== null && stream.controller.signal.aborted
        && stream.controller.signal.reason === stream.stopReason && e === stream.stopReason;
      setError(stopped ? "" : e instanceof Error ? e.message : String(e));
      if(persistHistory)setMessages(m=>m.map((item,i)=>i===replyIndex?{...item,text:`[Réponse interrompue] ${partial || "Aucun texte reçu."}`}:item));
      setFailedRequest(stopped ? null : { query: q, projectId: target, evidence,partial:persistHistory });
    } finally {
      if (streamController.current === stream) streamController.current = null;
      setBusy(false); sending.current = false; inputRef.current?.focus();
    }
  };

  return <aside className="mac-assistant" aria-label="Assistant mémoire">
    <header className="chat-header">
      <span className="chat-avatar"><Glyph d={SPARK} size={20} /></span>
      <div><strong>Assistant projet</strong><small>Des réponses ancrées dans vos sources</small></div>
      <button type="button" className="chat-icon-button" aria-label="Nouvelle discussion" title="Nouvelle discussion"
        disabled={busy || saving || history.loading || resolvingProject || !messages.length} onClick={() => { if(persistHistory)history.newThread(); else setMessages([]); setWarnings([]); setError(""); setFailedRequest(null); setInput(""); inputRef.current?.focus(); }}>
        <Glyph d="M12 5v14M5 12h14" size={16} />
      </button>
      <button type="button" className="chat-icon-button" aria-label="Masquer l’assistant" title="Masquer l’assistant" onClick={onClose}>
        <Glyph d="m6 6 12 12M6 18 18 6" size={16} />
      </button>
    </header>
    <div className="chat-controls">
      <div className="chat-scope-row">
      {persistHistory && <label title="Changer de mode démarre une nouvelle discussion. Les discussions déjà enregistrées sont conservées.">
        <input type="checkbox" checked={ephemeral} disabled={busy || saving || history.loading || resolvingProject || !!history.error}
          onChange={event=>{history.newThread();setEphemeral(event.target.checked);inputRef.current?.focus();}} /> Conversation éphémère
      </label>}
        <label title="Inclure les mails classés et les informations qui restent à valider">
          <input type="checkbox" checked={includeEvidence} disabled={busy}
            onChange={(e) => { setIncludeEvidence(e.target.checked); setWarnings([]); }} /> Inclure les sources à confirmer
        </label>
        <span className="chat-level-legend" title="V : information retenue · P : source à confirmer">V / P</span>
      </div>
      {keepHistory && <div className="workspace-history"><select className="input" aria-label="Historique des discussions" value={history.threadId} disabled={busy || saving || history.loading || resolvingProject}
        onChange={e=>{if(e.target.value)void history.select(e.target.value);}}><option value="">Nouvelle discussion</option>{history.threads.map(t=><option key={t.id} value={t.id}>{t.title}</option>)}</select></div>}
      <select className="input" aria-label="Projet interrogé" value={projectId} disabled={busy || saving || history.loading || resolvingProject}
        onChange={(e) => void changeProject(e.target.value)}>
        <option value="">Tous les projets</option>
        {projects.map((p,i) => <option key={`${p.id}:${i}`} value={p.id}>{p.code} — {p.name}</option>)}
      </select>
      {resolvingProject&&<p role="status">Préparation de la connaissance du projet…</p>}
      {!resolvingProject&&projectId.startsWith("erp:")&&<button type="button" className="chat-text-button" disabled={busy || saving || history.loading} onClick={()=>void changeProject(projectId)}>Préparer la connaissance du projet</button>}
      {suggestedTarget && suggestedTarget!==projectId && projects.some(p=>p.id===suggestedTarget) && <button type="button" className="chat-text-button" disabled={busy || saving || history.loading || resolvingProject} onClick={()=>void changeProject(suggestedTarget)}>Interroger le projet affiché</button>}
      {keepHistory && <p role="status" className={`workspace-save-state ${history.error?"error":""}`}>{history.loading?"Chargement de la discussion…":history.error || history.status || "Les discussions sont conservées dans la base locale."}</p>}
      {history.error && <div className="chat-reply-actions"><button type="button" className="chat-text-button" disabled={busy || history.loading} onClick={history.retry}>Réessayer l’enregistrement</button>{history.threadId && <button type="button" className="chat-text-button" disabled={busy || history.loading} onClick={()=>{if(window.confirm("Recharger la version enregistrée et remplacer le brouillon affiché ?"))void history.select(history.threadId);}}>Relire la version enregistrée</button>}<button type="button" className="chat-text-button" disabled={busy || history.loading} onClick={history.fork}>Conserver une copie</button></div>}
    </div>
    <div className="chat-log" role="log" aria-label="Conversation" aria-live="polite" aria-busy={busy}>
      {messages.length === 0 && <div className="chat-welcome">
        <span className="chat-welcome-icon"><Glyph d={SPARK} size={28} /></span>
        <h3>Faisons le point.</h3><p>Interrogez les échanges, décisions et informations de vos projets.</p>
        <div className="chat-suggestions">{["Résume le projet", "Quels sont les points ouverts ?", "Quelles sont les prochaines échéances ?"].map((q) =>
          <button key={q} type="button" disabled={busy || resolvingProject || projectId.startsWith("erp:")} onClick={() => void send(q)}>{q}<Glyph d={P.chevR} size={14} /></button>,
        )}</div>
      </div>}
      {messages.map((message, i) => message.role === "assistant" ? <Reply key={i} message={message} onSourceOpen={onSourceOpen} />
        : <article key={i} className="chat-msg user"><div className="chat-message-label">{message.project}</div>
            <div className="chat-bubble">{message.text}</div></article>)}
      {busy && <div className="chat-thinking" role="status"><span className="chat-thinking-dots"><i /><i /><i /></span> Recherche et rédaction…{persistHistory && <button type="button" className="chat-text-button" onClick={stopResponse}>Arrêter la réponse</button>}</div>}
      <div ref={bottomRef} />
    </div>
    <div className="chat-footer">
      {warnings.length > 0 && <details className="chat-memory-status"><summary><Glyph d={P.search} size={13} />
        {warnings.some((w) => /recherche textuelle/i.test(w)) ? "Recherche textuelle des sources" : "Mémoire partiellement disponible"}
        <span>Détails</span></summary><p>{warnings.join("\n")}</p></details>}
      {error && <div className="chat-error" role="alert"><Glyph d={P.alert} size={15} /><span>{error}</span>
        {failedRequest && <button className="chat-text-button" type="button" disabled={busy}
          onClick={() => void send(failedRequest.query, true)}>Réessayer</button>}</div>}
      <form className="assistant-composer" onSubmit={(e) => { e.preventDefault(); void send(input); }}>
        <textarea ref={inputRef} placeholder="Posez votre question…" aria-label="Question à l’assistant"
          rows={1} maxLength={2000} value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); void send(input); }
          }} />
        <button className="chat-send" type="submit" disabled={busy || history.loading || resolvingProject || projectId.startsWith("erp:") || input.trim().length < 2}
          aria-label="Envoyer la question" title="Envoyer (Entrée)"><Glyph d="M12 19V5m-6 6 6-6 6 6" size={19} /></button>
      </form>
      <div className="assistant-composer-hint"><span>Entrée pour envoyer · ⇧ Entrée pour une ligne</span><span>V retenue · P à confirmer</span></div>
    </div>
  </aside>;
}
