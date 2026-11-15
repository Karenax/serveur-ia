import { agentLocation, agentPath, conversationsHref, projectConversationHref } from '../lib/agentRoutes';
import {useQueryState} from '../hooks/useQueryState';
import { useCallback, useEffect, useRef, useState, type ComponentType } from "react";
import { api, type PortfolioRow, type SearchHit } from "../lib/api";
import { parseWorkspaceRoute, projectTabs, routeKey, workspacePath, type ProjectTab, type WorkspaceRoute } from "../lib/workspaceNavigation";
import { Glyph, P } from "../os/icons";
import { AiSettingsForm, MailSettingsForm, MemorySettingsForm } from "./SettingsForms";
import { OperationsPanel } from "./OperationsPanel";
import { ThunderbirdPanel } from "./ThunderbirdPanel";
import { ActionDashboard } from "./ActionDashboard";
import { GlobalMeetingsView, GlobalJobsView, GlobalKnowledgeView, SourceInspector,type MeetingCreationRequest } from "./WorkspaceViews";
import { Badge, EmptyState, ErrorState, LoadingState } from "./Ui";
import { ProjectFolder } from "./ProjectFolder";
import { useWorkspaceWheel } from "../hooks/useWorkspaceWheel";
import { ProjectReferenceSettings } from "./ProjectReferenceSettings";
import { DeliverableSettings } from "./DeliverableSettings";
import { DocumentSettings } from "./DocumentSettings";
import { ConnectionStatus } from "./ConnectionStatus";
import { SearchView } from "./SearchView";
import { MeetingCaptureBar } from "./MeetingStudio";
import { SourcesLibrary } from "./SourcesLibrary";
import { FusionInsights } from "./FusionInsights";
import { NativeCaptureBar } from "./NativeMeetingCapture";
import type {WorkspaceCitation} from "../lib/workspaceApi";
import { withActivity } from "../lib/asyncActivity";
import "../project-kiara-preview.css";
import {MEETING_WORKSPACE_EVENT} from '../lib/meetingWorkspace';

export type ProjectWorkspaceProps = {projectId:string; initialTab:ProjectTab | "import"; row?:PortfolioRow; reloadRows:()=>Promise<void>; back:()=>void; onTabChange?:(tab:ProjectTab | "import")=>boolean|void; sidebarNavigation?:boolean;kiaraPresentation?:boolean};
export type ProjectCreateProps = {reload:()=>Promise<void> | void;close:()=>void;onCreated?:(id:string)=>Promise<void>};
export type MailPanelProps = {rows?:PortfolioRow[]; active?:boolean; reloadProjects?:()=>Promise<void>};
type Props = {canCreateProject?:boolean; portfolioLoading?:boolean; portfolioUnavailable?:boolean; rows:PortfolioRow[]; reload:()=>Promise<void>; error?:string; ProjectPanel:ComponentType<ProjectWorkspaceProps>; MailPanel:ComponentType<MailPanelProps>; CreatePanel:ComponentType<ProjectCreateProps>; SagePanel:ComponentType};
const navigation = [
  {page:"home", label:"Accueil", icon:P.grid}, {page:"projects", label:"Projets", icon:P.folder},
  {page:"mail", label:"Mails", icon:["M3 5h18v14H3zM3 5l9 7 9-7"]},
  {page:"meetings", label:"Réunions", icon:["M4 10v4M8 5v14M12 8v8M16 3v18M20 9v6"]},
  {page:"activity", label:"Activité", icon:["M3 12h4l3-6 4 12 3-6h4"]},
  {page:"sources", label:"Sources", icon:["M4 3h12l4 4v14H4zM15 3v5h5M8 12h8M8 16h8"]},
  {page:"knowledge", label:"Informations", icon:["M12 5v16M3 3h5l4 2 4-2h5v16h-5l-4 2-4-2H3z"]},
  {page:"jobs", label:"Suivi des analyses", icon:["M9 6h12M9 12h12M9 18h12M3 6h.01M3 12h.01M3 18h.01"]},
] satisfies {page: WorkspaceRoute['page']; label: string; icon: string[]}[];
const commandDestinations = [...navigation, {page:"search" as const, label:"Recherche", icon:P.search}, {page:"preparation" as const,label:"Préparer les réunions",icon:P.sync}];
const pageLabels:Record<string,string> = {...Object.fromEntries(commandDestinations.map(n=>[n.page,n.label])), imports:"Connexions & imports",stats:"Statistiques",preparation:"Réunions et transcription",settings:"Réglages",create:"Nouveau projet",project:"Projet"};
const settingsPages:WorkspaceRoute['page'][] = ["sources","knowledge","jobs","imports"];
const settingsAreaPages:WorkspaceRoute['page'][] = ["settings","stats","preparation",...settingsPages];
const mainSettings = [["ai","Général"],["mail","Mails"],["references","Clients et équipe"],["appearance","Apparence"],["sources","Sources"],["knowledge","Informations"],["jobs","Suivi des analyses"],["imports","Connexions & imports"]];
const extraSettings = [["stats","Statistiques"],["preparation","Réunions et transcription"],["memory","Recherche dans les documents"],["deliverables","Modèles de livrables"],["documents","Modèles de documents"],["operations","Sauvegardes et maintenance"]];
const sparkle = ["m12 3 3 6 6 3-6 3-3 6-3-6-6-3 6-3z"];
const settingsIcon = ["M4 6h16M4 12h16M4 18h16",'<circle cx="8" cy="6" r="2" fill="currentColor"/>','<circle cx="16" cy="12" r="2" fill="currentColor"/>','<circle cx="10" cy="18" r="2" fill="currentColor"/>'];
function preference(key:string, fallback:string) { try {return localStorage.getItem(key) || fallback;} catch {return fallback;} }
function savePreference(key:string,value:string) { try {localStorage.setItem(key,value);} catch {/* preference stays in this session */} }
function navigationBreakpoints() {
  return typeof window.matchMedia === 'function'
    ? {fusionNarrow:!window.matchMedia('(min-width:671px)').matches, standardNarrow:window.matchMedia('(max-width:850px)').matches}
    : {fusionNarrow:window.innerWidth<=670, standardNarrow:window.innerWidth<=850};
}

