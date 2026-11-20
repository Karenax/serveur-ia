import { agentLocation, agentPath, conversationsHref, projectConversationHref } from '../lib/agentRoutes';
import {DeviceSettingsPanel} from './DeviceSettingsPanel';
import {MeetingPreferences} from './MeetingPreferences';
import {useQueryState} from '../hooks/useQueryState';
import { Suspense, useCallback, useEffect, useRef, useState, type ComponentType, type ReactNode } from "react";
import {retryableLazy} from '../lib/retryableLazy';
import { api, type PortfolioRow, type SearchHit } from "../lib/api";
import { parseWorkspaceRoute, projectTabs, routeKey, workspacePath, type ProjectTab, type WorkspaceRoute } from "../lib/workspaceNavigation";
import { Glyph, P } from "../os/icons";
import { ThunderbirdPanel } from "./ThunderbirdPanel";
import { ActionDashboard } from "./ActionDashboard";
import type {MeetingCreationRequest} from "./WorkspaceViews";
import {SourceInspector} from "./SourceInspector";
import { Badge, EmptyState, ErrorState, LoadingState } from "./Ui";
import { ProjectFolder } from "./ProjectFolder";
import { WorkspaceViewBoundary } from "./WorkspaceViewBoundary";
import { openHelp } from '../../../../client-qwen/help.mjs';
import '../../../../client-qwen/help.css';
import { useWorkspaceWheel } from "../hooks/useWorkspaceWheel";
import { ConnectionStatus } from "./ConnectionStatus";
import { SearchView } from "./SearchView";
import { MeetingCaptureBar } from "./MeetingCaptureBar";

import { NativeCaptureBar } from "./NativeMeetingCapture";
import type {WorkspaceCitation} from "../lib/workspaceApi";
import { withActivity } from "../lib/asyncActivity";
import "../project-kiara-preview.css";
import {MEETING_WORKSPACE_EVENT} from '../lib/meetingWorkspace';
const NotesWorkspace = retryableLazy(
  () => import('./NotesWorkspace').then(module=>({default:module.NotesWorkspace})),
  () => import('./NotesWorkspace?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./NotesWorkspace')).NotesWorkspace})));
const SourcesLibrary = retryableLazy(
  () => import('./SourcesLibrary').then(module=>({default:module.SourcesLibrary})),
  () => import('./SourcesLibrary?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./SourcesLibrary')).SourcesLibrary})));

// These views share one module; reuse the recovered address in later views.
let recoveredWorkspaceViews = false;
const loadWorkspaceViews = ():Promise<typeof import('./WorkspaceViews')> => recoveredWorkspaceViews
  ? import('./WorkspaceViews?kiara-retry=1') as unknown as Promise<typeof import('./WorkspaceViews')>
  : import('./WorkspaceViews');
const retryWorkspaceViews = async ():Promise<typeof import('./WorkspaceViews')> => {
  const module = await import('./WorkspaceViews?kiara-retry=1') as unknown as typeof import('./WorkspaceViews');
  recoveredWorkspaceViews = true;
  return module;
};
const GlobalMeetingsView = retryableLazy(() => loadWorkspaceViews().then(module=>({default:module.GlobalMeetingsView})), () => retryWorkspaceViews().then(module=>({default:module.GlobalMeetingsView})));
const GlobalKnowledgeView = retryableLazy(() => loadWorkspaceViews().then(module=>({default:module.GlobalKnowledgeView})), () => retryWorkspaceViews().then(module=>({default:module.GlobalKnowledgeView})));
const GlobalJobsView = retryableLazy(() => loadWorkspaceViews().then(module=>({default:module.GlobalJobsView})), () => retryWorkspaceViews().then(module=>({default:module.GlobalJobsView})));

const ProjectReferenceSettings = retryableLazy(
  () => import('./ProjectReferenceSettings').then(module=>({default:module.ProjectReferenceSettings})),
  () => import('./ProjectReferenceSettings?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./ProjectReferenceSettings')).ProjectReferenceSettings})));
const DeliverableSettings = retryableLazy(
  () => import('./DeliverableSettings').then(module=>({default:module.DeliverableSettings})),
  () => import('./DeliverableSettings?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./DeliverableSettings')).DeliverableSettings})));
const DocumentSettings = retryableLazy(
  () => import('./DocumentSettings').then(module=>({default:module.DocumentSettings})),
  () => import('./DocumentSettings?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./DocumentSettings')).DocumentSettings})));
let recoveredFusionInsights = false;
const loadFusionInsights = ():Promise<typeof import('./FusionInsights')> => recoveredFusionInsights
  ? import('./FusionInsights?kiara-retry=1') as unknown as Promise<typeof import('./FusionInsights')>
  : import('./FusionInsights');
const retryFusionInsights = async ():Promise<typeof import('./FusionInsights')> => {
  const module = await import('./FusionInsights?kiara-retry=1') as unknown as typeof import('./FusionInsights');
  recoveredFusionInsights = true;
  return module;
};
const FusionInsights = retryableLazy(() => loadFusionInsights().then(module=>({default:module.FusionInsights})), () => retryFusionInsights().then(module=>({default:module.FusionInsights})));

let recoveredSettings = false;
const loadSettings = ():Promise<typeof import('./SettingsForms')> => recoveredSettings
  ? import('./SettingsForms?kiara-retry=1') as unknown as Promise<typeof import('./SettingsForms')>
  : import('./SettingsForms');
const retrySettings = async ():Promise<typeof import('./SettingsForms')> => {
  const module = await import('./SettingsForms?kiara-retry=1') as unknown as typeof import('./SettingsForms');
  recoveredSettings = true;
  return module;
};
const AiSettingsForm = retryableLazy(() => loadSettings().then(module=>({default:module.AiSettingsForm})), () => retrySettings().then(module=>({default:module.AiSettingsForm})));
const MailSettingsForm = retryableLazy(() => loadSettings().then(module=>({default:module.MailSettingsForm})), () => retrySettings().then(module=>({default:module.MailSettingsForm})));
const MemorySettingsForm = retryableLazy(() => loadSettings().then(module=>({default:module.MemorySettingsForm})), () => retrySettings().then(module=>({default:module.MemorySettingsForm})));
const OperationsPanel = retryableLazy(
  () => import('./OperationsPanel').then(module=>({default:module.OperationsPanel})),
  () => import('./OperationsPanel?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./OperationsPanel')).OperationsPanel})));
function DeferredSetting({children}:{children:ReactNode}) {
  return <WorkspaceViewBoundary><Suspense fallback={<LoadingState label="Chargement des réglages"/>}>{children}</Suspense></WorkspaceViewBoundary>;
}

