import { agentPath } from './lib/agentRoutes';
import { PurchasesPanel, TrackingPanel, BomPanel } from "./components/WorkshopPanels";
import { MemoryRetryButton } from "./components/MemoryRetryButton";
import { AsyncDownloadLink } from './components/AsyncDownloadLink';
import {meetingWorkspaceHref,requestMeetingWorkspace} from './lib/meetingWorkspace';

import { Suspense, useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import {retryableLazy} from './lib/retryableLazy';
import { api, type BrainAction, type BrainKnowledge, type SageStatus, type BrainLinkState, type CdcItem, type CdcReview, type CdcSource, type ProjectDetail, type CdcJob, type Meeting, type NetworkLink, type PortfolioRow } from "./lib/api";
import { type TriageProgress } from "./lib/mailTriage";
import { useDurableMailTriage } from "./hooks/useDurableMailTriage";
import { useDebouncedValue } from "./hooks/useDebouncedValue";
import { useCdcJobs } from "./hooks/useCdcJobs";
import { useProjectData } from "./hooks/useProjectData";
import { CdcJobsPanel } from "./components/CdcJobsPanel";
import { CdcSourceUpload } from "./components/CdcSourceUpload";
import {SourceInspector} from "./components/SourceInspector";
import type {WorkspaceCitation} from "./lib/workspaceApi";
import {kindLabel} from "./lib/businessLabels";
import { TransferPanel } from "./components/TransferPanel";
import { MeetingAudioPanel } from "./components/MeetingAudioPanel";
import { ProjectReviewsPanel } from "./components/ProjectReviewsPanel";
import { PlanningMilestonesPanel } from "./components/PlanningMilestonesPanel";
import { PlanningTasksPanel } from "./components/PlanningTasksPanel";
import { PlanningBaselinesPanel } from "./components/PlanningBaselinesPanel";
import { PlanningTemplatesPanel } from "./components/PlanningTemplatesPanel";
import { PlanningHistoryPanel } from "./components/PlanningHistoryPanel";
import type { DeliverableFocus } from "./lib/projectDeliverables";
import { ProjectIdentityPanel } from "./components/ProjectIdentityPanel";
import { ProjectCockpit } from "./components/ProjectCockpit";
import { Icon } from "./os/icons";
import "./styles/app.css";

import type { ProjectCreateProps, MailPanelProps } from "./components/WorkspaceShell";
import { mailProjects } from "./lib/mailProjects";
import { parseWorkspaceRoute, projectTabLabels, projectSection, projectSections } from "./lib/workspaceNavigation";
import { Badge, EmptyState, ErrorState, LoadingState } from "./components/Ui";
import {WorkspaceViewBoundary} from './components/WorkspaceViewBoundary';
import { withActivity } from "./lib/asyncActivity";
export {App} from './AppEntry';

const MailWorkspace = retryableLazy(
  () => import('./components/MailWorkspace').then(module=>({default:module.MailWorkspace})),
  () => import('./components/MailWorkspace?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./components/MailWorkspace')).MailWorkspace})));
export const CdcReviewPanel = retryableLazy(
  () => import('./components/CdcReviewPanel').then(module=>({default:module.CdcReviewPanel})),
  () => import('./components/CdcReviewPanel?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./components/CdcReviewPanel')).CdcReviewPanel})));
const ProjectDocumentsPanel = retryableLazy(
  () => import('./components/ProjectDocumentsPanel').then(module=>({default:module.ProjectDocumentsPanel})),
  () => import('./components/ProjectDocumentsPanel?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./components/ProjectDocumentsPanel')).ProjectDocumentsPanel})));
const ProjectNotesPanel = retryableLazy(
  () => import('./components/ProjectNotesPanel').then(module=>({default:module.ProjectNotesPanel})),
  () => import('./components/ProjectNotesPanel?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./components/ProjectNotesPanel')).ProjectNotesPanel})));