export function WorkspaceShell({rows,reload,error,canCreateProject=true,portfolioLoading=false,portfolioUnavailable=false,ProjectPanel,MailPanel,CreatePanel,SagePanel}:Props) {
  const [route,setRoute] = useState<WorkspaceRoute>(()=>parseWorkspaceRoute(window.location.pathname,window.location.search));
  const showProjectPresentation = route.page === "projects" || route.page === "project";
  const [visited,setVisited] = useState<WorkspaceRoute[]>(()=>[parseWorkspaceRoute(window.location.pathname,window.location.search)]);
  const [mobileMenu,setMobileMenu] = useState(false);
  const [navigationViewport,setNavigationViewport] = useState(navigationBreakpoints);
  const fusionWorkspace = route.page==='sources'||route.page==='meetings';
  const narrow = navigationViewport.standardNarrow;
  const mobileToggle = useRef<HTMLButtonElement>(null);
  const previousMenu = useRef(false);
  useEffect(()=>{
    const resized=()=>setNavigationViewport(navigationBreakpoints());
    const queries=typeof window.matchMedia==='function'
      ? [window.matchMedia('(min-width:671px)'),window.matchMedia('(max-width:850px)')] : [];
    window.addEventListener('resize',resized);
    queries.forEach(query=>query.addEventListener('change',resized));
    return()=>{window.removeEventListener('resize',resized);queries.forEach(query=>query.removeEventListener('change',resized));};
  },[]);
  useEffect(()=>{if(!narrow)setMobileMenu(false);},[narrow]);
  useEffect(()=>{
    if(mobileMenu&&narrow)document.querySelector<HTMLAnchorElement>(".workspace-sidebar nav a")?.focus();
    else if(previousMenu.current){if(narrow)mobileToggle.current?.focus();else document.querySelector<HTMLButtonElement>(".workspace-search-trigger")?.focus();}
    else if(narrow&&document.activeElement?.closest('.workspace-sidebar'))mobileToggle.current?.focus();
    previousMenu.current=mobileMenu&&narrow;
  },[mobileMenu,narrow]);
  const [theme,setTheme] = useState(() => {
    const shared = preference("fred-theme", "");
    if (document.body.dataset.kiaraDesktop === "true") {
      if (shared === "system") return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "dark" : "light";
      if (shared === "light" || shared === "dark") return shared;
    }
    return preference("agent-ui-theme","light");
  });
  const [density,setDensity] = useState(()=>preference("agent-ui-density","comfortable"));
  const [commandOpen,setCommandOpen] = useState(false);
  const [command,setCommand] = useState("");
  const [hits,setHits] = useState<SearchHit[]>([]);
  const [searchError,setSearchError] = useState("");
  const [searching,setSearching] = useState(false);
  const commandDialog = useRef<HTMLDialogElement>(null);
  const commandInput = useRef<HTMLInputElement>(null);
  const mainRef = useRef<HTMLElement>(null);
  const shellRef = useRef<HTMLDivElement>(null);
  const [favorites,setFavorites] = useState<string[]>(()=>{try{return JSON.parse(preference("agent-project-favorites",preference("mp-desk-pins","[]")));}catch{return[];}});
  const [source,setSource] = useState<{sourceId:string;title?:string;evidence?:WorkspaceCitation[]} | null>(()=>{
    const sourceId=new URLSearchParams(window.location.search).get('source');
    return agentLocation(window.location.pathname)==='/app/sources'&&sourceId&&/^[A-Za-z0-9_-]+$/.test(sourceId)?{sourceId}:null;
  });
  const [notice,setNotice] = useState("");
  const [requestedSession,setRequestedSession] = useState<string | null>(null);
  const [studioOpen,setStudioOpen]=useState(false);
  const [requestedCreation,setRequestedCreation] = useState<MeetingCreationRequest|null>(null);
  const [importing,setImporting] = useState(false);
  const importFile = useRef<HTMLInputElement>(null);
  const current = route.page === "project" ? rows.find(r=>r.id===route.projectId) : undefined;
  const [projectQuery,setProjectQuery] = useQueryState<string>("q","",workspacePath({page:"projects"}));
  const [projectFilter,setProjectFilter] = useQueryState<string>("status","active",workspacePath({page:"projects"}));
  const [integrationsTab,setIntegrationsTab] = useQueryState<string>("connection","sage","/app/imports");
  const [settingsTab,setSettingsTab] = useQueryState<string>("settings",route.page==="stats"?"stats":route.page==="preparation"?"preparation":"ai","/app/settings");
  const [settingsOptionsOpen,setSettingsOptionsOpen] = useState(false);
  const [referencesStarted,setReferencesStarted] = useState(false);
  const [deliverablesStarted,setDeliverablesStarted] = useState(false);
  const [deliverablesBusy,setDeliverablesBusy] = useState(false);
  const [documentsStarted,setDocumentsStarted] = useState(false);
  const [documentsBusy,setDocumentsBusy] = useState(false);
  useEffect(()=>{if(settingsTab==="documents")setDocumentsStarted(true);},[settingsTab]);
  useEffect(()=>{if(route.page==='stats'||route.page==='preparation')setSettingsTab(route.page);},[route.page]);
  const changeSettingsTab=(id:string)=>{if(settingsTab==="documents"&&document.querySelector('[aria-label="Réglages documentaires"][data-workspace-dirty="true"]')&&!window.confirm("Changer de rubrique en conservant les réglages documentaires non enregistrés ?"))return;setSettingsTab(id);setSettingsOptionsOpen(false);};
  useEffect(()=>{if(settingsTab==="references")setReferencesStarted(true);},[settingsTab]);
  useEffect(()=>{if(settingsTab==="deliverables")setDeliverablesStarted(true);},[settingsTab]);
  const [microphones,setMicrophones] = useState<string[]>([]);
  useWorkspaceWheel(shellRef, !mobileMenu && !commandOpen && !source);
  useEffect(()=>{
    const update=(event:Event)=>{const {projectId,recording}=(event as CustomEvent).detail;
      setMicrophones(previous=>recording?Array.from(new Set([...previous,projectId])):previous.filter(id=>id!==projectId));};
    window.addEventListener("agent-microphone",update);return()=>window.removeEventListener("agent-microphone",update);
  },[]);

  const projectListQuery = useRef(route.page === 'projects' ? window.location.search : '');
  const applyRoute = useCallback((next:WorkspaceRoute)=>{
    setRoute(next); setVisited(previous=>{
      const existing=previous.findIndex(r=>routeKey(r)===routeKey(next));
      return existing<0?[...previous,next]:previous.map((r,i)=>i===existing?next:r);
    });setMobileMenu(false);setNotice("");
  },[]);
  const navigate = useCallback((next:WorkspaceRoute)=>{
    if(documentsBusy){setNotice("Réglages documentaires en cours. Attendre le résultat avant de changer de rubrique.");return false;}
    if(deliverablesBusy){setNotice("Opération sur les livrables en cours. Attendre son résultat avant de changer de rubrique.");return false;}
    const correction=document.querySelector('[data-workspace-dirty="true"]');
    if (correction && !window.confirm("Une correction est ouverte. Changer de rubrique en conservant ce brouillon ?")) return false;
    if (window.location.pathname === workspacePath({page:'projects'})) projectListQuery.current = window.location.search;
    const target = workspacePath(next);
    const listQuery = next.page === 'projects' ? projectListQuery.current : '';
    if(target + listQuery !== window.location.pathname + window.location.search) {
      window.history.pushState(null,"",target + listQuery);
    }
    applyRoute(next);
    window.dispatchEvent(new Event('agent:querychange'));
    return true;
  },[applyRoute,deliverablesBusy,documentsBusy]);
  const openProject = useCallback((id:string,tab:string="pilotage")=>{
    if (tab==="deliverables") tab="documents";
    if (["tasks", "milestones", "planning"].includes(tab)) tab="planification";
    return navigate({page:"project",projectId:id,tab:projectTabs.includes(tab as ProjectTab)?tab as ProjectTab:"pilotage"});
  },[navigate]);
  const openSettingsTab=(id:string)=>{
    if(settingsPages.includes(id as WorkspaceRoute['page'])){navigate({page:id as WorkspaceRoute['page']});return;}
    if(!['settings','stats','preparation'].includes(route.page)&&!navigate({page:'settings'}))return;
    changeSettingsTab(id);
  };
  const createMeeting=useCallback((projectId?:string)=>{
    if(!navigate({page:'meetings'}))return false;
    setRequestedCreation(previous=>({key:(previous?.key??0)+1,projectId:rows.some(row=>row.id===projectId)?projectId:undefined}));
    return true;
  },[navigate,rows]);
  useEffect(()=>{
    const open=(event:Event)=>{
      const projectId=(event as CustomEvent<{projectId?:unknown}>).detail?.projectId;
      if(typeof projectId!=='string'||!rows.some(row=>row.id===projectId))return;
      // Handle the link even when the existing navigation guard refuses it.
      event.preventDefault();
      navigate({page:'meetings',projectId});
    };
    window.addEventListener(MEETING_WORKSPACE_EVENT,open);
    return()=>window.removeEventListener(MEETING_WORKSPACE_EVENT,open);
  },[navigate,rows]);
  useEffect(()=>{
    if(route.page!=="meetings"||!requestedSession)return;
    window.dispatchEvent(new CustomEvent("agent-open-meeting-session",{detail:{sessionId:requestedSession}}));
    setRequestedSession(null);
  },[route.page,requestedSession]);
  useEffect(()=>{
    if (route.page === "projects" && window.location.pathname !== workspacePath(route)) {
      window.history.replaceState(window.history.state,"",workspacePath(route) + window.location.search + window.location.hash);
      window.dispatchEvent(new Event('agent:querychange'));
    } else if(!agentLocation(window.location.pathname).startsWith("/app")) {
      window.history.replaceState(null,"",workspacePath(route));
    }
    const pop=()=>applyRoute(parseWorkspaceRoute(window.location.pathname,window.location.search));
    window.addEventListener("popstate",pop);return()=>window.removeEventListener("popstate",pop);
  },[applyRoute]);
  useEffect(()=>{
    const previousTheme=document.body.dataset.theme;
    document.body.removeAttribute("data-theme");document.body.classList.add("agent-workspace-body");
    return()=>{document.body.classList.remove("agent-workspace-body");if(previousTheme)document.body.dataset.theme=previousTheme;};
  },[]);
  useEffect(()=>{savePreference("agent-ui-theme",theme);},[theme]);
  useEffect(()=>{savePreference("agent-ui-density",density);},[density]);
  useEffect(()=>{savePreference("agent-project-favorites",JSON.stringify(favorites));},[favorites]);
  useEffect(()=>{
    const keyboard=(e:KeyboardEvent)=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();navigate({page:"search"});}if(e.key==="Escape")setMobileMenu(false);};
    window.addEventListener("keydown",keyboard);return()=>window.removeEventListener("keydown",keyboard);
  },[navigate]);
  useEffect(()=>{
    const dialog=commandDialog.current;if(!dialog)return;
    if(commandOpen){dialog.showModal?.();commandInput.current?.focus();}else if(dialog.open)dialog.close();
  },[commandOpen]);
  useEffect(()=>{
    if(!commandOpen)return;let cancelled=false;setHits([]);setSearchError("");
    if(command.trim().length<2){setSearching(false);return;}
    setSearching(true);const timer=window.setTimeout(()=>{
      api.search(command.trim(),current?.id).then((result:any)=>{if(!cancelled)setHits(result.hits || result || []);})
        .catch(e=>{if(!cancelled)setSearchError(String(e.message||e));}).finally(()=>{if(!cancelled)setSearching(false);});
    },250);return()=>{cancelled=true;window.clearTimeout(timer);};
  },[command,commandOpen,current?.id]);
  useEffect(() => {
    const brand = "Kiara";
    document.title = `${current?.code || pageLabels[route.page]} · ${brand}`;
  }, [route.page, current?.code]);
  const favorite=(id:string)=>setFavorites(ids=>ids.includes(id)?ids.filter(v=>v!==id):[...ids,id]);
  const conversationsPath = conversationsHref();
  const projectAssistantPath = projectConversationHref(current?.id);
  const importArchive=async(file:File)=>{
    if(importing)return;setImporting(true);setNotice("");
    try{await withActivity("Importation d’une archive de projet…",async()=>{const data=JSON.parse(await file.text());const result:any=await api.importJson(data);await reload();setNotice("Archive importée. Les projets existants sont conservés.");if(result.project_id || result.id)openProject(result.project_id || result.id);});}
    catch(e){setNotice("Import impossible : "+String((e as Error).message));}finally{setImporting(false);if(importFile.current)importFile.current.value="";}
  };
  const filtered=rows.filter(r=>`${r.code} ${r.title} ${r.client_name||""}`.toLowerCase().includes(projectQuery.toLowerCase())&&
    (projectFilter==="all"||projectFilter==="active"&&r.status==="active"||projectFilter==="closed"&&r.status!=="active"||projectFilter==="late"&&r.en_retard>0||projectFilter==="review"&&(r.corrections>0||r.unconfirmed>0)));
  const portfolio=(compact=false)=><div className="workspace-table-wrap"><table className="workspace-portfolio"><thead><tr><th>Projet / client</th><th>État</th><th>Avancement</th>{compact&&<th className="numeric">Reste à faire</th>}<th>Prochaine étape</th><th><span className="sr-only">Favori</span></th></tr></thead><tbody>{(compact?rows.filter(r=>r.status==="active").slice(0,5):filtered).map(r=><tr key={r.id}><td><button type="button" className="workspace-project-link" aria-label={`${r.code} · ${r.title}`} onClick={()=>openProject(r.id)}>{compact&&<ProjectFolder code={r.code}/>}<span>{compact?`${r.code} · ${r.title}`:r.title}</span></button><small>{!compact&&`${r.code} · `}{r.client_name||"Client à renseigner"}</small></td><td>{compact?<Badge value={r.status==="active"?"En cours":"Archivé"} tone={r.status==="active"?"ok":"neutral"}/>:<span className={r.status==="active"?"kiara-project-active":"workspace-muted"}>{r.status==="active"?"En cours":"Archivé"}</span>}</td><td><span className="numeric">{r.taches&&r.taches!=="0/0"&&r.taches!=="0 / 0"?`${Math.round(r.avancement)} %`:"Aucun planning"}</span>{compact&&<div className="workspace-meter"><span style={{width:`${Math.max(0,Math.min(100,r.avancement))}%`}}/></div>}</td>{compact&&<td className="numeric">{r.initial_hours||r.consumed_hours||r.remaining_mode==='reestimated'?`${r.raf} h`:"À estimer"}</td>}<td>{r.jalon_en_cours||"Jalon à définir"}<small>{r.jalon_echeance||"Échéance à préciser"}</small></td><td><button type="button" className="workspace-icon-button" aria-label={`${favorites.includes(r.id)?"Retirer":"Ajouter"} ${r.code} ${favorites.includes(r.id)?"des":"aux"} favoris`} aria-pressed={favorites.includes(r.id)} onClick={()=>favorite(r.id)}><Glyph d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9z"/></button></td></tr>)}</tbody></table>{!compact&&!filtered.length&&<EmptyState title="Aucun projet dans cette vue" detail="Changez le filtre ou créez un projet."/>}</div>;
  const selectCommand=(next:WorkspaceRoute)=>{setCommandOpen(false);setCommand("");navigate(next);};
  const projectCreated = async (_id:string) => {
    await reload();
    projectListQuery.current = "";
    setProjectQuery("");setProjectFilter("active");
    navigate({page:"projects"});setNotice("Projet ajouté au portefeuille.");
  };

  const studioHere=route.page==='meetings'&&studioOpen;
  const breadcrumb=<nav className="workspace-breadcrumb" aria-label="Fil d’Ariane"><a href={agentPath("/app/")} onClick={e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();navigate({page:"home"});}}>Espace de travail</a><Glyph d={P.chevR} size={12}/><span>{route.page==="project"?`${current?.code||"Projet"} · ${current?.client_name||"Client à renseigner"}`:pageLabels[route.page]}</span></nav>;
  return <div ref={shellRef} className={`workspace-shell ${density==="compact"?"workspace-compact":""}`} data-workspace-theme={theme} data-kiara-navigation="true" data-project-presentation={showProjectPresentation ? "kiara" : undefined} data-fusion-workspace={fusionWorkspace?route.page:undefined} data-meeting-studio={studioHere?'true':undefined}>
    <a className="workspace-skip" href="#workspace-main">Aller au contenu</a>
    {mobileMenu&&<button className="workspace-menu-backdrop" type="button" aria-label="Fermer le menu" onClick={()=>setMobileMenu(false)}/>}
    <aside className={`workspace-sidebar ${mobileMenu?"is-open":""}`} aria-label="Menu principal" aria-hidden={narrow&&!mobileMenu?true:undefined} inert={narrow&&!mobileMenu}>
      <a className="workspace-brand" href={agentPath("/app/")} onClick={e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();navigate({page:"home"});}}><span aria-hidden="true">K</span>Kiara</a>
      <nav aria-label="Grandes rubriques">{conversationsPath&&<a href={conversationsPath}><Glyph d={P.chevL}/><span>Conversations</span></a>}{navigation.filter(n=>n.page!=="home"&&!settingsPages.includes(n.page)).map(n=><div className="workspace-nav-group" key={n.page}><a href={workspacePath({page:n.page})} aria-current={route.page===n.page||(n.page==="projects"&&route.page==="project")?"page":undefined} className={n.page==="projects"&&route.page==="project"?"workspace-nav-parent-active":undefined} onClick={e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();navigate({page:n.page});}}><Glyph d={n.icon}/><span>{n.label}</span></a>
      </div>)}</nav>
      {!!favorites.length&&<details className="workspace-favorites"><summary>Projets favoris</summary>{favorites.filter(id=>rows.some(r=>r.id===id)).slice(0,8).map(id=>{const r=rows.find(p=>p.id===id)!;return <button key={id} type="button" onClick={()=>openProject(id)}><ProjectFolder code={r.code}/><span>{r.code}<small>{r.title}</small></span></button>;})}</details>}
      <div className="workspace-sidebar-foot"><nav><a href={agentPath("/app/settings")} aria-current={route.page==="settings"?"page":undefined} className={settingsAreaPages.includes(route.page)?"workspace-nav-parent-active":undefined} onClick={e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();navigate({page:"settings"});}}><Glyph d={settingsIcon}/><span>Réglages</span></a></nav><span className="workspace-local"><i/>{document.body.dataset.kiaraDesktop==='true' ? 'Serveur Kiara' : 'Espace de travail'}</span></div>
    </aside>
    <div className="workspace-body" inert={narrow&&mobileMenu}><header className="workspace-topbar">
      <button ref={mobileToggle} type="button" className="workspace-icon-button workspace-mobile-toggle" aria-label="Ouvrir le menu" aria-expanded={mobileMenu} onClick={()=>setMobileMenu(v=>!v)}><Glyph d={P.list}/></button>
      <button type="button" className="workspace-search-trigger" aria-label="Rechercher dans Kiara" title="Recherche globale · Ctrl K" onClick={()=>navigate({page:"search"})}><Glyph d={P.search}/><span>Rechercher…</span></button>
      <button type="button" className="workspace-icon-button" aria-label="Accès rapide aux rubriques" title="Accès rapide aux rubriques" onClick={()=>setCommandOpen(true)}><Glyph d={P.grid}/></button>
      <ConnectionStatus onOpenJobs={()=>navigate({page:"jobs"})}/>
      {projectAssistantPath && <a className="button secondary workspace-assistant-toggle" aria-label="Assistant de projet" href={projectAssistantPath}><Glyph d={sparkle}/><span>Assistant de projet</span></a>}
    </header>
    <div className="workspace-area"><main id="workspace-main" ref={mainRef} className="workspace-main">
      {route.page!=="mail"&&route.page!=="activity"&&!studioHere&&!showProjectPresentation&&breadcrumb}
      {notice&&<div className="workspace-notice" role="status">{notice}</div>}
      <MeetingCaptureBar onOpen={sessionId=>{if(navigate({page:"meetings"}))setRequestedSession(sessionId);}}/>
      <NativeCaptureBar onOpen={sessionId=>{if(navigate({page:"meetings"}))setRequestedSession(sessionId);}}/>
      {error && <div role="alert"><ErrorState message={error} retry={()=>void reload()}/></div>}
      {microphones.map(id=><div className="workspace-notice" role="status" key={id}>● Microphone actif · {rows.find(r=>r.id===id)?.code || "Réunion"} <button type="button" className="workspace-text-button" onClick={()=>{if(openProject(id,"reviews"))window.dispatchEvent(new CustomEvent("agent-show-recording",{detail:{projectId:id}}));}}>Revenir à l’enregistrement</button> <button type="button" className="button secondary" onClick={()=>window.dispatchEvent(new CustomEvent("agent-stop-recording",{detail:{projectId:id}}))}>Arrêter l’enregistrement</button></div>)}
      {settingsAreaPages.includes(route.page)&&<>
        {['settings','stats','preparation'].includes(route.page)&&<div className="workspace-page-header"><h1>Réglages</h1></div>}
        <div className="workspace-settings-navigation"><nav className="workspace-tabs" aria-label="Réglages">{mainSettings.map(([id,label])=><button type="button" key={id} aria-pressed={(settingsPages.includes(route.page)?route.page:settingsTab)===id} disabled={deliverablesBusy||documentsBusy} onClick={()=>openSettingsTab(id)}>{label}</button>)}</nav>
          <div className="workspace-options"><button type="button" className="button secondary" aria-expanded={settingsOptionsOpen} aria-controls="workspace-extra-settings" disabled={deliverablesBusy||documentsBusy} onClick={()=>setSettingsOptionsOpen(v=>!v)}>Autres réglages{!settingsPages.includes(route.page)&&extraSettings.find(([id])=>id===settingsTab)&&` · ${extraSettings.find(([id])=>id===settingsTab)![1]}`}</button><div id="workspace-extra-settings" className="workspace-options-panel" hidden={!settingsOptionsOpen} role="group" aria-label="Réglages supplémentaires">{extraSettings.map(([id,label])=><button type="button" key={id} aria-pressed={!settingsPages.includes(route.page)&&settingsTab===id} disabled={deliverablesBusy||documentsBusy} onClick={()=>openSettingsTab(id)}>{label}</button>)}</div></div>
        </div>
      </>}
      {visited.map(view=>{
        const visible=routeKey(view)===routeKey(route), key=routeKey(view);
        if ((view.page==='home'||view.page==='projects')&&(portfolioLoading||portfolioUnavailable)) return <div key={key} hidden={!visible} className="workspace-cached-view">{portfolioLoading?<LoadingState label="Chargement des projets"/>:<p>Le portefeuille est indisponible. Les autres rubriques restent accessibles ; utilisez Réessayer pour recharger les projets.</p>}</div>;
        return <div key={key} hidden={!visible} className="workspace-cached-view" data-workspace-view={key}>
          {view.page==="home"&&<><div className="workspace-page-header"><h1>Accueil</h1><button type="button" className="button primary" onClick={()=>navigate({page:"projects"})}><Glyph d={P.folder}/>Ouvrir les projets</button></div><section className="workspace-section"><div className="workspace-section-heading"><h2>À traiter</h2></div><ActionDashboard onOpen={openProject}/></section><details className="workspace-overview-options"><summary>Chiffres des projets</summary><div className="workspace-stat-grid"><button onClick={()=>navigate({page:"projects"})} type="button"><span>Projets en cours</span><strong>{rows.filter(r=>r.status==="active").length}</strong></button><button onClick={()=>{setProjectFilter("review");navigate({page:"projects"});}} type="button"><span>Exigences à vérifier</span><strong>{rows.reduce((n,r)=>n+(r.unconfirmed||0),0)}</strong></button><button onClick={()=>navigate({page:"projects"})} type="button"><span>Heures restantes</span><strong>{Math.round(rows.filter(r=>r.status==="active").reduce((n,r)=>n+r.raf,0))} <small>h</small></strong></button></div></details><section className="workspace-section"><div className="workspace-section-heading"><h2>Projets en cours</h2><button className="workspace-text-button" type="button" onClick={()=>navigate({page:"projects"})}>Tous les projets →</button></div>{portfolio(true)}</section></>}
          {view.page==="projects"&&<><div className="workspace-page-header"><h1>Projets</h1>{canCreateProject&&<button className="button primary" type="button" onClick={()=>navigate({page:"create"})}>＋ Nouveau projet</button>}</div><div className="workspace-toolbar"><input className="input" aria-label="Rechercher un projet" placeholder="Code, titre ou client…" value={projectQuery} onChange={e=>setProjectQuery(e.target.value)}/><select className="input" aria-label="État des projets" value={projectFilter} onChange={e=>setProjectFilter(e.target.value)}><option value="active">Actifs</option><option value="all">Tous</option><option value="closed">Archivés</option><option value="late">En retard</option><option value="review">À examiner</option></select></div>{portfolio()}{filtered.length>0&&<p className="kiara-project-count" role="status">{filtered.length} {filtered.length===1?"projet":"projets"}</p>}</>}
          {view.page==="project"&&<ProjectPanel projectId={view.projectId!} initialTab={view.tab||"pilotage"} row={rows.find(r=>r.id===view.projectId)} reloadRows={reload} back={()=>navigate({page:"projects"})} kiaraPresentation onTabChange={tab=>tab==="import"?navigate({page:"imports"}):openProject(view.projectId!,tab)}/>}
          {view.page==="mail"&&<><div className="workspace-page-header"><h1>Mails</h1></div><MailPanel rows={rows} active={visible} reloadProjects={reload}/></>}
          {view.page==="meetings"&&<GlobalMeetingsView rows={rows} onOpenProject={openProject} active={visible} initialProjectId={visible?route.projectId:view.projectId} creationRequest={requestedCreation} onStudioOpenChange={setStudioOpen} studioNavigation={breadcrumb}/>}
          {view.page==="sources"&&<SourcesLibrary rows={rows} active={visible} onOpenSource={(sourceId,title,evidence)=>setSource({sourceId,title,evidence})} onOpenProject={openProject} onCreateMeeting={createMeeting}/>}
          
          
          {view.page==="knowledge"&&<GlobalKnowledgeView rows={rows} onOpenProject={openProject} active={visible}/>}
          {view.page==="search"&&<SearchView rows={rows} onOpenProject={openProject} active={visible}/>}
          {view.page==="activity"&&<>
            <div className="workspace-page-header"><h1>Activité</h1>
              {document.body.dataset.kiaraDesktop==='true'&&<a className="button secondary" href="/chat#notifications">Notifications</a>}
            </div>
            <section className="workspace-section">
              <div className="workspace-section-heading"><h2>À traiter</h2></div>
              {visible&&<ActionDashboard onOpen={openProject}/>}
            </section>
            <GlobalJobsView rows={rows} onOpenProject={openProject} active={visible} embedded/>
          </>}
          {view.page==="jobs"&&<GlobalJobsView rows={rows} onOpenProject={openProject} active={visible}/>}
          {view.page==="create"&&!canCreateProject&&<ErrorState message="Vous ne disposez pas de l’autorisation de créer un projet."/>}
          {view.page==="create"&&canCreateProject&&<><div className="workspace-page-header"><div><h1>Nouveau projet</h1><p>Créer un projet ou reprendre un dossier technique existant.</p></div><button className="button secondary" onClick={()=>navigate({page:"projects"})}>Retour au portefeuille</button></div><CreatePanel reload={reload} close={()=>navigate({page:"projects"})} onCreated={projectCreated}/></>}
          {view.page==="imports"&&<><div className="workspace-page-header"><div><h1>Connexions & imports</h1><p>Sage, Thunderbird et dossiers réseau.</p></div></div><nav className="workspace-tabs" aria-label="Connexions">{[["sage","Import Sage"],["thunderbird","Thunderbird"],["network","Dossiers réseau"],["archives","Archives JSON"]].map(([id,label])=><button type="button" key={id} aria-pressed={integrationsTab===id} onClick={()=>setIntegrationsTab(id)}>{label}</button>)}</nav><section hidden={integrationsTab!=="archives"} className="card"><h2>Reprendre une archive de projet</h2><p>Importer une sauvegarde JSON dans le portefeuille.</p><button type="button" className="button secondary" disabled={importing} onClick={()=>importFile.current?.click()}><Glyph d={P.download}/>Importer une archive JSON</button><input ref={importFile} type="file" accept="application/json,.json" hidden onChange={e=>{const f=e.target.files?.[0];if(f)void importArchive(f);}}/></section><div hidden={integrationsTab!=="sage"}><SagePanel/></div><div hidden={integrationsTab!=="thunderbird"}><ThunderbirdPanel/></div><div hidden={integrationsTab!=="network"}><EmptyState title="Les dossiers sont associés à chaque projet" detail="Choisissez explicitement un projet pour ouvrir ses Documents et gérer ses liens réseau."/>{rows.map(r=><button className="button secondary" key={r.id} type="button" onClick={()=>openProject(r.id,"documents")}>{r.code} · Documents</button>)}</div></>}
          {["settings","stats","preparation"].includes(view.page)&&<>
            <div hidden={settingsTab!=="stats"}>{settingsTab==="stats"&&<FusionInsights rows={rows} active={visible} initialTab="stats"/>}</div><div hidden={settingsTab!=="preparation"}>{settingsTab==="preparation"&&<FusionInsights rows={rows} active={visible} initialTab="preparation"/>}</div><div hidden={settingsTab!=="ai"}><AiSettingsForm/></div><div hidden={settingsTab!=="mail"}><MailSettingsForm/></div><div hidden={settingsTab!=="memory"}><MemorySettingsForm/></div><div hidden={settingsTab!=="references"}>{referencesStarted&&<ProjectReferenceSettings/>}</div><div hidden={settingsTab!=="deliverables"}>{deliverablesStarted&&<DeliverableSettings active={visible&&settingsTab==="deliverables"} onBusy={setDeliverablesBusy}/>}</div><div hidden={settingsTab!=="documents"}>{documentsStarted&&<DocumentSettings active={visible&&settingsTab==="documents"} onBusy={setDocumentsBusy}/>}</div><div hidden={settingsTab!=="operations"}><OperationsPanel/></div><section hidden={settingsTab!=="appearance"} className="card"><h2>Apparence</h2><div className="workspace-toolbar"><label>Thème<select className="input" value={theme} onChange={e=>setTheme(e.target.value)}><option value="light">Clair</option><option value="dark">Sombre</option></select></label><label>Densité<select className="input" value={density} onChange={e=>setDensity(e.target.value)}><option value="comfortable">Confortable</option><option value="compact">Compacte</option></select></label></div><p>Préférences enregistrées dans ce navigateur.</p></section></>}
        </div>;
      })}
    </main>
    </div></div>
    <dialog ref={commandDialog} className="workspace-command" aria-label="Recherche et navigation" onCancel={()=>setCommandOpen(false)} onClose={()=>setCommandOpen(false)}><div className="workspace-section-heading"><h2>Rechercher dans Kiara</h2><button type="button" className="workspace-icon-button" aria-label="Fermer la recherche" onClick={()=>setCommandOpen(false)}>×</button></div><input ref={commandInput} className="input" aria-label="Recherche globale" placeholder="Projet, rubrique, exigence, tâche…" value={command} onChange={e=>setCommand(e.target.value)}/><div className="workspace-command-results">{commandDestinations.filter(n=>n.label.toLowerCase().includes(command.toLowerCase())).map(n=><button type="button" key={n.page} onClick={()=>selectCommand({page:n.page})}><Glyph d={n.icon}/>{n.label}<small>Rubrique</small></button>)}{rows.filter(r=>`${r.code} ${r.title}`.toLowerCase().includes(command.toLowerCase())).slice(0,8).map(r=><button type="button" key={r.id} onClick={()=>selectCommand({page:"project",projectId:r.id,tab:"pilotage"})}><ProjectFolder code={r.code}/>{r.code} · {r.title}<small>Projet</small></button>)}{searching&&<p role="status">Recherche dans les éléments du projet…</p>}{searchError&&<ErrorState message={searchError}/>} {hits.slice(0,20).map((h,i)=><button type="button" key={`${h.type}:${i}`} onClick={()=>{setCommandOpen(false);openProject(h.project_id,h.tab);}}><Glyph d={P.search}/>{h.label}<small>{h.type}</small></button>)}</div><p className="workspace-muted">Échap pour fermer · la recherche métier respecte le projet affiché.</p></dialog>
    {source&&<SourceInspector sourceId={source.sourceId} title={source.title} evidence={source.evidence} onClose={()=>setSource(null)}/>}
  </div>;
}