export type ProjectWorkspaceProps = {active?:boolean; projectId:string; initialTab:ProjectTab | "import"; row?:PortfolioRow; reloadRows:()=>Promise<void>; back:()=>void; onTabChange?:(tab:ProjectTab | "import")=>boolean|void; registerCache?:(id:string,canRelease:()=>boolean)=>()=>void;};
export type ProjectCreateProps = {reload:()=>Promise<void> | void;close:()=>void;onCreated?:(id:string)=>Promise<void>};
export type MailPanelProps = {rows?:PortfolioRow[]; active?:boolean; reloadProjects?:()=>Promise<void>};
type Props = {canCreateProject?:boolean; readOnly?:boolean; canManageSharedSettings?:boolean; portfolioLoading?:boolean; portfolioUnavailable?:boolean; rows:PortfolioRow[]; reload:()=>Promise<void>; error?:string; ProjectPanel:ComponentType<ProjectWorkspaceProps>; MailPanel:ComponentType<MailPanelProps>; CreatePanel:ComponentType<ProjectCreateProps>; SagePanel:ComponentType};
const navigation = [
  {page:"home", label:"Accueil", icon:P.grid}, {page:"projects", label:"Projets", icon:P.folder},
  {page:"notes", label:"Notes", icon:P.note},
  {page:"mail", label:"Mails", icon:["M3 5h18v14H3zM3 5l9 7 9-7"]},
  {page:"meetings", label:"Réunions", icon:["M4 10v4M8 5v14M12 8v8M16 3v18M20 9v6"]},
  {page:"activity", label:"Activité", icon:["M3 12h4l3-6 4 12 3-6h4"]},
  {page:"sources", label:"Sources", icon:["M4 3h12l4 4v14H4zM15 3v5h5M8 12h8M8 16h8"]},
  {page:"knowledge", label:"Informations", icon:["M12 5v16M3 3h5l4 2 4-2h5v16h-5l-4 2-4-2H3z"]},
  {page:"jobs", label:"Suivi des analyses", icon:["M9 6h12M9 12h12M9 18h12M3 6h.01M3 12h.01M3 18h.01"]},
] satisfies {page: WorkspaceRoute['page']; label: string; icon: string[]}[];
const commandDestinations = [...navigation, {page:"search" as const, label:"Recherche", icon:P.search}, {page:"preparation" as const,label:"Préparer les réunions",icon:P.sync}];
const pageLabels:Record<string,string> = {...Object.fromEntries(commandDestinations.map(n=>[n.page,n.label])), imports:"Connexions et imports",stats:"Statistiques",preparation:"Réunions et transcription",settings:"Réglages",create:"Nouveau projet",project:"Projet"};
const settingsPages:WorkspaceRoute['page'][] = ["sources","knowledge","jobs","imports"];
const settingsAreaPages:WorkspaceRoute['page'][] = ["settings","stats","preparation","imports"];
function settingsRoute(id:string): WorkspaceRoute {
  return id==="imports" ? {page:"imports"} : {page:"settings",setting:id};
}
const nativeSettingsGroups = [
  {label:"Voix et dictée", items:[["vocal","Conversation vocale"],["dictee","Dictée"]]},
  {label:"Cet appareil", items:[["mises-a-jour","Mises à jour"],["connexion","Connexion au serveur"],["api-locale","API locale et intégrations"]]},
];
const nativeSettings = nativeSettingsGroups.flatMap(group=>group.items);
const settingsGroups = [
  {label:"Mes préférences", items:[["appearance","Apparence et lecture"],["notification-settings","Notifications"],["access","Mon accès"]]},
  ...nativeSettingsGroups,
  {label:"Espace de travail", items:[["ai","Assistant IA"],["mail","Mails et Thunderbird"],["preparation","Réunions et transcription"],["memory","Recherche documentaire"],["imports","Connexions et imports"]]},
  {label:"Projets et administration", items:[["references","Clients et équipe"],["deliverables","Modèles de livrables"],["documents","Modèles de documents"],["operations","Sauvegarde du service Projets"]]},
];
const localSettingHashes:Record<string,string> = {
  access:"#reglages", appearance:"#apparence", "notification-settings":"#reglages-notifications",
  vocal:"#reglages-vocal", dictee:"#reglages-dictee", "mises-a-jour":"#reglages-mises-a-jour",
  connexion:"#reglages-connexion", "api-locale":"#reglages-api-locale",
};
const sparkle = ["m12 3 3 6 6 3-6 3-3 6-3-6-6-3 6-3z"];
const bell = ["M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"];
const helpIcon = ['<circle cx="12" cy="12" r="9"/>', 'M9.1 9a3 3 0 0 1 5.8 1c0 1.5-1.5 2.2-2.2 2.8-.5.4-.7.8-.7 1.2M12 17h.01'];
const settingsIcon = ["M4 6h16M4 12h16M4 18h16",'<circle cx="8" cy="6" r="2" fill="currentColor"/>','<circle cx="16" cy="12" r="2" fill="currentColor"/>','<circle cx="10" cy="18" r="2" fill="currentColor"/>'];
const MAX_CACHED_PROJECTS = 6;
function preference(key:string, fallback:string) { try {return localStorage.getItem(key) || fallback;} catch {return fallback;} }
function savePreference(key:string,value:string) { try {localStorage.setItem(key,value);} catch {/* preference stays in this session */} }
function readWorkspaceRoute(windows:boolean):WorkspaceRoute {
  const route=parseWorkspaceRoute(window.location.pathname,window.location.search);
  return windows&&route.page==="home"?{page:"projects"}:route;
}
function navigationBreakpoints() {
  return typeof window.matchMedia === 'function'
    ? {fusionNarrow:!window.matchMedia('(min-width:671px)').matches, standardNarrow:window.matchMedia('(max-width:850px)').matches}
    : {fusionNarrow:window.innerWidth<=670, standardNarrow:window.innerWidth<=850};
}

