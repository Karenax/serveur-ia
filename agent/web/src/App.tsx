import { agentLocation, agentPath, projectConversationHref } from './lib/agentRoutes';
import { PurchasesPanel, TrackingPanel, BomPanel } from "./components/WorkshopPanels";
import { MemoryRetryButton } from "./components/MemoryRetryButton";
import { AsyncDownloadLink } from './components/AsyncDownloadLink';
import {meetingWorkspaceHref,requestMeetingWorkspace} from './lib/meetingWorkspace';
import { AiSettingsForm, MailSettingsForm, MemorySettingsForm } from "./components/SettingsForms";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api, type BrainAction, type BrainKnowledge, type SageStatus, type BrainLinkState, type CdcItem, type CdcReview, type CdcSource, type ProjectDetail, type CdcJob, type Meeting, type NetworkLink, type PortfolioRow, type SearchHit } from "./lib/api";
import { CdcReviewPanel } from "./components/CdcReviewPanel";
export { CdcReviewPanel } from "./components/CdcReviewPanel";
import { type TriageProgress } from "./lib/mailTriage";
import { useDurableMailTriage } from "./hooks/useDurableMailTriage";
import { useDebouncedValue } from "./hooks/useDebouncedValue";
import { useCdcJobs } from "./hooks/useCdcJobs";
import { CdcJobsPanel } from "./components/CdcJobsPanel";
import { CdcSourceUpload } from "./components/CdcSourceUpload";
import {SourceInspector} from "./components/WorkspaceViews";
import type {WorkspaceCitation} from "./lib/workspaceApi";
import {kindLabel} from "./lib/businessLabels";
import { TransferPanel } from "./components/TransferPanel";
import { ActionDashboard } from "./components/ActionDashboard";
import { OperationsPanel } from "./components/OperationsPanel";
import { MeetingAudioPanel } from "./components/MeetingAudioPanel";
import { ProjectReviewsPanel } from "./components/ProjectReviewsPanel";
import { ProjectDocumentsPanel } from "./components/ProjectDocumentsPanel";
import { ProjectNotesPanel } from "./components/ProjectNotesPanel";
import { MilestonesPanel } from "./components/MilestonesPanel";
import { PlanningMilestonesPanel } from "./components/PlanningMilestonesPanel";
import { PlanningTasksPanel } from "./components/PlanningTasksPanel";
import { PlanningBaselinesPanel } from "./components/PlanningBaselinesPanel";
import { PlanningTemplatesPanel } from "./components/PlanningTemplatesPanel";
import { PlanningHistoryPanel } from "./components/PlanningHistoryPanel";
import { ProjectDeliverablesPanel } from "./components/ProjectDeliverablesPanel";
import type { DeliverableFocus } from "./lib/projectDeliverables";
import { ProjectIdentityPanel } from "./components/ProjectIdentityPanel";
import { ProjectCockpit } from "./components/ProjectCockpit";
import { MailWorkspace } from "./components/MailWorkspace";
import { WorkspaceShell, type ProjectCreateProps, type MailPanelProps } from "./components/WorkspaceShell";
import { mailProjects } from "./lib/mailProjects";
import { ProjectFolder } from "./components/ProjectFolder";
import { parseWorkspaceRoute, projectTabLabels, projectSection, projectSections } from "./lib/workspaceNavigation";
import { Badge, EmptyState, ErrorState, LoadingState } from "./components/Ui";
import "./styles.css";
import "./project-workspace.css";
import "./project-cdc-analysis.css";
import "./cdc-review.css";
import "./minipilot.css";
import "./macos.css";
import "./themes.css";
import "./workspace-shell.css";
import { AppIcon, Glyph, P } from "./os/icons";
import { clearWallpaperImage, loadWallpaperImage, saveWallpaperImage } from "./lib/wallpaper";
import { withActivity } from "./lib/asyncActivity";

// Appliqué avant le premier rendu (évite un flash du thème par défaut),
// l'état React dans Desktop prend ensuite le relais avec les mêmes clés.
try {
  document.body.dataset.theme = localStorage.getItem("mp-theme") || "golden";
  const rawWp = localStorage.getItem("mp-wallpaper");
  if (rawWp) {
    const parsed = JSON.parse(rawWp) as { mode?: unknown; color?: unknown };
    if (parsed.mode === "image" || parsed.mode === "color") {
      document.body.dataset.wallpaper = parsed.mode;
      if (typeof parsed.color === "string") {
        document.body.style.setProperty("--wp-color", parsed.color);
      }
    }
  }
} catch {
  /* premier affichage : défauts */
}

const KINDS = ["function", "constraint", "requirement", "data", "interface", "open_point"];

// Les rubriques métier restent disponibles dans le bureau historique et l'arbre projet.
// Les documents à remettre ont un seul panneau, dans Documents ; Sage reste global.
type TabId =
  | "pilotage" | "cdc" | "planification"
  | "atelier" | "reviews" | "documents" | "import" | "connaissance";
const TABS: { id: TabId; label: string }[] = [
  { id: "pilotage", label: projectTabLabels.pilotage },
  { id: "cdc", label: projectTabLabels.cdc },
  { id: "planification", label: projectTabLabels.planification },
  { id: "atelier", label: projectTabLabels.atelier },
  { id: "reviews", label: projectTabLabels.reviews },
  { id: "documents", label: projectTabLabels.documents },
  { id: "connaissance", label: projectTabLabels.connaissance },
];

export function App() {
  const [rows, setRows] = useState<PortfolioRow[] | null>(null);
  const [error, setError] = useState("");
  const loadGeneration = useRef(0);
  const [canCreateProject, setCanCreateProject] = useState(false);
  useEffect(() => {
    let active = true;
    const refreshPermissions = () => {
      void api.session().then(({operator}) => {
        if (active) setCanCreateProject(operator.role !== 'reader' && operator.project_ids === null);
      }).catch(() => { if (active) setCanCreateProject(false); });
    };
    refreshPermissions();
    window.addEventListener('focus', refreshPermissions);
    return () => { active = false; window.removeEventListener('focus', refreshPermissions); };
  }, []);


  const load = useCallback(async (quiet = false) => {
    const generation=++loadGeneration.current;
    try {
      setError("");
      const result=await (quiet === true ? api.portfolio(true) : api.portfolio());
      if(generation===loadGeneration.current)setRows(result);
    } catch (e: any) {
      if(generation===loadGeneration.current)setError(String(e.message || e));
    }
  }, []);
  useEffect(() => {
    load();
    const refreshVisible = () => {if(!document.hidden)void load(true);};
    const timer = window.setInterval(() => {
      if (/^\/app\/?$|^\/app\/(projects|projets|mail)\/?$/.test(agentLocation(window.location.pathname)))refreshVisible();
    }, 10_000);
    window.addEventListener("focus",refreshVisible);
    document.addEventListener("visibilitychange",refreshVisible);
    return()=>{loadGeneration.current++;window.clearInterval(timer);window.removeEventListener("focus",refreshVisible);document.removeEventListener("visibilitychange",refreshVisible);};
  }, [load]);

  return <WorkspaceShell canCreateProject={canCreateProject} rows={rows ?? []} portfolioLoading={!rows && !error} portfolioUnavailable={!rows && !!error} reload={load} error={error} ProjectPanel={ProjectWindow}
    MailPanel={MailApp} CreatePanel={ScanImport} SagePanel={SagePanel} />;
}

/* ── Détail projet (corps de la fenêtre projet) ─────────────────────── */

