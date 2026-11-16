import { agentPath } from '../lib/agentRoutes';
import {MessageContent} from './MessageContent';
import { useEffect, useId, useMemo, useRef, useState, type CSSProperties, type DragEvent } from "react";
import { api, type PortfolioRow, type DiscardSuggestion, type SourceMail } from "../lib/api";
import { Glyph, P } from "../os/icons";
import { ThunderbirdPanel, type ThunderbirdReply } from "./ThunderbirdPanel";
import { AsyncDownloadLink } from './AsyncDownloadLink';
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { rankProjects, focusPercent, folderDigits } from "../lib/mailFocus";
import "../mail-workspace.css";

type Project = { id: string; code: string; name: string };
type ProjectTile = { id: string; miniId: string | null; brainId: string | null; code: string; title: string; score: number | null };
type ClassificationEvidence = { key: string; label: string; weight: number; samples?: number };
type PendingMail = {
  proposal_id: string; source_id: string; sender: string; subject: string;
  received_at: string | null; excerpt: string; target_project_id: string | null;
  target_code: string | null; target_name: string | null; confidence: number; reason: string;
  evidence?: ClassificationEvidence[];
  discard_suggestion?: DiscardSuggestion;
  candidates?: { project_id: string; code: string; score: number; evidence?: ClassificationEvidence[] }[];
};
type Mail = {
  id: string; sender: string; subject: string; date: string | null; excerpt: string;
  projectId: string | null; projectCode: string | null; pending?: PendingMail; attachments: number;
};
type Detail = {
  body_html?:string|null; inline_images?:Record<string,string>;
  id: string; author: string; received_at?: string; participants?: string[];
  sender?: string; recipients?: {to: string[]; cc: string[]};
  attachments?: {index: number; filename: string; mime: string; previewable: boolean}[];
  metadata?: SourceMail["metadata"];
  artifacts: { kind: string; text: string }[];
};
type Props = {
  active?: boolean; scoped?: boolean; readOnly?: boolean;
  queue: PendingMail[]; projects: Project[]; portfolio: PortfolioRow[];
  links: Record<string, { brainId: string | null; brainCode: string | null; linked: boolean }>;
  stats: { pending_sources: number; queued: number; divers_count: number } | null;
  query: string; onQuery: (value: string) => void;
  sort: string; onSort: (value: string) => void; queueTotal: number;
  selected: Set<string>; onToggle: (id: string) => void; onSelectAll: () => void; onClearSelected: () => void;
  offset: number; onPage: (offset: number) => void; pageHasNext: boolean;
  onReload: () => Promise<void>; onRunTriage: (force: boolean) => void; onCancelTriage: () => void;
  triaging: boolean; busy: string; dropping: boolean; autoInfo: string; message: string;
  triageProgress?: import("../lib/mailTriage").TriageProgress | null;
  onDecide: (entry: PendingMail, projectId: string | null) => Promise<void>;
  onReject: (entry: PendingMail) => Promise<void>;
  onResolveTarget?: (target: string) => Promise<string>;
  onCreateProject?: (code:string,title:string) => Promise<string>;
  onDragStart: (event: DragEvent, entry: PendingMail) => void;
  onDrop: (event: DragEvent, miniId: string, brainId: string | null) => void;
  dragOver: string | null; onDragOver: (key: string | null) => void;
};
const CLASSIFIED_REFRESH_MS = 15_000;
const ENVELOPE = ["M3 5h18v14H3z", "m3 5 9 7 9-7"];
const SPARK = "m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z";
const PAPERCLIP = "m8 13 7-7a3 3 0 0 1 4 4l-9 9a5 5 0 0 1-7-7l9-9m-6 12 8-8";
const errorText = (e: unknown) => e instanceof Error ? e.message : String(e);
const senderName = (sender: string) => sender.replace(/<[^>]*>/g, "").replace(/^\"|\"$/g, "").trim() || sender;
const hue = (text: string) => [...text].reduce((n, char) => n + char.charCodeAt(0) * 7, 0) % 360;
const color = (text: string) => ({ "--maildesk-hue": hue(text) } as CSSProperties);
const shortDate = (date: string | null) => {
  if (!date || Number.isNaN(Date.parse(date))) return "";
  return new Intl.DateTimeFormat("fr-FR", { day: "numeric", month: "short" }).format(new Date(date));
};
const fullDate = (date: string | null) => {
  if (!date || Number.isNaN(Date.parse(date))) return "Date non renseignée";
  return new Intl.DateTimeFormat("fr-FR", { dateStyle: "long", timeStyle: "short" }).format(new Date(date));
};
const normalize = (text: string) => text.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
const classificationReason = (reason: string) => {
  if (reason.includes("plusieurs projets")) return "Plusieurs projets présentent des indices proches. Le choix reste à préciser.";
  if (reason.includes("aucun projet") || reason === "résolution ambiguë") return "Les indices disponibles ne suffisent pas encore à proposer un projet fiable.";
  const labels: Record<string, string> = {
    explicit_code: "Référence explicite du projet repérée", explicit_alias: "Référence alternative déclarée reconnue",
    alias: "Alias du projet reconnu", ai_hint: "Correspondance proposée par l’analyse IA",
    sender_customer: "Expéditeur correspondant au client déclaré", thread_history: "Conversation déjà liée au projet",
  };
  return reason.replace(/^(triage IA|suggestion de projet)\s*:\s*/, "").split(", ").map((key) => labels[key] || key).join(" · ");
};
function readableText(text: string) {
  if (!/<(?:html|body|div|p|br|table|span|a)\b[^>]*>/i.test(text)) return text;
  const document = new DOMParser().parseFromString(text, "text/html");
  document.querySelectorAll("script, style, head, iframe, object, embed, img").forEach(node => node.remove());
  document.querySelectorAll("br").forEach(node => node.replaceWith("\n"));
  document.querySelectorAll("p, div, tr, li, h1, h2, h3, blockquote").forEach(node => node.append("\n"));
  return (document.body.textContent || "").replace(/\n[ \t]*\n(?:[ \t]*\n)+/g, "\n\n").trim();
}

export function MailWorkspace(props: Props) {
  const [thunderbirdOpen, setThunderbirdOpen] = useState(false);
  const [thunderbirdSetup, setThunderbirdSetup] = useState(false);
  const [thunderbirdAvailable, setThunderbirdAvailable] = useState(false);
  const [canReply, setCanReply] = useState(false);
  useEffect(() => {
    if (props.readOnly || document.body.dataset.kiaraDesktop !== "true") return;
    const controller = new AbortController();
    fetch("/api/v1/kiara/thunderbird-extension", {signal: controller.signal})
      .then(response => response.ok ? response.json() : null)
      .then(extension => { if (!controller.signal.aborted) setThunderbirdAvailable(typeof extension?.version === "string"); })
      .catch(() => {});
    if (props.scoped) {
      fetch("/v1/thunderbird/status", {signal: controller.signal})
        .then(response => { if (!controller.signal.aborted) setCanReply(response.ok); })
        .catch(() => {});
    }
    return () => controller.abort();
  }, [props.readOnly, props.scoped]);
  const [analysisDetailsOpen, setAnalysisDetailsOpen] = useState(false);
  const analysisDetailsId = useId();
  const tools = useRef<HTMLDetailsElement>(null);
  const [reply, setReply] = useState<ThunderbirdReply>();
  const [folder, setFolder] = useState(props.scoped && props.readOnly ? "classified" : "pending");
  const [sources, setSources] = useState<SourceMail[]>([]);
  const [sourceOffset, setSourceOffset] = useState(0);
  const [sourceLoading, setSourceLoading] = useState(false);
  const [sourcePageError, setSourcePageError] = useState("");
  const [activeId, setActiveId] = useState<string | null>(null);
  const [detail, setDetail] = useState<Detail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [detailAttempt, setDetailAttempt] = useState(0);
  const [localError, setLocalError] = useState("");
  const [localNotice, setLocalNotice] = useState("");
  const [sourceBusy, setSourceBusy] = useState(false);
  const [emlOpen, setEmlOpen] = useState(false);
  const [emlProject, setEmlProject] = useState("");
  const [emlFiles, setEmlFiles] = useState<File[]>([]);
  const [usage, setUsage] = useState<Record<string,number>>({});
  const [usageRevision,setUsageRevision] = useState(0);
  const [validating,setValidating] = useState(false);
  const validation = useRef(false);
  const cursor = useRef(0);
  const requestedCursor = useRef<number|null>(null);
  const [targetOverride, setTarget] = useState<string | null>(null);
  const [projectForm, setProjectForm] = useState(false);
  const [projectCode, setProjectCode] = useState("");
  const [projectTitle, setProjectTitle] = useState("");
  const [projectError, setProjectError] = useState("");
  const [creatingProject, setCreatingProject] = useState(false);
  const projectCreation = useRef(false);
  const projectFormId = useId();
  const activeIdRef = useRef(activeId);
  activeIdRef.current = activeId;
  const sort = props.sort;
  const searchQuery = useDebouncedValue(props.query);
  const [sourceTotal, setSourceTotal] = useState(0);
  const [sourceHasNext, setSourceHasNext] = useState(false);
  const [classifiedSelected, setClassifiedSelected] = useState<Set<string>>(new Set());
  const [sourcesRevision, setSourcesRevision] = useState(0);
  useEffect(()=>{let alive=true;api.mailProjectUsage().then(result=>{if(alive)setUsage(Object.fromEntries(result.projects.map(row=>[row.project_id,row.score])));}).catch(()=>{});return()=>{alive=false;};},[usageRevision,props.queueTotal,sourcesRevision]);
  const [syncing, setSyncing] = useState(false);
  const sourceGeneration = useRef(0);
  const classifiedDrag = useRef<string[]>([]);
  const operation = useRef(false);
  const appliedTargets = useRef(new Map<string,string>());
  const pending = folder === "pending";
  const rejected = folder === "rejected";
  const readingOnly = props.readOnly || rejected;
  const locked = validating || !!props.busy || props.dropping || sourceBusy || creatingProject;
  const sourceProject = folder.startsWith("project:") ? folder.slice(8)
    : folder === "divers" ? props.projects.find((p) => p.code.toUpperCase() === "DIVERS")?.id : undefined;

  useEffect(() => {
    setSourceOffset(0); setClassifiedSelected(new Set());
  }, [searchQuery, sort, sourceProject]);
  useEffect(() => {
    if (pending || props.active === false) {setSourceLoading(false); return;}
    let inFlight = false;
    const fetchPage = async (background = false) => {
      if (inFlight) return;
      inFlight = true;
      const generation = ++sourceGeneration.current;
      if (!background) setSourceLoading(true);
      try {
        const page = rejected
          ? await api.rejectedMailPage(sourceOffset, searchQuery, sort)
          : await api.classifiedMailPage(sourceOffset, searchQuery, sort, sourceProject);
        if (generation !== sourceGeneration.current) return;
        const mapped = page.rows.map(row => {
          const target = appliedTargets.current.get(row.source_id);
          if (target === row.project_id) appliedTargets.current.delete(row.source_id);
          return { ...row, project_id: target || row.project_id };
        });
        const visible = sourceProject ? mapped.filter(row => row.project_id === sourceProject) : mapped;
        const total = Math.max(0, page.total - (mapped.length - visible.length));
        setSources(visible);
        setSourceTotal(total);
        setSourceHasNext(sourceOffset + visible.length < total);
        setSourcePageError("");
        if (!visible.length && sourceOffset > 0) setSourceOffset(total ? Math.floor((total - 1) / 100) * 100 : 0);
      } catch (error) {
        if (generation === sourceGeneration.current) setSourcePageError(errorText(error));
      } finally {
        inFlight = false;
        if (generation === sourceGeneration.current) setSourceLoading(false);
      }
    };
    void fetchPage();
    const timer = window.setInterval(() => {
      if (!document.hidden && !operation.current) void fetchPage(true);
    }, CLASSIFIED_REFRESH_MS);
    return () => {
      window.clearInterval(timer);
      sourceGeneration.current++;
    };
  }, [sourceOffset, sourcesRevision, props.stats?.pending_sources, sourceProject, searchQuery, sort, pending, rejected, props.active]);

  const mails = useMemo<Mail[]>(() => {
    const rows: Mail[] = pending ? props.queue.map((entry) => ({ id: entry.source_id, sender: entry.sender,
      subject: entry.subject, date: entry.received_at, excerpt: entry.excerpt, projectId: entry.target_project_id,
      projectCode: entry.target_code, pending: entry, attachments: 0 })) : sources.map((source) => ({
      id: source.source_id, sender: source.author || "", subject: source.metadata?.subject || "", date: source.received_at || null,
      excerpt: readableText(source.excerpt || ""), projectId: source.project_id,
      projectCode: props.projects.find((p) => p.id === source.project_id)?.code || null,
      attachments: source.metadata?.attachments?.length || 0,
    }));
    return rows.filter((mail) => (!folder.startsWith("project:") || mail.projectId === folder.slice(8)) &&
      (folder !== "divers" || mail.projectCode?.toUpperCase() === "DIVERS"));
  }, [folder, props.queue, sources, props.projects, props.query, sort, pending]);
  const active = mails.find((mail) => mail.id === activeId) || null;
  const rankedProjects = useMemo(()=>rankProjects(props.projects,active?.pending),[props.projects,active?.pending]);
  const suggestedTarget = active?.pending ? rankedProjects.find(p=>p.score!=null)?.id : active?.projectId;
  const target = targetOverride ?? suggestedTarget ?? "";
  const targetScore = target==="DISCARD" ? active?.pending?.discard_suggestion?.probability : rankedProjects.find(p=>p.id===target)?.score;
  const destination = rankedProjects.find(p=>p.id===target) || props.portfolio.find(p=>`erp:${p.id}`===target);
  const targetEvidence = active?.pending?.candidates?.find(candidate=>candidate.project_id===target)?.evidence
    || (target===active?.pending?.target_project_id ? active.pending.evidence : undefined);
  const projectTiles = useMemo(() => {
    const tiles: ProjectTile[] = props.portfolio.filter(project=>project.code.toUpperCase()!=="DIVERS").map(project=>{
      const matches = rankedProjects.filter(candidate=>candidate.code.trim().toUpperCase()===project.code.trim().toUpperCase());
      const brainId = props.links[project.id]?.brainId || project.brain_project_id || (matches.length===1 && !matches[0].id.startsWith("erp:") ? matches[0].id : null);
      const id = brainId || `erp:${project.id}`;
      return {id,miniId:project.id,brainId,code:project.code,title:project.title,score:rankedProjects.find(candidate=>candidate.id===id)?.score??null};
    });
    for(const project of rankedProjects)if(project.code.toUpperCase()!=="DIVERS" && !tiles.some(tile=>tile.id===project.id)){
      tiles.push({id:project.id,miniId:project.id.startsWith("erp:")?project.id.slice(4):null,brainId:project.id.startsWith("erp:")?null:project.id,code:project.code,title:project.name,score:project.score});
    }
    return tiles.sort((a,b)=>(b.score??-1)-(a.score??-1) || Number(b.id===active?.projectId)-Number(a.id===active?.projectId) || (usage[b.id]||0)-(usage[a.id]||0) || a.code.localeCompare(b.code));
  },[props.portfolio,props.links,rankedProjects,active?.projectId,usage]);
  const scoredTiles = projectTiles.filter(project=>project.score!=null && project.score>0);
  const visibleProjectTiles = (scoredTiles.length ? scoredTiles : projectTiles).slice(0,4);
  const otherProjectTiles = projectTiles.filter(project=>!visibleProjectTiles.includes(project));
  const selectedCount = pending ? props.selected.size : classifiedSelected.size;
  const folderTitle = pending ? "À classer" : folder === "classified" ? "Mails classés"
    : rejected ? "Mails rejetés" : folder === "divers" ? "Divers" : props.projects.find((p) => p.id === folder.slice(8))?.code || "Projet";

  useEffect(() => {
    const index=mails.findIndex(mail=>mail.id===activeId);
    if(index>=0){cursor.current=index;return;}
    const desired=requestedCursor.current??cursor.current;
    requestedCursor.current=null;
    setActiveId(mails.length?mails[desired<0?mails.length-1:Math.min(desired,mails.length-1)].id:null);
  }, [mails, activeId]);
  useEffect(()=>{
    if(target && target!=="DISCARD" && !target.startsWith("erp:") && !props.projects.some(project=>project.id===target))setTarget(null);
  },[props.projects,target]);
  useEffect(() => {
    setDetail(null); setDetailError(""); setTarget(null);
    setProjectForm(false); setProjectError(""); setProjectCode(""); setProjectTitle("");
    if (!activeId) { setDetailLoading(false); return; }
    const controller = new AbortController();
    setDetailLoading(true);
    api.brainSourceDetail(activeId, controller.signal).then((result: Detail) => {
      if (!controller.signal.aborted) setDetail(result);
    }).catch((e: unknown) => { if (!controller.signal.aborted) setDetailError(errorText(e)); })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    return () => controller.abort();
  }, [activeId, detailAttempt]);

  const createProject = async () => {
    if(!props.onCreateProject || !projectTitle.trim() || projectCreation.current || locked)return;
    projectCreation.current=true;setCreatingProject(true);setProjectError("");
    const source=activeId;
    try {
      const id=await props.onCreateProject(projectCode.trim(),projectTitle.trim());
      if(activeIdRef.current===source){setTarget(id);setProjectForm(false);setProjectCode("");setProjectTitle("");}
      setLocalNotice("Projet créé et sélectionné.");
    } catch(error) {setProjectError(errorText(error));}
    finally {projectCreation.current=false;setCreatingProject(false);}
  };

  const changeFolder = (value: string) => {
    if (rejected !== (value === "rejected")) {
      sourceGeneration.current++;
      setSources([]); setSourceTotal(0); setSourceHasNext(false); setSourcePageError("");
    }
    cursor.current=0;setFolder(value); setActiveId(null); setSourceOffset(0); setClassifiedSelected(new Set());
    props.onClearSelected(); props.onQuery(""); setLocalNotice("");
  };
  const refresh = async () => {
    try { await props.onReload(); setSourcesRevision((n) => n + 1); }
    catch (e) { setLocalError(errorText(e)); }
  };
  const emlProjects = props.projects.filter(project => project.code.toUpperCase() !== "DIVERS" && !project.id.startsWith("erp:"));
  const showEmlImport = () => {
    const currentProject = folder.startsWith("project:") ? folder.slice(8) : "";
    setEmlProject(emlProjects.some(project => project.id === currentProject) ? currentProject : "");
    setEmlFiles([]);
    setEmlOpen(true);
    if (tools.current) tools.current.open = false;
  };
  const importEml = async () => {
    const automatic = emlProject === "automatic";
    if (props.readOnly || locked || operation.current || !emlProject || !emlFiles.length ||
        (automatic ? props.scoped : !emlProjects.some(project => project.id === emlProject))) return;
    operation.current = true;
    setSourceBusy(true);
    setLocalError("");
    setLocalNotice("Import des mails en cours…");
    let imported = 0;
    let duplicates = 0;
    let pending = 0;
    const failures: string[] = [];
    try {
      for (const file of emlFiles) {
        try {
          const result = await api.brainImportEml(automatic ? null : emlProject, file);
          if (result.status === "duplicate") duplicates++;
          else {
            imported++;
            if (result.status === "resolution_pending") pending++;
          }
        } catch (error) {
          failures.push(`${file.name} — ${errorText(error)}`);
        }
      }
      if (imported) {
        if (!automatic) changeFolder(`project:${emlProject}`);
        await refresh();
      }
      const summary = [`${imported} mail${imported === 1 ? "" : "s"} importé${imported === 1 ? "" : "s"}.`,
        duplicates ? `${duplicates} déjà présent${duplicates === 1 ? "" : "s"}.` : "",
        pending ? `${pending} à rattacher dans Sources.` : ""].filter(Boolean).join(" ");
      if (!failures.length) {
        setEmlOpen(false);
        tools.current?.querySelector("summary")?.focus();
        setLocalNotice(summary);
      } else {
        setLocalNotice("");
        setLocalError(`${summary} ${failures.join(" · ")}`);
      }
    } finally {
      operation.current = false;
      setSourceBusy(false);
    }
  };
  const rejectCurrent = async () => {
    if (!active?.pending || props.readOnly || locked || operation.current) return;
    if (!window.confirm("Retirer ce mail de la file et l’exclure des prochains classements ? Son contenu reste dans Kiara et Thunderbird.")) return;
    operation.current = true;
    setSourceBusy(true); setLocalError(""); setLocalNotice("");
    try {
      await props.onReject(active.pending);
      setActiveId(null); setTarget(null);
      setLocalNotice("Mail rejeté. Retrouvez-le dans Options → Dossier → Mails rejetés.");
      void refresh();
    } catch (error) { setLocalError(errorText(error)); }
    finally { operation.current = false; setSourceBusy(false); }
  };
  const discard = async (ids: string[]) => {
    if (!ids.length || locked || operation.current) return;
    if (!window.confirm(`Supprimer le contenu de ${ids.length === 1 ? 'ce mail' : `ces ${ids.length} mails`} de Kiara ?\n\nLes informations exclusivement issues de ces mails seront aussi supprimées. Les originaux dans votre messagerie sont conservés. Une sauvegarde technique est créée pour permettre une récupération ; cette action ne peut pas être annulée dans cette vue.\n\nPour garder ces mails sans projet, choisissez Divers. Continuer la suppression ?`)) return;
    operation.current = true; setSourceBusy(true); setLocalError(""); setLocalNotice("Suppression du mail de Kiara…");
    let done = 0; let cleanupPending = false;
    try {
      for (const id of ids) {
        const result = await api.brainDiscardSource(id);
        cleanupPending ||= !!(result.memory_cleanup_pending || result.raw_cleanup_pending);
        done++;
      }
      setActiveId(null); setTarget(""); props.onClearSelected(); setClassifiedSelected(new Set());
      setLocalNotice(`${done} mail(s) supprimé(s) de Kiara et exclus des analyses et de la connaissance.${cleanupPending ? " Nettoyage externe encore en attente." : ""}`);
    } catch (e) { setLocalError(`${done} mail(s) supprimé(s) de Kiara. ${errorText(e)}`); }
    finally {
      props.onClearSelected(); setClassifiedSelected(new Set());
      await refresh(); setSourceBusy(false); operation.current = false; classifiedDrag.current = [];
    }
  };
  const scan = async () => {
    if (syncing) return;
    setSyncing(true); setLocalError(""); setLocalNotice("Synchronisation des mails…");
    try { const result = await api.brainScanGlobal(); setLocalNotice(result.source==="thunderbird"?"Synchronisation demandée. Thunderbird doit être ouvert ; les nouveaux mails apparaîtront à leur réception.":`${result.imported ?? 0} nouveau(x) mail(s) importé(s).`); await refresh(); }
    catch (e) { setLocalError(errorText(e)); }
    finally { setSyncing(false); }
  };
  const selectAll = () => {
    if (pending) { props.onSelectAll(); return; }
    const all = mails.length > 0 && mails.every((mail) => classifiedSelected.has(mail.id));
    setClassifiedSelected(all ? new Set() : new Set(mails.map((mail) => mail.id)));
  };
  const isSelected = (mail: Mail) => pending ? props.selected.has(mail.pending!.proposal_id) : classifiedSelected.has(mail.id);
  const toggle = (mail: Mail) => {
    if (mail.pending) props.onToggle(mail.pending.proposal_id);
    else setClassifiedSelected((previous) => { const next = new Set(previous); if (next.has(mail.id)) next.delete(mail.id); else next.add(mail.id); return next; });
  };
  const classifySources = async (ids: string[], projectId: string) => {
    if (!ids.length || !projectId || operation.current || locked) return;
    operation.current = true; setSourceBusy(true); setLocalError(""); setLocalNotice("Classement des mails…");
    const failures: string[] = []; let done = 0;
    try {
      const resolvedTarget = props.onResolveTarget ? await props.onResolveTarget(projectId) : projectId;
      for (const id of ids) {
        try {
          await api.brainReassignSource(id, resolvedTarget);
          appliedTargets.current.set(id,resolvedTarget);sourceGeneration.current++;
          setSources(previous=>previous.map(row=>row.source_id===id?{...row,project_id:resolvedTarget}:row));
          if(sourceProject && sourceProject!==resolvedTarget)setSourceTotal(previous=>Math.max(0,previous-1));
          setClassifiedSelected(previous=>{const next=new Set(previous);next.delete(id);return next;});
          setTarget("");done++;
        }
        catch (e) { failures.push(errorText(e)); }
      }
      setLocalNotice(`${done} mail(s) reclassé(s).`);
      if (failures.length) setLocalError(failures[0]);
    } catch(e) {setLocalError(errorText(e));}
    finally { setSourceBusy(false); operation.current = false; classifiedDrag.current = []; void refresh(); }
  };
  const drop = (event: DragEvent, miniId: string, brainId: string | null) => {
    if (locked) { event.preventDefault(); return; }
    if (miniId === "DISCARD") {
      event.preventDefault(); props.onDragOver(null);
      if (pending) {
        let ids: string[] = [];
        try { ids = JSON.parse(event.dataTransfer.getData("application/x-triage-mails") || "[]"); } catch { /* sélection ci-dessous */ }
        if (!ids.length) ids = Array.from(props.selected);
        void discard(props.queue.filter((entry) => ids.includes(entry.proposal_id)).map((entry) => entry.source_id));
      } else {
        let ids = classifiedDrag.current;
        try { const raw = event.dataTransfer.getData("application/x-agent-classified-mail"); if (raw) ids = JSON.parse(raw); } catch { /* geste en mémoire */ }
        void discard(ids);
      }
      return;
    }
    if (pending) { props.onDrop(event, miniId, brainId); return; }
    event.preventDefault(); props.onDragOver(null);
    let ids = classifiedDrag.current;
    try { const data = event.dataTransfer.getData("application/x-agent-classified-mail"); if (data) ids = JSON.parse(data); } catch { /* mémoire du geste */ }
    if (!brainId && !props.onResolveTarget) { setLocalError("Reliez ce projet dans Connaissance avant de reclasser ses mails."); return; }
    void (async () => {
      try {
        if (!props.onResolveTarget && brainId && miniId !== "DIVERS" && props.links[miniId] && !props.links[miniId].linked) await api.saveBrainLink(miniId, brainId);
        const brainOnly = !!brainId && !props.portfolio.some(project=>project.id===miniId) && props.projects.some(project=>project.id===brainId);
        await classifySources(ids, miniId !== "DIVERS" && props.onResolveTarget && !props.links[miniId]?.linked && !brainOnly ? `erp:${miniId}` : brainId!);
      } catch (e) { setLocalError(errorText(e)); }
    })();
  };
  const dropProject = (event: DragEvent, project: ProjectTile) => {
    drop(event,project.miniId||project.id,project.brainId);
  };
  const body = detail?.body_html || detail?.artifacts.find((a) => a.kind === "body_text")?.text ||
    detail?.artifacts.find((a) => a.text)?.text || "";
  const attachments: {index?: number; filename: string; mime?: string; previewable?: boolean}[] = detail?.attachments || detail?.metadata?.attachments || [];
  const offset = pending ? props.offset : sourceOffset;
  const pageSize = pending ? 200 : 100;
  const hasNext = pending ? props.pageHasNext : sourceHasNext;
  const total = pending ? props.queueTotal : sourceTotal;
  const nextPage = (next: number) => {
    setActiveId(null); props.onClearSelected(); setClassifiedSelected(new Set());
    if (pending) props.onPage(next); else setSourceOffset(next);
  };

  const navigateMail=(direction:number)=>{
    if(locked)return;
    const index=mails.findIndex(mail=>mail.id===activeId),next=index+direction;
    if(next>=0 && next<mails.length)setActiveId(mails[next].id);
    else if(direction>0 && hasNext){requestedCursor.current=0;if(pending)props.onPage(offset+pageSize);else setSourceOffset(offset+pageSize);}
    else if(direction<0 && offset>0){requestedCursor.current=-1;if(pending)props.onPage(Math.max(0,offset-pageSize));else setSourceOffset(Math.max(0,offset-pageSize));}
  };
  const diversProject = props.projects.find(project=>project.code.toUpperCase()==="DIVERS");
  const validateCurrent=async(destination=target)=>{
    if(!active||!destination||locked||validation.current)return;
    validation.current=true;setValidating(true);
    try{
      if(destination==="DISCARD")await discard([active.id]);
      else if(active.pending)await props.onDecide(active.pending,destination===active.pending.target_project_id?null:destination);
      else await classifySources([active.id],destination);
      setUsageRevision(n=>n+1);
    }catch(error){setLocalError(errorText(error));}
    finally{validation.current=false;setValidating(false);}
  };
  const dragCurrentMail = (event: DragEvent<HTMLElement>) => {
    if (!active || locked || readingOnly) { event.preventDefault(); return; }
    if ((event.target as HTMLElement).closest("a, button, input, select, summary")) { event.preventDefault(); return; }
    event.dataTransfer.setData("text/plain", active.subject || "Mail");
    if (active.pending) props.onDragStart(event, active.pending);
    else {
      classifiedDrag.current = [active.id];
      event.dataTransfer.setData("application/x-agent-classified-mail", JSON.stringify([active.id]));
      event.dataTransfer.effectAllowed = "move";
    }
  };
  const visibleMessage=/^Analyse terminée\s*:\s*0\s*\/\s*0 mails traités/.test(props.message) && !props.message.includes("Actualisation impossible") ? "" : props.message;
  const displayedError = localError || (!pending ? sourcePageError : "");
  const analysisMessage = props.triaging || /^Analyse\b/i.test(visibleMessage);
  const analysisFailure = props.triageProgress?.status==="failed" || visibleMessage.includes("Actualisation impossible");
  const showAnalysis = props.triaging || !!(props.triageProgress && props.triageProgress.total>0) || analysisMessage;
  const projectTile = (project: ProjectTile) => {
    const key = project.miniId ? `mini:${project.miniId}` : `brain:${project.id}`;
    return <button key={project.id} type="button" style={color(project.code)} title={`${project.code} — ${project.title}\nDéposer pour classer`} disabled={locked}
      className={`maildesk-project${props.dragOver===key?" drop-target":""}${target===project.id?" active":""}`}
      onClick={()=>{setTarget(project.id);setProjectForm(false);}}
      onDragOver={event=>{event.preventDefault();if(!locked)props.onDragOver(key);}} onDragLeave={()=>props.onDragOver(null)} onDrop={event=>dropProject(event,project)}>
      <span className="maildesk-project-icon"><Glyph d={P.folder} size={30}/><b>{folderDigits(project.code)}</b></span>
      <span><b>{project.code}</b><small>{project.title}</small>{project.score!=null && <em aria-label={`Correspondance ${focusPercent(project.score)}`}>{focusPercent(project.score)}</em>}</span>
    </button>;
  };
  return <div className={`maildesk maildesk-focus${active ? " maildesk-reading" : ""}`}>
    <header className="maildesk-toolbar">
      <div className="maildesk-brand"><span><Glyph d={ENVELOPE} size={21} /></span><strong>Mails</strong></div>
      <div className="maildesk-focus-navigation"><span title={folderTitle}>{active?`Mail ${offset+mails.findIndex(mail=>mail.id===activeId)+1} / ${total}`:`0 mail sur ${total}`}</span>
        <button type="button" className="maildesk-secondary" aria-label="Mail précédent" disabled={locked || (!offset && mails.findIndex(mail=>mail.id===activeId)<=0)} onClick={()=>navigateMail(-1)}><Glyph d={P.chevL} size={15}/></button>
        <button type="button" className="maildesk-secondary" aria-label="Mail suivant" disabled={locked || !active || (mails.findIndex(mail=>mail.id===activeId)===mails.length-1 && !hasNext)} onClick={()=>navigateMail(1)}><Glyph d={P.chevR} size={15}/></button>
      </div>
      <label className="maildesk-search"><Glyph d={P.search} size={16} /><input aria-label="Rechercher dans tous les mails du dossier"
        placeholder="Rechercher dans tous les mails du dossier…" value={props.query} onChange={(e) => props.onQuery(e.target.value)} />
        {props.query && <button type="button" aria-label="Effacer la recherche" onClick={() => props.onQuery("")}>×</button>}</label>
      <div className="maildesk-toolbar-actions">
        {!props.scoped && !props.readOnly && <button type="button" className="maildesk-primary" aria-label={props.triaging ? "Analyse des mails en cours" : "Analyser les nouveaux mails"} disabled={props.triaging || locked} onClick={() => {if(tools.current)tools.current.open=false;props.onRunTriage(false);}}>
          <Glyph d={SPARK} size={16} /><span>{props.triaging ? "Analyse en cours…" : "Analyser les nouveaux"}</span></button>
        }
        <details ref={tools} className="maildesk-tools"><summary aria-label="Autres actions">Options</summary><div>
          {!props.readOnly && (!props.scoped || emlProjects.length > 0) && <button type="button" disabled={locked} onClick={showEmlImport}>Importer des mails EML</button>}
          {!props.scoped && !props.readOnly && <>
          <button type="button" disabled={syncing} onClick={() => void scan()}>{syncing ? "Synchronisation…" : "Synchroniser les mails"}</button>
          <button type="button" onClick={() => { setReply(undefined); setThunderbirdOpen(true); if(tools.current)tools.current.open=false; }}>Nouveau message</button>
          <button type="button" disabled={props.triaging || locked} onClick={() => {if(tools.current)tools.current.open=false;props.onRunTriage(true);}}>Tout ré-analyser</button>
          </>}
          {thunderbirdAvailable && <button type="button" onClick={() => {setThunderbirdSetup(true); if(tools.current)tools.current.open=false;}}>Extension Thunderbird</button>}
          <button type="button" onClick={() => void refresh()}>Actualiser la boîte</button>
        <label>Dossier<select className="maildesk-folder-picker" aria-label="Dossier de mails" value={folder} onChange={event=>{changeFolder(event.target.value);if(tools.current)tools.current.open=false;}}>
          {!(props.scoped && props.readOnly) && <option value="pending">À classer</option>}<option value="classified">Mails classés</option>{!props.readOnly && <option value="rejected">Mails rejetés</option>}{!props.scoped && <option value="divers">Divers</option>}
          {props.projects.filter(project=>project.code!=="DIVERS").map(project=><option key={project.id} value={`project:${project.id}`}>{project.code}</option>)}
        </select></label>
        <label>Ordre<select aria-label="Ordre des mails" value={sort} onChange={event=>props.onSort(event.target.value)}><option value="newest">Plus récents</option><option value="oldest">Plus anciens</option></select></label>
        </div></details>
      </div>
    </header>
    {emlOpen && <form className="maildesk-compose maildesk-eml" aria-label="Importer des mails EML"
      onSubmit={event => { event.preventDefault(); void importEml(); }}>
      <label>Projet de destination<select autoFocus required value={emlProject} disabled={sourceBusy}
        onChange={event => setEmlProject(event.target.value)}>
        <option value="">Choisir un projet</option>
        {!props.scoped && <option value="automatic">Détecter le projet automatiquement</option>}
        {emlProjects.map(project => <option key={project.id} value={project.id}>{project.code} · {project.name}</option>)}
      </select></label>
      <label>Fichiers EML<input type="file" accept=".eml,message/rfc822" multiple required disabled={sourceBusy}
        onChange={event => setEmlFiles(Array.from(event.target.files || []))} /></label>
      <button type="submit" className="maildesk-primary" disabled={!emlProject || !emlFiles.length || locked}>Importer</button>
      <button type="button" className="maildesk-secondary" disabled={sourceBusy} onClick={() => setEmlOpen(false)}>Fermer</button>
    </form>}
    {thunderbirdSetup && <div className="maildesk-compose"><button type="button" className="maildesk-secondary" onClick={()=>setThunderbirdSetup(false)}>Fermer les réglages Thunderbird</button><ThunderbirdPanel extensionOnly /></div>}
    {thunderbirdOpen && <div className="maildesk-compose"><button type="button" className="maildesk-secondary" onClick={()=>setThunderbirdOpen(false)}>Fermer le message</button><ThunderbirdPanel key={reply?.sourceId || "new"} compose reply={reply} onUpdated={() => { void refresh(); }} /></div>}
    {showAnalysis && <section className="maildesk-analysis-progress" aria-label="Progression de l’analyse des mails">
      <div className="maildesk-analysis-summary">
        <strong aria-live="polite">{props.triageProgress ? `${props.triageProgress.processed} / ${props.triageProgress.total} mails traités` : props.triaging ? "Analyse en cours…" : "Analyse terminée"}</strong>
        {props.triageProgress && <progress aria-label="Mails traités" aria-valuetext={`${props.triageProgress.processed} sur ${props.triageProgress.total} mails traités`}
          max={Math.max(1, props.triageProgress.total)} value={props.triageProgress.processed} />}
        {!!props.triageProgress?.errors && <span className="maildesk-analysis-errors">{props.triageProgress.errors} mail(s) en échec</span>}
        {props.triaging && <button type="button" className="maildesk-secondary" onClick={props.onCancelTriage}>Interrompre l’analyse</button>}
        <button type="button" className="maildesk-analysis-toggle" aria-expanded={analysisDetailsOpen} aria-controls={analysisDetailsId} onClick={()=>setAnalysisDetailsOpen(open=>!open)}>{analysisDetailsOpen ? "Réduire" : "Détails"}</button>
      </div>
      <div id={analysisDetailsId} className="maildesk-analysis-details" hidden={!analysisDetailsOpen}>
        {props.triageProgress && <p>{props.triageProgress.classified} proposition(s) de classement · {props.triageProgress.divers} vers Divers{props.triageProgress.autoClassified ? ` · ${props.triageProgress.autoClassified} mail(s) classé(s) automatiquement` : ""}</p>}
        {analysisMessage && visibleMessage && <p>{visibleMessage}</p>}
      </div>
    </section>}
    {(displayedError || localNotice || ((!analysisMessage || analysisFailure) && visibleMessage)) && <div className={`maildesk-notice${displayedError || analysisFailure ? " error" : ""}`} role={displayedError || analysisFailure ? "alert" : "status"}>
      <Glyph d={displayedError || analysisFailure ? P.alert : P.check} size={14} /><span>{displayedError || localNotice || visibleMessage}</span>
    </div>}
    <div className="maildesk-layout">
      <aside className="maildesk-sidebar" aria-label="Projets de classement">
        {readingOnly ? <p>{rejected ? 'Les mails rejetés sont exclus du classement.' : props.scoped ? 'Seuls les mails classés dans vos projets sont accessibles.' : 'Consultation en lecture seule.'}</p> : <>
        {active && (
              <div className="maildesk-decision">
                <label className="maildesk-project-select">Projet de classement
                  <select aria-label="Projet de classement" value={target} disabled={locked} onChange={(e) => {
                    if(e.target.value==="CREATE"){setProjectForm(true);setProjectError("");}
                    else {setTarget(e.target.value);setProjectForm(false);}
                  }}>
                    <option value="">Choisir une destination…</option>
                    {rankedProjects.map(project=><option key={project.id} value={project.id}>{project.code} — {project.name}</option>)}
                    {target.startsWith("erp:") && <option value={target}>{props.portfolio.find(p=>`erp:${p.id}`===target)?.code}</option>}
                    {!props.scoped && <option value="DISCARD">Supprimer de Kiara</option>}
                    {props.onCreateProject && <option value="CREATE">＋ Créer un projet…</option>}</select>
                </label>
                <div className="maildesk-decision-main"><div className="maildesk-focus-score"><div><span>{target==="DISCARD" ? "Contenu à supprimer de Kiara" : targetOverride ? "Projet choisi" : active.pending ? "Projet proposé" : "Projet du mail"}</span><strong>{target==="DISCARD"?"Supprimer de Kiara":destination?.code||"Choisir un projet"}</strong>{destination && <small>{"name" in destination ? destination.name : destination.title}</small>}</div></div>
                  <button type="button" className="maildesk-primary" disabled={locked || projectForm || !target || target==="CREATE"} onClick={()=>void validateCurrent()}>{validating?"Classement…":target==="DISCARD"?"Supprimer le contenu de Kiara":active.pending?"Classer et suivant":"Enregistrer le classement"}</button>
                </div>
                {active.pending && <button type="button" className="maildesk-reject" disabled={locked || projectForm}
                  onClick={()=>void rejectCurrent()}>Rejeter le mail</button>}
              </div>
        )}
        {scoredTiles.length > 0 && Math.max(...scoredTiles.map(p=>p.score ?? 0)) < 0.75 && <p className="maildesk-confidence" role="status">{props.scoped ? "Les indices sont faibles. Vérifiez le projet avant de classer ce mail." : "Aucun projet identifié avec assez de confiance. Choisissez une destination ou gardez ce mail dans Divers."}</p>}
        <div className="maildesk-project-heading"><strong>{scoredTiles.length ? "Projets proposés" : "Projets"}</strong><small>Glissez le mail sur une vignette</small></div>
        <div className="maildesk-projects maildesk-likely-projects" aria-label="Projets proposés — déposez le mail dessus">
          {visibleProjectTiles.map(projectTile)}
        </div>
        {!!otherProjectTiles.length && <details className="maildesk-project-picker"><summary>Tous les projets <small>{projectTiles.length}</small></summary>
          <div className="maildesk-projects" aria-label="Autres projets de classement">{otherProjectTiles.map(projectTile)}</div>
        </details>}
        {!props.scoped && <div className="maildesk-projects maildesk-project-fallbacks" aria-label="Autres destinations">
          {(() => {
            const project = props.projects.find((p) => p.code.toUpperCase() === "DIVERS");
            return <button type="button" className={`maildesk-project divers${props.dragOver === "mini:DIVERS" ? " drop-target" : ""}`}
              title="Déposer les mails sans projet identifié" disabled={locked || !project} onClick={() => setTarget(project?.id||"")}
              onDragOver={(e) => { e.preventDefault(); props.onDragOver("mini:DIVERS"); }} onDragLeave={() => props.onDragOver(null)}
              onDrop={(e) => drop(e, "DIVERS", project?.id || null)}>
              <span className="maildesk-project-icon"><Glyph d={P.folder} size={20} /></span><span><b>DIVERS</b><small>À réexaminer plus tard</small></span>
            </button>;
          })()}
          <button type="button" className={`maildesk-project discard${props.dragOver === "mini:DISCARD" ? " drop-target" : ""}`}
            title="Supprimer le contenu de Kiara et empêcher sa réanalyse" disabled={locked}
            onClick={() => setTarget("DISCARD")}
            onDragOver={(e) => { e.preventDefault(); props.onDragOver("mini:DISCARD"); }} onDragLeave={() => props.onDragOver(null)}
            onDrop={(e) => drop(e, "DISCARD", null)}>
            <span className="maildesk-project-icon"><Glyph d={P.trash} size={20} /></span>
            <span><b>Supprimer de Kiara</b><small>Supprime la copie importée dans Kiara</small></span>
          </button>
        </div>}
        {active && <div className="maildesk-classification-options">
                {active.pending && <details className="maildesk-reason"><summary>Pourquoi cette proposition ?</summary>
                  {targetScore!=null && <p>{target==="DISCARD" ? "Score de suppression proposée" : "Score de correspondance"} : {focusPercent(targetScore)}</p>}
                  <p>{target===active.pending.target_project_id ? classificationReason(active.pending.reason) : targetEvidence?.length ? "Indices repérés pour ce projet." : target===suggestedTarget && !targetOverride ? "Ce projet présente les meilleurs indices disponibles. Vérifiez le classement avant de valider." : "Cette destination est choisie manuellement."}</p>
                  {!!targetEvidence?.length && <ul>{targetEvidence.map(evidence=><li key={evidence.key}>{evidence.label}</li>)}</ul>}
                  {active.pending.discard_suggestion?.probability!=null && <div className="maildesk-discard-estimate"><p>Suggestion de suppression : {focusPercent(active.pending.discard_suggestion.probability)}</p><p>{active.pending.discard_suggestion.reason}</p><small>Estimation issue des mails déjà classés ou supprimés de Kiara ; elle reste à vérifier.</small></div>}
                </details>}
                {!props.scoped && <details className="maildesk-mail-options"><summary>Options du mail</summary><div className="maildesk-secondary-actions">
                  <button type="button" className="maildesk-secondary" aria-label="Classer dans Divers" disabled={locked || !diversProject} onClick={()=>void validateCurrent(diversProject!.id)}>Classer dans Divers</button>
                  <button type="button" className="maildesk-reject" disabled={locked} onClick={()=>void discard([active.id])}>Supprimer ce mail de Kiara</button>
                </div><p>La suppression retire le contenu de ce mail de Kiara et l’exclut des analyses.</p></details>}
                {projectForm && <form className="maildesk-create-project" aria-label="Créer un projet depuis ce mail" onSubmit={event=>{event.preventDefault();void createProject();}}>
                  <strong>Nouveau projet</strong><p>Créez sa destination sans quitter ce mail, puis validez son affectation.</p>
                  <div className="maildesk-create-project-fields"><label htmlFor={`${projectFormId}-code`}>Code du projet <small>(facultatif)</small>
                    <input id={`${projectFormId}-code`} value={projectCode} maxLength={64} disabled={creatingProject} onChange={e=>setProjectCode(e.target.value)}/></label>
                    <label htmlFor={`${projectFormId}-title`}>Nom du projet<input id={`${projectFormId}-title`} autoFocus required maxLength={256} value={projectTitle} disabled={creatingProject} onChange={e=>setProjectTitle(e.target.value)}/></label></div>
                  {projectError && <p role="alert">{projectError}</p>}
                  <div className="maildesk-decision-actions"><button type="submit" className="maildesk-primary" disabled={creatingProject || !projectTitle.trim()}>{creatingProject?"Création…":"Créer et sélectionner"}</button>
                    <button type="button" className="maildesk-secondary" disabled={creatingProject} onClick={()=>setProjectForm(false)}>Annuler</button></div>
                </form>}
        </div>}
        {props.autoInfo && <details className="maildesk-sync-details"><summary>Synchronisation automatique</summary><p>{props.autoInfo}</p></details>}
        </>}
      </aside>
      <section className="maildesk-reader" aria-label="Espace de lecture">
        {!active ? <div className="maildesk-reader-empty"><div className="maildesk-envelope-art"><Glyph d={ENVELOPE} size={46} /><span><Glyph d={SPARK} size={17} /></span></div>
          <h2>Aucun mail dans ce dossier</h2></div>
          : <>
            <div className="maildesk-reader-scroll">
              <header className="maildesk-reader-heading" draggable={!locked&&!readingOnly} onDragStart={dragCurrentMail} title={readingOnly?undefined:"Glisser ce mail vers un projet"}><h1>{active.subject || "Sans objet"}</h1>
                <div className="maildesk-message-meta">
                  <strong title={detail?.sender || active.sender}>{senderName(detail?.sender || active.sender) || "Expéditeur non renseigné"}</strong>
                  <time title={fullDate(detail?.received_at || active.date)}>{shortDate(detail?.received_at || active.date)}</time>
                  <details key={active.id} className="maildesk-message-details"><summary>Détails du mail</summary><div>
                    <dl><dt>De</dt><dd>{detail?.sender || active.sender || "Expéditeur non renseigné"}</dd>
                      <dt>{detail?.recipients ? "À" : "Destinataires"}</dt><dd>{(detail?.recipients?.to || detail?.participants || []).join(", ") || (detailLoading ? "Chargement…" : "Non renseignés")}</dd>
                      {!!detail?.recipients?.cc.length && <><dt>Copie</dt><dd>{detail.recipients.cc.join(", ")}</dd></>}
                      <dt>Date</dt><dd>{fullDate(detail?.received_at || active.date)}</dd></dl>
                <div className="maildesk-message-actions">{!readingOnly && (!props.scoped || (canReply && !active.pending)) && <button type="button" className="maildesk-secondary" onClick={() => {setReply({sourceId:active.id,sender:active.sender,subject:active.subject});setThunderbirdOpen(true);}}>Préparer une réponse</button>}
                      <AsyncDownloadLink href={agentPath(`/v1/sources/${encodeURIComponent(active.id)}/raw`)} title="Télécharger le mail original" filename="mail-original.eml">Original</AsyncDownloadLink></div>
                  </div></details>
                </div>
              </header>
              <article className="maildesk-paper" draggable={!locked&&!readingOnly} onDragStart={dragCurrentMail}>                {detailLoading ? <div className="maildesk-reader-loading" role="status"><div /><div /><div /><span>Ouverture du message…</span></div>
                  : detailError ? <div className="maildesk-read-error" role="alert"><p>{detailError}</p><button className="maildesk-secondary" type="button" onClick={() => setDetailAttempt((n) => n + 1)}>Réessayer la lecture</button></div>
                  : body ? <div className="maildesk-body-text"><MessageContent text={body} inlineImages={detail?.inline_images} /></div> : <p className="maildesk-body-empty">Ce mail ne contient pas de texte extrait. Consultez le fichier original.</p>}
              </article>
              {!!attachments.length && <section className="maildesk-attachments" aria-label="Pièces jointes"><h3><Glyph d={PAPERCLIP} size={16} />{attachments.length} pièce(s) jointe(s)</h3>
                <div>{attachments.map((attachment, index) => <div key={index} className="maildesk-attachment"><span><Glyph d={P.folder} size={19} /></span><div><strong>{attachment.filename}</strong><small>{attachment.mime || "Pièce jointe"}</small>
                  {attachment.index != null ? <div className="maildesk-attachment-actions">
                    {attachment.previewable && <a target="_blank" rel="noopener noreferrer" href={agentPath(`/v1/sources/${encodeURIComponent(active.id)}/attachments/${attachment.index}`)}>Visualiser</a>}
                    <AsyncDownloadLink href={agentPath(`/v1/sources/${encodeURIComponent(active.id)}/attachments/${attachment.index}?download=true`)} filename={attachment.filename}>Télécharger</AsyncDownloadLink>
                  </div> : <small>Mail original nécessaire pour ouvrir cette pièce jointe</small>}
                </div></div>)}</div>
                </section>}
            </div>
          </>}
      </section>
    </div>
  </div>;
}