export function WorkspaceShell({rows,reload,error,canCreateProject=true,readOnly=false,canManageSharedSettings=!readOnly,portfolioLoading=false,portfolioUnavailable=false,ProjectPanel,MailPanel,CreatePanel,SagePanel}:Props) {
  useEffect(()=>{
    function dismissMenus(event:MouseEvent){
      if(!event.isTrusted)return;
      const path=event.composedPath();
      // Only dropdown disclosures opt in. Inline forms and expandable sections stay open.
      for(const menu of document.querySelectorAll<HTMLDetailsElement>('details[open]:is(.icon-menu-details,[data-dismiss-outside])')){
        if(!path.includes(menu))menu.open=false;
      }
    }
    document.addEventListener('click',dismissMenus,true);
    return()=>document.removeEventListener('click',dismissMenus,true);
  },[]);
  const windows = document.body.dataset.kiaraWindows === "true";
  const [route,setRoute] = useState(()=>readWorkspaceRoute(windows));
  const showProjectPresentation = route.page === "projects" || route.page === "project";
  const [visited,setVisited] = useState<WorkspaceRoute[]>(()=>[route]);
  const routeRef = useRef(route);
  const cacheChecks = useRef(new Map<string,()=>boolean>());
  const cacheOrder = useRef(new Map<string,number>(route.page==='project'&&route.projectId?[[route.projectId,1]]:[]));
  const cacheClock = useRef(1);
  const [cacheGeneration,setCacheGeneration] = useState(0);
  const registerCache = useCallback((id:string,canRelease:()=>boolean)=>{
    cacheChecks.current.set(id,canRelease);setCacheGeneration(value=>value+1);
    return()=>{if(cacheChecks.current.get(id)===canRelease)cacheChecks.current.delete(id);};
  },[]);
  useEffect(()=>{
    if(visited.filter(view=>view.page==='project').length<=MAX_CACHED_PROJECTS)return;
    setVisited(previous=>{
      let excess=previous.filter(view=>view.page==='project').length-MAX_CACHED_PROJECTS;
      if(excess<=0)return previous;
      const candidates=previous.filter(view=>view.page==='project'&&view.projectId&&routeKey(view)!==routeKey(routeRef.current))
        .sort((a,b)=>(cacheOrder.current.get(a.projectId!)||0)-(cacheOrder.current.get(b.projectId!)||0));
      const remove=new Set<string>();
      for(const view of candidates){
        if(excess<=0)break;
        const id=view.projectId!,check=cacheChecks.current.get(id);
        // Unknown views stay mounted. A project opts in only while it can be recreated without losing local state.
        let releasable=false;
        try {releasable=check?.()===true;} catch {/* An uncertain view must remain mounted. */}
        if(releasable){remove.add(routeKey(view));excess--;}
      }
      return remove.size?previous.filter(view=>!remove.has(routeKey(view))):previous;
    });
  },[visited,route,cacheGeneration]);
  useEffect(()=>{
    const retained=new Set(visited.filter(view=>view.page==='project').map(view=>view.projectId));
    if(routeRef.current.page==='project')retained.add(routeRef.current.projectId);
    for(const id of cacheOrder.current.keys())if(!retained.has(id))cacheOrder.current.delete(id);
  },[visited]);
  const [mobileMenu,setMobileMenu] = useState(false);
  const [sidebarCollapsed,setSidebarCollapsed] = useState(()=>preference("fred-sidebar-collapsed","false")==="true");
  const toggleSidebar = useCallback(()=>{
    setSidebarCollapsed(previous=>{
      const next=!previous;
      savePreference("fred-sidebar-collapsed",String(next));
      return next;
    });
  },[]);
  useEffect(()=>{
    const sync=(event:StorageEvent)=>{
      if(event.key==="fred-sidebar-collapsed")setSidebarCollapsed(event.newValue==="true");
    };
    window.addEventListener("storage",sync);
    return()=>window.removeEventListener("storage",sync);
  },[]);
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
  const [themeChoice,setThemeChoice] = useState(()=>preference("fred-theme",preference("agent-ui-theme","light")));
  const [systemDark,setSystemDark] = useState(()=>window.matchMedia?.("(prefers-color-scheme: dark)").matches??false);
  const theme = themeChoice==="dark" || (themeChoice==="system" && systemDark) ? "dark" : "light";
  const [readingFont,setReadingFont] = useState(()=>preference("fred-reading-font","system"));
  const [readingSize,setReadingSize] = useState(()=>preference("fred-reading-size","standard"));
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
  const [integrationsTab,setIntegrationsTab] = useQueryState<string>("connection","sage",agentPath("/app/imports"));
  const settingsTab = route.page==="stats"?"stats":route.page==="preparation"?"preparation":route.page==="imports"?"imports":route.setting??"ai";
  const lastSetting = useRef(settingsTab);
  useEffect(()=>{
    if(settingsAreaPages.includes(route.page))lastSetting.current=settingsTab;
  },[route.page,settingsTab]);
  const [settingsStarted,setSettingsStarted] = useState<Set<string>>(()=>new Set());
  const [referencesStarted,setReferencesStarted] = useState(false);
  const [deliverablesStarted,setDeliverablesStarted] = useState(false);
  const [deliverablesBusy,setDeliverablesBusy] = useState(false);
  const [documentsStarted,setDocumentsStarted] = useState(false);
  const [documentsBusy,setDocumentsBusy] = useState(false);
  const [sharedDocumentsBusy,setSharedDocumentsBusy] = useState(false);
  const [meetingPreferencesBusy,setMeetingPreferencesBusy] = useState(false);
  const [meetingAdministration,setMeetingAdministration] = useState(false);
  const [documentDefaults,setDocumentDefaults] = useState(false);
  useEffect(()=>{if(settingsTab==="documents")setDocumentsStarted(true);},[settingsTab]);
  useEffect(()=>{setSettingsStarted(previous=>{
    if(previous.has(settingsTab))return previous;
    return new Set(previous).add(settingsTab);
  });},[settingsTab]);
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
    routeRef.current=next;
    if(next.page==='project'&&next.projectId)cacheOrder.current.set(next.projectId,++cacheClock.current);
    setRoute(next); setVisited(previous=>{
      const existing=previous.findIndex(r=>routeKey(r)===routeKey(next));
      return existing<0?[...previous,next]:previous.map((r,i)=>i===existing?next:r);
    });setMobileMenu(false);setNotice("");
  },[]);
  const canLeaveCurrentView = useCallback(()=>{
    if(meetingPreferencesBusy){setNotice("Enregistrement des réglages de réunion en cours.");return false;}
    if(documentsBusy||sharedDocumentsBusy){setNotice("Réglages documentaires en cours. Attendre le résultat avant de changer de rubrique.");return false;}
    if(deliverablesBusy){setNotice("Opération sur les livrables en cours. Attendre son résultat avant de changer de rubrique.");return false;}
    const editing=Array.from(document.querySelectorAll('[data-workspace-dirty="true"]')).some(node=>!node.closest('[hidden]'));
    if (editing && !window.confirm("Une modification est en cours. Changer de rubrique en conservant ce brouillon ?")) return false;
    return true;
  },[deliverablesBusy,documentsBusy,sharedDocumentsBusy,meetingPreferencesBusy]);
  const navigate = useCallback((next:WorkspaceRoute)=>{
    if(!canLeaveCurrentView())return false;
    if (window.location.pathname === workspacePath({page:'projects'})) projectListQuery.current = window.location.search;
    const target = workspacePath(next);
    const listQuery = next.page === 'projects' ? projectListQuery.current : '';
    if(target + listQuery !== window.location.pathname + window.location.search) {
      window.history.pushState(null,"",target + listQuery);
    }
    applyRoute(next);
    window.dispatchEvent(new Event('agent:querychange'));
    return true;
  },[applyRoute,canLeaveCurrentView]);
  const guardConversationLink = (event: React.MouseEvent<HTMLAnchorElement>)=>{
    if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
    if(document.querySelector('[data-workspace-dirty="true"]')){
      setNotice("Enregistrez ou fermez la modification en cours avant de revenir à Conversations.");
      event.preventDefault();
    }else if(!canLeaveCurrentView())event.preventDefault();
  };
  const openProject = useCallback((id:string,tab:string="pilotage")=>{
    if (tab==="deliverables") tab="documents";
    if (["tasks", "milestones", "planning"].includes(tab)) tab="planification";
    return navigate({page:"project",projectId:id,tab:projectTabs.includes(tab as ProjectTab)?tab as ProjectTab:"pilotage"});
  },[navigate]);
  const openSettingsTab=(id:string)=>{
    if(navigate(settingsRoute(id))&&window.scrollY>0)window.scrollTo({top:0,behavior:"instant"});
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
    const normalize = (current:WorkspaceRoute) => {
      const path = agentLocation(window.location.pathname);
      const target = new URL(workspacePath(current), window.location.origin);
      if (!path.startsWith("/app")) {
        window.history.replaceState(null,"",target.pathname + target.search);
      } else if (target.pathname !== window.location.pathname &&
          (current.page==="projects" || /^\/app\/(projects|reunions|mails|preparation)(?:\/|$)/.test(path))) {
        const params = new URLSearchParams(window.location.search);
        if(path==="/app/preparation" || path==="/app/preparation/")params.set("settings","preparation");
        const query=params.toString();
        window.history.replaceState(window.history.state,"",target.pathname+(query?"?"+query:"")+window.location.hash);
        window.dispatchEvent(new Event('agent:querychange'));
      }
    };
    normalize(routeRef.current);
    const pop=()=>{
      const current=readWorkspaceRoute(windows);
      normalize(current);
      applyRoute(current);
    };
    window.addEventListener("popstate",pop);return()=>window.removeEventListener("popstate",pop);
  },[applyRoute,windows]);
  useEffect(()=>{
    const previousTheme=document.body.dataset.theme;
    document.body.removeAttribute("data-theme");document.body.classList.add("agent-workspace-body");
    return()=>{document.body.classList.remove("agent-workspace-body");if(previousTheme)document.body.dataset.theme=previousTheme;};
  },[]);
  const changeTheme = (value:string) => {
    savePreference("fred-theme",value);
    savePreference("agent-ui-theme",value);
    setThemeChoice(value);
  };
  useEffect(()=>{
    const query=window.matchMedia?.("(prefers-color-scheme: dark)");
    const apply=(event: MediaQueryListEvent)=>setSystemDark(event.matches);
    query?.addEventListener("change",apply);
    return()=>query?.removeEventListener("change",apply);
  },[]);
  useEffect(()=>{savePreference("agent-ui-density",density);},[density]);
  useEffect(()=>{savePreference("agent-project-favorites",JSON.stringify(favorites));},[favorites]);
  useEffect(()=>{
    const keyboard=(e:KeyboardEvent)=>{
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();navigate({page:"search"});}
      const target=e.target as HTMLElement|null;
      if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="b"&&!["INPUT","TEXTAREA","SELECT"].includes(target?.tagName||"")&&!target?.isContentEditable){e.preventDefault();toggleSidebar();}
      if(e.key==="Escape")setMobileMenu(false);
    };
    window.addEventListener("keydown",keyboard);return()=>window.removeEventListener("keydown",keyboard);
  },[navigate,toggleSidebar]);
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
  const directDeviceSettings = windows && document.body.dataset.kiaraDeviceSettings === 'true';
  const shownSettings = settingsGroups
    .filter(group => group.label !== "Cet appareil" || windows)
    .map(group => ({...group, items:group.items.filter(([id]) =>
      !["access","notification-settings"].includes(id) || Boolean(conversationsPath))}));
  const selectedSetting = shownSettings.flatMap(group=>group.items).find(([id])=>id===settingsTab);
  const settingsTitle = selectedSetting?.[1] ?? "Assistant IA";
  const currentSetting = selectedSetting?.[0] ?? (settingsTab==="stats"?"stats":"ai");
  function localSettingPath(id:string) {
    if (!conversationsPath || !localSettingHashes[id]) return null;
    if (["vocal","dictee","mises-a-jour","connexion","api-locale"].includes(id)) {
      if (!windows) return null;
      if (!directDeviceSettings) return id==="mises-a-jour" ? conversationsPath+"#reglages" : null;
    }
    return conversationsPath+localSettingHashes[id];
  }
  const localHash = localSettingHashes[currentSetting];
  const preferencePath = localSettingPath(currentSetting);
  const devicePanelPath = windows
    ? (document.body.dataset.kiaraInlineSettings==="true"?"/device-settings":null)
    : (document.body.dataset.kiaraWebConversations==="true"?agentPath("/app/device-settings"):null);
  const deviceSection = localHash&&preferencePath&&devicePanelPath&&currentSetting!=="appearance"
    ? (currentSetting==="access"?"acces":localHash.slice("#reglages-".length))
    : undefined;
  const notificationSection = deviceSection === "notifications" && document.body.dataset.kiaraNotificationSettings==="true"
    ? deviceSection : undefined;
  const standaloneSection = windows && document.body.dataset.kiaraNativeSettings==="true" &&
    nativeSettings.some(([id])=>id===deviceSection) ? deviceSection : undefined;
  const nativeDeviceSection = notificationSection || standaloneSection ? undefined : deviceSection;
  const [devicePanelStarted,setDevicePanelStarted] = useState(false);
  const [notificationPanelStarted,setNotificationPanelStarted] = useState(false);
  const [standaloneStarted,setStandaloneStarted] = useState<string[]>([]);
  useEffect(()=>{if(nativeDeviceSection)setDevicePanelStarted(true);},[nativeDeviceSection]);
  useEffect(()=>{if(notificationSection)setNotificationPanelStarted(true);},[notificationSection]);
  useEffect(()=>{
    if(standaloneSection)setStandaloneStarted(previous=>previous.includes(standaloneSection)?previous:[...previous,standaloneSection]);
  },[standaloneSection]);
  const projectAssistantPath = !windows || current ? projectConversationHref(current?.id) : null;
  const importArchive=async(file:File)=>{
    if(importing)return;setImporting(true);setNotice("");
    try{await withActivity("Importation d’une archive de projet…",async()=>{const data=JSON.parse(await file.text());const result:any=await api.importJson(data);await reload();setNotice("Archive importée. Les projets existants sont conservés.");if(result.project_id || result.id)openProject(result.project_id || result.id);});}
    catch(e){setNotice("Import impossible : "+String((e as Error).message));}finally{setImporting(false);if(importFile.current)importFile.current.value="";}
  };
  const filtered=rows.filter(r=>`${r.code} ${r.title} ${r.client_name||""}`.toLowerCase().includes(projectQuery.toLowerCase())&&
    (projectFilter==="all"||projectFilter==="active"&&r.status==="active"||projectFilter==="closed"&&r.status!=="active"||projectFilter==="late"&&r.en_retard>0||projectFilter==="review"&&(r.corrections>0||r.unconfirmed>0)));
  const portfolio=(compact=false)=><div className="workspace-table-wrap"><table className="workspace-portfolio"><thead><tr><th>Projet / client</th><th>État</th><th>Avancement</th>{compact&&<th className="numeric">Reste à faire</th>}<th>Prochaine étape</th><th><span className="sr-only">Favori</span></th></tr></thead><tbody>{(compact?rows.filter(r=>r.status==="active").slice(0,5):filtered).map(r=><tr key={r.id}><td><button type="button" className="workspace-project-link" aria-label={`${r.code} · ${r.title}`} onClick={()=>openProject(r.id)}>{compact&&<ProjectFolder code={r.code}/>}<span>{compact?`${r.code} · ${r.title}`:r.title}</span></button><small>{!compact&&`${r.code} · `}{r.client_name||"Client à renseigner"}</small></td><td>{compact?<Badge value={r.status==="active"?"En cours":"Archivé"} tone={r.status==="active"?"ok":"neutral"}/>:<span className={r.status==="active"?"kiara-project-active":"workspace-muted"}>{r.status==="active"?"En cours":"Archivé"}</span>}</td><td><span className="numeric">{r.taches&&r.taches!=="0/0"&&r.taches!=="0 / 0"?`${Math.round(r.avancement)} %`:"Aucun planning"}</span>{compact&&<div className="workspace-meter"><span style={{width:`${Math.max(0,Math.min(100,r.avancement))}%`}}/></div>}</td>{compact&&<td className="numeric">{r.initial_hours||r.consumed_hours||r.remaining_mode==='reestimated'?`${r.raf} h`:"À estimer"}</td>}<td>{r.jalon_en_cours||"Jalon à définir"}<small>{r.jalon_echeance||"Échéance à préciser"}</small></td><td><button type="button" className="workspace-icon-button" aria-label={`${favorites.includes(r.id)?"Retirer":"Ajouter"} ${r.code} ${favorites.includes(r.id)?"des":"aux"} favoris`} aria-pressed={favorites.includes(r.id)} onClick={()=>favorite(r.id)}><Glyph d="m12 3 2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3l-5.6 2.9 1.1-6.2L3 9.6l6.2-.9z"/></button></td></tr>)}</tbody></table>{!compact&&!filtered.length&&<EmptyState title="Aucun projet dans cette vue" detail="Changez le filtre ou créez un projet."/>}</div>;
  const selectCommand=(next:WorkspaceRoute)=>{setCommandOpen(false);setCommand("");navigate(next);};
  const normalizeCommand=(value:string)=>value.toLocaleLowerCase("fr").normalize("NFD").replace(/[\u0300-\u036f]/g,"").trim();
  const commandTerm = normalizeCommand(command);
  const settingKeywords:Record<string,string> = {vocal:"voix micro parlée",dictee:"micro reconnaissance orale", "notification-settings":"alertes cloche",
    mail:"liaison dossiers synchronisation",appearance:"thème sombre police taille",operations:"archives restauration"};
  const matchingSettings = commandTerm ? shownSettings.flatMap(group=>group.items.map(([id,label])=>({id,label,group:group.label})))
    .filter(({id,label})=>normalizeCommand(label+" "+(settingKeywords[id]??"")).includes(commandTerm)) : [];
  const matchingDestinations = commandDestinations.filter(item => (!windows || item.page !== 'home') && normalizeCommand(item.label).includes(commandTerm));
  const matchingProjects = rows.filter(row => normalizeCommand(row.code+" "+row.title).includes(commandTerm)).slice(0, 8);
  const projectCreated = async (_id:string) => {
    await reload();
    projectListQuery.current = "";
    setProjectQuery("");setProjectFilter("active");
    navigate({page:"projects"});setNotice("Projet ajouté au portefeuille.");
  };

  const studioHere=route.page==='meetings'&&studioOpen;
  const helpTopic = (() => {
    switch (route.page) {
      case 'home': return 'accueil';
      case 'project': return `project-${route.tab ?? 'pilotage'}`;
      case 'meetings': return studioHere ? 'meeting-studio' : 'meetings';
      case 'activity': return route.activity === 'analyses' ? 'jobs' : route.activity ?? 'activity';
      case 'settings': return currentSetting === 'stats' ? 'stats' : `settings-${currentSetting}`;
      case 'preparation': return 'settings-preparation';
      case 'imports': return ['sage', 'thunderbird', 'network', 'archives'].includes(integrationsTab) ? `imports-${integrationsTab}` : 'imports';
      default: return route.page;
    }
  })();
  const portalEntry:WorkspaceRoute={page:windows?"projects":"home"};
  const openPortalEntry=(event: React.MouseEvent<HTMLAnchorElement>)=>{
    if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
    event.preventDefault();
    navigate(portalEntry);
  };
  const breadcrumb=<nav className="workspace-breadcrumb" aria-label="Fil d’Ariane"><a href={workspacePath(portalEntry)} onClick={openPortalEntry}>{windows?"Kiara":"Espace de travail"}</a><Glyph d={P.chevR} size={12}/><span>{route.page==="project"?`${current?.code||"Projet"} · ${current?.client_name||"Client à renseigner"}`:pageLabels[route.page]}</span></nav>;
  return <div ref={shellRef} className={`workspace-shell ${density==="compact"?"workspace-compact":""} ${sidebarCollapsed?"workspace-sidebar-collapsed":""}`} data-workspace-theme={theme} data-kiara-navigation="true" data-sidebar-collapsed={sidebarCollapsed?"true":"false"} data-project-presentation={showProjectPresentation ? "kiara" : undefined} data-fusion-workspace={fusionWorkspace?route.page:undefined} data-meeting-studio={studioHere?'true':undefined}>
    <a className="workspace-skip" href="#workspace-main">Aller au contenu</a>
    {mobileMenu&&<button className="workspace-menu-backdrop" type="button" aria-label="Fermer le menu" onClick={()=>setMobileMenu(false)}/>}
    <aside className={`workspace-sidebar ${mobileMenu?"is-open":""}`} aria-label="Menu principal" aria-hidden={narrow&&!mobileMenu?true:undefined} inert={narrow&&!mobileMenu}>
      <a className="workspace-brand" aria-label={windows?"Kiara · Portefeuille des projets":"Kiara · Accueil"} href={workspacePath(portalEntry)} onClick={openPortalEntry}><span aria-hidden="true">K</span>Kiara</a>
      <nav aria-label="Grandes rubriques">{conversationsPath&&<a href={conversationsPath} aria-label="Conversations" title="Conversations" onClick={guardConversationLink}><Glyph d="M3 4h18v12H8l-5 4V4"/><span>Conversations</span></a>}{navigation.filter(n=>n.page!=="home"&&!settingsPages.includes(n.page)).map(n=><div className="workspace-nav-group" key={n.page}><a href={workspacePath({page:n.page})} aria-label={n.label} title={n.label} aria-current={route.page===n.page||(n.page==="projects"&&route.page==="project")?"page":undefined} className={n.page==="projects"&&route.page==="project"?"workspace-nav-parent-active":undefined} onClick={e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();navigate({page:n.page});}}><Glyph d={n.icon}/><span>{n.label}</span></a>
      </div>)}</nav>
      <div className="workspace-sidebar-foot"><nav><a href={workspacePath(settingsRoute(lastSetting.current))} aria-label="Réglages" title="Réglages" aria-current={settingsAreaPages.includes(route.page)?"page":undefined} className={settingsAreaPages.includes(route.page)?"workspace-nav-parent-active":undefined} onClick={e=>{if(e.ctrlKey||e.metaKey||e.shiftKey||e.altKey)return;e.preventDefault();openSettingsTab(lastSetting.current);}}><Glyph d={settingsIcon}/><span>Réglages</span></a></nav><span className="workspace-local"><i/>{document.body.dataset.kiaraDesktop==='true' ? 'Serveur Kiara' : 'Espace de travail'}</span></div>
    </aside>
    <div className="workspace-body" inert={narrow&&mobileMenu}><header className="workspace-topbar">
      <button ref={mobileToggle} type="button" className="workspace-icon-button workspace-mobile-toggle"
        aria-label={narrow?(mobileMenu?"Fermer le menu":"Ouvrir le menu"):"Afficher ou masquer la navigation"}
        aria-expanded={narrow?mobileMenu:!sidebarCollapsed}
        onClick={()=>narrow?setMobileMenu(v=>!v):toggleSidebar()}>
        <Glyph d={narrow?P.list:["M3 4h18v16H3V4m5 0v16"]}/>
      </button>
      <button type="button" className="workspace-search-trigger" aria-label="Rechercher dans Kiara" title="Rechercher dans les documents · Ctrl K" onClick={()=>navigate({page:"search"})}><Glyph d={P.search}/><span>Rechercher…</span></button>
      <button type="button" className="workspace-icon-button" aria-label="Accès rapide" title="Aller à une rubrique ou un réglage" onClick={()=>setCommandOpen(true)}><Glyph d={P.grid}/></button>
      <ConnectionStatus onOpenJobs={()=>navigate({page:"activity",activity:"analyses"})}/>
      {conversationsPath && (windows || document.body.dataset.kiaraWebConversations==="true") && <a className="workspace-icon-button" href={conversationsPath+"#notifications"} onClick={guardConversationLink} aria-label="Notifications" title="Notifications"><Glyph d={bell}/></a>}
      <button type="button" className="workspace-icon-button" aria-label="Aide" title="Aide sur cette page" aria-haspopup="dialog"
        onClick={event=>void openHelp(event.currentTarget, helpTopic, () => import('../../../../client-qwen/help.html?raw').then(module => module.default))}>
        <Glyph d={helpIcon}/>
      </button>
      {projectAssistantPath && <a className="button secondary workspace-assistant-toggle" aria-label="Assistant de projet" href={projectAssistantPath} onClick={guardConversationLink}><Glyph d={sparkle}/><span>Assistant de projet</span></a>}
    </header>
    <div className="workspace-area"><main id="workspace-main" ref={mainRef} className={settingsAreaPages.includes(route.page)?"workspace-main workspace-settings-layout":"workspace-main"}>
      {route.page!=="mail"&&route.page!=="activity"&&route.page!=="notes"&&!studioHere&&!showProjectPresentation&&breadcrumb}
      {notice&&<div className="workspace-notice" role="status">{notice}</div>}
      <MeetingCaptureBar onOpen={sessionId=>{if(navigate({page:"meetings"}))setRequestedSession(sessionId);}}/>
      <NativeCaptureBar onOpen={sessionId=>{if(navigate({page:"meetings"}))setRequestedSession(sessionId);}}/>
      {error && <div role="alert"><ErrorState message={error} retry={()=>void reload()}/></div>}
      {microphones.map(id=><div className="workspace-notice" role="status" key={id}>● Microphone actif · {rows.find(r=>r.id===id)?.code || "Réunion"} <button type="button" className="workspace-text-button" onClick={()=>{if(openProject(id,"reviews"))window.dispatchEvent(new CustomEvent("agent-show-recording",{detail:{projectId:id}}));}}>Revenir à l’enregistrement</button> <button type="button" className="button secondary" onClick={()=>window.dispatchEvent(new CustomEvent("agent-stop-recording",{detail:{projectId:id}}))}>Arrêter l’enregistrement</button></div>)}
      {settingsAreaPages.includes(route.page)&&<>
        <div className="workspace-page-header"><h1>Réglages</h1></div>
        <nav className="workspace-settings-navigation" aria-label="Réglages">
          {shownSettings.map(group=><div className="workspace-settings-group" key={group.label} role="group" aria-label={group.label}>
            <h2>{group.label}</h2>
            <div className="workspace-tabs">
              {group.items.map(([id,label])=><button type="button" key={id}
                aria-pressed={currentSetting===id}
                disabled={deliverablesBusy||documentsBusy||sharedDocumentsBusy||meetingPreferencesBusy}
                onClick={()=>openSettingsTab(id)}>{label}</button>)}
            </div>
          </div>)}
        </nav>
      </>}
      {visited.map(view=>{
        const visible=routeKey(view)===routeKey(route), key=routeKey(view);
        if ((view.page==='home'||view.page==='projects')&&(portfolioLoading||portfolioUnavailable)) return <div key={key} hidden={!visible} className="workspace-cached-view">{portfolioLoading?<LoadingState label="Chargement des projets"/>:<p>Le portefeuille est indisponible. Les autres rubriques restent accessibles ; utilisez Réessayer pour recharger les projets.</p>}</div>;
        return <div key={key} hidden={!visible} className="workspace-cached-view" data-workspace-view={key}>
          <WorkspaceViewBoundary>
          {view.page==="home"&&<><div className="workspace-page-header"><h1>Accueil</h1><div className="workspace-toolbar"><button type="button" className="button secondary" onClick={()=>navigate({page:"notes"})}><Glyph d={P.note}/>Notes</button><button type="button" className="button primary" onClick={()=>navigate({page:"projects"})}><Glyph d={P.folder}/>Ouvrir les projets</button></div></div><section className="workspace-section"><div className="workspace-section-heading"><h2>À traiter</h2></div><ActionDashboard onOpen={openProject}/></section><details className="workspace-overview-options"><summary>Chiffres des projets</summary><div className="workspace-stat-grid"><button onClick={()=>navigate({page:"projects"})} type="button" aria-label="Voir les projets en cours"><span>Projets en cours</span><strong>{rows.filter(r=>r.status==="active").length}</strong></button><button onClick={()=>{setProjectFilter("review");navigate({page:"projects"});}} type="button" aria-label="Voir les exigences à vérifier"><span>Exigences à vérifier</span><strong>{rows.reduce((n,r)=>n+(r.unconfirmed||0),0)}</strong></button><button onClick={()=>navigate({page:"projects"})} type="button" aria-label="Voir les heures restantes"><span>Heures restantes</span><strong>{Math.round(rows.filter(r=>r.status==="active").reduce((n,r)=>n+r.raf,0))} <small>h</small></strong></button></div></details><section className="workspace-section"><div className="workspace-section-heading"><h2>Projets en cours</h2><button className="workspace-text-button" type="button" onClick={()=>navigate({page:"projects"})}>Tous les projets →</button></div>{portfolio(true)}</section></>}
          {view.page==="projects"&&<><div className="workspace-page-header"><h1>Projets</h1>{canCreateProject&&<button className="button primary" type="button" onClick={()=>navigate({page:"create"})}>＋ Nouveau projet</button>}</div>{!!favorites.length&&<details data-dismiss-outside className="workspace-favorites"><summary>Projets favoris</summary>{favorites.filter(id=>rows.some(r=>r.id===id)).slice(0,8).map(id=>{const r=rows.find(p=>p.id===id)!;return <button key={id} type="button" aria-label={`Ouvrir le projet ${r.code} — ${r.title}`} onClick={()=>openProject(id)}><ProjectFolder code={r.code}/><span>{r.code}<small>{r.title}</small></span></button>;})}</details>}<div className="workspace-toolbar"><input className="input" aria-label="Rechercher un projet" placeholder="Code, titre ou client…" value={projectQuery} onChange={e=>setProjectQuery(e.target.value)}/><select className="input" aria-label="État des projets" value={projectFilter} onChange={e=>setProjectFilter(e.target.value)}><option value="active">Actifs</option><option value="all">Tous</option><option value="closed">Archivés</option><option value="late">En retard</option><option value="review">À examiner</option></select></div>{portfolio()}{filtered.length>0&&<p className="kiara-project-count" role="status">{filtered.length} {filtered.length===1?"projet":"projets"}</p>}</>}
          {view.page==="notes"&&<WorkspaceViewBoundary><Suspense fallback={<LoadingState label="Chargement des notes"/>}><NotesWorkspace active={visible} initialProjectId={view.projectId}
            onReturn={view.projectId?()=>openProject(view.projectId!,view.tab??"documents"):undefined}/></Suspense></WorkspaceViewBoundary>}
          {view.page==="project"&&<><ProjectPanel active={visible} projectId={view.projectId!} initialTab={view.tab||"pilotage"} row={rows.find(r=>r.id===view.projectId)} reloadRows={reload} registerCache={registerCache} back={()=>navigate({page:"projects"})} onTabChange={tab=>tab==="import"?navigate({page:"imports"}):openProject(view.projectId!,tab)}/>{visible&&<nav className="workspace-related-links" aria-label="Ressources du projet">
            <a className="button secondary" href={workspacePath({page:"notes",projectId:view.projectId,tab:view.tab})} onClick={event=>{
              if(event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
              event.preventDefault();navigate({page:"notes",projectId:view.projectId,tab:view.tab});
            }}>Ouvrir le carnet du projet</a>
            {view.tab==="documents"&&<button type="button" className="workspace-text-button" onClick={()=>navigate({page:"search"})}>
              Rechercher dans tous les projets
            </button>}
          </nav>}</>}
          {view.page==="mail"&&<><div className="workspace-page-header"><h1>Mails</h1></div><MailPanel rows={rows} active={visible} reloadProjects={reload}/></>}
          {view.page==="meetings"&&<Suspense fallback={<LoadingState label="Chargement des réunions"/>}><GlobalMeetingsView rows={rows} onOpenProject={openProject} active={visible} initialProjectId={visible?route.projectId:view.projectId} creationRequest={requestedCreation} onStudioOpenChange={setStudioOpen} studioNavigation={breadcrumb}/></Suspense>}
          {view.page==="sources"&&<Suspense fallback={<LoadingState label="Chargement des sources"/>}><SourcesLibrary rows={rows} active={visible} onOpenSource={(sourceId,title,evidence)=>setSource({sourceId,title,evidence})} onOpenProject={openProject} onCreateMeeting={createMeeting}/></Suspense>}


          {view.page==="knowledge"&&<Suspense fallback={<LoadingState label="Chargement des informations"/>}><GlobalKnowledgeView rows={rows} onOpenProject={openProject} active={visible}/></Suspense>}
          {view.page==="search"&&<><SearchView rows={rows} onOpenProject={openProject} active={visible}/><nav className="workspace-related-links" aria-label="Explorer les ressources"><button type="button" className="workspace-text-button" onClick={()=>navigate({page:"sources"})}>Toutes les sources</button><button type="button" className="workspace-text-button" onClick={()=>navigate({page:"knowledge"})}>Toutes les informations</button></nav></>}
          {view.page==="activity"&&<>
            <div className="workspace-page-header"><h1>Activité</h1>
              {!windows&&document.body.dataset.kiaraDesktop==='true'&&<a className="button secondary" href="/chat#notifications">Notifications</a>}
            </div>
            <nav className="workspace-tabs" aria-label="Vues d’activité">
              <button type="button" aria-pressed={!view.activity} onClick={()=>navigate({page:"activity"})}>À traiter</button>
              <button type="button" aria-pressed={view.activity==="analyses"} onClick={()=>navigate({page:"activity",activity:"analyses"})}>Analyses</button>
              <button type="button" aria-pressed={view.activity==="stats"} onClick={()=>navigate({page:"activity",activity:"stats"})}>Statistiques</button>
            </nav>
            {!view.activity&&<section className="workspace-section">
              <div className="workspace-section-heading"><h2>À traiter</h2></div>
              {visible&&<ActionDashboard onOpen={openProject}/>}
            </section>}
            {view.activity==="analyses"&&<WorkspaceViewBoundary><Suspense fallback={<LoadingState label="Chargement des traitements"/>}>
              <GlobalJobsView rows={rows} onOpenProject={openProject} active={visible} embedded/>
            </Suspense></WorkspaceViewBoundary>}
            {view.activity==="stats"&&<DeferredSetting><FusionInsights rows={rows} active={visible} initialTab="stats"/></DeferredSetting>}
          </>}
          {view.page==="create"&&!canCreateProject&&<ErrorState message="Vous ne disposez pas de l’autorisation de créer un projet."/>}
          {view.page==="create"&&canCreateProject&&<><div className="workspace-page-header"><div><h1>Nouveau projet</h1><p>Créer un projet ou reprendre un dossier technique existant.</p></div><button className="button secondary" onClick={()=>navigate({page:"projects"})}>Retour au portefeuille</button></div><CreatePanel reload={reload} close={()=>navigate({page:"projects"})} onCreated={projectCreated}/></>}
          {view.page==="imports"&&<><h2>Connexions et imports</h2><nav className="workspace-tabs" aria-label="Connexions">{[["sage","Import Sage"],["thunderbird","Thunderbird"],["network","Dossiers réseau"],["archives","Archives de projet"]].map(([id,label])=><button type="button" key={id} aria-pressed={integrationsTab===id} onClick={()=>setIntegrationsTab(id)}>{label}</button>)}</nav><section hidden={integrationsTab!=="archives"} className="card"><h2>Reprendre une archive de projet</h2><p>Importer une sauvegarde JSON dans le portefeuille.</p><button type="button" className="button secondary" disabled={importing} onClick={()=>importFile.current?.click()}><Glyph d={P.download}/>Importer une archive JSON</button><input ref={importFile} type="file" accept="application/json,.json" hidden aria-label="Importer une archive JSON" onChange={e=>{const f=e.target.files?.[0];if(f)void importArchive(f);}}/></section><div hidden={integrationsTab!=="sage"}><SagePanel/></div><div hidden={integrationsTab!=="thunderbird"}><button type="button" className="button secondary" onClick={()=>openSettingsTab("mail")}>Ouvrir les réglages Thunderbird</button></div><div hidden={integrationsTab!=="network"}><EmptyState title="Les dossiers sont associés à chaque projet" detail="Choisissez explicitement un projet pour ouvrir ses Documents et gérer ses liens réseau."/>{rows.map(r=><button className="button secondary" key={r.id} type="button" onClick={()=>openProject(r.id,"documents")}>{r.code} · Documents</button>)}</div></>}
          {["settings","stats","preparation"].includes(view.page)&&<>
            {readOnly&&!localHash&&!["stats","preparation","documents"].includes(currentSetting)&&<p role="status" className="workspace-notice">Ces réglages sont en lecture seule pour votre accès.</p>}
            <fieldset className="settings-fields" disabled={readOnly&&!localHash&&!["stats","preparation","documents"].includes(currentSetting)}>
            <div hidden={settingsTab!=="stats"}>{settingsStarted.has("stats")&&<DeferredSetting><FusionInsights rows={rows} active={visible&&settingsTab==="stats"} initialTab="stats"/></DeferredSetting>}</div><div hidden={settingsTab!=="preparation"}>{settingsStarted.has("preparation")&&<>
              <MeetingPreferences active={visible&&settingsTab==="preparation"} onBusy={setMeetingPreferencesBusy}/>
              {canManageSharedSettings&&<details className="progressive-options" onToggle={event=>{if(event.currentTarget.open)setMeetingAdministration(true);}}>
                <summary>Réglages du service de réunion</summary>
                {meetingAdministration&&<DeferredSetting><FusionInsights rows={rows} active={visible&&settingsTab==="preparation"} initialTab="preparation"/></DeferredSetting>}
              </details>}
            </>}</div><div hidden={currentSetting!=="ai"}><h2>Assistant IA</h2>{(settingsStarted.has("ai")||currentSetting==="ai")&&<DeferredSetting><AiSettingsForm/></DeferredSetting>}</div><div hidden={settingsTab!=="mail"}>{settingsStarted.has("mail")&&<DeferredSetting><><h2>Mails et Thunderbird</h2><MailSettingsForm active={visible&&settingsTab==="mail"}/>
              {visible&&settingsTab==="mail"&&<details className="progressive-options"><summary>Installer ou mettre à jour la liaison Thunderbird</summary>
                <ThunderbirdPanel extensionOnly /></details>}</></DeferredSetting>}</div><div hidden={settingsTab!=="memory"}>{settingsStarted.has("memory")&&<DeferredSetting><><h2>Recherche documentaire</h2><MemorySettingsForm active={visible&&settingsTab==="memory"}/></></DeferredSetting>}</div><div hidden={settingsTab!=="references"}>{referencesStarted&&<DeferredSetting><ProjectReferenceSettings/></DeferredSetting>}</div><div hidden={settingsTab!=="deliverables"}>{deliverablesStarted&&<DeferredSetting><DeliverableSettings active={visible&&settingsTab==="deliverables"} onBusy={setDeliverablesBusy}/></DeferredSetting>}</div><div hidden={settingsTab!=="documents"}>{documentsStarted&&<DeferredSetting>
              <DocumentSettings active={visible&&settingsTab==="documents"} onBusy={setDocumentsBusy}/>
              {canManageSharedSettings&&<details className="progressive-options" onToggle={event=>{if(event.currentTarget.open)setDocumentDefaults(true);}}>
                <summary>Critères par défaut de l’espace de travail</summary>
                {documentDefaults&&<DocumentSettings shared active={visible&&settingsTab==="documents"} onBusy={setSharedDocumentsBusy}/>}
              </details>}
            </DeferredSetting>}</div><div hidden={settingsTab!=="operations"}>{settingsStarted.has("operations")&&<DeferredSetting><OperationsPanel/></DeferredSetting>}</div>{currentSetting==="appearance"&&<section className="card">
              <h2>{settingsTitle}</h2>
              <div className="workspace-toolbar">
                <label>Thème<select className="input" value={themeChoice} onChange={event=>changeTheme(event.target.value)}>
                  <option value="light">Clair</option><option value="dark">Sombre</option><option value="system">Comme le système</option>
                </select></label>
                <label>Densité<select className="input" value={density} onChange={event=>setDensity(event.target.value)}>
                  <option value="comfortable">Confortable</option><option value="compact">Compacte</option>
                </select></label>
              </div>
              {conversationsPath&&<fieldset className="appearance-reading">
                <legend>Lecture des conversations</legend>
                <div className="workspace-toolbar">
                  <label>Police<select className="input" value={readingFont} onChange={event=>{
                    setReadingFont(event.target.value);savePreference("fred-reading-font",event.target.value);
                  }}>
                    <option value="system">Segoe UI</option><option value="humanist">Arial</option>
                    <option value="serif">Georgia</option><option value="mono">Consolas</option>
                  </select></label>
                  <label>Taille du texte<select className="input" value={readingSize} onChange={event=>{
                    setReadingSize(event.target.value);savePreference("fred-reading-size",event.target.value);
                  }}>
                    <option value="compact">14 px</option><option value="standard">15 px</option>
                    <option value="large">17 px</option><option value="extra">19 px</option>
                  </select></label>
                </div>
              </fieldset>}
              <p className="workspace-muted">{windows?"Préférences de cet appareil.":"Préférences de ce navigateur."}</p>
            </section>}
            {devicePanelPath&&(devicePanelStarted||nativeDeviceSection)&&
              <DeviceSettingsPanel path={devicePanelPath} section={visible?nativeDeviceSection:undefined} title={nativeDeviceSection?settingsTitle:"Réglages de Kiara"}/>}
            {devicePanelPath&&(notificationPanelStarted||notificationSection)&&
              <DeviceSettingsPanel path={devicePanelPath+"?section=notifications"} section={visible?notificationSection:undefined} title="Notifications"/>}
            {devicePanelPath&&nativeSettings.filter(([id])=>standaloneStarted.includes(id)||id===standaloneSection).map(([id,title])=>
              <DeviceSettingsPanel key={id} path={devicePanelPath+"?section="+encodeURIComponent(id)}
                section={visible&&standaloneSection===id?id:undefined} title={title}/>)}
            {localHash&&currentSetting!=="appearance"&&!deviceSection&&<section className="card">
              <h2>{settingsTitle}</h2>
              {currentSetting==="notification-settings"&&<p>Choisissez les événements à recevoir et la discrétion des alertes pour votre compte.</p>}
              {preferencePath
                ? <a className="button secondary" href={preferencePath} onClick={guardConversationLink}>Ouvrir {settingsTitle.toLocaleLowerCase("fr")}</a>
                : <p>Ouvrez l’application Kiara pour régler cette fonction sur votre appareil.</p>}
            </section>}
            </fieldset></>}
          </WorkspaceViewBoundary>
        </div>;
      })}
    </main>
    </div></div>
    <dialog ref={commandDialog} className="workspace-command" aria-label="Accès rapide" onCancel={()=>setCommandOpen(false)} onClose={()=>setCommandOpen(false)}>
      <div className="workspace-section-heading"><h2>Aller à…</h2><button type="button" className="workspace-icon-button" aria-label="Fermer l’accès rapide" onClick={()=>setCommandOpen(false)}>×</button></div>
      <label className="workspace-command-field">Ouvrir une rubrique, un projet ou un élément
        <input ref={commandInput} className="input" placeholder="Ex. Réunions, code projet, tâche" value={command} onChange={e=>setCommand(e.target.value)}/>
      </label>
      <div className="workspace-command-results">
        {matchingDestinations.length>0&&<section aria-label="Rubriques"><h3>Rubriques</h3>
          {matchingDestinations.map(item=><button type="button" key={item.page} aria-label={`Ouvrir la rubrique ${item.label}`} onClick={()=>selectCommand(item.page==="jobs"?{page:"activity",activity:"analyses"}:{page:item.page})}><Glyph d={item.icon}/>{item.label}</button>)}
        </section>}
        {matchingSettings.length>0&&<section aria-label="Réglages"><h3>Réglages</h3>
          {matchingSettings.map(({id,label,group})=><button key={id} type="button"
            onClick={()=>{setCommandOpen(false);setCommand("");openSettingsTab(id);}}>
            {label}<small>{group}</small></button>)}
        </section>}
        {commandTerm&&!matchingDestinations.length&&!matchingSettings.length&&!matchingProjects.length&&!searching&&!searchError&&!hits.length
          &&<p role="status">Aucun résultat pour cette recherche.</p>}
        {matchingProjects.length>0&&<section aria-label="Projets"><h3>Projets</h3>
          {matchingProjects.map(row=><button type="button" key={row.id} aria-label={`Ouvrir le projet ${row.code} — ${row.title}`} onClick={()=>selectCommand({page:"project",projectId:row.id,tab:"pilotage"})}><ProjectFolder code={row.code}/>{row.code} · {row.title}</button>)}
        </section>}
        {(searching||searchError||hits.length>0)&&<section aria-label="Éléments de projet"><h3>Éléments de projet</h3>
          {searching&&<p role="status">Recherche en cours…</p>}{searchError&&<ErrorState message={searchError}/>}
          {hits.slice(0,20).map((hit,index)=><button type="button" key={`${hit.type}:${index}`} aria-label={`Ouvrir le résultat ${hit.label}`} onClick={()=>{setCommandOpen(false);openProject(hit.project_id,hit.tab);}}><Glyph d={P.search}/>{hit.label}<small>{hit.type}</small></button>)}
        </section>}
      </div>
      <p className="workspace-muted">Échap pour fermer · les éléments sont filtrés selon les accès et le projet affiché.</p>
    </dialog>
    {source&&<SourceInspector sourceId={source.sourceId} title={source.title} evidence={source.evidence} onClose={()=>setSource(null)}/>}
  </div>;
}