const ProjectDeliverablesPanel = retryableLazy(
  () => import('./components/ProjectDeliverablesPanel').then(module=>({default:module.ProjectDeliverablesPanel})),
  () => import('./components/ProjectDeliverablesPanel?kiara-retry=1').then(module=>({default:(module as unknown as typeof import('./components/ProjectDeliverablesPanel')).ProjectDeliverablesPanel})));

const KINDS = ["function", "constraint", "requirement", "data", "interface", "open_point"];

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

/* ── Détail projet (corps de la fenêtre projet) ─────────────────────── */

export function Detail(props: {
  active?: boolean;
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
          link.download = `Kiara-Projet-${current.code || current.id}.json`;
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
      <button type="button" className="kiara-project-back" onClick={props.back}>← Tous les projets</button>
      <div className="mp-breadcrumb compact">
        <div className="kiara-project-title">
          <h1 tabIndex={-1}>{current.title}</h1>
          <p>{current.code}{current.client_name && ` · ${current.client_name}`}
            <span className={current.status === "active" ? "kiara-project-active" : ""}>{current.status === "active" ? "En cours" : "Archivé"}</span>
          </p>
        </div>
        <span className="mp-spacer" />
        <details className="project-options discrete-icon-menu icon-menu-details" onClick={event=>{if((event.target as HTMLElement).closest('button'))event.currentTarget.open=false;}}><summary className="discrete-icon-summary icon-menu-summary" aria-label="Options du projet" title="Options du projet"><Icon name="more" size={16} /><span className="sr-only">Options du projet</span></summary><div className="project-options-menu icon-menu-popover">
        <button type="button" className="button secondary sm" onClick={() => setTab('planification')}>Voir le planning</button>
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

      {(tab === "pilotage" || visitedTabs.has("pilotage")) && <div hidden={tab !== "pilotage"}>
        {pilotTab==='identity'&&<div className="planning-heading"><h3>Fiche et équipe</h3><button type="button" className="button secondary sm" onClick={()=>setPilotTab('cockpit')}>Retour à la vue d’ensemble</button></div>}
        {pilotTab === 'cockpit' && <div className="kiara-project-grid">
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
        <details hidden={pilotTab!=='cockpit'} className="kiara-project-cockpit">
        <summary>Suivi détaillé du projet</summary><ProjectCockpit projectId={current.id} active={props.active !== false && tab==='pilotage'&&pilotTab==='cockpit'} revision={detail?.planning_revision} onSaved={props.refresh}
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
        <ProjectDocumentViews projectId={current.id} active={props.active !== false && tab==='documents'} view={documentView} setView={setDocumentView} onSaved={props.refresh} focus={deliverableFocus} onFocusHandled={consumeDeliverableFocus}/>
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
            <details className="project-options planning-tools discrete-icon-menu icon-menu-details" onClick={event=>{if((event.target as HTMLElement).closest('button'))event.currentTarget.open=false;}}><summary className="discrete-icon-summary icon-menu-summary" aria-label="Outils du planning" title="Outils du planning"><Icon name="sliders" size={16} /><span className="sr-only">Outils du planning</span></summary><div className="project-options-menu icon-menu-popover">
              <button type="button" className="button secondary sm" aria-pressed={planTab==='planning'} onClick={()=>setPlanTab('planning')}>Dates et charge du projet</button>
              <button type="button" className="button secondary sm" aria-pressed={planTab==='models'} onClick={()=>setPlanTab('models')}>Modèles de planning</button>
              <button type="button" className="button secondary sm" aria-pressed={planTab==='baselines'} onClick={()=>setPlanTab('baselines')}>Planning de référence et écarts</button>
              <button type="button" className="button secondary sm" aria-pressed={planTab==='history'} onClick={()=>setPlanTab('history')}>Historique des modifications</button>
              <button type="button" className="button secondary sm" onClick={()=>{if(setTab('documents')===false)return;setDocumentView('deliverables');}}>Documents à remettre</button>
            </div></details>
          </div>
          <div hidden={planTab !== "planning"}>{<PlanningTab projectId={current.id} active={props.active !== false && tab === "planification" && planTab === "planning"} />}</div>
          <div hidden={planTab !== "jalons"}>{(
            <PlanningMilestonesPanel projectId={current.id} onSaved={props.refresh} active={props.active !== false && tab === "planification" && planTab === "jalons"} onOpenDeliverable={openGateDeliverable} />
          )}</div>
          <div hidden={planTab !== "tasks"}>{(
            <PlanningTasksPanel projectId={current.id} onSaved={props.refresh} active={props.active !== false && tab === "planification" && planTab === "tasks"} />
          )}</div>
          <div hidden={planTab !== "baselines"}><PlanningBaselinesPanel projectId={current.id} onSaved={props.refresh} active={props.active !== false && tab === "planification" && planTab === "baselines"}/></div>
          <div hidden={planTab !== "history"}><PlanningHistoryPanel projectId={current.id} active={props.active !== false && tab === "planification" && planTab === "history"}/></div>
          <div hidden={planTab !== "models"}><PlanningTemplatesPanel projectId={current.id} onSaved={props.refresh} active={props.active !== false && tab === "planification" && planTab === "models"}/></div>
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
            <WorkspaceViewBoundary><Suspense fallback={<LoadingState label="Chargement de la revue CDC"/>}>
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
            </Suspense></WorkspaceViewBoundary>
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
        <ReviewsPanel key={current.id} projectId={current.id} active={props.active !== false && tab === "reviews"} meetings={props.meetings} refresh={props.refresh} onOpenDocument={(id,title)=>{openGateDeliverable({deliverableId:id,checkId:'',milestoneId:'',milestoneTitle:`Revue · ${title}`,version:null,origin:'review'});}} />
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
  const load = useCallback(async () => {
    if (!active || document.hidden) return;
    const generation = ++loadGeneration.current;
    try {
      setError("");setPortfolioNotice("");
      const session=await api.session();
      if (generation !== loadGeneration.current) return;
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
  }, [queueOffset, searchQuery, sort, rows, active]);
  useEffect(() => {
    if (!active) return;
    const visibility = () => {
      if (document.hidden) loadGeneration.current++;
      else void load();
    };
    document.addEventListener('visibilitychange', visibility);
    if (!document.hidden) void load();
    return () => {document.removeEventListener('visibilitychange', visibility);loadGeneration.current++;};
  }, [load, active]);

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

  const durableTriage = useDurableMailTriage({enabled:mailAccessReady&&!mailAccess.scoped&&!mailAccess.readOnly,active,onProgress: setTriageProgress,
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
    <>{portfolioNotice&&<p role="status" className="workspace-notice">{portfolioNotice}</p>}<WorkspaceViewBoundary><Suspense fallback={<LoadingState label="Chargement des mails"/>}><MailWorkspace key={`${mailAccess.scoped}-${mailAccess.readOnly}`} active={active} scoped={mailAccess.scoped} readOnly={mailAccess.readOnly} queue={queue} projects={mailAccess.scoped ? projects : mailProjects(portfolio,projects)} portfolio={mailAccess.scoped ? portfolio.filter(project=>thumbLinks[project.id]?.linked) : portfolio} links={thumbLinks} stats={stats}
      query={query} onQuery={value => {setQuery(value); setQueueOffset(0); setSelected(new Set());}}
      sort={sort} onSort={value => {setSort(value); setQueueOffset(0); setSelected(new Set());}} queueTotal={queueTotal} selected={selected} onToggle={toggleSelect}
      onSelectAll={selectAllFiltered} onClearSelected={() => setSelected(new Set())}
      offset={queueOffset} onPage={setQueueOffset} pageHasNext={queueHasNext}
      onReload={load} onRunTriage={(force) => { void runTriage(force); }}
      onCancelTriage={() => { void durableTriage.cancel(); }} triaging={triaging} triageProgress={triageProgress} busy={busy}
      dropping={dropping} autoInfo={autoInfo} message={[msg,error && `Actualisation impossible : ${error}`].filter(Boolean).join(" ")} onDecide={decide} onReject={reject}
      onResolveTarget={resolveTarget}
      onCreateProject={mailAccess.scoped ? undefined : createMailProject}
      onDragStart={onDragStart} onDrop={onDropOnProject} dragOver={dragOver} onDragOver={setDragOver} /></Suspense></WorkspaceViewBoundary></>
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
    {(view==='deliverables'||visited.has('deliverables'))&&<div hidden={view!=='deliverables'}><WorkspaceViewBoundary><Suspense fallback={<LoadingState label="Chargement des livrables"/>}><ProjectDeliverablesPanel projectId={projectId} active={active&&view==='deliverables'} onSaved={onSaved} focus={focus} onFocusHandled={onFocusHandled}/></Suspense></WorkspaceViewBoundary></div>}
    {(view==='prepare'||visited.has('prepare'))&&<div hidden={view!=='prepare'}><WorkspaceViewBoundary><Suspense fallback={<LoadingState label="Chargement de la préparation documentaire"/>}><ProjectDocumentsPanel projectId={projectId} active={active&&view==='prepare'}/></Suspense></WorkspaceViewBoundary></div>}
    {(view==='notes'||visited.has('notes'))&&<div hidden={view!=='notes'}><WorkspaceViewBoundary><Suspense fallback={<LoadingState label="Chargement des notes"/>}><ProjectNotesPanel projectId={projectId} active={active&&view==='notes'}/></Suspense></WorkspaceViewBoundary></div>}
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
    <p><a className="button primary" href={meetingWorkspaceHref(projectId)} onClick={event=>{if(requestMeetingWorkspace(projectId))event.preventDefault();}}>Ouvrir les séances du projet</a></p>
    <div className="mp-subtabs" role="tablist" aria-label="Réunions et revues">
      <button type="button" role="tab" aria-selected={view==='rlp'} className={`mp-subtab ${view==='rlp'?'active':''}`} onClick={()=>setView('rlp')}>Revue de lancement</button>
      <button type="button" role="tab" aria-selected={view==='meetings'} className={`mp-subtab ${view==='meetings'?'active':''}`} onClick={()=>{setView('meetings');setVisited(true);}}>Comptes rendus et audio</button>
    </div>
    <div hidden={view!=='rlp'}><ProjectReviewsPanel projectId={projectId} active={active&&view==='rlp'} onSaved={refresh} onOpenDocument={onOpenDocument}/></div>
    {visited&&<div hidden={view!=='meetings'}><LegacyMeetingsPanel projectId={projectId} meetings={meetings} refresh={refresh} initialMeetingId={initialMeetingId} active={active&&view==='meetings'}/></div>}
  </div>;
}

function LegacyMeetingsPanel({ projectId, meetings, refresh, initialMeetingId, active }: {
  projectId: string; meetings: Meeting[]; refresh: () => void; initialMeetingId?: string | null; active: boolean;
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
      <MeetingAudioPanel key={projectId} projectId={projectId} onPublished={refresh} viewActive={active} />
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
                <label>Action<input className="input" placeholder="Nouvelle action" value={actionTitle} onChange={(e) => setActionTitle(e.target.value)} style={{ width: 260 }} /></label>
                <label>Pilote<input className="input" placeholder="Nom du pilote" value={actionOwner} onChange={(e) => setActionOwner(e.target.value)} style={{ width: 120 }} /></label>
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
export function SagePanel() {
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

export function ProjectWindow(props: {
  active?: boolean;
  projectId: string;
  initialTab: TabId;
  row?: PortfolioRow;
  reloadRows: () => Promise<void>;
  back: () => void;
  onTabChange?: (tab: TabId) => boolean | void;
  registerCache?: (id: string, canRelease: () => boolean) => () => void;
}) {
  const cacheRoot = useRef<HTMLDivElement>(null);
  const detailMounted = useRef(false);
  const retained = useRef(props.initialTab !== 'pilotage');
  if (props.initialTab !== 'pilotage') retained.current = true;
  const retainOnInteraction = useCallback((event:React.SyntheticEvent) => {
    const target = event.target;
    const back = target instanceof Element && target.closest('.kiara-project-back');
    if (back && ['click','pointerdown','mousedown','touchstart'].includes(event.type)) return;
    if (back && event.type === 'keydown' && ['Enter',' '].includes((event as React.KeyboardEvent).key)) return;
    retained.current = true;
  }, []);
  const canRelease = useCallback(() => {
    const root = cacheRoot.current;
    if (retained.current) return false;
    // A view that has never rendered Detail has no project-local form or capture.
    if (!root) return !detailMounted.current;
    if (root.querySelector('[data-workspace-dirty="true"],[data-workspace-busy="true"],[data-mic-recording="true"],[aria-busy="true"],[contenteditable="true"],details[open],dialog[open]')) return false;
    for (const field of root.querySelectorAll<HTMLInputElement|HTMLTextAreaElement>('input,textarea')) {
      if (field instanceof HTMLInputElement && field.type === 'file') {if(field.files?.length)return false;}
      else if (field instanceof HTMLInputElement && ['checkbox','radio'].includes(field.type)) {if(field.checked!==field.defaultChecked)return false;}
      else if (field.value!==field.defaultValue) return false;
    }
    for (const select of root.querySelectorAll<HTMLSelectElement>('select')) {
      const options = Array.from(select.options), declared = options.filter(option=>option.defaultSelected);
      const defaults = declared.length ? declared : select.multiple ? [] : options.filter(option=>!option.disabled).slice(0,1);
      if (options.some(option=>option.selected!==defaults.includes(option))) return false;
    }
    if (Array.from(root.querySelectorAll<HTMLMediaElement>('audio,video')).some(media=>!media.paused || !!media.srcObject)) return false;
    return true;
  }, []);
  useLayoutEffect(() => props.registerCache?.(props.projectId,canRelease), [props.projectId,props.registerCache,canRelease]);
  const row = props.row?.id === props.projectId ? props.row : undefined;
  const lastRow = useRef<PortfolioRow | undefined>(row);
  if (row) lastRow.current = row;
  else if (lastRow.current?.id !== props.projectId) lastRow.current = undefined;
  const available = !!row;
  const { detail, items, sources, meetings, error, refresh } = useProjectData(props.projectId, props.reloadRows);
  const previousView = useRef({projectId: props.projectId, active: props.active !== false && available});
  useEffect(() => {
    const active = props.active !== false && available;
    const previous = previousView.current;
    previousView.current = {projectId: props.projectId, active};
    // A cached project may have changed elsewhere while its view was hidden.
    // Keep Detail mounted so unsaved forms and ongoing captures remain intact.
    if (active && !previous.active && previous.projectId === props.projectId) void refresh();
    // refresh is specific to this render; only a visibility transition triggers it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.active, props.projectId, available]);
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
  const analysis = useCdcJobs(props.projectId, refresh, props.active !== false && available);
  if (detail && lastRow.current) detailMounted.current = true;
  if (!lastRow.current) return <EmptyState title="Projet introuvable" detail="Il a peut-être été filtré ou supprimé." />;
  if (!available && !detail) return <EmptyState title="Projet introuvable" detail="Il a peut-être été filtré ou supprimé." />;
  if (error && !detail) return <ErrorState message={error} retry={refresh} />;
  if (!detail) return <LoadingState label="Chargement du projet" />;
  return (
    <>{!available && <EmptyState title="Projet introuvable" detail="Il a peut-être été filtré ou supprimé. Les saisies ouvertes restent conservées pendant cette session." />}
    {available && error && <ErrorState message={error} retry={refresh} />}
    <div ref={cacheRoot} hidden={!available} inert={!available}
      onClickCapture={retainOnInteraction} onPointerDownCapture={retainOnInteraction} onMouseDownCapture={retainOnInteraction}
      onTouchStartCapture={retainOnInteraction} onKeyDownCapture={retainOnInteraction} onInputCapture={retainOnInteraction}
      onChangeCapture={retainOnInteraction} onSubmitCapture={retainOnInteraction} onPasteCapture={retainOnInteraction}
      onDropCapture={retainOnInteraction} onWheelCapture={retainOnInteraction}><Detail
      active={props.active !== false && available}
      current={lastRow.current}
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
    /></div></>
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