export function Detail(props: {
  current: PortfolioRow;
  detail: ProjectDetail | null;
  items: CdcItem[];
  sources: CdcSource[];
  meetings: Meeting[];
  tab: TabId;
  setTab: (t: TabId) => boolean | void;
  cdcTab: "sources" | "revue" | "synthese" | "controles" | "transfert";
  setCdcTab: (t: "sources" | "revue" | "synthese" | "controles" | "transfert") => void;
  analyze: (sourceId: string) => void;
  analyzing: boolean;
  analyzeMsg: string;
  aiStatus: { reachable: boolean; detail: string } | null;
  jobs: CdcJob[]; jobsError: string; cancelJob: (id: string) => void; retryJob: (id: string) => void;
  editing: boolean;
  setEditing: (v: boolean) => void;
  back: () => void;
  refresh: () => Promise<boolean | void> | boolean | void;
  sidebarNavigation?: boolean;
  kiaraPresentation?: boolean;
}) {
  const { current, detail, items, sources, tab, setTab } = props;
  const [kind, setKind] = useState("function");
  const [itemTitle, setItemTitle] = useState("");
  const [projectExport, setProjectExport] = useState<"idle" | "pending" | "failed">("idle");
  const [quote, setQuote] = useState("");
  const [page, setPage] = useState(1);
  const [planTab, setPlanTab] = useState<"planning" | "jalons" | "tasks" | "models" | "baselines" | "history">("jalons");
  const [documentView,setDocumentView]=useState<ProjectDocumentView>('deliverables');
  const [pilotTab,setPilotTab]=useState<'cockpit'|'identity'>('cockpit');
  const [identityVisited,setIdentityVisited]=useState(false);
  const [deliverableFocus,setDeliverableFocus]=useState<DeliverableFocus|null>(null);
  const deliverableFocusSequence=useRef(0);
  const openGateDeliverable=useCallback((focus:Omit<DeliverableFocus,'requestId'>)=>{if(setTab('documents')===false)return;setDeliverableFocus({...focus,requestId:++deliverableFocusSequence.current});setDocumentView('deliverables');},[setTab]);
  const consumeDeliverableFocus=useCallback(()=>setDeliverableFocus(null),[]);
  const [shopTab, setShopTab] = useState<"purchases" | "time" | "bom">("purchases");
  const [review, setReview] = useState<CdcReview | null>(null);
  const [reviewKind, setReviewKind] = useState("all");
  const [reviewStatus, setReviewStatus] = useState("pending");
  const [reviewQuery, setReviewQuery] = useState("");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [visitedTabs, setVisitedTabs] = useState<Set<TabId>>(() => new Set([tab]));
  useEffect(() => { setVisitedTabs(previous => new Set([...previous, tab])); }, [tab]);

  const loadReview = async () => {
    try {
      setReview(await api.cdcReview(current.id));
    } catch {
      setReview(null);
    }
  };
  useEffect(() => {
    loadReview();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [current.id, items.length]);

  const unconfirmed = items.filter((i) => !["confirmed", "rejected", "superseded"].includes(i.knowledge_status || "candidate"));
  const pointsOuverts = items.filter((i) => i.kind === "open_point" && !["rejected", "superseded"].includes(i.knowledge_status || "candidate"));
  const pointsATraiter = [...unconfirmed,...pointsOuverts.filter(point=>!unconfirmed.some(item=>item.id===point.id))];

  const saveProject = async () => {
    if (projectExport === "pending") return;
    setProjectExport("pending");
    try {
      await withActivity("Préparation de la sauvegarde du projet…", async () => {
        const archive = await api.exportProject(current.id);
        const blob = new Blob([JSON.stringify(archive, null, 2)], { type: "application/json" });
        const url = URL.createObjectURL(blob);
        try {
          const link = document.createElement("a");
          link.href = url;
          link.download = `minipilot-${current.code || current.id}.json`;
          link.click();
        } finally {
          URL.revokeObjectURL(url);
        }
      });
      setProjectExport("idle");
    } catch {
      setProjectExport("failed");
    }
  };

  const section = projectSection(tab === "import" ? "pilotage" : tab);
  const tasks = (detail?.tasks || []).filter(task => task.status !== 'done')
    .sort((first, second) => (first.due_date || '9999').localeCompare(second.due_date || '9999')).slice(0, 3);
  const today = new Date().setHours(0, 0, 0, 0);
  const nextMeeting = props.meetings.filter(meeting => Date.parse(meeting.date) >= today)
    .sort((first, second) => Date.parse(first.date) - Date.parse(second.date))[0];

  return (
    <div className="mp-detail">
      {props.kiaraPresentation && <button type="button" className="kiara-project-back" onClick={props.back}>← Tous les projets</button>}
      <div className="mp-breadcrumb compact">
        {props.kiaraPresentation ? <div className="kiara-project-title">
          <h1 tabIndex={-1}>{current.title}</h1>
          <p>{current.code}{current.client_name && ` · ${current.client_name}`}
            <span className={current.status === "active" ? "kiara-project-active" : ""}>{current.status === "active" ? "En cours" : "Archivé"}</span>
          </p>
        </div> : <>
          <ProjectFolder code={current.code}/><Badge value={current.code} tone="info" />
          <h1>{current.title}</h1>
          <span className="mp-client">{current.client_name || "Client à renseigner"}</span>
          <Badge value={current.status === "active" ? "En cours" : "Archivé"} />
        </>}
        <span className="mp-spacer" />
        {props.kiaraPresentation
          ? <button type="button" className="button secondary" onClick={() => setTab('planification')}>Voir le planning</button>
          : <button className="button secondary sm" onClick={props.back} title="Retour aux projets">← Projets</button>}
        <details className="project-options" onClick={event=>{if((event.target as HTMLElement).closest('button'))event.currentTarget.open=false;}}><summary>Options du projet</summary><div className="project-options-menu">
        <button className="button secondary sm" onClick={() => {if(setTab('pilotage')===false)return;setPilotTab('identity');setIdentityVisited(true);}}>Fiche et équipe</button>
        <button
          className="button secondary sm"
          title="Exporter le projet en JSON (sauvegarde manuelle)"
          disabled={projectExport === "pending"}
          onClick={saveProject}
        >
          Sauvegarder le projet
        </button>
        <button className="button secondary sm" onClick={() => props.setEditing(!props.editing)} title="Modifier le projet">
          Modifier le projet
        </button>
        </div></details>
      </div>

      {projectExport === "failed" && (
        <div className="state-panel error">
          <p role="alert">La sauvegarde du projet a échoué.</p>
          <button type="button" className="button secondary" onClick={saveProject}>
            Réessayer la sauvegarde
          </button>
        </div>
      )}

      {props.editing && (
        <EditProject current={current} detail={detail} refresh={props.refresh} close={() => props.setEditing(false)} />
      )}

      {props.kiaraPresentation && <>
        <nav className="kiara-project-tabs" aria-label="Rubriques du projet">
          {projectSections.map(item => <button key={item.slug} type="button"
            aria-current={item.tab === section ? "page" : undefined}
            onClick={() => {
              if (setTab(item.tab) !== false && item.tab === 'pilotage') setPilotTab('cockpit');
            }}>{item.label}</button>)}
        </nav>
        {section === 'planification' && <div className="kiara-project-subnav" role="group" aria-label="Vues de pilotage">
          <button type="button" className="button secondary sm" aria-pressed={tab === 'planification'} onClick={() => setTab('planification')}>Planning</button>
          <button type="button" className="button secondary sm" aria-pressed={tab === 'cdc'} onClick={() => setTab('cdc')}>Cahier des charges</button>
          <button type="button" className="button secondary sm" aria-pressed={tab === 'atelier'} onClick={() => setTab('atelier')}>Atelier</button>
        </div>}
        {section === 'documents' && <div className="kiara-project-subnav" role="group" aria-label="Vues documentaires">
          <button type="button" className="button secondary sm" aria-pressed={tab === 'documents'} onClick={() => setTab('documents')}>Documents du projet</button>
          <button type="button" className="button secondary sm" aria-pressed={tab === 'connaissance'} onClick={() => setTab('connaissance')}>Informations</button>
        </div>}
      </>}

      {!props.kiaraPresentation && !props.sidebarNavigation && <nav className="project-tabs sticky-tabs" aria-label="Sous-modules du projet">
        <div className="project-tabs-track">
          {TABS.map((t) => {
            const count =
              t.id === "planification"
                ? (detail?.tasks || []).filter((x: any) => x.status !== "done").length +
                  (detail?.milestones || []).length
                : t.id === "cdc"
                  ? items.length
                  : t.id === "reviews"
                    ? props.meetings.reduce((s: number, m: any) => s + (m.open_actions || 0), 0)
                    : 0;
            return (
              <button
                key={t.id}
                type="button"
                className={tab === t.id ? "active" : ""}
                aria-current={tab === t.id ? "page" : undefined}
                title={t.label}
                onClick={() => setTab(t.id)}
              >
                {t.label}
                {count > 0 && <span className="tab-badge">{count}</span>}
              </button>
            );
          })}
        </div>
      </nav>}

      {(tab === "pilotage" || visitedTabs.has("pilotage")) && <div hidden={tab !== "pilotage"}>
        {pilotTab==='identity'&&<div className="planning-heading"><h3>Fiche et équipe</h3><button type="button" className="button secondary sm" onClick={()=>setPilotTab('cockpit')}>Retour à la vue d’ensemble</button></div>}
        {props.kiaraPresentation && pilotTab === 'cockpit' && <div className="kiara-project-grid">
          <section><h2>À traiter</h2>
            {tasks.length ? <ul>{tasks.map(task => <li key={task.id}>{task.title}{task.due_date && ` · ${task.due_date}`}</li>)}</ul>
              : <p>Aucune tâche planifiée à traiter.</p>}
          </section>
          <section><h2>Situation</h2><dl>
            <dt>Avancement</dt><dd>{current.taches && !/^0\s*\/\s*0$/.test(current.taches) ? `${Math.round(current.avancement)} %` : 'À planifier'}</dd>
            <dt>Échéance</dt><dd>{current.jalon_echeance || 'À définir'}</dd>
            <dt>Client</dt><dd>{current.client_name || 'À renseigner'}</dd>
          </dl></section>
          <section><h2>Documents</h2>
            <p>{detail?.deliverables?.length ? `${detail.deliverables.length} livrable(s)` : 'Consulter les documents du projet.'}</p>
            <button type="button" className="kiara-project-text-action" onClick={() => setTab('documents')}>Voir les documents</button>
          </section>
          <section><h2>Prochaine réunion</h2>
            <p>{nextMeeting ? `${nextMeeting.title} · ${nextMeeting.date}` : 'Aucune réunion à venir.'}</p>
            <button type="button" className="kiara-project-text-action" onClick={() => setTab('reviews')}>Voir les réunions</button>
          </section>
        </div>}
        <details open={!props.kiaraPresentation} hidden={pilotTab!=='cockpit'} className="kiara-project-cockpit">
        <summary hidden={!props.kiaraPresentation}>Suivi détaillé du projet</summary><ProjectCockpit projectId={current.id} active={tab==='pilotage'&&pilotTab==='cockpit'} revision={detail?.planning_revision} onSaved={props.refresh}
          onOpenDeliverable={openGateDeliverable}
          onOpenPlanning={()=>{if(setTab('planification')===false)return;setPlanTab('jalons');}} onOpenCdc={()=>{if(setTab('cdc')===false)return;props.setCdcTab('revue');}}/></details>
        {(pilotTab==='identity'||identityVisited)&&<div hidden={pilotTab!=='identity'}>{(
        detail == null ? (
          <LoadingState label="Chargement du projet" />
        ) : (
        <table className="data-table compact project-summary">
          <tbody>
            <tr><td>Jalon en cours</td><td><b>{current.jalon_en_cours}</b>{current.jalon_echeance && ` — ${current.jalon_echeance}`}</td></tr>
            <tr><td>Avancement</td><td><b>{current.avancement} %</b></td></tr>
            <tr><td>Heures prévues</td><td>{current.initial_hours} h</td></tr>
            <tr><td>Heures consommées</td><td>{current.consumed_hours} h</td></tr>
            <tr><td>Reste à faire</td><td><b>{current.raf} h</b> — {current.remaining_mode === "reestimated" ? "réestimé" : "solde de charge"}</td></tr>
            <tr><td>Tâches (terminées/total)</td><td><b>{current.taches}</b> — {current.en_retard} en retard</td></tr>
            <tr><td>Actions à corriger</td><td><b>{current.correction_label}</b></td></tr>
            <tr><td>Éléments CDC</td><td><b>{items.length}</b> (dont {pointsOuverts.length} point(s) ouvert(s))</td></tr>
            <tr><td>Heures prévues dans le CDC</td><td><b>{items.filter(i => !["rejected", "superseded"].includes(i.knowledge_status || "candidate")).reduce((s, i) => s + (i.estimated_hours || 0), 0).toFixed(1)} h</b></td></tr>
          </tbody>
        </table>
        )
      )}<ProjectIdentityPanel projectId={current.id} onSaved={props.refresh}/></div>}</div>}

      {(tab === "documents" || visitedTabs.has("documents")) && <div hidden={tab !== "documents"}>{current && (
        <ProjectDocumentViews projectId={current.id} active={tab==='documents'} view={documentView} setView={setDocumentView} onSaved={props.refresh} focus={deliverableFocus} onFocusHandled={consumeDeliverableFocus}/>
      )}</div>}

      {(tab === "planification" || visitedTabs.has("planification")) && <div hidden={tab !== "planification"}>{current && (
        <div>
          <div className="mp-subtabs" role="tablist" aria-label="Planification">
            {(
              [
                ["jalons", `Échéances ${(detail?.milestones || []).length}`],
                ["tasks", `Tâches ${(detail?.tasks || []).filter((x: any) => x.status !== "done").length}`],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={planTab === id}
                className={planTab === id ? "active" : ""}
                onClick={() => setPlanTab(id)}
              >
                {label}
              </button>
            ))}
            <details className="project-options planning-tools" onClick={event=>{if((event.target as HTMLElement).closest('button'))event.currentTarget.open=false;}}><summary>Outils du planning</summary><div className="project-options-menu">
              <button type="button" className="button secondary sm" aria-pressed={planTab==='planning'} onClick={()=>setPlanTab('planning')}>Dates et charge du projet</button>
              <button type="button" className="button secondary sm" aria-pressed={planTab==='models'} onClick={()=>setPlanTab('models')}>Modèles de planning</button>
              <button type="button" className="button secondary sm" aria-pressed={planTab==='baselines'} onClick={()=>setPlanTab('baselines')}>Planning de référence et écarts</button>
              <button type="button" className="button secondary sm" aria-pressed={planTab==='history'} onClick={()=>setPlanTab('history')}>Historique des modifications</button>
              <button type="button" className="button secondary sm" onClick={()=>{if(setTab('documents')===false)return;setDocumentView('deliverables');}}>Documents à remettre</button>
            </div></details>
          </div>
          <div hidden={planTab !== "planning"}>{<PlanningTab projectId={current.id} active={tab === "planification" && planTab === "planning"} />}</div>
          <div hidden={planTab !== "jalons"}>{(
            <PlanningMilestonesPanel projectId={current.id} onSaved={props.refresh} active={tab === "planification" && planTab === "jalons"} onOpenDeliverable={openGateDeliverable} />
          )}</div>
          <div hidden={planTab !== "tasks"}>{(
            <PlanningTasksPanel projectId={current.id} onSaved={props.refresh} active={tab === "planification" && planTab === "tasks"} />
          )}</div>
          <div hidden={planTab !== "baselines"}><PlanningBaselinesPanel projectId={current.id} onSaved={props.refresh} active={tab === "planification" && planTab === "baselines"}/></div>
          <div hidden={planTab !== "history"}><PlanningHistoryPanel projectId={current.id} active={tab === "planification" && planTab === "history"}/></div>
          <div hidden={planTab !== "models"}><PlanningTemplatesPanel projectId={current.id} onSaved={props.refresh} active={tab === "planification" && planTab === "models"}/></div>
        </div>
      )}</div>}

      {(tab === "cdc" || visitedTabs.has("cdc")) && <div hidden={tab !== "cdc"}>{(
        <div className="cdc-matrix">
          <div className="mp-subtabs">
            {(
              [
                ["sources", `Documents client ${sources.length}`],
                ["revue", `À vérifier ${review ? `${review.reviewed}/${review.total}` : items.length}`],
                ["synthese", `Exigences ${items.length}`],
                ["controles", `Points à traiter ${pointsATraiter.length}`],
                ["transfert", "Transfert BE"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                className={props.cdcTab === id ? "active" : ""}
                onClick={() => props.setCdcTab(id)}
              >
                {label}
              </button>
            ))}
            <span className="mp-spacer" />
            <button className="button primary" onClick={() => props.setCdcTab("transfert")}>
              Générer le transfert BE
            </button>
          </div>

          <div hidden={props.cdcTab !== "sources"}>{(
            <div>
              <div className="mp-doc-head">
                <span>{sources.length} document(s)</span>
                <span className="mp-spacer" />
                <CdcSourceUpload projectId={current.id} sources={sources} onRefresh={props.refresh} />
              </div>
              <table className="data-table compact">
                <thead><tr><th>RÉF.</th><th>DOCUMENT</th><th>RÉVISION</th><th>ÉTAT</th><th>PAGES</th><th>TAILLE</th><th></th></tr></thead>
                <tbody>
                  {sources.map((s) => (
                    <tr key={s.id}>
                      <td>{s.ref}</td>
                      <td><b>{s.filename}</b></td>
                      <td>{s.revision}</td>
                      <td><Badge value={s.status} tone={s.status === "PRÊTE" ? "info" : "warning"} /></td>
                      <td>{s.pages}</td>
                      <td>{s.size}</td>
                      <td>
                        <button
                          className="button primary"
                          disabled={s.analyzable === false || props.analyzing}
                          title={
                            s.analyzable === false
                              ? s.hint || "Ré-importe le CDC"
                              : "Extraire fonctions et contraintes (IA)"
                          }
                          onClick={() => props.analyze(s.id)}
                        >
                          {props.analyzing ? "Analyse…" : "Analyser"}
                        </button>
                        {s.hint && <div><small>{s.hint}</small></div>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <CdcJobsPanel jobs={props.jobs} error={props.jobsError} onCancel={props.cancelJob} onRetry={props.retryJob} />
              {props.aiStatus && !props.aiStatus.reachable && (
                <p><small>Aucun serveur IA joignable ({props.aiStatus.detail}) — configure l'IA dans Réglages.</small></p>
              )}
            </div>
          )}</div>

          <div hidden={props.cdcTab !== "revue"}>{(
            <CdcReviewPanel
              projectId={current.id}
              items={items}
              review={review}
              reviewKind={reviewKind}
              setReviewKind={setReviewKind}
              reviewStatus={reviewStatus}
              setReviewStatus={setReviewStatus}
              reviewQuery={reviewQuery}
              setReviewQuery={setReviewQuery}
              selected={selected}
              setSelected={setSelected}
              refresh={props.refresh}
              reloadReview={loadReview}
            />
          )}</div>

          <div hidden={props.cdcTab !== "synthese"}>{(
            <div>
              <div className="inline-form">
                <div className="xp-select" aria-label="Type d'élément">
                  {KINDS.map((k) => (
                    <button key={k} type="button" aria-selected={k === kind} className={k === kind ? "selected" : ""} onClick={() => setKind(k)}>
                      {kindLabel(k)}
                    </button>
                  ))}
                </div>
              </div>
              <div className="inline-form">
                <label className="ux-field">Titre de l’exigence<input className="input" placeholder="Titre" value={itemTitle} onChange={(e) => setItemTitle(e.target.value)} style={{ width: 200 }} /></label>
                <label className="ux-field">Citation du CDC<input className="input" placeholder="Citation exacte du CDC" value={quote} onChange={(e) => setQuote(e.target.value)} style={{ width: 280 }} /></label>
                <label className="ux-field">Page<input className="input" type="number" aria-label="Page du CDC" min={1} value={page} onChange={(e) => setPage(parseInt(e.target.value || "1"))} style={{ width: 70 }} /></label>
                <button
                  className="button primary"
                  onClick={async () => {
                    if (!itemTitle.trim() || !quote.trim()) {
                      alert("Titre + citation exacte requis (règle XPilot)");
                      return;
                    }
                    try {
                      await api.addCdcItem(current.id, { kind, title: itemTitle.trim(), source_quote: quote.trim(), physical_page: page });
                      setItemTitle("");
                      setQuote("");
                      props.refresh();
                    } catch (err: any) {
                      alert(String(err.message || err));
                    }
                  }}
                >
                  + Élément
                </button>
              </div>
              <table className="data-table compact">
                <thead><tr><th>Type</th><th>Titre</th><th>Citation</th><th>Page</th></tr></thead>
                <tbody>
                  {items.map((i) => (
                    <tr key={i.id}>
                      <td><Badge value={i.kind} tone={i.kind === "constraint" ? "warning" : i.kind === "function" ? "info" : "neutral"} /></td>
                      <td>{i.title}</td><td>{i.source_quote}</td><td>{i.physical_page}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}</div>

          <div hidden={props.cdcTab !== "controles"}><CdcActionList items={pointsATraiter} onOpen={item=>{setReviewKind('all');setReviewStatus('all');setReviewQuery(item.id);props.setCdcTab('revue');}}/></div>

          <div hidden={props.cdcTab !== "transfert"}><TransferPanel key={current.id} projectId={current.id} /></div>

        </div>
      )}</div>}

      {(tab === "reviews" || visitedTabs.has("reviews")) && <div hidden={tab !== "reviews"}>{current && (
        <ReviewsPanel key={current.id} projectId={current.id} active={tab === "reviews"} meetings={props.meetings} refresh={props.refresh} onOpenDocument={(id,title)=>{openGateDeliverable({deliverableId:id,checkId:'',milestoneId:'',milestoneTitle:`Revue · ${title}`,version:null,origin:'review'});}} />
      )}</div>}

      {(tab === "atelier" || visitedTabs.has("atelier")) && <div hidden={tab !== "atelier"}>{current && (
        <div>
          <div className="mp-subtabs" role="tablist" aria-label="Atelier">
            {(
              [
                ["purchases", "Achats"],
                ["time", "Pointage"],
                ["bom", "Nomenclature"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={shopTab === id}
                className={shopTab === id ? "active" : ""}
                onClick={() => setShopTab(id)}
              >
                {label}
              </button>
            ))}
          </div>
          <div hidden={shopTab !== "purchases"}>{<PurchasesPanel projectId={current.id} />}</div>
          <div hidden={shopTab !== "time"}>{<TrackingPanel projectId={current.id} />}</div>
          <div hidden={shopTab !== "bom"}><BomPanel key={current.id} projectId={current.id} /></div>
        </div>
      )}</div>}

      {(tab === "import" || visitedTabs.has("import")) && <div hidden={tab !== "import"}>{(
        <SagePanel />
      )}</div>}

      {(tab === "connaissance" || visitedTabs.has("connaissance")) && <div hidden={tab !== "connaissance"}>{current && (
        <BrainPanel projectId={current.id} />
      )}</div>}

      {!TABS.some((t) => t.id === tab) && (
        <EmptyState title="Onglet inconnu" detail="Reviens au pilotage ou recharge le projet." />
      )}
    </div>
  );
}

function EditProject(props: { current: PortfolioRow; detail: ProjectDetail | null; refresh: () => void; close: () => void }) {
  const [code, setCode] = useState(props.current.code);
  const [title, setTitle] = useState(props.current.title);
  const [remaining, setRemaining] = useState(props.detail?.remaining_hours == null ? "" : String(props.detail.remaining_hours));
  return (
    <div className="card mp-create">
      <input className="input" aria-label="Code" value={code} onChange={(e) => setCode(e.target.value)} style={{ width: 200 }} />
      <input className="input" aria-label="Titre" value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: 280 }} />
      <label>Reste à faire réestimé (h)<input className="input" aria-label="Reste à faire réestimé" type="number" min={0} step="0.1" value={remaining} onChange={e => setRemaining(e.target.value)} placeholder="Solde calculé" /></label>
      <button
        className="button primary"
        onClick={async () => {
          await api.patchProject(props.current.id, { code, title, remaining_hours: remaining === "" ? null : Number(remaining) });
          props.close();
          props.refresh();
        }}
      >
        Enregistrer
      </button>
    </div>
  );
}

/* Panneau "Fichiers liés au projet" repris de XPilot (ProjectLinksPanel, sans signatures) */
function SettingsApp(props: {
  theme: string;
  onTheme: (t: string) => void;
  wallpaper: Wallpaper;
  onWallpaper: (w: Wallpaper) => void;
  customColors: CustomColors;
  onCustomColors: (c: CustomColors) => void;
}) {
  const [status, setStatus] = useState<any>(null);
  const [wpMsg, setWpMsg] = useState("");
  useEffect(() => { api.brainStatus().then(setStatus).catch(() => setStatus({ reachable: false })); }, []);

  const onWallpaperFile = async (f: File | undefined) => {
    if (!f) return;
    if (!f.type.startsWith("image/")) {
      setWpMsg("Choisis un fichier image (PNG, JPEG… ).");
      return;
    }
    if (f.size > 4_000_000) {
      setWpMsg("Image trop lourde (> 4 Mo) : réduis-la, sinon elle ne sera pas mémorisée.");
      return;
    }
    try {
      await withActivity("Enregistrement du fond d’écran…", async () => {
        const dataUrl = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader();
          reader.onload = () => resolve(String(reader.result));
          reader.onerror = () => reject(reader.error);
          reader.readAsDataURL(f);
        });
        await saveWallpaperImage(dataUrl);
        props.onWallpaper({ ...props.wallpaper, mode: "image" });
        setWpMsg("Fond d'écran enregistré dans ce navigateur.");
      });
    } catch {
      setWpMsg("Lecture impossible : réessaie avec un autre fichier.");
    }
  };

  const resetAppearance = async () => {
    await withActivity("Réinitialisation de l’apparence…", async () => {
      await clearWallpaperImage();
      props.onWallpaper({ mode: "auto", color: "#1d3a7a" });
      props.onTheme("golden");
      props.onCustomColors({ primary: null, accent: null, danger: null });
      setWpMsg("Apparence réinitialisée.");
    });
  };

  return (
    <div>
      <p><small>Serveur Agent : {status?.url || "…"} — cœur de connaissance {status?.reachable ? "joignable" : "injoignable"}.</small></p>
      <h4>Intelligence artificielle</h4>
      <AiSettingsForm />
      <hr />
      <h4>E-mails</h4>
      <MailSettingsForm />
      <hr />
      <h4>Mémoire</h4>
      <MemorySettingsForm />
      <hr />
      <h4>Apparence</h4>
      <p><small>Thème de couleur et fond d'écran du bureau, mémorisés dans ce navigateur.</small></p>
      <div className="inline-form">
        {THEMES.map((t) => (
          <button
            key={t.id}
            type="button"
            className="button secondary"
            aria-pressed={props.theme === t.id}
            title={t.dark ? "Thème sombre" : "Thème clair"}
            onClick={() => props.onTheme(t.id)}
            style={{ gap: 8 }}
          >
            <span
              aria-hidden="true"
              style={{
                display: "inline-block", width: 22, height: 22,
                borderRadius: 6, background: t.swatch,
                border: props.theme === t.id ? "2px solid currentColor" : "1px solid rgba(0,0,0,.2)",
              }}
            />
            {t.label}{props.theme === t.id ? " ✓" : ""}
          </button>
        ))}
      </div>
      <div className="inline-form">
        <label>Fond d'écran{" "}
          <select
            className="input"
            value={props.wallpaper.mode}
            onChange={(e) => props.onWallpaper({ ...props.wallpaper, mode: e.target.value as WallpaperMode })}
          >
            <option value="auto">Automatique (suit le thème)</option>
            <option value="image">Image personnelle</option>
            <option value="color">Couleur unie</option>
          </select>
        </label>
        {props.wallpaper.mode === "image" && (
          <label className="button secondary" style={{ cursor: "pointer" }}>
            Choisir une image…
            <input
              type="file"
              accept="image/*"
              hidden
              onChange={(e) => { void onWallpaperFile(e.target.files?.[0]); e.target.value = ""; }}
            />
          </label>
        )}
        {props.wallpaper.mode === "color" && (
          <input
            type="color"
            aria-label="Couleur du fond d'écran"
            value={props.wallpaper.color}
            onChange={(e) => props.onWallpaper({ ...props.wallpaper, color: e.target.value })}
          />
        )}
        <button className="button secondary" onClick={() => { void resetAppearance(); }}>
          Réinitialiser
        </button>
      </div>
      {wpMsg && <p><small>{wpMsg}</small></p>}
      <p><small>Boutons, accents et danger (vide = couleurs du thème) :</small></p>
      <div className="inline-form">
        {COLOR_PRESETS.map((p) => {
          const active = props.customColors.primary === p.primary
            && props.customColors.accent === p.accent
            && props.customColors.danger === p.danger;
          return (
            <button
              key={p.label}
              type="button"
              className="button secondary"
              aria-pressed={active}
              title={`${p.label} — boutons ${p.primary}, accents ${p.accent}, danger ${p.danger}`}
              onClick={() => props.onCustomColors({ primary: p.primary, accent: p.accent, danger: p.danger })}
              style={{ gap: 8 }}
            >
              <span
                aria-hidden="true"
                style={{
                  display: "inline-block", width: 22, height: 22,
                  borderRadius: 6,
                  background: `linear-gradient(135deg, ${p.primary} 0 33%, ${p.accent} 33% 66%, ${p.danger} 66% 100%)`,
                  border: active ? "2px solid currentColor" : "1px solid rgba(0,0,0,.2)",
                }}
              />
              {p.label}{active ? " ✓" : ""}
            </button>
          );
        })}
      </div>
      <div className="inline-form">
        <label>Boutons{" "}
          <input
            type="color"
            aria-label="Couleur des boutons principaux"
            value={props.customColors.primary ?? "#e30613"}
            onChange={(e) => props.onCustomColors({ ...props.customColors, primary: e.target.value })}
          />
        </label>
        <label>Accents{" "}
          <input
            type="color"
            aria-label="Couleur des accents"
            value={props.customColors.accent ?? "#438ed8"}
            onChange={(e) => props.onCustomColors({ ...props.customColors, accent: e.target.value })}
          />
        </label>
        <label>Danger{" "}
          <input
            type="color"
            aria-label="Couleur des états danger"
            value={props.customColors.danger ?? "#b7131d"}
            onChange={(e) => props.onCustomColors({ ...props.customColors, danger: e.target.value })}
          />
        </label>
        {(props.customColors.primary || props.customColors.accent || props.customColors.danger) && (
          <button
            className="button secondary"
            onClick={() => props.onCustomColors({ primary: null, accent: null, danger: null })}
          >
            Couleurs du thème
          </button>
        )}
      </div>
      <hr />
      <h4>Interface</h4>
      <p><small>Les autres préférences d'affichage (dock, épingles, taille de police) sont stockées dans ce navigateur et se règlent via le menu Affichage et le clic droit sur les icônes.</small></p>
      <OperationsPanel />
    </div>
  );
}

type TriageEntry = {
  proposal_id: string;
  source_id: string;
  sender: string;
  subject: string;
  received_at: string | null;
  excerpt: string;
  target_project_id: string | null;
  target_code: string | null;
  target_name: string | null;
  confidence: number;
  reason: string;
};

export function MailApp({rows, active = true, reloadProjects}: MailPanelProps = {}) {
  const [queueOffset, setQueueOffset] = useState(0);
  const [queueHasNext, setQueueHasNext] = useState(false);
  const [queueTotal, setQueueTotal] = useState(0);
  const [sort, setSort] = useState("newest");
  const loadGeneration = useRef(0);
  const [stats, setStats] = useState<{ pending_sources: number; queued: number;
    divers_project_id: string; divers_count: number } | null>(null);
  const [queue, setQueue] = useState<TriageEntry[]>([]);
  const [projects, setProjects] = useState<{ id: string; code: string; name: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [portfolioNotice,setPortfolioNotice]=useState("");
  const [mailAccess,setMailAccess]=useState<{scoped:boolean;readOnly:boolean}>({scoped:false,readOnly:false});
  const [mailAccessReady,setMailAccessReady]=useState(false);
  const [msg, setMsg] = useState("");
  const [triaging, setTriaging] = useState(false);
  const [triageProgress, setTriageProgress] = useState<TriageProgress | null>(null);
  const [busy, setBusy] = useState("");
  const [query, setQuery] = useState("");
  const searchQuery = useDebouncedValue(query);
  const [portfolio, setPortfolio] = useState<PortfolioRow[]>([]);
  const [thumbLinks, setThumbLinks] = useState<Record<string, { brainId: string | null; brainCode: string | null; linked: boolean }>>({});
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [dragOver, setDragOver] = useState<string | null>(null);
  const [dropping, setDropping] = useState(false);
  const [autoInfo, setAutoInfo] = useState("");
  const classificationLock = useRef(false);
  const decidedSources = useRef(new Set<string>());
  const hasLoaded = useRef(false);
  const wasActive = useRef(active);

  const load = useCallback(async () => {
    const generation = ++loadGeneration.current;
    try {
      setError("");setPortfolioNotice("");
      const session=await api.session();
      const scoped=Array.isArray(session.operator.project_ids);
      const readOnly=session.operator.role==='reader';
      const [st, q, pr, pf, au] = await Promise.all([
        scoped?Promise.resolve(null):api.brainTriageStats(), scoped&&readOnly?Promise.resolve({rows:[],total:0,has_next:false,offset:0,limit:200}):api.pendingMailPage(queueOffset, searchQuery, sort), api.brainProjects(),
        api.portfolio().catch((cause:unknown)=>{if(generation===loadGeneration.current)setPortfolioNotice(`Actualisation impossible pour le portefeuille : ${cause instanceof Error?cause.message:'Réessayez ultérieurement'}. Les mails restent disponibles avec les projets déjà connus.`);return rows||[];}), scoped?Promise.resolve(null):api.brainAutoStatus().catch(() => null),
      ]);
      if (generation !== loadGeneration.current) return;
      setMailAccess({scoped,readOnly});
      setMailAccessReady(true);
      if (!q.rows.length && queueOffset > 0) {
        setQueueOffset(q.total ? Math.floor((q.total-1)/200)*200 : 0);
        return;
      }
      setStats(st);
      const visible = q.rows.filter(entry=>!decidedSources.current.has(entry.source_id));
      setQueue(visible); setQueueHasNext(q.has_next); setQueueTotal(Math.max(0,q.total-(q.rows.length-visible.length)));
      setProjects(pr);
      setPortfolio(pf);
      if (au) {
        const when = au.last_run_at ? ` — dernier passage ${String(au.last_run_at).slice(0, 16).replace("T", " ")}` : " — pas encore passé";
        const what = au.last_result
          ? ` (${au.last_result.triage?.triaged ?? 0} classé(s))` : "";
        setAutoInfo(au.source==="thunderbird"?"Source Thunderbird · synchronisation via la liaison locale.":au.enabled
          ? `Scan auto toutes les ${au.interval_minutes} min : actif${when}${what}.`
          : "Scan auto coupé (Réglages → E-mails).");
      }
      // Résout chaque projet ouvert vers son projet Brain (lien ou même code).
      const byCode: Record<string, string[]> = {};
      for (const b of pr as { id: string; code: string }[]) {
        const code=(b.code || "").trim().toUpperCase();
        (byCode[code] ||= []).push(b.id);
      }
      const entries = (pf as PortfolioRow[]).map(r => {
        const matches = r.code.trim() ? byCode[r.code.trim().toUpperCase()] || [] : [];
        const match = matches.length===1 ? matches[0] : undefined;
        return [r.id, {brainId: r.brain_project_id || match || null,
          brainCode: r.brain_code || (match ? r.code : null), linked: !!r.brain_project_id}];
      });
      setThumbLinks(Object.fromEntries(entries));
      hasLoaded.current = true;
    } catch (e: any) {
      if (generation === loadGeneration.current) setError(String(e.message || e));
    } finally {
      if (generation === loadGeneration.current) setLoading(false);
    }
  }, [queueOffset, searchQuery, sort, rows]);
  useEffect(() => {
    load();
    return () => {loadGeneration.current++;};
  }, [load]);
  useEffect(()=>{if(active && !wasActive.current)void load();wasActive.current=active;}, [active, load]);

  const resolveTarget = async (target: string) => {
    const miniId = target.startsWith("erp:") ? target.slice(4)
      : portfolio.find(p=>thumbLinks[p.id]?.brainId===target && !thumbLinks[p.id].linked)?.id;
    if (!miniId) return target;
    const link = await api.ensureBrainLink(miniId);
    if (!link.brain_project_id) throw new Error("Le projet cible n’a pas pu être relié.");
    setThumbLinks(previous=>({...previous,[miniId]:{brainId:link.brain_project_id!,brainCode:link.brain_code || null,linked:true}}));
    setPortfolio(previous=>previous.map(project=>project.id===miniId?{...project,brain_project_id:link.brain_project_id!,brain_code:link.brain_code || null}:project));
    return link.brain_project_id;
  };
  const createMailProject = async (code:string,title:string) => {
    const created = await api.createProject(code,title) as {id:string;code:string;title:string;status:string};
    loadGeneration.current++;
    setPortfolio(previous=>[{...created,brain_project_id:null,brain_code:null,client_name:"",raf:0,avancement:0} as PortfolioRow,...previous.filter(p=>p.id!==created.id)]);
    await load();
    if(reloadProjects)await reloadProjects().catch(error=>setError(String(error.message || error)));
    return `erp:${created.id}`;
  };
  const removeDecided = (entries: TriageEntry[]) => {
    const ids = new Set(entries.map(entry=>entry.source_id));
    const newlyDecided = [...ids].filter(id=>!decidedSources.current.has(id));
    newlyDecided.forEach(id=>decidedSources.current.add(id));
    loadGeneration.current++;
    setQueue(previous=>previous.filter(entry=>!ids.has(entry.source_id)));
    setQueueTotal(previous=>Math.max(0,previous-newlyDecided.length));
    setStats(previous=>previous ? {...previous,pending_sources:Math.max(0,previous.pending_sources-newlyDecided.length),queued:Math.max(0,previous.queued-newlyDecided.length)} : previous);
    setSelected(previous=>new Set([...previous].filter(id=>!entries.some(entry=>entry.proposal_id===id))));
  };

  const durableTriage = useDurableMailTriage({enabled:mailAccessReady&&!mailAccess.scoped&&!mailAccess.readOnly,onProgress: setTriageProgress,
    onRunning: setTriaging, onMessage: setMsg, onSettled: load});
  const runTriage = async (force: boolean) => {
    if (force && !window.confirm(
      "Ré-analyser TOUS les mails à classer, y compris ceux ayant déjà une proposition ? Les propositions de classement en attente seront remplacées.")) return;
    await durableTriage.start(force);
  };

  const decide = async (entry: TriageEntry, projectId: string | null) => {
    if(classificationLock.current) return;
    classificationLock.current = true;
    setBusy(entry.proposal_id);
    try {
      if (projectId) {
        await api.brainTriageAssign(entry.proposal_id, await resolveTarget(projectId));
      } else {
        await api.brainTriageAccept(entry.proposal_id);
      }
      removeDecided([entry]);
      setMsg("1 mail classé.");
    } catch (e: any) {
      setMsg(String(e.message || e));
    } finally {
      classificationLock.current = false;
      setBusy("");
      void load();
    }
  };

  const reject = async (entry: TriageEntry) => {
    await api.brainTriageReject(entry.proposal_id);
    removeDecided([entry]);
  };

  const filtered = queue;

  const toggleSelect = (proposalId: string) => {
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(proposalId)) n.delete(proposalId);
      else n.add(proposalId);
      return n;
    });
  };
  const selectAllFiltered = () => {
    setSelected((s) => {
      const all = filtered.every((e) => s.has(e.proposal_id));
      if (all) return new Set();
      return new Set(filtered.map((e) => e.proposal_id));
    });
  };

  const lastDrag = useRef<string[]>([]);

  const onDragStart = (e: React.DragEvent, entry: TriageEntry) => {
    // Glisser une ligne non cochée = ne déplacer qu'elle (comportement standard).
    const ids = selected.has(entry.proposal_id) && selected.size > 0
      ? Array.from(selected)
      : [entry.proposal_id];
    if (!selected.has(entry.proposal_id)) setSelected(new Set(ids));
    lastDrag.current = ids;
    try {
      e.dataTransfer.setData("application/x-triage-mails", JSON.stringify(ids));
    } catch {
      /* certains navigateurs restreignent setData : lastDrag prend le relais */
    }
    e.dataTransfer.effectAllowed = "move";
  };

  const onDropOnProject = (e: React.DragEvent, miniId: string | "DIVERS", brainId: string | null) => {
    e.preventDefault();
    let ids: string[] = [];
    try {
      const raw = e.dataTransfer.getData("application/x-triage-mails");
      if (raw) ids = JSON.parse(raw);
    } catch {
      /* repli ci-dessous */
    }
    if (!ids.length) ids = lastDrag.current;
    void dropOnProject(miniId, brainId, ids);
  };

  const dropOnProject = async (miniId: string | "DIVERS", brainId: string | null, ids: string[]) => {
    if (!ids.length || classificationLock.current) return;
    classificationLock.current = true;
    setDropping(true);
    setDragOver(null);
    try {
      const brainOnly = !!brainId && projects.some(project=>project.id===brainId)
        && !portfolio.some(project=>project.id===miniId);
      const targetBrainId = miniId === "DIVERS" ? brainId
        : await resolveTarget(brainId && (thumbLinks[miniId]?.linked || brainOnly) ? brainId : `erp:${miniId}`);
      if (!targetBrainId) {
        setMsg("Projet non relié au Brain : relie-le d'abord dans Connaissance.");
        return;
      }
      let ok = 0;
      const errs: string[] = [];
      const entries = queue.filter(entry=>ids.includes(entry.proposal_id));
      const completed = new Set<string>();
      for (let i = 0; i < ids.length; i++) {
        setMsg(`Classement ${i + 1}/${ids.length}…`);
        try {
          const entry = entries.find(entry=>entry.proposal_id===ids[i]);
          if (!entry || completed.has(entry.source_id)) continue;
          await api.brainTriageAssign(ids[i], targetBrainId);
          completed.add(entry.source_id);
          removeDecided(entries.filter(row=>row.source_id===entry.source_id));
          ok++;
        } catch (err: any) {
          errs.push(String(err.message || err));
        }
      }
      setMsg(errs.length
        ? `${ok}/${ids.length} classé(s). Erreurs : ${errs[0]}`
        : `${ok} mail(s) classé(s).`);
    } catch (e: any) {
      setMsg(String(e.message || e));
    } finally {
      classificationLock.current = false;
      setDropping(false);
      lastDrag.current = [];
      void load();
    }
  };

  if (loading) return <LoadingState label="Chargement du tri des mails" />;
  if (error && !hasLoaded.current) return <ErrorState message={error} retry={load} />;

  return (
    <>{portfolioNotice&&<p role="status" className="workspace-notice">{portfolioNotice}</p>}<MailWorkspace key={`${mailAccess.scoped}-${mailAccess.readOnly}`} active={active} scoped={mailAccess.scoped} readOnly={mailAccess.readOnly} queue={queue} projects={mailAccess.scoped ? projects : mailProjects(portfolio,projects)} portfolio={mailAccess.scoped ? portfolio.filter(project=>thumbLinks[project.id]?.linked) : portfolio} links={thumbLinks} stats={stats}
      query={query} onQuery={value => {setQuery(value); setQueueOffset(0); setSelected(new Set());}}
      sort={sort} onSort={value => {setSort(value); setQueueOffset(0); setSelected(new Set());}} queueTotal={queueTotal} selected={selected} onToggle={toggleSelect}
      onSelectAll={selectAllFiltered} onClearSelected={() => setSelected(new Set())}
      offset={queueOffset} onPage={setQueueOffset} pageHasNext={queueHasNext}
      onReload={load} onRunTriage={(force) => { void runTriage(force); }}
      onCancelTriage={() => { void durableTriage.cancel(); }} triaging={triaging} triageProgress={triageProgress} busy={busy}
      dropping={dropping} autoInfo={autoInfo} message={[msg,error && `Actualisation impossible : ${error}`].filter(Boolean).join(" ")} onDecide={decide} onReject={reject}
      onResolveTarget={resolveTarget}
      onCreateProject={mailAccess.scoped ? undefined : createMailProject}
      onDragStart={onDragStart} onDrop={onDropOnProject} dragOver={dragOver} onDragOver={setDragOver} /></>
  );
}

function BrainApp({ rows, onOpenProject }: { rows: any[]; onOpenProject: (id: string) => void }) {
  const [status, setStatus] = useState<{ reachable: boolean; url: string; detail?: string } | null>(null);
  const [overview, setOverview] = useState<any>(null);
  const [links, setLinks] = useState<Record<string, BrainLinkState>>({});
  const [proposals, setProposals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [scanMsg, setScanMsg] = useState("");

  const load = async () => {
    try {
      setLoading(true);
      setError("");
      const st = await api.brainStatus();
      setStatus(st);
      if (!st.reachable) return;
      const [ov, pp] = await Promise.all([api.brainOverview(), api.brainProposals()]);
      setOverview(ov);
      setProposals(pp);
      const entries = await Promise.all(
        rows.map(async (r) => [r.id, await api.brainLink(r.id)] as const),
      );
      setLinks(Object.fromEntries(entries));
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, []);

  const scan = async () => {
    try {
      setScanMsg("Scan en cours…");
      const r: any = await api.brainScanGlobal();
      setScanMsg(`Scan : ${r.scanned} mail(s), ${r.imported} importé(s), ${r.duplicates} doublon(s).`);
      await load();
    } catch (e: any) {
      setScanMsg(String(e.message || e));
    }
  };

  if (loading) return <LoadingState label="Chargement de la connaissance" />;
  if (error) return <ErrorState message={error} retry={load} />;
  if (!status?.reachable)
    return (
      <EmptyState
        title="Coeur de connaissance injoignable"
        detail={`${status?.detail || "Project Brain ne répond pas."} Démarre-le sur le port 8001.`}
      />
    );
  const brainUi = `${status.url}/ui`;
  return (
    <div>
      <div className="card mp-create">
        <p>
          <strong>Cœur de connaissance</strong> — IA {overview.ai.provider}/{overview.ai.model}{" "}
          ({overview.ai.enabled ? "activée" : "coupée"}) · dossier{" "}
          <small>{overview.mail.folder}</small> ({overview.mail.eml_count ?? "?"} mails) ·{" "}
          {overview.pending_count} en attente projet, {overview.proposals_count} information(s) à examiner.
        </p>
        <button className="button" onClick={scan}>Scanner les mails</button>{" "}
        <a href={brainUi} target="_blank" rel="noreferrer">Examiner les exceptions</a>
        {scanMsg && <p><small>{scanMsg}</small></p>}
        <details>
          <summary>Réglage IA</summary>
          <AiSettingsForm />
        </details>
      </div>
      <h4>Projets ({rows.length})</h4>
      <table className="data-table compact">
        <thead><tr><th>Code</th><th>Titre</th><th>Brain</th><th></th></tr></thead>
        <tbody>
          {rows.map((r) => {
            const lk = links[r.id];
            return (
              <tr key={r.id}>
                <td><b>{r.code}</b></td>
                <td>{r.title}</td>
                <td>{lk ? (lk.linked ? lk.brain_code : "—") : "…"}</td>
                <td><button className="button" onClick={() => onOpenProject(r.id)}>Ouvrir</button></td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <h4>File de validation ({proposals.length})</h4>
      {proposals.length === 0 ? (
        <EmptyState title="Rien à valider" detail="Les propositions IA apparaîtront ici." />
      ) : (
        <table className="data-table compact">
          <thead><tr><th>Type</th><th>Sujet</th><th>Confiance</th></tr></thead>
          <tbody>
            {proposals.slice(0, 30).map((p: any) => (
              <tr key={p.id}><td><Badge value={p.kind} /></td><td>{p.subject}</td><td>{p.confidence}</td></tr>
            ))}
          </tbody>
        </table>
      )}
      {proposals.length > 30 && (
        <p><small>…et {proposals.length - 30} autres — <a href={brainUi} target="_blank" rel="noreferrer">tout valider dans Project Brain</a>.</small></p>
      )}
    </div>
  );
}

function BrainPanel({ projectId }: { projectId: string }) {
  const [proof,setProof]=useState<WorkspaceCitation|null>(null);
  const [link, setLink] = useState<BrainLinkState | null>(null);
  const [knowledge, setKnowledge] = useState<BrainKnowledge[]>([]);
  const [demotedKnowledge,setDemotedKnowledge]=useState(false);
  const [knowledgeOffset,setKnowledgeOffset]=useState(0);
  const [changingKnowledge,setChangingKnowledge]=useState('');
  const [actions, setActions] = useState<BrainAction[]>([]);
  const [risks, setRisks] = useState<BrainAction[]>([]);
  const [status, setStatus] = useState<{ reachable: boolean; url: string; detail?: string } | null>(null);
  const [overview, setOverview] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [pick, setPick] = useState("");
  const [scanMsg, setScanMsg] = useState("");

  // Connaissance canonique, utilisable par défaut et déclassable dans le projet.
  const load = async () => {
    try {
      setLoading(true);
      setError("");
      const [st, lk, ov] = await Promise.all([
        api.brainStatus(), api.brainLink(projectId), api.brainOverview(),
      ]);
      setStatus(st);
      setLink(lk);
      setOverview(ov);
      if (lk.linked) {
        const [k, a, r] = await Promise.all([
          api.brainKnowledge(projectId,demotedKnowledge?'invalidated':'validated',knowledgeOffset,50),
          api.brainActions(projectId),
          api.brainRisks(projectId),
        ]);
        setKnowledge(k);
        setActions(a);
        setRisks(r);
        setPick(lk.brain_project_id || "");
      } else if (lk.suggested) {
        setPick(lk.suggested.id);
      }
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [projectId,demotedKnowledge,knowledgeOffset]);

  const save = async () => {
    if (!pick) return;
    try {
      setError("");
      await api.saveBrainLink(projectId, pick);
      await load();
    } catch (e: any) {
      setError(String(e.message || e));
    }
  };

  const unlink = async () => {
    try {
      setError("");
      await api.unlinkBrain(projectId);
      await load();
    } catch (e: any) {
      setError(String(e.message || e));
    }
  };

  const scan = async () => {
    try {
      setScanMsg("Scan en cours…");
      const r: any = link?.linked ? await api.brainScan(projectId) : await api.brainScanGlobal();
      setScanMsg(`Scan : ${r.scanned} mail(s), ${r.imported} importé(s), ${r.duplicates} doublon(s).`);
      await load();
    } catch (e: any) {
      setScanMsg(String(e.message || e));
    }
  };

  if (loading) return <LoadingState label="Chargement de la connaissance" />;
  if (error) return <ErrorState message={error} retry={load} />;
  if (!status?.reachable)
    return (
      <EmptyState
        title="Coeur de connaissance injoignable"
        detail={`${status?.detail || "Project Brain ne répond pas."} Vérifie le serveur sur le port 8001.`}
      />
    );

  const brainUi = `${status.url}/ui`;
  return (
    <div>
      {overview && (
        <details className="card mp-create"><summary>Import des mails et état de l’analyse</summary>
          <p>
            <strong>Analyse des informations</strong> — IA {overview.ai.provider}/{overview.ai.model}{" "}
            ({overview.ai.enabled ? "activée" : "coupée"}) · dossier{" "}
            <small>{overview.mail.folder}</small> ({overview.mail.eml_count ?? "?"} mails) ·{" "}
            {overview.pending_count} en attente projet, {overview.proposals_count} information(s) à examiner.
          </p>
          <button className="button" onClick={scan}>Scanner les mails</button>{" "}
          <a href={brainUi} target="_blank" rel="noreferrer">Examiner les exceptions</a>{" "}
          <small>Configuration disponible dans Réglages.</small>
          {scanMsg && <p><small>{scanMsg}</small></p>}
        </details>
      )}
      {!link?.linked ? (
        <div className="card mp-create">
          <p>
            <strong>Associer les informations à ce projet.</strong>
            {link?.suggested
              ? ` Suggestion par code : ${link.suggested.code} — ${link.suggested.name}.`
              : " Choisissez le projet correspondant."}
          </p>
          <select className="input" aria-label="Projet correspondant" value={pick} onChange={(e) => setPick(e.target.value)}>
            <option value="">— Choisir —</option>
            {(link?.brain_projects || []).map((b) => (
              <option key={b.id} value={b.id}>{b.code} — {b.name}</option>
            ))}
          </select>{" "}
          <button className="button primary" onClick={save} disabled={!pick}>Relier</button>
          {link?.brain_error && <p><small>{link.brain_error}</small></p>}
        </div>
      ) : (
        <div>
          <details><summary>Association du projet et état de l’analyse</summary><p>
            Associé à <b>{link.brain_code}</b> · {link.memory?.truth_items ?? link.memory?.truth_projections ?? "?"} information(s) retenue(s),{" "}
            {link.memory?.evidence_projections ?? "?"} justificatif(s).{" "}
            <button className="button" onClick={unlink}>Dissocier</button>
          </p>
          {link.memory && <p><small>Moteur : {link.memory.health?.engine} — {link.memory.health?.status} ·
            {link.memory.pending || 0} en attente, {link.memory.failed || 0} en échec, {link.memory.obsolete || 0} à purger.</small>{" "}
            <MemoryRetryButton key={projectId} projectId={projectId} onComplete={async () => setLink(await api.brainLink(projectId))} />
          </p>}</details>
          {link.memory_error && <p role="alert">Analyse des informations : {link.memory_error}</p>}
          <h4>Informations {demotedKnowledge?'déclassées':'retenues'} {knowledge.length ? `(${knowledgeOffset+1}–${knowledgeOffset+knowledge.length})` : '(0)'}</h4>
          <label><input type="checkbox" checked={demotedKnowledge} onChange={e=>{setDemotedKnowledge(e.target.checked);setKnowledgeOffset(0);}}/> Voir les informations déclassées</label>
          {knowledge.length === 0 ? (
            <EmptyState title="Aucune information pour ce filtre" detail="Les informations des documents associés sont retenues par défaut ; vous pouvez les écarter à tout moment." />
          ) : (
            <table className="data-table compact">
              <thead><tr><th>Type</th><th>Sujet</th><th>Valeur</th><th>Statut</th><th>Action</th></tr></thead>
              <tbody>
                {knowledge.map((k) => (
                  <tr key={k.id}><td><Badge value={k.kind} /></td><td>{k.subject}</td><td>{k.value}<div className="knowledge-provenance">{k.validated_at&&<small>{new Date(k.validated_at).toLocaleDateString('fr-FR')} · Version {k.version ?? 1}</small>}{(k.citations||[]).map((citation,index)=><button type="button" className="button secondary sm" key={`${citation.source_id}:${index}`} onClick={()=>setProof(citation)}>Consulter la source{(k.citations?.length||0)>1?` ${index+1}`:''}</button>)}{!k.citations?.length&&<small>Aucune preuve accessible associée</small>}</div></td><td>{demotedKnowledge?'Déclassée':k.validation_mode==='default'?'Issue d’une source':'Confirmée'}</td><td><button type="button" className="button secondary sm" disabled={!!changingKnowledge} onClick={()=>void(async()=>{setChangingKnowledge(k.id);setError('');try{await api.changeBrainKnowledge(projectId,k.id,demotedKnowledge?'restore':'invalidate');await load();}catch(e){setError(String(e instanceof Error?e.message:e));}finally{setChangingKnowledge('');}})()}>{changingKnowledge===k.id?'Enregistrement…':demotedKnowledge?'Rétablir':'Déclasser'}</button></td></tr>
                ))}
              </tbody>
            </table>
          )}
          {(knowledgeOffset>0||knowledge.length===50)&&<nav aria-label="Pages des informations du projet"><button type="button" disabled={loading||knowledgeOffset===0} onClick={()=>setKnowledgeOffset(Math.max(0,knowledgeOffset-50))}>Précédentes</button>{' '}<button type="button" disabled={loading||knowledge.length<50} onClick={()=>setKnowledgeOffset(knowledgeOffset+50)}>Suivantes</button></nav>}
          {proof&&<SourceInspector sourceId={proof.source_id} title={proof.title} evidence={[proof]} onClose={()=>setProof(null)}/>}
          <details><summary>Actions ouvertes ({actions.length})</summary>
          <ul>{actions.map((a) => <li key={a.id}><b>{a.subject}</b> — {a.value}</li>)}</ul></details>
          <details><summary>Risques ({risks.length})</summary>
          <ul>{risks.map((r) => <li key={r.id}><b>{r.subject}</b> — {r.value}</li>)}</ul></details>
        </div>
      )}
    </div>
  );
}

/* ── Revue élément par élément (équivalent XPilot ProjectCdcAnalysisPanel) ── */

type ProjectDocumentView='deliverables'|'prepare'|'notes'|'links';
export function ProjectDocumentViews({projectId,active,view,setView,onSaved,focus,onFocusHandled}:{projectId:string;active:boolean;view:ProjectDocumentView;setView:(view:ProjectDocumentView)=>void;onSaved:()=>void;focus?:DeliverableFocus|null;onFocusHandled:()=>void}) {
  const [visited,setVisited]=useState<Set<ProjectDocumentView>>(()=>new Set([view]));
  useEffect(()=>setVisited(previous=>new Set([...previous,view])),[view]);
  const show=(value:ProjectDocumentView)=>{setVisited(previous=>new Set([...previous,value]));setView(value);};
  return <div><div className="mp-subtabs" role="tablist" aria-label="Documents du projet">
    <button type="button" role="tab" aria-selected={view==='deliverables'} className={view==='deliverables'?'active':''} onClick={()=>show('deliverables')}>À remettre</button>
    <button type="button" role="tab" aria-selected={view==='links'} className={view==='links'?'active':''} onClick={()=>show('links')}>Fichiers et dossiers</button>
    <button type="button" role="tab" aria-selected={view==='notes'} className={view==='notes'?'active':''} onClick={()=>show('notes')}>Notes</button>
    <span className="mp-spacer"/><button type="button" className="button secondary sm" aria-pressed={view==='prepare'} onClick={()=>show('prepare')}>Préparer un document</button>
  </div>
    {(view==='deliverables'||visited.has('deliverables'))&&<div hidden={view!=='deliverables'}><ProjectDeliverablesPanel projectId={projectId} active={active&&view==='deliverables'} onSaved={onSaved} focus={focus} onFocusHandled={onFocusHandled}/></div>}
    {(view==='prepare'||visited.has('prepare'))&&<div hidden={view!=='prepare'}><ProjectDocumentsPanel projectId={projectId} active={active&&view==='prepare'}/></div>}
    {(view==='notes'||visited.has('notes'))&&<div hidden={view!=='notes'}><ProjectNotesPanel projectId={projectId} active={active&&view==='notes'}/></div>}
    {(view==='links'||visited.has('links'))&&<div hidden={view!=='links'}><LinksPanel projectId={projectId}/></div>}
  </div>;
}

function LinksPanel({ projectId }: { projectId: string }) {
  const [links, setLinks] = useState<NetworkLink[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [newCode, setNewCode] = useState("");
  const [newLibelle, setNewLibelle] = useState("");
  const [copied, setCopied] = useState<string | null>(null);

  // Proposer le chemin à copier lorsque le poste ne peut pas l’ouvrir.
  const openPath = async (key: string, chemin: string | null) => {
    const p = (chemin || "").trim();
    if (!p) {
      setCopied(key + ":vide");
      window.setTimeout(() => setCopied(null), 2500);
      return;
    }
    try {
      await api.openPath(p, projectId);
      setCopied(key);
    } catch {
      try {
        await navigator.clipboard.writeText(p);
      } catch {
        const ta = document.createElement("textarea");
        ta.value = p;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        ta.remove();
      }
      setCopied(key + ":copie");
    }
    window.setTimeout(() => setCopied(null), 3000);
  };

  const load = async () => {
    try {
      setLoading(true);
      setError("");
      setLinks(await api.networkLinks(projectId));
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    load();
  }, [projectId]);

  const save = async () => {
    try {
      setSaving(true);
      setError("");
      setLinks(
        await api.saveNetworkLinks(
          projectId,
          links.map((l) => ({ code: l.code, libelle: l.libelle, chemin: l.chemin })),
        ),
      );
      alert("Liens enregistrés");
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingState label="Chargement des liens réseau" />;
  if (error) return <ErrorState message={error} retry={load} />;

  return (
    <section className="links-panel">
      <header className="links-toolbar">
        <div className="links-toolbar-label">
          <span>
            <strong>Fichiers liés au projet</strong>
            <small>Chemins réseau (UNC) — code unique par projet</small>
          </span>
        </div>
        <button className="button primary" type="button" disabled={saving} onClick={save}>
          💾 Enregistrer les liens
        </button>
      </header>
      {links.map((link, index) => (
        <div className={`link-edit${link.required ? " required-link" : ""}`} key={link.id || index}>
          <input
            aria-label="Code"
            value={link.code}
            readOnly={link.required}
            title={link.required ? "Lien obligatoire : code verrouillé" : "Code"}
            onChange={(e) =>
              setLinks((items) =>
                items.map((item, i) => (i === index ? { ...item, code: e.target.value } : item)),
              )
            }
            placeholder="Code"
            style={{ width: 140 }}
          />
          <input
            aria-label="Libellé"
            value={link.libelle}
            readOnly={link.required}
            onChange={(e) =>
              setLinks((items) =>
                items.map((item, i) => (i === index ? { ...item, libelle: e.target.value } : item)),
              )
            }
            placeholder="Libellé"
            style={{ width: 200 }}
          />
          <input
            aria-label="Chemin réseau"
            value={link.chemin || ""}
            onChange={(e) =>
              setLinks((items) =>
                items.map((item, i) => (i === index ? { ...item, chemin: e.target.value } : item)),
              )
            }
            placeholder="Aucun fichier enregistré — ex : \\serveur\affaires\PRJ-001"
            style={{ flex: 1, minWidth: 260 }}
          />
          <button
            className="button secondary"
            type="button"
            title="Ouvre le dossier/fichier réseau dans l'Explorateur Windows"
            onClick={() => openPath(link.code || String(index), link.chemin)}
          >
            📂 Ouvrir
          </button>
          {copied === (link.code || String(index)) && (
            <small style={{ color: "#0a7d3b" }}>Ouvert dans l'Explorateur</small>
          )}
          {copied === (link.code || String(index)) + ":copie" && (
            <small style={{ color: "#b34000" }}>Ouverture impossible — chemin copié</small>
          )}
          {copied === (link.code || String(index)) + ":vide" && (
            <small style={{ color: "#b34000" }}>Aucun chemin renseigné</small>
          )}
          {!link.required && (
            <button
              className="button secondary"
              type="button"
              title="Supprimer ce lien"
              onClick={() => setLinks((items) => items.filter((_, i) => i !== index))}
            >
              ✕
            </button>
          )}
        </div>
      ))}
      <div className="inline-form">
        <label className="ux-field">Code du lien<input className="input" placeholder="Code (ex : plans_be)" value={newCode} onChange={(e) => setNewCode(e.target.value)} style={{ width: 140 }} /></label>
        <label className="ux-field">Libellé du lien<input className="input" placeholder="Libellé (ex : Plans BE)" value={newLibelle} onChange={(e) => setNewLibelle(e.target.value)} style={{ width: 200 }} /></label>
        <button
          className="button secondary"
          type="button"
          onClick={() => {
            if (!newCode.trim() || !newLibelle.trim()) return;
            setLinks((items) => [
              ...items,
              { id: `new-${Date.now()}`, code: newCode.trim(), libelle: newLibelle.trim(), chemin: null, ordre: items.length, required: false },
            ]);
            setNewCode("");
            setNewLibelle("");
          }}
        >
          + Lien
        </button>
      </div>
    </section>
  );
}

/* Création de projet : manuel ou depuis un dossier réseau (scan TDAO/TDSP) */
export function ScanImport({ reload, close, onCreated }: ProjectCreateProps) {
  const [mode, setMode] = useState<"manual" | "folder">("folder");
  const [code, setCode] = useState("");
  const [title, setTitle] = useState("");
  const [folder, setFolder] = useState("");
  const [preview, setPreview] = useState<any>(null);
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const creatingRef = useRef(false);

  const scan = async () => {
    if (!folder.trim()) return;
    try {
      setScanning(true);
      setError("");
      setPreview(null);
      const p: any = await api.scanFolder(folder.trim());
      setPreview(p);
      setCode(p.code || "");
      setTitle(p.title || "");
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {
      setScanning(false);
    }
  };

  const createManual = async () => {
    if (!title.trim() || creatingRef.current) return;
    creatingRef.current=true;setCreating(true);setError("");
    try {
      const result=await api.createProject(code.trim(), title.trim());
      if(onCreated)await onCreated(result.id);else{await reload();close();}
      setCode("");setTitle("");setPreview(null);
    } catch (e: any) {setError(String(e.message || e));}
    finally {creatingRef.current=false;setCreating(false);}
  };

  const doImport = async () => {
    if(creatingRef.current)return;
    creatingRef.current=true;setCreating(true);
    try {
      setError("");
      const result:any=await api.importFolder(folder.trim(), code.trim() || undefined, title.trim() || undefined);
      if(onCreated)await onCreated(result.project_id || result.id);else{await reload();close();}
      setCode("");setTitle("");setFolder("");setPreview(null);
    } catch (e: any) {
      setError(String(e.message || e));
    } finally {creatingRef.current=false;setCreating(false);}
  };

  return (
    <div className="card">
      <div className="mp-subtabs">
        <button type="button" disabled={creating} className={mode === "folder" ? "active" : ""} onClick={() => setMode("folder")}>
          Depuis dossier réseau
        </button>
        <button type="button" disabled={creating} className={mode === "manual" ? "active" : ""} onClick={() => setMode("manual")}>
          Manuel
        </button>
      </div>

      {error && <ErrorState message={error}/>}

      {mode === "manual" ? (
        <div className="inline-form">
          <label className="ux-field">Code du projet<input className="input" placeholder="Code (ex : AIRB25LTH0806-A)" value={code} onChange={(e) => setCode(e.target.value)} style={{ width: 220 }} /></label>
          <label className="ux-field">Titre du projet<input className="input" placeholder="Titre du projet" value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: 320 }} /></label>
          <button className="button primary" disabled={creating || !title.trim()} onClick={createManual}>{creating ? "Création…" : "Créer"}</button>
        </div>
      ) : (
        <div>
          <div className="inline-form">
            <label className="ux-field" style={{flex:1}}>Dossier réseau du projet<input
              className="input"
              aria-label="Dossier réseau du projet"
              placeholder="Chemin réseau — ex : V:\00 - AIRB26LTx0000-A - Description"
              value={folder}
              onChange={(e) => setFolder(e.target.value)}
              style={{ flex: 1, minWidth: 320 }}
            /></label>
            <button className="button secondary" onClick={scan} disabled={scanning || creating}>
              {scanning ? "Scan…" : "🔍 Scanner"}
            </button>
          </div>
          {preview && (
            <div className="card">
              {(preview.warnings || []).map((warning:string,index:number)=><p key={index} role="alert">{warning}</p>)}
              <table className="data-table compact">
                <tbody>
                  <tr><td>Code détecté</td><td><b>{preview.code}</b></td></tr>
                  <tr><td>Titre</td><td><b>{preview.title}</b></td></tr>
                  <tr><td>Client</td><td>{preview.client_name || "—"} {preview.offer_number && `(offre ${preview.offer_number})`}</td></tr>
                  <tr><td>TDAO</td><td>{preview.tdao_file || "non trouvé"}</td></tr>
                  <tr><td>TDSP</td><td>{preview.tdsp_file || "non trouvé"}</td></tr>
                  <tr><td>Heures TDAO</td><td><b>{preview.budget_h} h</b></td></tr>
                </tbody>
              </table>
              <div className="inline-form">
                <input className="input" aria-label="Code" value={code} onChange={(e) => setCode(e.target.value)} style={{ width: 200 }} />
                <input className="input" aria-label="Titre" value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: 300 }} />
                <button className="button primary" disabled={creating} onClick={doImport}>{creating ? "Import…" : "Importer le projet"}</button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* Comptes rendus de réunion (onglet Revues) : décisions + actions → tâches */
function meetingTargetFromUrl(projectId: string, meetings: Meeting[]): string | null {
  const route = parseWorkspaceRoute(window.location.pathname, window.location.search);
  if (route.page !== 'project' || route.projectId !== projectId || route.tab !== 'reviews') return null;
  const id = new URLSearchParams(window.location.search).get('meeting');
  return id && meetings.some(meeting => meeting.id === id) ? id : null;
}

function ReviewsPanel({ projectId, meetings, refresh, active, onOpenDocument }: {
  projectId: string; meetings: Meeting[]; refresh: () => void; active: boolean; onOpenDocument:(id:string,title:string)=>void;
}) {
  const initialMeetingId = meetingTargetFromUrl(projectId, meetings);
  const [view, setView] = useState<'rlp'|'meetings'>(()=>initialMeetingId?'meetings':'rlp');
  const [visited, setVisited] = useState(!!initialMeetingId);
  useEffect(()=>{const showRecording=(event:Event)=>{if((event as CustomEvent<{projectId?:string}>).detail?.projectId!==projectId)return;setView('meetings');setVisited(true);};window.addEventListener('agent-show-recording',showRecording);return()=>window.removeEventListener('agent-show-recording',showRecording);},[projectId]);
  return <div>
    <p><a className="button primary" href={meetingWorkspaceHref(projectId)} onClick={event=>{if(requestMeetingWorkspace(projectId))event.preventDefault();}}>Ouvrir le Studio des réunions et notes</a></p>
    <div className="mp-subtabs" role="tablist" aria-label="Réunions et revues">
      <button type="button" role="tab" aria-selected={view==='rlp'} className={`mp-subtab ${view==='rlp'?'active':''}`} onClick={()=>setView('rlp')}>Revue de lancement</button>
      <button type="button" role="tab" aria-selected={view==='meetings'} className={`mp-subtab ${view==='meetings'?'active':''}`} onClick={()=>{setView('meetings');setVisited(true);}}>Réunions et audio</button>
    </div>
    <div hidden={view!=='rlp'}><ProjectReviewsPanel projectId={projectId} active={active&&view==='rlp'} onSaved={refresh} onOpenDocument={onOpenDocument}/></div>
    {visited&&<div hidden={view!=='meetings'}><LegacyMeetingsPanel projectId={projectId} meetings={meetings} refresh={refresh} initialMeetingId={initialMeetingId}/></div>}
  </div>;
}

function LegacyMeetingsPanel({ projectId, meetings, refresh, initialMeetingId }: {
  projectId: string; meetings: Meeting[]; refresh: () => void; initialMeetingId?: string | null;
}) {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [title, setTitle] = useState("");
  const [participants, setParticipants] = useState("");
  const [decisions, setDecisions] = useState("");
  const [openId, setOpenId] = useState<string | null>(()=>initialMeetingId&&meetings.some(meeting=>meeting.id===initialMeetingId)?initialMeetingId:null);
  const [actionTitle, setActionTitle] = useState("");
  const [actionOwner, setActionOwner] = useState("");
  const [exportMd, setExportMd] = useState("");

  const create = async () => {
    if (!title.trim()) return;
    const m: any = await api.createMeeting(projectId, {
      date, title: title.trim(), participants: participants.trim(), decisions: decisions.trim(),
    });
    setTitle("");
    setDecisions("");
    setOpenId(m.id);
    refresh();
  };

  return (
    <div>
      <MeetingAudioPanel key={projectId} projectId={projectId} onPublished={refresh} />
      <details className="card progressive-options">
        <summary>Saisir un compte rendu</summary>
        <div className="inline-form">
          <input className="input" type="date" aria-label="Date" value={date} onChange={(e) => setDate(e.target.value)} />
          <input className="input" aria-label="Titre du compte rendu" placeholder="Titre (ex : Point hebdo)" value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: 260 }} />
          <input className="input" aria-label="Participants" placeholder="Participants" value={participants} onChange={(e) => setParticipants(e.target.value)} style={{ width: 220 }} />
        </div>
        <textarea
          className="input"
          aria-label="Décisions du compte rendu"
          placeholder="Décisions (une par ligne)"
          value={decisions}
          onChange={(e) => setDecisions(e.target.value)}
          rows={3}
          style={{ width: "100%", marginTop: 8 }}
        />
        <div className="inline-form">
          <button className="button primary" disabled={!title.trim()} onClick={create}>Enregistrer le compte rendu</button>
        </div>
      </details>

      {meetings.length === 0 && (
        <EmptyState title="Aucun compte rendu" detail="Préparez-le depuis l’audio ou ouvrez « Saisir un compte rendu »." />
      )}

      {meetings.map((m) => (
        <div className="card" key={m.id}>
          <div className="inline-form">
            <b>{m.date} — {m.title}</b>
            {m.open_actions > 0 && <Badge value={`${m.open_actions} action(s)`} tone="warning" />}
            <span className="mp-spacer" />
            <button className="button secondary" onClick={() => setOpenId(openId === m.id ? null : m.id)}>
              {openId === m.id ? "Refermer" : "Ouvrir"}
            </button>
            <button
              className="button secondary"
              onClick={async () => {
                const r: any = await api.exportMeeting(projectId, m.id);
                setExportMd(r.markdown);
                const url = URL.createObjectURL(new Blob([r.markdown], {type: 'text/markdown;charset=utf-8'}));
                const link = document.createElement('a');
                link.href = url; link.download = r.filename || r.file;
                document.body.append(link); link.click(); link.remove();
                window.setTimeout(() => URL.revokeObjectURL(url), 1000);
              }}
            >
              Exporter
            </button>
            <AsyncDownloadLink className="button secondary" download
              href={agentPath(`/api/v1/projects/${encodeURIComponent(projectId)}/meetings/${encodeURIComponent(m.id)}/pdf`)}
              activityLabel="Préparation du PDF du compte rendu…">Exporter en PDF</AsyncDownloadLink>
          </div>
          {openId === m.id && (
            <div>
              <p><b>Participants :</b> {m.participants || "—"}</p>
              <p style={{ whiteSpace: "pre-wrap" }}><b>Décisions :</b>{"\n"}{m.decisions || "—"}</p>
              <div className="project-action-table-scroll" role="region" aria-label={`Actions de la réunion ${m.title}`} tabIndex={0}>
              <table className="data-table compact">
                <thead><tr><th>Action</th><th>Pilote</th><th>Échéance</th><th></th></tr></thead>
                <tbody>
                  {m.actions.map((a) => (
                    <tr key={a.id}>
                      <td>{a.title}</td>
                      <td>{a.owner || "—"}</td>
                      <td>{a.due_date || "—"}</td>
                      <td>
                        {a.task_id ? (
                          <Badge value="en tâche" tone="info" />
                        ) : (
                          <button
                            className="button secondary"
                            onClick={async () => {
                              await api.actionToTask(projectId, m.id, a.id);
                              refresh();
                            }}
                          >
                            → Tâche
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              </div>
              <div className="inline-form">
                <input className="input" placeholder="Nouvelle action" value={actionTitle} onChange={(e) => setActionTitle(e.target.value)} style={{ width: 260 }} />
                <input className="input" placeholder="Pilote" value={actionOwner} onChange={(e) => setActionOwner(e.target.value)} style={{ width: 120 }} />
                <button
                  className="button secondary"
                  onClick={async () => {
                    if (!actionTitle.trim()) return;
                    await api.addAction(projectId, m.id, { title: actionTitle.trim(), owner: actionOwner.trim() });
                    setActionTitle("");
                    setActionOwner("");
                    refresh();
                  }}
                >
                  + Action
                </button>
              </div>
            </div>
          )}
        </div>
      ))}

      {exportMd && (
        <div className="card">
          <b>Aperçu export CR</b>
          <pre style={{ whiteSpace: "pre-wrap", fontSize: 13 }}>{exportMd}</pre>
        </div>
      )}
    </div>
  );
}

const TASK_STATUSES = ["todo", "in_progress", "done"];

/* Tâches éditables : statut + échéance */
function TasksPanel({ projectId, rows, refresh }: { projectId: string; rows: any[]; refresh: () => void }) {
  const [title, setTitle] = useState("");
  const [due, setDue] = useState("");
  return (
    <div>
      <div className="inline-form">
        <input className="input" placeholder="Nouvelle tâche" value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: 300 }} />
        <input className="input" type="date" aria-label="Échéance" value={due} onChange={(e) => setDue(e.target.value)} />
        <button
          className="button primary"
          onClick={async () => {
            if (!title.trim()) return;
            await api.addTask(projectId, title.trim(), due.trim());
            setTitle("");
            setDue("");
            refresh();
          }}
        >
          + Tâche
        </button>
      </div>
      <div className="project-action-table-scroll" role="region" aria-label="Tableau des tâches" tabIndex={0}>
      <table className="data-table compact">
        <caption className="mp-caption">Cliquer sur le statut pour l'avancer · échéance modifiable au clavier</caption>
        <thead><tr><th>Tâche</th><th>Statut</th><th>Échéance</th></tr></thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={3}>
              <EmptyState title="Aucune tâche" detail="Crée la première tâche ci-dessus, ou convertis une action de CR en tâche (onglet Revues)." />
            </td></tr>
          )}
          {rows.map((t) => (
            <tr key={t.id} className={t.due_date && t.status !== "done" && t.status !== "cancelled" && t.due_date < new Date().toISOString().slice(0, 10) ? "mp-late" : ""}>
              <td>{t.title}</td>
              <td>
                <button
                  className="button secondary"
                  title="Cliquer pour avancer le statut"
                  onClick={async () => {
                    const next = TASK_STATUSES[(TASK_STATUSES.indexOf(t.status) + 1) % TASK_STATUSES.length] || "todo";
                    await api.patchTask(projectId, t.id, { status: next });
                    refresh();
                  }}
                >
                  {t.status} →
                </button>
              </td>
              <td>
                <input
                  className="input" type="date" aria-label="Échéance" defaultValue={t.due_date || ""}
                  onBlur={async (e) => {
                    if (e.target.value !== (t.due_date || "")) {
                      await api.patchTask(projectId, t.id, { due_date: e.target.value });
                      refresh();
                    }
                  }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}


function DeliverablesPanel({ projectId, rows, refresh }: { projectId: string; rows: any[]; refresh: () => void }) {
  const [title, setTitle] = useState("");
  return (
    <div>
      <div className="inline-form">
        <input className="input" placeholder="Nouveau livrable" value={title} onChange={(e) => setTitle(e.target.value)} style={{ width: 300 }} />
        <button
          className="button primary"
          onClick={async () => {
            if (!title.trim()) return;
            await api.addDeliverable(projectId, title.trim());
            setTitle("");
            refresh();
          }}
        >
          + Livrable
        </button>
      </div>
      <table className="data-table compact">
        <thead><tr><th>Livrable</th><th>Statut</th></tr></thead>
        <tbody>
          {rows.map((d) => (
            <tr key={d.id}>
              <td>{d.title}</td>
              <td>
                <button
                  className="button secondary"
                  title="Cliquer pour avancer le statut"
                  onClick={async () => {
                    const next = TASK_STATUSES[(TASK_STATUSES.indexOf(d.status) + 1) % TASK_STATUSES.length] || "todo";
                    await api.patchDeliverable(projectId, d.id, { status: next });
                    refresh();
                  }}
                >
                  {d.status} →
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* Planning : échéancier + charge restante */
function PlanningTab({ projectId, active = true }: { projectId: string; active?: boolean }) {
  const [data, setData] = useState<any>(null);
  const [reload, setReload] = useState(0);
  useEffect(() => {
    if (!active) return;
    let alive = true;
    setData(null);
    api.planning(projectId).then(value => { if (alive) setData(value); }).catch(() => { if (alive) setData({ error: true }); });
    return () => { alive = false; };
  }, [projectId, active, reload]);
  if (!data) return <LoadingState label="Chargement du planning" />;
  if (data.error) return <ErrorState message="Planning inaccessible" retry={() => setReload(value => value + 1)} />;
  return (
    <section className="planning-panel" aria-label="Vue d’ensemble du planning">
      <div className="planning-heading"><h3>Vue d’ensemble du planning</h3><button type="button" className="button secondary sm" onClick={() => setReload(value => value + 1)}>Recharger le planning</button></div>
      <div className="planning-table-scroll">
      <table className="data-table compact">
        <tbody>
          <tr><td>Éléments en retard</td><td><b>{data.overdue_count}</b></td></tr>
          <tr><td>Sans échéance</td><td><b>{data.undated_count}</b></td></tr>
          <tr><td>Reste à faire</td><td><b>{data.remaining_hours} h</b></td></tr>
          <tr><td>Heures prévues</td><td><b>{data.budget_hours} h</b>{data.consumed_pct != null && ` — ${data.consumed_pct}% consommé`}</td></tr>
        </tbody>
      </table>
      </div>
      <div className="planning-table-scroll">
      <table className="data-table compact planning-overview-table">
        <thead><tr><th>Type</th><th>Titre</th><th>Échéance</th><th>État</th></tr></thead>
        <tbody>
          {data.entries.map((e: any, i: number) => (
            <tr key={`${e.type}-${e.id}-${i}`} className={e.overdue ? "mp-late" : ""}>
              <td><Badge value={e.type === "milestone" ? "jalon" : "tâche"} tone="neutral" /></td>
              <td>{e.title}</td>
              <td>{e.due_date || "—"}</td>
              <td>{e.overdue ? <Badge value="en retard" tone="warning" /> : (e.status || "—")}</td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </section>
  );
}

/* Import Sage : configuration du partage + lancement + statut par source */
function SagePanel() {
  const [root, setRoot] = useState("");
  const [status, setStatus] = useState<SageStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [operation, setOperation] = useState<"save" | "import" | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [statusError, setStatusError] = useState("");

  const load = async () => {
    setLoading(true);
    try {
      const [config, current] = await Promise.all([api.sageConfig(), api.sageStatus()]);
      setRoot(config.root_path);
      setStatus(current);
      setStatusError("");
    } catch (failure) {
      setStatusError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => { void load(); }, []);

  const save = async () => {
    setOperation("save");
    setNotice("");
    setError("");
    try {
      await api.saveSageConfig(root.trim());
      setNotice("Dossier enregistré.");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      setOperation(null);
    }
  };

  const importSage = async () => {
    setOperation("import");
    setNotice("");
    setError("");
    setStatusError("");
    try {
      const result = await api.sageRun();
      setNotice(`${result.total_rows} ligne(s) importée(s).`);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : String(failure));
    } finally {
      try {
        setStatus(await api.sageStatus());
      } catch (failure) {
        setStatusError(failure instanceof Error ? failure.message : String(failure));
      } finally {
        setOperation(null);
      }
    }
  };

  const importError = error || status?.batch?.error_message;
  const locked = loading || operation !== null;

  return (
    <div>
      <div className="card">
        <b>Exports Sage (CSV `;` — dossiers Achats, Pointages)</b>
        <div className="inline-form">
          <input
            className="input"
            aria-label="Racine des exports Sage"
            placeholder="Chemin réseau — ex : \\serveur\Sage\Exports"
            value={root}
            disabled={locked}
            onChange={(event) => setRoot(event.target.value)}
            style={{ flex: 1, minWidth: 300 }}
          />
          <button type="button" className="button secondary" disabled={locked || !root.trim()} onClick={save}>
            Enregistrer
          </button>
          <button type="button" className="button primary" disabled={locked} onClick={importSage}>
            {operation === "import" ? "Import en cours…" : "Lancer l’import"}
          </button>
        </div>
        {notice && <p role="status">{notice}</p>}
        {importError && <p role="alert">{importError}</p>}
        {statusError && <ErrorState message={statusError} retry={load} />}
      </div>
      {status?.sources.length ? (
        <table className="data-table compact">
          <thead><tr><th>Source</th><th>Fichier</th><th>Lignes</th></tr></thead>
          <tbody>
            {status.sources.map((source) => (
              <tr key={source.source}><td>{source.folder}</td><td>{source.file_name}</td><td>{source.rows}</td></tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {status && !status.batch && <EmptyState title="Jamais importé" detail="Enregistrez le dossier des exports, puis lancez l’import." />}
    </div>
  );
}

/* Achats du projet (depuis Sage, rattachés par code affaire) */
/* ══ Bureau façon macOS : Finder, fenêtres, dock, Spotlight ═══════════ */

type WinKind = "finder" | "project" | "create" | "about" | "brain" | "settings" | "mail";
type Win = {
  key: string;
  kind: WinKind;
  projectId?: string;
  tab?: TabId;
  min?: boolean;
  max?: boolean;
  x: number;
  y: number;
  w?: number;
  h?: number;
  z: number;
};

/* Icônes d'applications globales (dock, Launchpad, menu Applications) : Connaissance,
   Réglages et Mails ouvrent leur propre fenêtre ; le reste ouvre un module projet. */
type DockTab = TabId | "settings" | "mail";
const DOCK_APPS: { tab: DockTab; label: string; icon: (props: { size?: number }) => React.ReactElement }[] = [
  { tab: "reviews", label: "Revues", icon: AppIcon.chat },
  { tab: "documents", label: "Documents", icon: AppIcon.docs },
  { tab: "import", label: "Import Sage", icon: AppIcon.import },
  { tab: "connaissance", label: "Connaissance", icon: AppIcon.notes },
  { tab: "settings", label: "Réglages", icon: AppIcon.settings },
  { tab: "mail", label: "Mails", icon: AppIcon.mail },
];

/* Icônes épinglées dans le Dock : le reste reste accessible via Apps (Launchpad). */
const DOCK_PINNED: DockTab[] = ["connaissance", "mail"];

/* Thèmes de couleur du bureau (+ fond associé). "golden" = look historique. */
const THEMES = [
  { id: "golden", label: "Doré", swatch: "linear-gradient(180deg,#1d3a7a,#e08a4e)", dark: false },
  { id: "foret", label: "Forêt", swatch: "linear-gradient(180deg,#0a3324,#6faf7f)", dark: false },
  { id: "ocean", label: "Océan", swatch: "linear-gradient(180deg,#06294f,#7fc4d8)", dark: false },
  { id: "rose", label: "Rose", swatch: "linear-gradient(180deg,#45204a,#e8a8b5)", dark: false },
  { id: "graphite", label: "Graphite (sombre)", swatch: "linear-gradient(180deg,#0d1420,#2e3b52)", dark: true },
] as const;
type ThemeId = (typeof THEMES)[number]["id"];
type WallpaperMode = "auto" | "image" | "color";
type Wallpaper = { mode: WallpaperMode; color: string };
type CustomColors = { primary: string | null; accent: string | null; danger: string | null };

/* Palettes prédéfinies : boutons + accents + danger associés. */
const COLOR_PRESETS = [
  { label: "Rouge (origine)", primary: "#e30613", accent: "#438ed8", danger: "#b7131d" },
  { label: "Bleu", primary: "#2563eb", accent: "#438ed8", danger: "#b91c1c" },
  { label: "Vert", primary: "#16a34a", accent: "#35b56e", danger: "#b91c1c" },
  { label: "Violet", primary: "#7c3aed", accent: "#8b5cf6", danger: "#b91c1c" },
  { label: "Orange", primary: "#ea580c", accent: "#f1a83b", danger: "#b91c1c" },
  { label: "Turquoise", primary: "#0d9488", accent: "#2dd4bf", danger: "#b91c1c" },
];

/* Assombrit une couleur #rrggbb d'un ratio (0-1) pour les survols. */
function shade(hex: string, ratio: number): string {
  const m = /^#([0-9a-f]{6})$/i.exec(hex.trim());
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  const f = (c: number) => Math.round(c * (1 - ratio));
  const r = f(n >> 16), g = f((n >> 8) & 0xff), b = f(n & 0xff);
  return `#${((r << 16) | (g << 8) | b).toString(16).padStart(6, "0")}`;
}

/* Positions initiales des icônes du bureau (déplaçables, mémorisées). */
const ICON_HOME: Record<string, { x: number; y: number }> = {
  hd: { x: 16, y: 40 },
  projets: { x: 16, y: 158 },
  new: { x: 16, y: 276 },
};

const FILTER_LABELS: Record<string, string> = {
  all: "Projets",
  active: "Actifs",
  late: "En retard",
  todo: "À corriger",
  closed: "Corbeille",
};

function useProjectData(projectId: string, reloadRows: () => Promise<void> | void) {
  const [detail, setDetail] = useState<ProjectDetail | null>(null);
  const [items, setItems] = useState<CdcItem[]>([]);
  const [sources, setSources] = useState<CdcSource[]>([]);
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [error, setError] = useState("");
  const generation = useRef(0);
  const refresh = async () => {
    const request = ++generation.current;
    try {
      setError("");
      const [project, cdcItems, cdcSources, reviews] = await Promise.all([
        api.detail(projectId), api.cdcItems(projectId), api.cdcSources(projectId), api.meetings(projectId),
      ]);
      if (request !== generation.current) return false;
      setDetail(project); setItems(cdcItems); setSources(cdcSources); setMeetings(reviews);
      await reloadRows();
      return true;
    } catch (e: unknown) {
      if (request === generation.current) setError(e instanceof Error ? e.message : String(e));
      return false;
    }
  };
  useEffect(() => {
    setDetail(null); setItems([]); setSources([]); setMeetings([]);
    void refresh();
    return () => {generation.current += 1;};
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);
  return { detail, items, sources, meetings, error, refresh };
}

function Desktop(props: {
  rows: PortfolioRow[];
  allRows: PortfolioRow[];
  total: number;
  kpis: { n: number; corriger: number; retard: number; raf: number };
  query: string;
  setQuery: (v: string) => void;
  status: string;
  setStatus: (v: string) => void;
  reload: () => Promise<void>;
}) {
  const { allRows, reload } = props;
  const [wins, setWins] = useState<Win[]>([
    { key: "finder", kind: "finder", x: 310, y: 208, z: 1 },
  ]);
  const [activeKey, setActiveKey] = useState("finder");
  const [spotlight, setSpotlight] = useState(false);
  const [launchpad, setLaunchpad] = useState(false);
  const [selIcon, setSelIcon] = useState<string | null>(null);
  const [notice, setNotice] = useState("");
  const [dockSide, setDockSide] = useState<"bottom" | "left">(() => {
    try {
      return localStorage.getItem("mp-dock-side") === "left" ? "left" : "bottom";
    } catch {
      return "bottom";
    }
  });
  const zRef = useRef(1);
  const noticeTimer = useRef<number | null>(null);

  const toggleDock = () =>
    setDockSide((s) => {
      const n = s === "bottom" ? "left" : "bottom";
      try {
        localStorage.setItem("mp-dock-side", n);
      } catch {
        /* stockage indisponible : position non persistée */
      }
      return n;
    });

  const [dockVisible, setDockVisible] = useState<boolean>(() => {
    try {
      return localStorage.getItem("mp-dock-visible") !== "0";
    } catch {
      return true;
    }
  });
  const assistantOpen = false;
  const toggleAssistant = () => {
    const path = projectConversationHref();
    if (path) window.location.assign(path);
  };
  const toggleDockVisible = () =>
    setDockVisible((v) => {
      try {
        localStorage.setItem("mp-dock-visible", v ? "0" : "1");
      } catch {
        /* stockage indisponible : visibilité non persistée */
      }
      return !v;
    });

  const [theme, setThemeState] = useState<string>(() => {
    try {
      return localStorage.getItem("mp-theme") || "golden";
    } catch {
      return "golden";
    }
  });
  const setTheme = (t: string) => {
    setThemeState(t);
    try {
      localStorage.setItem("mp-theme", t);
    } catch {
      /* stockage indisponible */
    }
  };
  const [wallpaper, setWallpaperState] = useState<Wallpaper>(() => {
    try {
      const raw = localStorage.getItem("mp-wallpaper");
      if (raw) {
        const parsed = JSON.parse(raw) as { mode?: unknown; color?: unknown };
        if (parsed.mode === "image" || parsed.mode === "color") {
          return {
            mode: parsed.mode,
            color: typeof parsed.color === "string" ? parsed.color : "#1d3a7a",
          };
        }
      }
    } catch {
      /* stockage indisponible : automatique */
    }
    return { mode: "auto", color: "#1d3a7a" };
  });
  const setWallpaper = (w: Wallpaper) => {
    setWallpaperState(w);
    try {
      localStorage.setItem("mp-wallpaper", JSON.stringify(w));
    } catch {
      /* stockage indisponible */
    }
  };
  const [customColors, setCustomColorsState] = useState<CustomColors>(() => {
    try {
      const raw = localStorage.getItem("mp-colors");
      if (raw) {
        const parsed = JSON.parse(raw) as { primary?: unknown; accent?: unknown; danger?: unknown };
        const hex = (v: unknown) => (typeof v === "string" && /^#[0-9a-f]{6}$/i.test(v) ? v : null);
        return { primary: hex(parsed.primary), accent: hex(parsed.accent), danger: hex(parsed.danger) };
      }
    } catch {
      /* stockage indisponible : couleurs du thème */
    }
    return { primary: null, accent: null, danger: null };
  });
  const setCustomColors = (c: CustomColors) => {
    setCustomColorsState(c);
    try {
      localStorage.setItem("mp-colors", JSON.stringify(c));
    } catch {
      /* stockage indisponible */
    }
  };
  useEffect(() => {
    document.body.dataset.theme = theme;
    document.body.dataset.wallpaper = wallpaper.mode;
    document.body.style.setProperty("--wp-color", wallpaper.color);
    if (wallpaper.mode === "image") {
      loadWallpaperImage().then((img) => {
        document.body.style.setProperty("--wp-image", img ? `url("${img}")` : "none");
      });
    } else {
      document.body.style.setProperty("--wp-image", "none");
    }
    const style = document.body.style;
    if (customColors.primary) {
      style.setProperty("--button-primary-bg", customColors.primary);
      style.setProperty("--button-primary-hover-bg", shade(customColors.primary, 0.14));
    } else {
      style.removeProperty("--button-primary-bg");
      style.removeProperty("--button-primary-hover-bg");
    }
    if (customColors.accent) {
      style.setProperty("--project-selection-color", customColors.accent);
      style.setProperty("--state-information", customColors.accent);
    } else {
      style.removeProperty("--project-selection-color");
      style.removeProperty("--state-information");
    }
    if (customColors.danger) {
      style.setProperty("--button-danger-bg", customColors.danger);
      style.setProperty("--button-danger-hover-bg", shade(customColors.danger, 0.14));
      style.setProperty("--danger-strong", customColors.danger);
    } else {
      style.removeProperty("--button-danger-bg");
      style.removeProperty("--button-danger-hover-bg");
      style.removeProperty("--danger-strong");
    }
  }, [theme, wallpaper, customColors]);

  const [dockZoom, setDockZoom] = useState<number>(() => {
    try {
      const v = parseInt(localStorage.getItem("mp-dock-zoom") || "50", 10);
      return Number.isFinite(v) ? Math.min(72, Math.max(32, v)) : 50;
    } catch {
      return 50;
    }
  });
  const changeZoom = (z: number) => {
    const v = Math.min(72, Math.max(32, Math.round(z)));
    setDockZoom(v);
    try {
      localStorage.setItem("mp-dock-zoom", String(v));
    } catch {
      /* stockage indisponible */
    }
  };

  type CtxItem = { label: string; run: () => void };
  const [ctx, setCtx] = useState<{ x: number; y: number; items: CtxItem[] } | null>(null);
  const showCtx = (x: number, y: number, items: CtxItem[]) => setCtx({ x, y, items });

  // Projets épinglés au bureau (raccourcis) et modules épinglés au Dock.
  const [deskPins, setDeskPins] = useState<string[]>(() => {
    try {
      const v = JSON.parse(localStorage.getItem("mp-desk-pins") || "[]") as unknown;
      return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
    } catch {
      return [];
    }
  });
  const [dockPins, setDockPins] = useState<DockTab[]>(() => {
    try {
      const v = JSON.parse(localStorage.getItem("mp-dock-pins") || "null") as unknown;
      if (Array.isArray(v)) {
        const ok = v.filter((t): t is DockTab => DOCK_APPS.some((x) => x.tab === t));
        if (ok.length > 0) return ok;
      }
    } catch {
      /* stockage indisponible */
    }
    return DOCK_PINNED.slice();
  });
  const toggleDeskPin = (id: string) =>
    setDeskPins((p) => {
      const n = p.includes(id) ? p.filter((x) => x !== id) : [...p, id];
      try {
        localStorage.setItem("mp-desk-pins", JSON.stringify(n));
      } catch {
        /* stockage indisponible */
      }
      return n;
    });
  const toggleDockPin = (tab: DockTab) =>
    setDockPins((p) => {
      const n = p.includes(tab) ? p.filter((x) => x !== tab) : [...p, tab];
      try {
        localStorage.setItem("mp-dock-pins", JSON.stringify(n));
      } catch {
        /* stockage indisponible */
      }
      return n;
    });

  const [iconPos, setIconPos] = useState<Record<string, { x: number; y: number }>>(() => {
    try {
      const raw = localStorage.getItem("mp-icon-pos");
      if (raw) return { ...ICON_HOME, ...(JSON.parse(raw) as Record<string, { x: number; y: number }>) };
    } catch {
      /* stockage indisponible : positions par défaut */
    }
    return ICON_HOME;
  });
  const iconPosRef = useRef(iconPos);
  iconPosRef.current = iconPos;
  const iconDrag = useRef<{ id: string; sx: number; sy: number; px: number; py: number } | null>(null);

  const iconDown = (id: string) => (e: React.PointerEvent<HTMLButtonElement>) => {
    if (e.button !== 0) return;
    const p = iconPosRef.current[id] ?? ICON_HOME[id];
    iconDrag.current = { id, sx: e.clientX, sy: e.clientY, px: p.x, py: p.y };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const iconMove = (e: React.PointerEvent<HTMLButtonElement>) => {
    const d = iconDrag.current;
    if (!d) return;
    const nx = Math.max(0, Math.min(d.px + e.clientX - d.sx, window.innerWidth - 110));
    const ny = Math.max(32, Math.min(d.py + e.clientY - d.sy, window.innerHeight - 170));
    setIconPos((pos) => ({ ...pos, [d.id]: { x: Math.round(nx), y: Math.round(ny) } }));
  };
  const iconUp = () => {
    if (!iconDrag.current) return;
    iconDrag.current = null;
    try {
      localStorage.setItem("mp-icon-pos", JSON.stringify(iconPosRef.current));
    } catch {
      /* stockage indisponible */
    }
  };

  const notify = (msg: string) => {
    setNotice(msg);
    if (noticeTimer.current) window.clearTimeout(noticeTimer.current);
    noticeTimer.current = window.setTimeout(() => setNotice(""), 3500);
  };

  const place = (n: number) => ({ x: 60 + ((n * 37) % 8) * 34, y: 56 + ((n * 53) % 8) * 30 });

  const focus = (key: string) => {
    zRef.current += 1;
    const z = zRef.current;
    setWins((ws) => ws.map((w) => (w.key === key ? { ...w, z, min: false } : w)));
    setActiveKey(key);
  };

  // Les fenêtres d'app s'ouvrent agrandies par défaut (create/about restent
  // flottantes). Le choix de l'utilisateur est conservé à la réouverture.
  const openWin = (w: Omit<Win, "z">) => {
    zRef.current += 1;
    const z = zRef.current;
    setWins((ws) => {
      const i = ws.findIndex((x) => x.key === w.key);
      if (i >= 0) {
        const next = ws.slice();
        next[i] = { ...next[i], ...w, z, min: false };
        return next;
      }
      const maxByDefault = w.kind !== "create" && w.kind !== "about";
      return [...ws, { ...w, max: w.max ?? maxByDefault, z }];
    });
    setActiveKey(w.key);
  };

  const closeWin = (key: string) =>
    setWins((ws) => {
      const next = ws.filter((w) => w.key !== key);
      const top = next.slice().sort((a, b) => b.z - a.z)[0];
      setActiveKey(top ? top.key : "");
      return next;
    });

  const openFinder = () => openWin({ key: "finder", kind: "finder", ...place(wins.length) });
  const openCreate = () => openWin({ key: "create", kind: "create", ...place(wins.length + 1) });
  const openAbout = () => openWin({ key: "about", kind: "about", ...place(wins.length + 2) });
  const openSettings = () => openWin({ key: "settings", kind: "settings", ...place(wins.length + 5) });
  const openMail = () => openWin({ key: "mail", kind: "mail", ...place(wins.length + 6) });
  const lastProject = useRef<string | null>(null);
  // Onglet demandé via une icône alors qu'aucun projet n'est ouvert :
  // mémorisé pour l'appliquer à l'ouverture depuis le Finder.
  const pendingTab = useRef<TabId | null>(null);
  const openProject = (projectId: string, tab: TabId = pendingTab.current ?? "pilotage") => {
    pendingTab.current = null;
    lastProject.current = projectId;
    openWin({ key: `project:${projectId}`, kind: "project", projectId, tab, ...place(wins.length + 3) });
  };
  const goFilter = (f: string) => {
    props.setStatus(f);
    openFinder();
  };
  const minAll = () => setWins((ws) => ws.map((w) => ({ ...w, min: true })));
  const unminAll = () => {
    setWins((ws) => ws.map((w) => ({ ...w, min: false })));
    const top = wins.slice().sort((a, b) => b.z - a.z)[0];
    if (top) focus(top.key);
  };

  const openBrain = () => {
    openWin({ key: "brain", kind: "brain", ...place(wins.length + 4) });
  };

  // Un module s'ouvre toujours sur un projet : fenêtre au premier plan,
  // puis réduite, puis dernier projet ouvert, puis projet unique, sinon Finder.
  // Exception : Connaissance est une app globale (tous projets), pas un onglet.
  const openModule = (tab: DockTab) => {
    if (tab === "connaissance") {
      openBrain();
      return;
    }
    if (tab === "settings") {
      openSettings();
      return;
    }
    if (tab === "mail") {
      openMail();
      return;
    }
    const byZ = (a: Win, b: Win) => b.z - a.z;
    const visible = wins.filter((w) => w.kind === "project" && !w.min && w.projectId).sort(byZ)[0];
    if (visible && visible.projectId) {
      openProject(visible.projectId, tab);
      return;
    }
    const hidden = wins.filter((w) => w.kind === "project" && w.projectId).sort(byZ)[0];
    if (hidden && hidden.projectId) {
      openProject(hidden.projectId, tab);
      return;
    }
    if (lastProject.current) {
      openProject(lastProject.current, tab);
      return;
    }
    if (allRows.length === 1) {
      openProject(allRows[0].id, tab);
      return;
    }
    pendingTab.current = tab;
    openFinder();
  };

  const backToFinder = (key: string) => {
    closeWin(key);
    openFinder();
  };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT")) return;
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setSpotlight(true);
      }
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "n") {
        e.preventDefault();
        openCreate();
      }
      if ((e.metaKey || e.ctrlKey) && e.altKey && e.key.toLowerCase() === "d") {
        e.preventDefault();
        toggleDockVisible();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [wins.length]);

  const rowOf = (pid?: string) => allRows.find((r) => r.id === pid);
  const winTitle = (w: Win) => {
    if (w.kind === "finder") return "Projets";
    if (w.kind === "create") return "Nouveau projet";
    if (w.kind === "about") return "À propos de ce Mac";
    if (w.kind === "brain") return "Connaissance";
    if (w.kind === "settings") return "Réglages";
    if (w.kind === "mail") return "Mails";
    const r = rowOf(w.projectId);
    return r ? `${r.code} — ${r.title}` : `Projet ${w.projectId?.slice(0, 8) ?? ""}`;
  };
  const winSize = (w: Win) => {
    if (w.kind === "finder") return { w: 920, h: 580 };
    if (w.kind === "project") return { w: 1060, h: 660 };
    if (w.kind === "create") return { w: 620, h: 480 };
    if (w.kind === "brain") return { w: 1000, h: 640 };
    if (w.kind === "settings") return { w: 820, h: 620 };
    if (w.kind === "mail") return { w: 1040, h: 660 };
    return { w: 440, h: 380 };
  };

  const today = new Date();

  return (
    <div className={`mac-wallpaper${assistantOpen ? " assistant-open" : ""}`}>
      <div className="wallpaper" />
      <MenuBar
        wins={wins}
        activeKey={activeKey}
        onFocus={focus}
        onCloseWin={closeWin}
        onFinder={openFinder}
        onCreate={openCreate}
        onModule={openModule}
        onAbout={openAbout}
        onSpotlight={() => setSpotlight(true)}
        onGoFilter={goFilter}
        onMinAll={minAll}
        onUnminAll={unminAll}
        dockSide={dockSide}
        onToggleDock={toggleDock}
        dockVisible={dockVisible}
        onToggleDockVisible={toggleDockVisible}
        theme={theme}
        onTheme={setTheme}
        assistantOpen={assistantOpen}
        onToggleAssistant={toggleAssistant}
        notify={notify}
        reload={reload}
      />

      <div className="mac-widgets">
        <button
          type="button"
          className="mac-widget"
          onClick={() => goFilter("all")}
          title="Ouvrir Projets"
        >
          <small>Agent</small>
          <strong>{props.total}</strong>
          <span>{props.total} projet(s) — {props.kpis.corriger} à corriger</span>
          <small>Ouvrir Projets</small>
        </button>
        <button
          type="button"
          className="mac-widget"
          onClick={() => goFilter("late")}
          title="Voir les retards"
        >
          <small>{today.toLocaleDateString("fr-FR", { weekday: "long" })}</small>
          <strong>{today.getDate()}</strong>
          <span>{props.kpis.retard > 0 ? `${props.kpis.retard} tâche(s) en retard` : "RAS — rien en retard"}</span>
        </button>
      </div>

      <div className="mac-desktop-files">
        <button
          type="button"
          className={selIcon === "hd" ? "selected" : ""}
          style={{ left: (iconPos.hd ?? ICON_HOME.hd).x, top: (iconPos.hd ?? ICON_HOME.hd).y }}
          onPointerDown={iconDown("hd")}
          onPointerMove={iconMove}
          onPointerUp={iconUp}
          onClick={() => setSelIcon("hd")}
          onDoubleClick={openAbout}
          title="Agent HD — glisser pour déplacer, double-clic pour les informations système"
        >
          <AppIcon.disk size={54} />
          <span>Agent HD</span>
        </button>
        <button
          type="button"
          className={selIcon === "projets" ? "selected" : ""}
          style={{ left: (iconPos.projets ?? ICON_HOME.projets).x, top: (iconPos.projets ?? ICON_HOME.projets).y }}
          onPointerDown={iconDown("projets")}
          onPointerMove={iconMove}
          onPointerUp={iconUp}
          onClick={() => setSelIcon("projets")}
          onDoubleClick={openFinder}
          title="Projets — glisser pour déplacer, double-clic pour ouvrir"
        >
          <AppIcon.finder size={54} />
          <span>Projets</span>
        </button>
        <button
          type="button"
          className={selIcon === "new" ? "selected" : ""}
          style={{ left: (iconPos.new ?? ICON_HOME.new).x, top: (iconPos.new ?? ICON_HOME.new).y }}
          onPointerDown={iconDown("new")}
          onPointerMove={iconMove}
          onPointerUp={iconUp}
          onClick={() => setSelIcon("new")}
          onDoubleClick={openCreate}
          title="Nouveau projet — glisser pour déplacer, double-clic pour créer"
        >
          <AppIcon.newdoc size={50} />
          <span>Nouveau projet</span>
        </button>
        {deskPins.map((pid, i) => {
          const r = allRows.find((x) => x.id === pid);
          if (!r) return null;
          const key = `desk:${pid}`;
          const p = iconPos[key] ?? { x: 150 + ((i * 24) % 130), y: 60 + i * 118 };
          return (
            <button
              key={key}
              type="button"
              className={selIcon === key ? "selected" : ""}
              style={{ left: p.x, top: p.y }}
              onPointerDown={iconDown(key)}
              onPointerMove={iconMove}
              onPointerUp={iconUp}
              onClick={() => setSelIcon(key)}
              onDoubleClick={() => openProject(pid)}
              onContextMenu={(e) => {
                e.preventDefault();
                setSelIcon(key);
                showCtx(e.clientX, e.clientY, [
                  { label: "Ouvrir", run: () => openProject(pid) },
                  { label: "Retirer du Bureau", run: () => toggleDeskPin(pid) },
                ]);
              }}
              title={`${r.code} — ${r.title} (double-clic pour ouvrir, clic droit pour retirer)`}
            >
              <AppIcon.folder size={54} />
              <span>{r.code || "Projet"}</span>
            </button>
          );
        })}
      </div>

      {wins
        .filter((w) => !w.min)
        .map((w) => {
          const s = winSize(w);
          return (
            <OsWindow
              key={w.key}
              win={w}
              active={w.key === activeKey}
              title={winTitle(w)}
              width={s.w}
              height={s.h}
              onFocus={() => focus(w.key)}
              onClose={() => closeWin(w.key)}
              onMin={() => setWins((ws) => ws.map((x) => (x.key === w.key ? { ...x, min: true } : x)))}
              onMax={() => setWins((ws) => ws.map((x) => (x.key === w.key ? { ...x, max: !x.max } : x)))}
              onMove={(x, y) => setWins((ws) => ws.map((x2) => (x2.key === w.key ? { ...x2, x, y } : x2)))}
              onResize={(x, y, ww, hh) => setWins((ws) => ws.map((x2) => (x2.key === w.key ? { ...x2, x, y, w: ww, h: hh } : x2)))}
              dockSide={dockSide}
              dockVisible={dockVisible}
              assistantOpen={assistantOpen}
            >
              {w.kind === "finder" && (
                <FinderView
                  rows={props.rows}
                  total={props.total}
                  query={props.query}
                  setQuery={props.setQuery}
                  status={props.status}
                  setStatus={props.setStatus}
                  onOpen={(id, tab) => openProject(id, TABS.some(t => t.id === tab) ? tab as TabId : "pilotage")}
                  onCreate={openCreate}
                  notify={notify}
                  reload={reload}
                  onCtx={showCtx}
                  deskPins={deskPins}
                  onToggleDeskPin={toggleDeskPin}
                />
              )}
              {w.kind === "project" && w.projectId && (
                <ProjectWindow
                  projectId={w.projectId}
                  initialTab={w.tab ?? "pilotage"}
                  row={rowOf(w.projectId)}
                  reloadRows={reload}
                  back={() => backToFinder(w.key)}
                />
              )}
              {w.kind === "create" && (
                <div className="mac-create">
                  <ScanImport reload={() => { reload(); }} close={() => closeWin(w.key)} />
                </div>
              )}
              {w.kind === "about" && <AboutView kpis={props.kpis} total={props.total} />}
              {w.kind === "brain" && (
                <BrainApp
                  rows={allRows}
                  onOpenProject={(id) => openProject(id, "connaissance")}
                />
              )}
              {w.kind === "settings" && (
                <SettingsApp
                  theme={theme}
                  onTheme={setTheme}
                  wallpaper={wallpaper}
                  onWallpaper={setWallpaper}
                  customColors={customColors}
                  onCustomColors={setCustomColors}
                />
              )}
              {w.kind === "mail" && <MailApp />}
            </OsWindow>
          );
        })}

      {notice && (
        <div className="mac-notice" role="status">
          <Glyph d={P.check} size={18} />
          <span>{notice}</span>
        </div>
      )}

      {dockVisible && (
        <Dock
          wins={wins}
          activeKey={activeKey}
          side={dockSide}
          zoom={dockZoom}
          onZoom={changeZoom}
          pins={dockPins}
          onCtx={showCtx}
          onUnpin={toggleDockPin}
          onFinder={openFinder}
          onCreate={openCreate}
          onModule={openModule}
          onFocus={focus}
          onLaunch={() => setLaunchpad(true)}
          onTrash={() => goFilter("closed")}
        />
      )}

      {launchpad && (
        <Launchpad
          close={() => setLaunchpad(false)}
          onModule={(tab) => { setLaunchpad(false); openModule(tab); }}
          onFinder={() => { setLaunchpad(false); openFinder(); }}
          onCreate={() => { setLaunchpad(false); openCreate(); }}
          onCtx={showCtx}
          dockPins={dockPins}
          onToggleDockPin={toggleDockPin}
        />
      )}

      {spotlight && (
        <Spotlight
          close={() => setSpotlight(false)}
          onOpen={(pid, tab) => {
            setSpotlight(false);
            openProject(pid, tab);
          }}
          activeProjectId={(() => {
            const w = wins.find((x) => x.key === activeKey);
            return w && w.kind === "project" ? w.projectId ?? null : null;
          })()}
        />
      )}

      <CtxMenu menu={ctx} close={() => setCtx(null)} />
    </div>
  );
}

function CtxMenu(props: {
  menu: { x: number; y: number; items: { label: string; run: () => void }[] } | null;
  close: () => void;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") props.close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [props.close]);
  if (!props.menu) return null;
  const { menu } = props;
  return (
    <>
      <div
        style={{ position: "fixed", inset: 0, zIndex: 9599 }}
        onClick={props.close}
        onContextMenu={(e) => { e.preventDefault(); props.close(); }}
      />
      <div
        className="mac-menu-drop"
        role="menu"
        style={{
          position: "fixed",
          left: Math.max(8, Math.min(menu.x, window.innerWidth - 260)),
          top: Math.max(34, Math.min(menu.y, window.innerHeight - menu.items.length * 30 - 20)),
          zIndex: 9600,
        }}
      >
        {menu.items.map((it, i) => (
          <button key={i} type="button" role="menuitem" onClick={() => { props.close(); it.run(); }}>
            {it.label}
          </button>
        ))}
      </div>
    </>
  );
}

function OsWindow(props: {
  win: Win;
  active: boolean;
  title: string;
  width: number;
  height: number;
  onFocus: () => void;
  onClose: () => void;
  onMin: () => void;
  onMax: () => void;
  onMove: (x: number, y: number) => void;
  onResize: (x: number, y: number, w: number, h: number) => void;
  dockSide: "bottom" | "left";
  dockVisible: boolean;
  children: React.ReactNode;
  assistantOpen: boolean;
}) {
  const { win } = props;
  const drag = useRef<{ dx: number; dy: number } | null>(null);
  const rz = useRef<{ dir: string; sx: number; sy: number; x0: number; y0: number; w0: number; h0: number } | null>(null);

  const W = Math.max(420, win.w ?? props.width);
  const H = Math.max(280, win.h ?? props.height);

  // Plein écran : épouse l'espace libre, réserve du Dock incluse quand il est visible.
  const dockInset = props.dockVisible ? 1 : 0;
  const rightInset = props.assistantOpen ? "calc(25vw + 8px)" : 8;
  const availableWidth = window.innerWidth * (props.assistantOpen ? 0.75 : 1);
  const style: React.CSSProperties = win.max
    ? props.dockSide === "left" && dockInset
      ? { left: 104, top: 38, right: rightInset, bottom: 8, zIndex: 1000 + win.z }
      : { left: 8, top: 38, right: rightInset, bottom: dockInset ? 86 : 8, zIndex: 1000 + win.z }
    : {
        left: Math.max(8, Math.min(win.x, availableWidth - Math.min(W, availableWidth - 16) - 8)),
        top: Math.max(32, win.y),
        width: Math.min(W, availableWidth - 16),
        height: Math.min(H, window.innerHeight - (dockInset ? 140 : 60)),
        zIndex: 1000 + win.z,
      };

  const startResize = (dir: string) => (e: React.PointerEvent<HTMLDivElement>) => {
    e.stopPropagation();
    e.preventDefault();
    props.onFocus();
    rz.current = { dir, sx: e.clientX, sy: e.clientY, x0: win.x, y0: win.y, w0: W, h0: H };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const moveResize = (e: React.PointerEvent<HTMLDivElement>) => {
    const r = rz.current;
    if (!r) return;
    const dx = e.clientX - r.sx;
    const dy = e.clientY - r.sy;
    let x = r.x0;
    let y = r.y0;
    let w = r.w0;
    let h = r.h0;
    if (r.dir.includes("e")) w = r.w0 + dx;
    if (r.dir.includes("s")) h = r.h0 + dy;
    if (r.dir.includes("w")) { x = r.x0 + dx; w = r.w0 - dx; }
    if (r.dir.includes("n")) { y = r.y0 + dy; h = r.h0 - dy; }
    if (w < 420) {
      if (r.dir.includes("w")) x -= 420 - w;
      w = 420;
    }
    if (h < 280) {
      if (r.dir.includes("n")) y -= 280 - h;
      h = 280;
    }
    props.onResize(x, Math.max(32, y), Math.round(w), Math.round(h));
  };
  const endResize = () => {
    rz.current = null;
  };

  return (
    <section
      className={`mac-window${props.active ? "" : " inactive"}`}
      style={style}
      onMouseDown={props.onFocus}
      aria-label={props.title}
    >
      {!win.max && (
        <>
          <div className="mac-rz rz-n" onPointerDown={startResize("n")} onPointerMove={moveResize} onPointerUp={endResize} />
          <div className="mac-rz rz-s" onPointerDown={startResize("s")} onPointerMove={moveResize} onPointerUp={endResize} />
          <div className="mac-rz rz-e" onPointerDown={startResize("e")} onPointerMove={moveResize} onPointerUp={endResize} />
          <div className="mac-rz rz-w" onPointerDown={startResize("w")} onPointerMove={moveResize} onPointerUp={endResize} />
          <div className="mac-rz rz-ne" onPointerDown={startResize("ne")} onPointerMove={moveResize} onPointerUp={endResize} />
          <div className="mac-rz rz-nw" onPointerDown={startResize("nw")} onPointerMove={moveResize} onPointerUp={endResize} />
          <div className="mac-rz rz-se" onPointerDown={startResize("se")} onPointerMove={moveResize} onPointerUp={endResize} />
          <div className="mac-rz rz-sw" onPointerDown={startResize("sw")} onPointerMove={moveResize} onPointerUp={endResize} />
        </>
      )}
      <header
        className="mac-titlebar"
        onPointerDown={(e) => {
          if ((e.target as HTMLElement).closest("button") || win.max) return;
          drag.current = { dx: e.clientX - win.x, dy: e.clientY - win.y };
          (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (!drag.current) return;
          props.onMove(e.clientX - drag.current.dx, e.clientY - drag.current.dy);
        }}
        onPointerUp={() => { drag.current = null; }}
        onDoubleClick={props.onMax}
      >
        <span className="mac-traffic">
          <button type="button" className="close" title="Fermer" onClick={props.onClose} />
          <button type="button" className="min" title="Réduire" onClick={props.onMin} />
          <button type="button" className="max" title="Agrandir" onClick={props.onMax} />
        </span>
        <span className="mac-win-title">{props.title}</span>
        <span className="mac-title-actions">
          <button type="button" title="Options de mosaïque" onClick={props.onMax}>
            <Glyph d={P.tiling} size={13} />
          </button>
        </span>
      </header>
      <div className="mac-win-body">{props.children}</div>
    </section>
  );
}

function MenuBar(props: {
  wins: Win[];
  activeKey: string;
  onFocus: (key: string) => void;
  onCloseWin: (key: string) => void;
  onFinder: () => void;
  onCreate: () => void;
  onModule: (tab: DockTab) => void;
  onAbout: () => void;
  onSpotlight: () => void;
  onGoFilter: (f: string) => void;
  onMinAll: () => void;
  onUnminAll: () => void;
  dockSide: "bottom" | "left";
  onToggleDock: () => void;
  dockVisible: boolean;
  onToggleDockVisible: () => void;
  theme: string;
  onTheme: (t: string) => void;
  assistantOpen: boolean;
  onToggleAssistant: () => void;
  notify: (msg: string) => void;
  reload: () => Promise<void>;
}) {
  const [menu, setMenu] = useState<string | null>(null);
  const [now, setNow] = useState(new Date());
  const [ai, setAi] = useState<any>(null);
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 10000);
    return () => clearInterval(t);
  }, []);
  useEffect(() => {
    api.aiStatus().then(setAi).catch(() => setAi(null));
  }, []);

  const active = props.wins.find((w) => w.key === props.activeKey);
  const activeProjectId = active && active.kind === "project" ? active.projectId : undefined;

  const close = () => setMenu(null);
  const go = (fn: () => void) => () => { close(); fn(); };

  const exportActive = async () => {
    if (!activeProjectId) return;
    const dump: any = await api.exportProject(activeProjectId);
    const blob = new Blob([JSON.stringify(dump, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `minipilot-${dump?.project?.code || activeProjectId.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    props.notify("Projet exporté en JSON");
    close();
  };

  const importJson = async (f: File) => {
    try {
      await withActivity("Importation d’un projet JSON…", async () => {
        const data = JSON.parse(await f.text());
        const created: any = await api.importJson(data);
        props.notify(`Projet importé : ${created.code}`);
        await props.reload();
      });
    } catch (err: any) {
      alert(String(err.message || err));
    }
    close();
  };

  const drop = (id: string, body: React.ReactNode) => (
    <div className="mac-menu" key={id}>
      <button
        type="button"
        className={menu === id ? "open" : ""}
        onClick={() => setMenu(menu === id ? null : id)}
      >
        {id === "logo" ? "◈" : id === "Applications" ? <strong>Applications</strong> : id}
      </button>
      {menu === id && (
        <>
          <div style={{ position: "fixed", inset: 0, zIndex: 8999 }} onClick={close} />
          <div className="mac-menu-drop">{body}</div>
        </>
      )}
    </div>
  );

  return (
    <header className="mac-menubar">
      <div style={{ display: "flex", alignItems: "center" }}>
        {drop("logo", (
          <button type="button" onClick={go(props.onAbout)}>À propos de Agent</button>
        ))}
        {drop("Applications", (
          <>
            <button type="button" onClick={go(props.onFinder)}>Projets</button>
            <button type="button" onClick={go(props.onCreate)}>
              Nouveau projet… <span className="kbd">⌘N</span>
            </button>
            <hr />
            {DOCK_APPS.map((a) => (
              <button type="button" key={a.tab} onClick={() => { close(); props.onModule(a.tab); }}>
                {a.label}
              </button>
            ))}
          </>
        ))}        {drop("Fichier", (
          <>
            <button type="button" onClick={go(props.onCreate)}>
              Nouveau projet… <span className="kbd">⌘N</span>
            </button>
            <button type="button" onClick={() => document.getElementById("mac-import-json")?.click()}>
              Importer un projet JSON…
            </button>
            <input
              id="mac-import-json"
              type="file"
              accept="application/json"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) importJson(f);
                e.target.value = "";
              }}
            />
            <button type="button" disabled={!activeProjectId} onClick={exportActive}>
              Exporter la fenêtre active (JSON)
            </button>
            <hr />
            <button type="button" disabled={!active} onClick={() => { if (active) props.onCloseWin(active.key); close(); }}>
              Fermer la fenêtre
            </button>
          </>
        ))}
        {drop("Édition", (
          <>
            <button type="button" onClick={go(props.onSpotlight)}>
              Rechercher dans Agent <span className="kbd">⌘K</span>
            </button>
            <hr />
            <button type="button" onClick={async () => { close(); await props.reload(); props.notify("Données rafraîchies"); }}>
              Rafraîchir les données
            </button>
          </>
        ))}
        {drop("Affichage", (
          <>
            <button type="button" onClick={go(props.onUnminAll)}>Tout ramener au premier plan</button>
            <button type="button" onClick={go(props.onMinAll)}>Réduire toutes les fenêtres</button>
            <hr />
            <button type="button" onClick={go(props.onToggleDock)}>
              {props.dockSide === "bottom" ? "Placer le Dock à gauche" : "Placer le Dock en bas"}
            </button>
            <button type="button" onClick={go(props.onToggleDockVisible)}>
              {props.dockVisible ? "Masquer le Dock" : "Afficher le Dock"} <span className="kbd">⌥⌘D</span>
            </button>
            <button type="button" onClick={go(props.onToggleAssistant)}>
              {props.assistantOpen ? "Masquer l'assistant" : "Afficher l'assistant"}
            </button>
            <hr />
            {THEMES.map((t) => (
              <button key={t.id} type="button" onClick={go(() => props.onTheme(t.id))}>
                {props.theme === t.id ? "● " : "○ "}Thème {t.label}
              </button>
            ))}
          </>
        ))}
        {drop("Aller", (
          <>
            <button type="button" onClick={go(() => props.onGoFilter("all"))}>Projets</button>
            <button type="button" onClick={go(props.onCreate)}>Nouveau projet</button>
            <button type="button" onClick={go(() => props.onGoFilter("closed"))}>Corbeille</button>
            <hr />
            <button type="button" onClick={() => { close(); props.onModule("settings"); }}>Réglages…</button>
            <button type="button" onClick={go(props.onAbout)}>À propos</button>
          </>
        ))}
        {drop("Fenêtre", (
          <>
            <button type="button" onClick={go(props.onFinder)}>Projets</button>
            <button type="button" onClick={go(props.onSpotlight)}>
              Recherche Spotlight <span className="kbd">⌘K</span>
            </button>
            <hr />
            {props.wins.length === 0 && <button type="button" disabled>Aucune fenêtre</button>}
            {props.wins.map((w) => (
              <button type="button" key={w.key} onClick={() => { props.onFocus(w.key); close(); }}>
                <span>{w.key === props.activeKey ? "● " : "○ "}{w.kind === "finder" ? "Projets" : w.kind === "create" ? "Nouveau projet" : w.kind === "about" ? "À propos" : w.kind === "brain" ? "Connaissance" : w.kind === "settings" ? "Réglages" : w.kind === "mail" ? "Mails" : `Projet ${w.projectId?.slice(0, 8)}…`}</span>
              </button>
            ))}
          </>
        ))}
        {drop("Aide", (
          <>
            <button type="button" onClick={async () => { close(); await props.reload(); }}>Rafraîchir les données</button>
            <button type="button" onClick={go(props.onAbout)}>Raccourcis clavier</button>
          </>
        ))}
      </div>
      <span className="spacer" />
      <span className="mac-status">
        {ai && (
          <span className={ai.reachable ? "ai-ok" : "ai-ko"} title={ai.reachable ? `IA connectée (${ai.model})` : "IA non connectée — saisie manuelle"}>
            ● IA
          </span>
        )}
        <button type="button" onClick={async () => { await props.reload(); props.notify("Données synchronisées"); }} title="Synchroniser">
          <Glyph d={P.sync} size={16} />
        </button>
        <button type="button" onClick={props.onSpotlight} title="Recherche Spotlight (⌘K)">
          <Glyph d={P.search} size={16} />
        </button>
        <div className="mac-menu" style={{ display: "inline-flex" }}>
          <button type="button" className={menu === "cc" ? "open" : ""} onClick={() => setMenu(menu === "cc" ? null : "cc")} title="Centre de contrôle" style={{ display: "inline-flex" }}>
            <Glyph d={P.ctrlCenter} size={19} />
          </button>
          {menu === "cc" && (
            <>
              <div style={{ position: "fixed", inset: 0, zIndex: 8999 }} onClick={close} />
              <div className="mac-menu-drop" style={{ left: "auto", right: 0 }}>
                <button type="button" onClick={go(props.onUnminAll)}>Tout ramener au premier plan</button>
                <button type="button" onClick={go(props.onMinAll)}>Réduire toutes les fenêtres</button>
              </div>
            </>
          )}
        </div>
        <button type="button" className="menu-clock" onClick={props.onSpotlight} title="Ouvrir la recherche">
          {now.toLocaleDateString("fr-FR", { weekday: "short", day: "numeric", month: "short" })}{" "}
          {now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}
        </button>
      </span>
    </header>
  );
}

function Dock(props: {
  wins: Win[];
  activeKey: string;
  side: "bottom" | "left";
  zoom: number;
  onZoom: (z: number) => void;
  pins: DockTab[];
  onCtx: (x: number, y: number, items: { label: string; run: () => void }[]) => void;
  onUnpin: (tab: DockTab) => void;
  onFinder: () => void;
  onCreate: () => void;
  onModule: (tab: DockTab) => void;
  onFocus: (key: string) => void;
  onLaunch: () => void;
  onTrash: () => void;
}) {
  const minimized = props.wins.filter((w) => w.min);
  const running = (kind: WinKind) => props.wins.some((w) => w.kind === kind && !w.min);
  const pinned = DOCK_APPS.filter((a) => props.pins.includes(a.tab));
  const z = props.zoom;
  const scaleDrag = useRef<{ sx: number; sy: number; z0: number } | null>(null);
  return (
    <nav className={`mac-dock${props.side === "left" ? " left" : ""}`} aria-label="Dock">
      <button type="button" className="mac-dock-app" aria-label="Toutes les applications" onClick={props.onLaunch}>
        <span className="dock-tooltip">Apps</span>
        <AppIcon.launchpad size={z} />
      </button>
      <button type="button" className="mac-dock-app" aria-label="Ouvrir Projets" onClick={props.onFinder}>
        <span className="dock-tooltip">Projets</span>
        <AppIcon.finder size={z} />
        {running("finder") && <span className="dot" />}
      </button>
      <button type="button" className="mac-dock-app" aria-label="Nouveau projet" onClick={props.onCreate}>
        <span className="dock-tooltip">Nouveau projet</span>
        <AppIcon.newdoc size={z} />
      </button>
      {pinned.map((a) => (
        <button
          key={a.tab}
          type="button"
          className="mac-dock-app"
          aria-label={`Ouvrir ${a.label}`}
          onClick={() => props.onModule(a.tab)}
          onContextMenu={(e) => {
            e.preventDefault();
            props.onCtx(e.clientX, e.clientY, [
              { label: `Ouvrir ${a.label}`, run: () => props.onModule(a.tab) },
              { label: "Retirer du Dock", run: () => props.onUnpin(a.tab) },
            ]);
          }}
        >
          <span className="dock-tooltip">{a.label}</span>
          <a.icon size={z} />
        </button>
      ))}
      <span className="mac-dock-divider" />
      {minimized.map((w) => (
        <button
          key={w.key}
          type="button"
          className="mac-dock-app"
          aria-label={`Restaurer ${w.key}`}
          onClick={() => props.onFocus(w.key)}
        >
          <span className="dock-tooltip">{w.kind === "finder" ? "Projets" : w.kind === "project" ? "Projet" : w.kind === "brain" ? "Connaissance" : w.kind === "settings" ? "Réglages" : w.kind === "mail" ? "Mails" : w.kind}</span>
          {(w.kind === "finder" || w.kind === "project") ? (
            <AppIcon.finder size={z} />
          ) : w.kind === "brain" ? (
            <AppIcon.notes size={z} />
          ) : w.kind === "settings" ? (
            <AppIcon.settings size={z} />
          ) : w.kind === "mail" ? (
            <AppIcon.mail size={z} />
          ) : (
            <svg width={Math.round(z * 0.88)} height={Math.round(z * 0.88)} viewBox="0 0 48 48" aria-hidden="true">
              <rect x="4" y="8" width="40" height="32" rx="6" fill="#e5e5ea" stroke="#8e8e93" />
              <rect x="4" y="8" width="40" height="9" rx="6" fill="#c7c7cc" />
              <circle cx="11" cy="12.5" r="2" fill="#ff5f57" />
              <circle cx="18" cy="12.5" r="2" fill="#febc2e" />
            </svg>
          )}
        </button>
      ))}
      {minimized.length > 0 && <span className="mac-dock-divider" />}
      <button type="button" className="mac-dock-app" aria-label="Ouvrir la corbeille" onClick={props.onTrash}>
        <span className="dock-tooltip">Corbeille</span>
        <AppIcon.trash size={z} />
      </button>
      <div
        className="mac-dock-scale"
        title="Taille des icônes — glisser pour ajuster"
        onPointerDown={(e) => {
          e.preventDefault();
          e.currentTarget.setPointerCapture(e.pointerId);
          scaleDrag.current = { sx: e.clientX, sy: e.clientY, z0: props.zoom };
        }}
        onPointerMove={(e) => {
          const d = scaleDrag.current;
          if (!d) return;
          const delta = props.side === "left" ? e.clientY - d.sy : e.clientX - d.sx;
          props.onZoom(d.z0 + delta * 0.12);
        }}
        onPointerUp={() => {
          scaleDrag.current = null;
        }}
      />
    </nav>
  );
}

function Launchpad(props: {
  close: () => void;
  onModule: (tab: DockTab) => void;
  onFinder: () => void;
  onCreate: () => void;
  onCtx: (x: number, y: number, items: { label: string; run: () => void }[]) => void;
  dockPins: DockTab[];
  onToggleDockPin: (tab: DockTab) => void;
}) {
  const [q, setQ] = useState("");
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") props.close();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [props.close]);
  const apps = DOCK_APPS.filter((a) =>
    a.label.toLowerCase().includes(q.trim().toLowerCase()),
  );
  return (
    <div className="mac-launchpad" onMouseDown={(e) => { if (e.target === e.currentTarget) props.close(); }}>
      <input
        className="lp-search"
        autoFocus
        aria-label="Rechercher une application"
        placeholder="Rechercher"
        value={q}
        onChange={(e) => setQ(e.target.value)}
      />
      <div className="lp-grid">
        <button type="button" className="lp-app" onClick={props.onFinder}>
          <AppIcon.finder size={64} /> Projets
        </button>
        <button type="button" className="lp-app" onClick={props.onCreate}>
          <AppIcon.newdoc size={64} /> Nouveau projet
        </button>
        {apps.map((a) => (
          <button
            key={a.tab}
            type="button"
            className="lp-app"
            onClick={() => props.onModule(a.tab)}
            onContextMenu={(e) => {
              e.preventDefault();
              props.onCtx(e.clientX, e.clientY, [
                { label: `Ouvrir ${a.label}`, run: () => props.onModule(a.tab) },
                {
                  label: props.dockPins.includes(a.tab) ? "Retirer du Dock" : "Épingler au Dock",
                  run: () => props.onToggleDockPin(a.tab),
                },
              ]);
            }}
          >
            <a.icon size={64} /> {a.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function FinderView(props: {
  rows: PortfolioRow[];
  total: number;
  query: string;
  setQuery: (v: string) => void;
  status: string;
  setStatus: (v: string) => void;
  onOpen: (id: string, tab?: string) => void;
  onCreate: () => void;
  notify: (msg: string) => void;
  reload: () => Promise<void>;
  onCtx: (x: number, y: number, items: { label: string; run: () => void }[]) => void;
  deskPins: string[];
  onToggleDeskPin: (id: string) => void;
}) {
  const [sel, setSel] = useState<string | null>(null);
  const [view, setView] = useState<"icon" | "list">("list");
  const histRef = useRef<string[]>([props.status]);
  const [hi, setHi] = useState(0);

  useEffect(() => {
    if (histRef.current[hi] !== props.status) {
      histRef.current = [...histRef.current.slice(0, hi + 1), props.status];
      setHi(histRef.current.length - 1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.status]);

  const select = (f: string) => {
    setSel(null);
    histRef.current = [...histRef.current.slice(0, hi + 1), f];
    setHi(histRef.current.length - 1);
    props.setStatus(f);
  };
  const back = () => {
    if (hi > 0) {
      props.setStatus(histRef.current[hi - 1]);
      setHi(hi - 1);
      setSel(null);
    }
  };
  const fwd = () => {
    if (hi < histRef.current.length - 1) {
      props.setStatus(histRef.current[hi + 1]);
      setHi(hi + 1);
      setSel(null);
    }
  };

  const favs = [
    { id: "all", label: "Projets", icon: P.folder },
    { id: "late", label: "En retard", icon: P.clock },
    { id: "todo", label: "À corriger", icon: P.alert },
  ];
  const label = FILTER_LABELS[props.status] ?? "Projets";
  const selected = props.rows.find((r) => r.id === sel);

  const doImport = async (f: File) => {
    try {
      await withActivity("Importation d’un projet JSON…", async () => {
        const data = JSON.parse(await f.text());
        const created: any = await api.importJson(data);
        props.notify(`Projet importé : ${created.code}`);
        await props.reload();
      });
    } catch (err: any) {
      alert(String(err.message || err));
    }
  };
  const doExportRow = async (r: PortfolioRow) => {
    const dump: any = await api.exportProject(r.id);
    const blob = new Blob([JSON.stringify(dump, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `minipilot-${dump?.project?.code || r.id.slice(0, 8)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    props.notify(`Projet exporté : ${dump?.project?.code || ""}`);
  };
  const doExport = () => {
    if (selected) doExportRow(selected);
  };
  const rowMenu = (r: PortfolioRow) => [
    { label: "Ouvrir", run: () => props.onOpen(r.id) },
    {
      label: props.deskPins.includes(r.id) ? "Retirer du Bureau" : "Épingler au Bureau",
      run: () => props.onToggleDeskPin(r.id),
    },
    { label: "Exporter en JSON", run: () => doExportRow(r) },
  ];

  return (
    <div className="mac-finder">
      <div className="mac-finder-body">
        <aside className="mac-finder-side" aria-label="Emplacements">
          <div className="side-title">Favoris</div>
          {favs.map((s) => (
            <button
              key={s.id}
              type="button"
              className={props.status === s.id ? "selected" : ""}
              onClick={() => select(s.id)}
            >
              <Glyph d={s.icon} size={18} /> {s.label}
            </button>
          ))}
          <button
            type="button"
            className={props.status === "closed" ? "selected" : ""}
            onClick={() => select("closed")}
          >
            <Glyph d={P.trash} size={18} /> Corbeille
          </button>
          <div className="side-foot">
            <Glyph d={P.cloud} size={15} />
            <span>Espace local</span>
          </div>
        </aside>

        <div className="mac-finder-main">
          <div className="mac-toolbar">
            <span className="hist">
              <button type="button" aria-label="Précédent" title="Précédent" disabled={hi <= 0} onClick={back}>
                <Glyph d={P.chevL} size={18} />
              </button>
              <button type="button" aria-label="Suivant" title="Suivant" disabled={hi >= histRef.current.length - 1} onClick={fwd}>
                <Glyph d={P.chevR} size={18} />
              </button>
            </span>
            <strong className="mac-folder-title">{label}</strong>
            <span className="spacer" />
            <span className="mac-view-switch">
              <button type="button" className={view === "icon" ? "active" : ""} aria-label="Présentation par icônes" aria-pressed={view === "icon"} onClick={() => setView("icon")}>
                <Glyph d={P.grid} size={16} />
              </button>
              <button type="button" className={view === "list" ? "active" : ""} aria-label="Présentation par liste" aria-pressed={view === "list"} onClick={() => setView("list")}>
                <Glyph d={P.list} size={16} />
              </button>
            </span>
            <label className="mac-finder-search">
              <Glyph d={P.search} size={15} />
              <input
                aria-label={`Rechercher dans ${label}`}
                placeholder="Rechercher"
                value={props.query}
                onChange={(e) => props.setQuery(e.target.value)}
              />
            </label>
          </div>

          <div className="mac-actions">
            <button type="button" title="Nouveau projet" onClick={props.onCreate}>
              <Glyph d={P.folder} size={16} /><span>Nouveau dossier</span>
            </button>
            <label style={{ display: "contents" }}>
              <button type="button" title="Importer un projet JSON" onClick={() => document.getElementById("mac-finder-import")?.click()}>
                <Glyph d={P.download} size={16} /><span>Importer</span>
              </button>
              <input
                id="mac-finder-import"
                type="file"
                accept="application/json"
                hidden
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) doImport(f);
                  e.target.value = "";
                }}
              />
            </label>
            <span className="spacer" />
            <button type="button" disabled={!selected} title="Ouvrir l'élément sélectionné" onClick={() => selected && props.onOpen(selected.id)}>
              <Glyph d={P.openExt} size={16} /><span>Ouvrir</span>
            </button>
            <button type="button" disabled={!selected} title="Exporter l'élément sélectionné (JSON)" onClick={doExport}>
              <Glyph d={P.exportUp} size={16} /><span>Exporter</span>
            </button>
          </div>

          <div className="mac-files">
            <ActionDashboard onOpen={props.onOpen} revision={props.rows} />
            {props.rows.length === 0 ? (
              <EmptyState title="Aucun projet" detail="Crée ton premier projet pour démarrer le pilotage." />
            ) : view === "icon" ? (
              <div className="mac-file-grid" role="listbox" aria-label={label}>
                {props.rows.map((r) => (
                  <button
                    key={r.id}
                    type="button"
                    role="option"
                    aria-selected={sel === r.id}
                    className={`mac-file${sel === r.id ? " selected" : ""}`}
                    onClick={() => setSel(r.id)}
                    onDoubleClick={() => props.onOpen(r.id)}
                    onContextMenu={(e) => { e.preventDefault(); setSel(r.id); props.onCtx(e.clientX, e.clientY, rowMenu(r)); }}
                    title={`${r.code} — ${r.title} (double-clic pour ouvrir, clic droit pour épingler)`}
                  >
                    <AppIcon.folder size={55} />
                    <span className="fname">{r.code || "Sans code"}{r.client_name ? ` — ${r.client_name}` : ""}</span>
                    <span className="fmeta">{r.title}</span>
                    {(r.corrections > 0 || r.en_retard > 0) && (
                      <span className="fwarn">⚠ {r.corrections > 0 ? `${r.corrections} à corriger` : ""}{r.corrections > 0 && r.en_retard > 0 ? " · " : ""}{r.en_retard > 0 ? `${r.en_retard} en retard` : ""}</span>
                    )}
                  </button>
                ))}
              </div>
            ) : (
              <table className="mac-file-list">
                <thead><tr><th>Projet</th><th>Code</th><th>Client</th><th>Jalon en cours</th><th>Échéance</th><th>Avancement</th><th>Tâches</th><th>Retard</th><th>À corriger</th></tr></thead>
                <tbody>
                  {props.rows.map((r) => (
                    <tr
                      key={r.id}
                      className={sel === r.id ? "selected" : ""}
                      onClick={() => setSel(r.id)}
                      onDoubleClick={() => props.onOpen(r.id)}
                      onContextMenu={(e) => { e.preventDefault(); setSel(r.id); props.onCtx(e.clientX, e.clientY, rowMenu(r)); }}
                      title="Double-clic pour ouvrir, clic droit pour épingler"
                    >
                      <td><b>{r.title}</b></td>
                      <td>{r.code || "—"}</td>
                      <td>{r.client_name || "—"}</td>
                      <td>{r.jalon_en_cours}</td>
                      <td>{r.jalon_echeance || "—"}</td>
                      <td>
                        <span style={{ display: "inline-flex", alignItems: "center", gap: 6 }}>
                          <span style={{ width: 60, height: 6, borderRadius: 3, background: "rgba(0,0,0,0.12)", overflow: "hidden" }}>
                            <span style={{ display: "block", height: "100%", width: `${r.avancement}%`, background: "#0a84ff" }} />
                          </span>
                          {r.avancement}%
                        </span>
                      </td>
                      <td>{r.taches}</td>
                      <td>{r.en_retard > 0 ? `${r.en_retard}` : "—"}</td>
                      <td>{r.corrections > 0 ? `${r.corrections}` : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <nav className="mac-crumbs" aria-label="Chemin du dossier">
            <button type="button" onClick={() => select("all")}>Projets</button>
            {props.status !== "all" && (
              <>
                <Glyph d={P.chevR} size={11} />
                <span>{label}</span>
              </>
            )}
          </nav>
          <footer className="mac-statusbar">
            {props.rows.length} élément(s) · /Projets
          </footer>
        </div>
      </div>
    </div>
  );
}

export function ProjectWindow(props: {
  projectId: string;
  initialTab: TabId;
  row?: PortfolioRow;
  reloadRows: () => Promise<void>;
  back: () => void;
  onTabChange?: (tab: TabId) => boolean | void;
  sidebarNavigation?: boolean;
  kiaraPresentation?: boolean;
}) {
  const { detail, items, sources, meetings, error, refresh } = useProjectData(props.projectId, props.reloadRows);
  const [tab, setTab] = useState<TabId>(TABS.some(t => t.id === props.initialTab) ? props.initialTab : "pilotage");
  const [cdcTab, setCdcTab] = useState<"sources" | "revue" | "synthese" | "controles" | "transfert">("sources");
  const [editing, setEditing] = useState(false);
  const [aiStatus, setAiStatus] = useState<{ reachable: boolean; detail: string } | null>(null);
  useEffect(() => {
    setTab(TABS.some(t => t.id === props.initialTab) ? props.initialTab : "pilotage");
  }, [props.initialTab]);
  useEffect(() => {
    api.aiStatus().then((s: any) => setAiStatus({ reachable: !!s.reachable, detail: s.detail || "" }))
      .catch(() => setAiStatus(null));
  }, []);
  const analysis = useCdcJobs(props.projectId, refresh);
  if (!props.row) return <EmptyState title="Projet introuvable" detail="Il a peut-être été filtré ou supprimé." />;
  if (error && !detail) return <ErrorState message={error} retry={refresh} />;
  if (!detail) return <LoadingState label="Chargement du projet" />;
  return (
    <>{error && <ErrorState message={error} retry={refresh} />}<Detail
      current={props.row}
      detail={detail}
      items={items}
      sources={sources}
      meetings={meetings}
      tab={tab}
      setTab={value => props.onTabChange ? props.onTabChange(value) : setTab(value)}
      cdcTab={cdcTab}
      setCdcTab={setCdcTab}
      analyze={analysis.enqueue}
      analyzing={analysis.running}
      analyzeMsg=""
      jobs={analysis.jobs} jobsError={analysis.error} cancelJob={analysis.cancel} retryJob={analysis.retry}
      aiStatus={aiStatus}
      editing={editing}
      setEditing={setEditing}
      back={props.back}
      refresh={refresh}
      sidebarNavigation={props.sidebarNavigation}
      kiaraPresentation={props.kiaraPresentation}
    /></>
  );
}

function Spotlight(props: {
  close: () => void;
  onOpen: (projectId: string, tab: TabId) => void;
  activeProjectId?: string | null;
  activeTab?: TabId;
}) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<SearchHit[]>([]);
  // ⌘K dans une fenêtre projet = recherche restreinte au projet.
  // Échap ferme la recherche ; un 2e Échap l'élargit à tout le portefeuille.
  const [wide, setWide] = useState(!props.activeProjectId);
  useEffect(() => {
    setWide(!props.activeProjectId);
  }, [props.activeProjectId]);
  useEffect(() => {
    if (q.trim().length < 2) {
      setHits([]);
      return;
    }
    const scope = !wide ? props.activeProjectId : null;
    const timer = setTimeout(async () => {
      try {
        setHits((await api.search(q.trim(), scope ?? undefined)) as SearchHit[]);
      } catch {
        setHits([]);
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [q, wide, props.activeProjectId]);
  const openHit = (h: SearchHit) => {
    if (!wide && props.activeProjectId) {
      // Déjà dans le projet : on change juste d'onglet vers le résultat.
      props.onOpen(props.activeProjectId, (TABS.some((t) => t.id === h.tab) ? h.tab : "pilotage") as TabId);
    } else {
      props.onOpen(h.project_id, (TABS.some((t) => t.id === h.tab) ? h.tab : "pilotage") as TabId);
    }
  };
  return (
    <div className="mac-spotlight-back" onMouseDown={(e) => { if (e.target === e.currentTarget) props.close(); }}>
      <div className="mac-spotlight">
        <input
          autoFocus
          aria-label="Recherche Spotlight"
          placeholder={
            !wide && props.activeProjectId
              ? "🔍 Dans ce projet — tâches, CDC, CR… (Échap : tout Agent)"
              : "🔍 Spotlight — projets, tâches, CDC, CR…"
          }
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              if (!wide && props.activeProjectId && q.trim()) {
                setWide(true);
              } else {
                props.close();
              }
            }
            if (e.key === "Enter" && hits.length > 0) {
              openHit(hits[0]);
            }
          }}
        />
        {!wide && props.activeProjectId && (
          <div className="spot-scope">
            <span>Recherche restreinte au projet actif</span>
            <button type="button" onClick={() => setWide(true)}>Élargir à tout Agent</button>
          </div>
        )}
        {hits.length > 0 && (
          <div className="hits">
            {hits.map((h, i) => (
              <button
                key={`${h.type}-${h.project_id}-${i}`}
                type="button"
                onClick={() => openHit(h)}
              >
                <Badge value={h.type} tone="neutral" /> {h.label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function AboutView(props: { kpis: { n: number; corriger: number; retard: number; raf: number }; total: number }) {
  return (
    <div className="mac-about">
      <div className="mac-logo">◈</div>
      <strong>Agent</strong>
      <span>Version 0.4.0 — connaissance projet et ERP local.</span>
      <table className="data-table compact">
        <tbody>
          <tr><td>Projets</td><td><b>{props.total}</b></td></tr>
          <tr><td>Projets à corriger</td><td><b>{props.kpis.corriger}</b></td></tr>
          <tr><td>Tâches en retard</td><td><b>{props.kpis.retard}</b></td></tr>
          <tr><td>RAF total</td><td><b>{props.kpis.raf} h</b></td></tr>
        </tbody>
      </table>
      <small style={{ color: "#636366" }}>
        Backend FastAPI + SQLite local · ⌘K recherche (restreinte au projet actif, Échap pour élargir) · ⌘N nouveau projet · double-clic pour ouvrir.
      </small>
    </div>
  );
}

function CdcActionList({items,onOpen}:{items:CdcItem[];onOpen:(item:CdcItem)=>void}) {
  const [query,setQuery]=useState(''),[kind,setKind]=useState('all'),[offset,setOffset]=useState(0);
  const filtered=items.filter(item=>(kind==='all'||item.kind===kind)&&`${item.id} ${item.title} ${item.source_quote}`.toLocaleLowerCase('fr-FR').includes(query.toLocaleLowerCase('fr-FR')));
  const pageOffset=Math.min(offset,Math.max(0,Math.ceil(filtered.length/20)-1)*20);
  const rows=filtered.slice(pageOffset,pageOffset+20);
  return <section aria-label="Points CDC à traiter"><div className="workspace-toolbar"><label className="ux-field">Rechercher un point<input className="input" type="search" value={query} onChange={e=>{setQuery(e.target.value);setOffset(0);}}/></label><label className="ux-field">Type<select className="input" value={kind} onChange={e=>{setKind(e.target.value);setOffset(0);}}><option value="all">Tous les types</option>{KINDS.map(k=><option key={k} value={k}>{kindLabel(k)}</option>)}</select></label></div>
    {!filtered.length?<p>Aucun point à traiter pour ces critères.</p>:<div className="workspace-table-wrap"><table className="data-table"><thead><tr><th>Type</th><th>Point</th><th>Action</th></tr></thead><tbody>{rows.map(item=><tr key={item.id}><td>{kindLabel(item.kind)}</td><td>{item.title}</td><td><button type="button" className="button secondary" onClick={()=>onOpen(item)}>Examiner et consulter la preuve</button></td></tr>)}</tbody></table></div>}
    {filtered.length>20&&<nav className="workspace-pagination" aria-label="Pages des points CDC"><button type="button" disabled={!pageOffset} onClick={()=>setOffset(Math.max(0,pageOffset-20))}>Précédent</button><span role="status">{pageOffset+1}–{Math.min(pageOffset+20,filtered.length)} sur {filtered.length}</span><button type="button" disabled={pageOffset+20>=filtered.length} onClick={()=>setOffset(pageOffset+20)}>Suivant</button></nav>}
  </section>;
}
