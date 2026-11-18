import { agentPath } from '../lib/agentRoutes';
import {useQueryState} from '../hooks/useQueryState';
import {MemoryRecovery} from './MemoryRecovery';
import {AsyncDownloadLink} from './AsyncDownloadLink';
import { Suspense, useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import {retryableLazy} from '../lib/retryableLazy';
import {WorkspaceViewBoundary} from './WorkspaceViewBoundary';
import { api, type PortfolioRow } from "../lib/api";
import { workspaceApi, type WorkspaceCitation, type WorkspaceJob, type WorkspaceKnowledge, type WorkspacePage } from "../lib/workspaceApi";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { Glyph, P } from "../os/icons";
import { meetingSessions, sessionExportUrl, type MeetingSession, type SessionCapabilities, type SessionCitation } from '../lib/meetingSessions';
import "../workspace-views.css";
import {fusionInsights} from '../lib/fusionInsights';
import {Modal} from './WorkspaceModal';
import {SourceInspector} from './SourceInspector';
import {dateLabel, errorMessage} from './workspaceViewUtils';
export {SourceInspector} from './SourceInspector';
const MeetingStudio = retryableLazy(
  () => import('./MeetingStudio').then(module => ({default: module.MeetingStudio})),
  () => import('./MeetingStudio?kiara-retry=1').then(module => ({default:(module as unknown as typeof import('./MeetingStudio')).MeetingStudio})));

export type WorkspaceViewProps = {rows: PortfolioRow[]; onOpenProject: (id: string, tab: string) => void; active?: boolean};
export type MeetingCreationRequest = {key:number;projectId?:string};
const PAGE_SIZE = 25;
const STATUS: Record<string, string> = {
  queued: "En attente", running: "En cours", completed: "Terminé", failed: "Échec", cancelled: "Annulé", interrupted: "Interrompu",
  idle: "À préparer", published: "Publié", validated: "Retenue", invalidated: "Déclassée", pending: "À examiner", accepted: "Accepté", rejected: "Écarté", superseded: "Remplacé",
  uploaded: "Audio importé", decoding: "Lecture audio", speakers: "Identification des voix", transcribing: "Transcription",
  transcribed: "Texte à relire", reviewed: "Texte validé", synthesizing: "Synthèse", consolidating: "Consolidation", draft: "Brouillon", publishing: "Publication",
};
const KIND: Record<string, string> = {fact: "Fait", action: "Action", risk: "Risque", decision: "Décision", requirement: "Exigence", constraint: "Contrainte", open_point: "Point ouvert", milestone: "Échéance", summary: "Compte rendu"};

function StateLabel({status}: {status: string}) {
  return <span className={`workspace-state workspace-state--${["failed", "interrupted", "running", "pending", "validated", "published", "completed"].includes(status) ? status : "neutral"}`}>{STATUS[status] || status || "À préparer"}</span>;
}

function ProjectFilter({rows, value, onChange, knowledge = false}: {rows: PortfolioRow[]; value: string; onChange: (id: string) => void; knowledge?: boolean}) {
  return <label className="workspace-filter">Projet
    <select value={value} onChange={event => onChange(event.target.value)}>
      <option value="">Tous les projets</option>
      {rows.map(row => <option key={row.id} value={row.id} disabled={knowledge && !row.brain_project_id}>
        {row.code} — {row.title}{knowledge && !row.brain_project_id ? " (informations non liées)" : ""}
      </option>)}
    </select>
  </label>;
}

function useWorkspacePage<T>(loader: (signal: AbortSignal,quiet?:boolean) => Promise<WorkspacePage<T>>, polling = false) {
  const [page, setPage] = useState<WorkspacePage<T>>({items: [], total: 0});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [revision, setRevision] = useState(0);
  const previousLoader = useRef<typeof loader | null>(null);
  const automaticRefresh = useRef(false);
  const currentRequest = useRef<AbortController | null>(null);
  const wasPolling = useRef(polling);
  useEffect(() => {
    if (polling && document.hidden) return;
    const controller = new AbortController();
    currentRequest.current = controller;
    let live = true;
    const quiet=previousLoader.current===loader&&automaticRefresh.current;
    automaticRefresh.current=false;
    if (previousLoader.current !== loader) setLoading(true);
    previousLoader.current = loader;
    setError("");
    void (quiet?loader(controller.signal,true):loader(controller.signal)).then(data => {if (live && !controller.signal.aborted) setPage(data);}).catch(cause => {
      if (live && !controller.signal.aborted) setError(errorMessage(cause));
    }).finally(() => {
      if(currentRequest.current===controller)currentRequest.current=null;
      if (live && !controller.signal.aborted) setLoading(false);
    });
    return () => {live = false; controller.abort();if(currentRequest.current===controller)currentRequest.current=null;};
  }, [loader, revision]);
  useEffect(() => {
    const previous=wasPolling.current;wasPolling.current=polling;
    if (!polling) {if(previous)currentRequest.current?.abort();return;}
    const refresh=()=>{automaticRefresh.current=true;setRevision(value=>value+1);};
    const visibility=()=>{if(document.hidden)currentRequest.current?.abort();else refresh();};
    if (!previous && !document.hidden) refresh();
    document.addEventListener('visibilitychange',visibility);
    const timer = window.setInterval(() => {if (!document.hidden && !currentRequest.current)refresh();}, 5000);
    return () => {window.clearInterval(timer);document.removeEventListener('visibilitychange',visibility);};
  }, [polling]);
  return {page, loading, error, reload: () => {automaticRefresh.current=false;setRevision(value => value + 1);}};
}

function ViewState({loading, error, count, retry, empty, children}: {loading: boolean; error: string; count: number; retry: () => void; empty: string; children: ReactNode}) {
  if (loading) return <div className="workspace-view-state" role="status">Chargement des données…</div>;
  if (error) return <div className="workspace-view-state workspace-view-error" role="alert"><p>{error}</p><button type="button" onClick={retry}>Réessayer</button></div>;
  if (!count) return <div className="workspace-view-state"><Glyph d={P.folder} size={28} /><strong>{empty}</strong><p>Modifiez les filtres ou ouvrez un projet pour poursuivre.</p></div>;
  return <>{children}</>;
}

function Pagination({offset, total, loading, setOffset}: {offset: number; total: number; loading: boolean; setOffset: (value: number) => void}) {
  if (total <= PAGE_SIZE && offset === 0) return null;
  return <nav className="workspace-pagination" aria-label="Pagination">
    <span aria-live="polite">{total ? `${offset + 1}–${Math.min(offset + PAGE_SIZE, total)} sur ${total}` : "0 résultat"}</span>
    <button type="button" disabled={loading || !offset} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}><Glyph d={P.chevL} />Précédents</button>
    <button type="button" disabled={loading || offset + PAGE_SIZE >= total} onClick={() => setOffset(offset + PAGE_SIZE)}>Suivants<Glyph d={P.chevR} /></button>
  </nav>;
}

export function GlobalMeetingsView({rows, onOpenProject, active=true,initialProjectId,creationRequest,studioNavigation,onStudioOpenChange}: WorkspaceViewProps&{
  initialProjectId?:string;creationRequest?:MeetingCreationRequest|null;studioNavigation?:ReactNode;onStudioOpenChange?:(open:boolean)=>void}) {
  const [project, setProject] = useQueryState<string>("project",initialProjectId||"","/app/meetings");
  const appliedRouteProject=useRef<string|null>(null);
  useEffect(()=>{
    const value=initialProjectId||'';
    if(!active||appliedRouteProject.current===value)return;
    // Initial query filters and pages have already been restored by the hooks.
    if(appliedRouteProject.current===null){appliedRouteProject.current=value;return;}
    appliedRouteProject.current=value;
    setProject(value);setOffset(0);setSessionOffset(0);setSelected(null);setStudio(null);
  },[active,initialProjectId]);
  const [search, setSearch] = useQueryState<string>("q","","/app/meetings");
  const q = useDebouncedValue(search);
  const [offset, setOffset] = useQueryState<number>("offset",0,"/app/meetings");
  const [selected, setSelected] = useState<string | null>(null);
  const [capabilities, setCapabilities] = useState<SessionCapabilities | null>(null);
  const [sessions, setSessions] = useState<MeetingSession[]>([]);
  const [sessionTotal, setSessionTotal] = useState(0);
  const [sessionOffset, setSessionOffset] = useQueryState<number>("sessions_offset",0,"/app/meetings");
  const [sessionError, setSessionError] = useState('');
  const [creationError,setCreationError] = useState('');
  const [studio, setStudio] = useState<string | null>(null);
  const studioOpen=!!studio&&!!capabilities?.enabled;
  useLayoutEffect(()=>{onStudioOpenChange?.(studioOpen);return()=>onStudioOpenChange?.(false);},[studioOpen,onStudioOpenChange]);
  const [sourceProof,setSourceProof]=useState<SessionCitation|null>(null);
  useEffect(()=>{setSourceProof(null);},[studio]);
  const [creating, setCreating] = useState(false);
  const [createBusy, setCreateBusy] = useState(false);
  const [activationBusy, setActivationBusy] = useState(false);
  const [title, setTitle] = useState('');
  const [kind, setKind] = useState<MeetingSession['kind']>('meeting');
  const [createProject, setCreateProject] = useState('');
  const [sessionTick, setSessionTick] = useState(0);
  const createCommand = useRef<string | null>(null);
  const handledCreationRequest = useRef<number|null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const refresh=()=>void meetingSessions.capabilities(controller.signal).then(value => {if(!controller.signal.aborted)setCapabilities(value);}).catch(() => undefined);
    refresh();window.addEventListener('agent-fusion-settings-changed',refresh);
    return () => {controller.abort();window.removeEventListener('agent-fusion-settings-changed',refresh);};
  }, []);
  useEffect(()=>{
    if(!active||!capabilities||!creationRequest||handledCreationRequest.current===creationRequest.key)return;
    handledCreationRequest.current=creationRequest.key;
    setCreationError('');
    setStudio(null);setSelected(null);setCreating(true);setKind('meeting');
    setCreateProject(rows.some(row=>row.id===creationRequest.projectId)?creationRequest.projectId!:'');
    createCommand.current=null;
  },[active,capabilities,creationRequest,rows]);
  useEffect(()=>{
    if(createProject&&!rows.some(row=>row.id===createProject)){
      setCreateProject('');setCreationError('Le projet choisi n’est plus accessible. Choisissez un projet autorisé ou conservez la séance à rattacher.');
      createCommand.current=null;
    }
  },[createProject,rows]);
  useEffect(() => {
    if (!capabilities||!active) return;
    const controller = new AbortController(); setSessionError('');
    void meetingSessions.list({project_id: project || undefined, q, offset: sessionOffset, limit: PAGE_SIZE}, controller.signal)
      .then(value => {setSessions(value.items); setSessionTotal(value.total);})
      .catch(failure => {if (!controller.signal.aborted) setSessionError(errorMessage(failure));});
    return () => controller.abort();
  }, [capabilities?.enabled, project, q, sessionOffset, sessionTick,active]);
  useEffect(() => {
    const open = (event: Event) => {
      const id = (event as CustomEvent<{sessionId?: string}>).detail?.sessionId;
      if (id) {setStudio(id); setCreating(false);}
    };
    window.addEventListener('agent-open-meeting-session', open);
    return () => window.removeEventListener('agent-open-meeting-session', open);
  }, []);
  const createSession = async () => {
    if (createBusy || activationBusy || !capabilities?.enabled || !title.trim()) return;
    setCreateBusy(true); setSessionError('');setCreationError(''); createCommand.current ??= crypto.randomUUID();
    try {
      const date = new Date();
      const created = await meetingSessions.create({command_id: createCommand.current, title: title.trim(), kind,
        project_id: createProject || null, date: `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`});
      createCommand.current = null; setStudio(created.id); setCreating(false); setTitle(''); setSessionTick(value => value + 1);
    } catch (failure) {setSessionError(errorMessage(failure));} finally {setCreateBusy(false);}
  };
  const activateMeetings = async () => {
    if (activationBusy) return;
    setActivationBusy(true);setCreationError('');
    try {
      const current = await fusionInsights.settings();
      const saved = await fusionInsights.save({enabled:true,live_transcription_enabled:current.live_transcription_enabled??false,
        proactive_enabled:current.proactive_enabled,auto_enhancement_enabled:current.auto_enhancement_enabled??false,
        mode:current.mode,onboarding_complete:current.onboarding_complete});
      setCapabilities(saved.capabilities);
      window.dispatchEvent(new Event('agent-fusion-settings-changed'));
    } catch (failure) {setCreationError(errorMessage(failure));}
    finally {setActivationBusy(false);}
  };
  const loader = useCallback((signal: AbortSignal,quiet=false) => quiet?workspaceApi.meetings({project_id: project || undefined, offset, limit: PAGE_SIZE, q},signal,true):workspaceApi.meetings({project_id: project || undefined, offset, limit: PAGE_SIZE, q}, signal), [project, offset, q]);
  const state = useWorkspacePage(loader,active);
  const meeting = state.page.items.find(item => item.id === selected);
  const prepared=sessions.filter(session=>!state.page.items.some(item=>item.session_id===session.id));
  const closeStudio=()=>{setStudio(null);setSourceProof(null); setSessionTick(value => value + 1); state.reload();};
  if (studio && capabilities?.enabled) return <><WorkspaceViewBoundary onLeave={closeStudio} leaveLabel="Retour aux réunions"><Suspense fallback={<p role="status">Chargement de la réunion…</p>}><MeetingStudio key={studio} sessionId={studio} rows={rows} capabilities={capabilities}
    active={active} navigation={studioNavigation}
    sessionList={sessions} onSelectSession={setStudio} onNewSession={()=>{setStudio(null);setKind('note');setCreating(true);setCreateProject(project);createCommand.current=null;}}
    onClose={closeStudio}
    onChanged={() => {setSessionTick(value => value + 1); state.reload();}} onOpenProject={onOpenProject} onOpenSource={setSourceProof}/></Suspense></WorkspaceViewBoundary>
    {sourceProof?.source_id&&<SourceInspector sourceId={sourceProof.source_id} evidence={[{...sourceProof,source_id:sourceProof.source_id,excerpt:sourceProof.excerpt||sourceProof.quote}]}
      onClose={()=>setSourceProof(null)}/>}</>;
  return <section className="workspace-view workspace-meetings" aria-label="Réunions">
    <header className="workspace-view-heading"><div><h1>Réunions</h1></div>
      {project&&<button type="button" onClick={() => onOpenProject(project, "reviews")}>Revues du projet</button>}
      <button type="button" className="workspace-primary" disabled={!capabilities} onClick={() => {setCreating(true);setCreationError('');setKind('meeting'); setCreateProject(project); createCommand.current = null;}}>Nouvelle séance</button>
    </header>
    <div className="workspace-view-toolbar"><ProjectFilter rows={rows} value={project} onChange={id => {setProject(id); setOffset(0); setSessionOffset(0); setSelected(null);}} />
      <label className="workspace-filter workspace-filter-search">Rechercher une réunion<input type="search" maxLength={255} placeholder="Titre ou projet…" value={search} onChange={event => {setSearch(event.target.value); setOffset(0); setSessionOffset(0); setSelected(null);}} /></label>
      <button type="button" aria-label="Actualiser les réunions" onClick={()=>{state.reload();setSessionTick(value=>value+1);}}><Glyph d={P.sync} /></button>
    </div>
    {sessionError && <p role="alert">{sessionError}</p>}
    {creationError&&<p role="alert">{creationError}</p>}
    {creating && <form className="meeting-create-form" aria-label="Créer une séance" onSubmit={event => {event.preventDefault(); void createSession();}}>
      <h2>Nouvelle séance</h2>
      {!capabilities?.enabled&&<div className="meeting-activation"><p>Les réunions sont désactivées sur ce PC. Activez l’espace de séance pour préparer l’audio et les notes.</p>
        <button type="button" disabled={activationBusy} onClick={()=>void activateMeetings()}>{activationBusy?'Activation…':'Activer les réunions'}</button>
        <p>Cette activation n’ouvre aucun microphone. Les réglages de transcription et d’assistance restent ceux que vous avez choisis.</p>
        <a href={agentPath("/app/preparation")}>Voir tous les réglages des réunions</a></div>}
      <label>Titre de la séance<input maxLength={255} value={title} disabled={createBusy||activationBusy} onChange={event => {setTitle(event.target.value); createCommand.current = null;}} required /></label>
      <label>Projet de la nouvelle séance<select value={createProject} disabled={createBusy} onChange={event => {setCreateProject(event.target.value); createCommand.current = null;}}>
        <option value="">À rattacher après la réunion</option>{rows.map(row => <option key={row.id} value={row.id}>{row.code} — {row.title}</option>)}</select></label>
      <label>Préparation<select value={kind} disabled={createBusy} onChange={event => {setKind(event.target.value as MeetingSession['kind']); createCommand.current = null;}}>
        <option value="meeting">Enregistrer une réunion</option><option value="note">Prendre des notes</option><option value="import">Importer un audio</option></select></label>

      <button type="submit" disabled={createBusy || activationBusy || !capabilities?.enabled || !title.trim()}>{createBusy ? 'Création…' : 'Ouvrir la séance'}</button>
      <button type="button" disabled={createBusy||activationBusy} onClick={() => setCreating(false)}>Fermer</button>
    </form>}
    {capabilities && sessions.length > 0 && <section className="meeting-session-library" aria-label="Séances préparées">
      <h2>Séances · {sessionTotal}</h2>{!capabilities.enabled&&<p>Les séances restent récupérables. Réactivez l’espace de séance dans Préparation pour les modifier.</p>}
      <div className="meeting-session-grid">{prepared.map(session => <article key={session.id}><button type="button" className="meeting-session-card" aria-label={`Ouvrir la séance ${session.title}`} disabled={!capabilities.enabled} onClick={() => setStudio(session.id)}>
        <span>{session.date} · {session.project_id ? rows.find(row => row.id === session.project_id)?.code || 'Projet' : 'À rattacher'}</span>
        <strong>{session.title}</strong><span>{STATUS[session.state] || ({created:'À préparer',recording:'Enregistrement',paused:'En pause',finalizing:'Consolidation',completed:'Audio conservé'} as Record<string,string>)[session.state] || session.state}</span>
        <small>{Math.round(session.total_bytes / 1024)} Ko conservés · {session.note_id ? 'Note du projet' : 'Notes de séance'}</small></button>
        <AsyncDownloadLink href={sessionExportUrl(session.id)} activityLabel="Préparation de l’archive de la séance…" filename="seance-agent.zip">Exporter et récupérer</AsyncDownloadLink></article>)}</div>
      {sessionTotal > PAGE_SIZE && <nav className="workspace-pagination" aria-label="Pagination des séances"><span>{sessionOffset+1}–{Math.min(sessionOffset+PAGE_SIZE,sessionTotal)} sur {sessionTotal}</span>
        <button type="button" disabled={!sessionOffset} onClick={() => setSessionOffset(value => Math.max(0,value-PAGE_SIZE))}>Séances précédentes</button>
        <button type="button" disabled={sessionOffset+PAGE_SIZE>=sessionTotal} onClick={() => setSessionOffset(value => value+PAGE_SIZE)}>Séances suivantes</button></nav>}
    </section>}
    <h2>Comptes rendus{!state.loading ? ` · ${state.page.total}` : ""}</h2>
    <ViewState loading={state.loading} error={state.error} count={state.page.items.length} retry={state.reload} empty="Aucun compte rendu pour ce périmètre">
      <div className="workspace-table-scroll"><table className="workspace-table"><thead><tr><th>Réunion</th><th>Projet</th><th>Date</th><th>État</th><th>Actions</th><th><span className="workspace-sr-only">Consulter</span></th></tr></thead>
        <tbody>{state.page.items.map(item => <tr key={item.id}><td><button type="button" className="workspace-text-button" onClick={() => item.session_id&&capabilities?.enabled?setStudio(item.session_id):setSelected(item.id)}>{item.title || "Réunion sans titre"}</button><small>{item.recording_id ? "Réunion audio" : "Compte rendu manuel"}</small>{item.session_id&&<AsyncDownloadLink href={sessionExportUrl(item.session_id)} activityLabel="Préparation de l’archive de la séance…" filename="seance-agent.zip">Récupérer la séance</AsyncDownloadLink>}</td>
          <td><button type="button" className="workspace-text-button" onClick={() => onOpenProject(item.project_id, "reviews")}>{item.project_code}</button><small>{item.project_title}</small></td>
          <td>{dateLabel(item.date)}</td><td><StateLabel status={item.stage || item.status} /></td><td>{item.actions.length}</td>
          <td><button type="button" onClick={() => onOpenProject(item.project_id, "reviews")}>Ouvrir</button></td></tr>)}</tbody>
      </table></div>
    </ViewState>
    <Pagination offset={offset} total={state.page.total} loading={state.loading} setOffset={value => {setOffset(value); setSelected(null);}} />
    {meeting && <Modal title={meeting.title || "Compte rendu"} onClose={() => setSelected(null)}>
      <div className="workspace-meeting-detail"><p className="workspace-meta">{meeting.project_code} — {meeting.project_title} · {dateLabel(meeting.date)}</p><StateLabel status={meeting.stage || meeting.status} />
        {meeting.participants && <p><strong>Participants</strong><br />{meeting.participants}</p>}
        <h3>Compte rendu et décisions</h3><p className="workspace-preserve">{meeting.decisions || "Le compte rendu est à préparer dans le projet."}</p>
        <h3>Actions</h3>{meeting.actions.length ? <ul className="workspace-detail-list">{meeting.actions.map(action => <li key={action.id}><strong>{action.title}</strong><span>{action.owner || "Responsable à préciser"} · {action.due_date ? dateLabel(action.due_date) : "Échéance à préciser"}{action.task_id ? " · Tâche créée" : ""}</span></li>)}</ul> : <p>Aucune action enregistrée.</p>}
        <button type="button" className="workspace-primary" onClick={() => onOpenProject(meeting.project_id, "reviews")}>{meeting.recording_id && !meeting.meeting_id ? "Reprendre le parcours audio dans le projet" : "Ouvrir le compte rendu dans le projet"}</button>
        {meeting.meeting_id&&<AsyncDownloadLink className="button secondary" download
          href={agentPath(`/api/v1/projects/${encodeURIComponent(meeting.project_id)}/meetings/${encodeURIComponent(meeting.meeting_id)}/pdf`)}
          activityLabel="Préparation du PDF du compte rendu…">Exporter en PDF</AsyncDownloadLink>}
      </div>
    </Modal>}
  </section>;
}

export function GlobalJobsView({rows, onOpenProject, active = true, embedded = false}: WorkspaceViewProps & {embedded?: boolean}) {
  const path = agentPath(embedded ? "/app/activite" : "/app/jobs");
  const Heading = embedded ? "h2" : "h1";
  const [project, setProject] = useQueryState<string>("project","",path);
  const [offset, setOffset] = useQueryState<number>("offset",0,path);
  const [force, setForce] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const loader = useCallback((signal: AbortSignal,quiet=false) => quiet?workspaceApi.jobs({project_id: project || undefined, offset, limit: PAGE_SIZE},signal,true):workspaceApi.jobs({project_id: project || undefined, offset, limit: PAGE_SIZE}, signal), [project, offset]);
  const state = useWorkspacePage(loader, active);
  const run = async (key: string, action: () => Promise<unknown>) => {
    setBusy(key); setError("");
    try {await action(); state.reload();} catch (cause) {setError(errorMessage(cause));} finally {setBusy("");}
  };
  const unit = (job: WorkspaceJob) => job.unit === "mails" ? "mails" : job.unit === "seconds" ? "s d’audio" : job.unit === "steps" ? "étapes" : job.unit === "passages" ? "passages" : "lots";
  return <section className="workspace-view" aria-label="Suivi des analyses">
    {active&&<MemoryRecovery/>}
    <header className="workspace-view-heading"><div><Heading>Suivi des analyses</Heading><p>Mails, documents et réunions en cours de traitement.</p></div><button type="button" aria-label="Actualiser les traitements" onClick={state.reload}><Glyph d={P.sync} />Actualiser</button></header>
    <div className="workspace-job-launch"><div><strong>Analyse globale des mails</strong><p>Le classement traite tous les mails admissibles, indépendamment du filtre projet de cette vue.</p></div>
      <label className="workspace-check"><input type="checkbox" checked={force} onChange={event => setForce(event.target.checked)} disabled={!!busy} />Ré-analyser les mails à classer ayant déjà une proposition</label>
      <button type="button" className="workspace-primary" disabled={!!busy || state.page.items.some(job => job.engine === "triage" && ["queued", "running"].includes(job.status))} onClick={() => void run("triage", () => workspaceApi.startTriage(force))}>{busy === "triage" ? "Lancement…" : "Analyser les mails"}</button>
    </div>
    <div className="workspace-view-toolbar"><ProjectFilter rows={rows} value={project} onChange={id => {setProject(id); setOffset(0);}} /><p className="workspace-meta">Mise à jour automatique</p></div>
    {error && <p className="workspace-view-error" role="alert">{error}</p>}
    <ViewState loading={state.loading} error={state.error} count={state.page.items.length} retry={state.reload} empty="Aucun traitement enregistré">
      <ul className="workspace-jobs-list">{state.page.items.map(job => <li key={`${job.engine}-${job.id}`} className="workspace-job-card">
        <div className="workspace-job-heading"><div><span className="workspace-eyebrow">{({cdc: "CDC & BE", audio: "Réunion audio", triage: "Mails",mail:"Analyse des mails", milestones:"Jalons du projet"})[job.engine]}</span><h2>{job.title}</h2>
          <span className="workspace-meta">{job.project_code ? `${job.project_code} — ${job.project_title}` : "Tous les projets"} · {dateLabel(job.created_at)}</span></div><StateLabel status={job.status} /></div>
        <div className="workspace-job-progress"><progress max={100} value={Math.min(100, Math.max(0, job.progress || 0))} aria-label={`Progression de ${job.title}`} /><strong>{Math.round(job.processed || 0)} / {job.total > 0 ? Math.round(job.total) : "?"} {unit(job)}</strong></div>
        <p className="workspace-meta">{STATUS[job.stage] || job.stage || STATUS[job.status]}</p>
        {job.error && <p className="workspace-view-error">{job.error}</p>}
        <div className="workspace-job-actions">{job.project_id && <button type="button" onClick={() => onOpenProject(job.project_id!, job.engine === "cdc" ? "cdc" : job.engine === "mail" ? "connaissance" : job.engine === "milestones" ? "planification" : "reviews")}>Ouvrir le projet</button>}
          {job.can_cancel && job.cancel_url && <button type="button" disabled={!!busy} onClick={() => void run(job.id, () => workspaceApi.jobAction(job.cancel_url!))}>{busy === job.id ? "Annulation demandée…" : "Annuler"}</button>}
          {job.can_retry && job.retry_url && <button type="button" className="workspace-primary" disabled={!!busy} onClick={() => void run(job.id, () => workspaceApi.jobAction(job.retry_url!))}>{busy === job.id ? "Reprise…" : "Reprendre"}</button>}
        </div>
      </li>)}</ul>
    </ViewState>
    <Pagination offset={offset} total={state.page.total} loading={state.loading} setOffset={setOffset} />
  </section>;
}

function ProposalReview({item, onClose, onSaved}: {item: WorkspaceKnowledge; onClose: () => void; onSaved: () => void}) {
  const [subject, setSubject] = useState(item.subject);
  const [value, setValue] = useState(item.value);
  const [comment, setComment] = useState("");
  const [supersedes, setSupersedes] = useState("");
  const [candidates, setCandidates] = useState<WorkspaceKnowledge[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sourceId, setSourceId] = useState<string | null>(null);
  const stableSubject = useDebouncedValue(subject);
  const dirty = subject !== item.subject || value !== item.value || !!comment || !!supersedes;
  useEffect(() => {
    const controller = new AbortController();
    setCandidates([]); setSupersedes("");
    if (!item.project_id) return () => controller.abort();
    void workspaceApi.knowledge({project_id: item.project_id, status: "validated", q: stableSubject.slice(0, 300), limit: 100}, controller.signal).then(result => {
      if (!controller.signal.aborted) setCandidates(result.items.filter(candidate => candidate.kind === item.kind && candidate.subject.trim() === stableSubject.trim() && candidate.value !== value));
    }).catch(() => { /* Une version contradictoire reste protégée par le contrôle serveur. */ });
    return () => controller.abort();
  }, [item.project_id, item.kind, stableSubject]);
  const decide = async (action: "reject" | "edit-and-accept") => {
    if (action !== "reject" && !item.project_id) {setError("Rattachez d’abord la source à un projet dans la rubrique Mails."); return;}
    if (action !== "reject" && (!subject.trim() || !value.trim())) {setError("Renseignez le sujet et la valeur avant de valider."); return;}
    setBusy(true); setError("");
    try {await workspaceApi.decide(item.id, action, {subject: subject.trim(), value: value.trim(), comment: comment.trim() || undefined, supersedes_id: supersedes || undefined}); onSaved();}
    catch (cause) {setError(errorMessage(cause));} finally {setBusy(false);}
  };
  return <>
    <Modal title="Examiner la proposition" onClose={onClose} dirty={dirty} busy={busy}>
      <form className="workspace-review-form" onSubmit={event => {event.preventDefault(); void decide("edit-and-accept");}}>
        <p className="workspace-meta">{item.project_code} — {item.project_name} · {KIND[item.kind] || item.kind}</p>
        <StateLabel status="pending" /><p>Relisez la source et corrigez cette proposition avant de la valider.</p>
        {!item.project_id && <p className="workspace-view-error">Cette proposition n’a pas de projet. Rattachez d’abord sa source dans la rubrique Mails.</p>}
        {item.reason && <p className="workspace-proof"><strong>Motif de la proposition</strong><br />{item.reason}</p>}
        <label>Sujet<input value={subject} maxLength={512} onChange={event => setSubject(event.target.value)} disabled={busy} required /></label>
        <label>Valeur<textarea rows={6} value={value} onChange={event => setValue(event.target.value)} disabled={busy} required /></label>
        {candidates.length > 0 && <label>Version à remplacer, si cette proposition la met à jour<select value={supersedes} onChange={event => setSupersedes(event.target.value)} disabled={busy}>
          <option value="">Aucun remplacement choisi</option>{candidates.map(candidate => <option key={candidate.id} value={candidate.id}>Version {candidate.version || 1} — {candidate.value.slice(0, 120)}</option>)}
        </select><small>Le serveur bloque toute contradiction sans choix explicite de la version remplacée.</small></label>}
        <label>Commentaire de validation<textarea rows={2} value={comment} onChange={event => setComment(event.target.value)} disabled={busy} /></label>
        <div className="workspace-citations"><strong>Sources à consulter</strong>{item.citations.length ? item.citations.map((citation, index) => <button type="button" key={index} onClick={() => setSourceId(citation.source_id)}><Glyph d={P.openExt} size={15} />{citation.title || `Source ${index + 1}`}</button>) : <p>Aucune preuve disponible dans ce projet. Vérifiez le contexte avant validation.</p>}</div>
        {error && <p className="workspace-view-error" role="alert">{error}</p>}
        <footer className="workspace-review-actions"><button type="button" disabled={busy} onClick={() => void decide("reject")}>Écarter la proposition</button><button className="workspace-primary" type="submit" disabled={busy || !item.project_id || !subject.trim() || !value.trim()}>{busy ? "Enregistrement…" : "Valider l’information"}</button></footer>
      </form>
    </Modal>
    {sourceId && <SourceInspector sourceId={sourceId} evidence={item.citations} onClose={() => setSourceId(null)} />}
  </>;
}

export function GlobalKnowledgeView({rows, onOpenProject}: WorkspaceViewProps) {
  const knowledgePath = agentPath("/app/knowledge");
  const [knowledgeProject, setKnowledgeProject] = useQueryState<string>("knowledge_project","",knowledgePath);
  const [projectsOpen, setProjectsOpen] = useState(false);
  const [projectList, setProjectList] = useState<Awaited<ReturnType<typeof workspaceApi.knowledgeProjects>>>([]);
  const [canCreate, setCanCreate] = useState(false);
  const [creating, setCreating] = useState(false);
  const [projectNotice, setProjectNotice] = useState("");
  const [projectError, setProjectError] = useState("");
  useEffect(()=>{
    if(!projectsOpen)return;
    const controller=new AbortController();
    setProjectError("");
    setCanCreate(false);
    workspaceApi.knowledgeProjects(controller.signal).then(projects=>{
      if(!controller.signal.aborted)setProjectList(projects);
    }).catch(error=>{if(!controller.signal.aborted)setProjectError(errorMessage(error));});
    api.session().then(({operator})=>{
      if(!controller.signal.aborted)setCanCreate(operator.role!=="reader"&&operator.project_ids===null);
    }).catch(()=>{if(!controller.signal.aborted)setCanCreate(false);});
    return ()=>controller.abort();
  },[projectsOpen]);
  const [mode, setMode] = useQueryState<"proposals" | "knowledge">("mode","knowledge",knowledgePath);
  const [demoted, setDemoted] = useQueryState<boolean>("demoted",false,knowledgePath);
  const [reviewOnly, setReviewOnly] = useQueryState<boolean>("review",false,knowledgePath);
  const [changing, setChanging] = useState('');
  const [changeError, setChangeError] = useState('');
  const [project, setProject] = useQueryState<string>("project","",knowledgePath);
  const [search, setSearch] = useQueryState<string>("q","",knowledgePath);
  const [offset, setOffset] = useQueryState<number>("offset",0,knowledgePath);
  const q = useDebouncedValue(search);
  const [review, setReview] = useState<WorkspaceKnowledge | null>(null);
  const [proof, setProof] = useState<{id: string; citations: WorkspaceCitation[]} | null>(null);
  const selectedProject = rows.find(row => row.id === project);
  const loader = useCallback((signal: AbortSignal) => {
    if (project && !knowledgeProject && !selectedProject?.brain_project_id) return Promise.reject(new Error("Ce projet n’est plus lié au moteur de connaissance. Ouvrez sa rubrique Informations pour vérifier la liaison."));
    return workspaceApi[mode]({project_id: knowledgeProject || selectedProject?.brain_project_id || undefined, offset, limit: PAGE_SIZE, q, status: mode === "proposals" ? "pending" : demoted ? "invalidated" : "validated", ...(mode === 'knowledge' && !demoted && reviewOnly ? {review_only: true} : {})}, signal);
  }, [mode, project, knowledgeProject, selectedProject?.brain_project_id, offset, q, demoted, reviewOnly]);
  const state = useWorkspacePage(loader);
  const change = async (item: WorkspaceKnowledge) => {
    if(!item.project_id)return;
    setChanging(item.id);setChangeError('');
    try{await workspaceApi.changeKnowledge(item.project_id,item.id,demoted?'restore':'invalidate');state.reload();}
    catch(error){setChangeError(errorMessage(error));}finally{setChanging('');}
  };
  const confirm = async (item: WorkspaceKnowledge) => {
    if (!item.project_id || !window.confirm('Confirmer cette information après vérification de sa source ?')) return;
    setChanging(item.id); setChangeError('');
    try {await workspaceApi.changeKnowledge(item.project_id, item.id, 'confirm'); state.reload();}
    catch (error) {setChangeError(errorMessage(error));} finally {setChanging('');}
  };
  return <section className="workspace-view" aria-label="Informations">
    <header className="workspace-view-heading"><div><h1>Informations</h1><p>Informations des mails, documents et réunions, avec leurs sources.</p></div><button type="button" aria-label="Actualiser les informations" onClick={state.reload}><Glyph d={P.sync} />Actualiser</button></header>
    <div className="workspace-view-tabs" role="group" aria-label="Informations à consulter"><button type="button" aria-pressed={mode === "knowledge"&&!demoted} onClick={() => {setMode("knowledge");setDemoted(false);setOffset(0);}}>Informations retenues</button><button type="button" aria-pressed={mode === "knowledge"&&demoted} onClick={() => {setMode("knowledge");setDemoted(true);setOffset(0);}}>Déclassées</button><button type="button" aria-pressed={mode === "proposals"} onClick={() => {setMode("proposals"); setOffset(0);}}>À vérifier</button></div>
    <details onToggle={event=>setProjectsOpen(event.currentTarget.open)}><summary>Projets de connaissance</summary>
      <label>Projet de connaissance<select value={knowledgeProject} onChange={event=>{
        setKnowledgeProject(event.target.value);setProject("");setOffset(0);
      }}><option value="">Tous les projets</option>
        {projectList.map(item=><option key={item.id} value={item.id}>{item.code} · {item.name}</option>)}
      </select></label>
      {canCreate&&<form onSubmit={event=>{
        event.preventDefault();
        const form=event.currentTarget,data=new FormData(form);
        const code=String(data.get("code")||"").trim(),name=String(data.get("name")||"").trim();
        if(creating||!code||!name)return;
        setCreating(true);setProjectError("");setProjectNotice("");
        void workspaceApi.createKnowledgeProject(code,name).then(item=>{
          setProjectList(previous=>[...previous.filter(project=>project.id!==item.id),item]);
          setKnowledgeProject(item.id);setProject("");setOffset(0);form.reset();
          setProjectNotice("Projet de connaissance créé.");
        }).catch(error=>setProjectError(errorMessage(error))).finally(()=>setCreating(false));
      }}>
        <label>Code du projet de connaissance<input name="code" className="input" required disabled={creating}/></label>
        <label>Nom du projet de connaissance<input name="name" className="input" required disabled={creating}/></label>
        <button type="submit" className="button" disabled={creating}>Créer le projet de connaissance</button>
      </form>}
      {projectNotice&&<p role="status">{projectNotice}</p>}{projectError&&<p role="alert">{projectError}</p>}
    </details>
    <div className="workspace-view-toolbar"><ProjectFilter rows={rows} knowledge value={project} onChange={id => {setKnowledgeProject("");setProject(id); setOffset(0);}} />
      {knowledgeProject&&<a href={agentPath(`/app/sources?knowledge_project=${encodeURIComponent(knowledgeProject)}`)}>Sources du projet</a>}
      <label className="workspace-filter workspace-filter-search">Rechercher une information<input type="search" maxLength={300} placeholder={mode === "proposals" ? "Sujet, valeur ou motif…" : "Sujet ou valeur…"} value={search} onChange={event => {setSearch(event.target.value); setOffset(0);}} /></label>
      {mode === 'knowledge' && !demoted && <label className="workspace-review-filter"><input type="checkbox" checked={reviewOnly} onChange={event => {setReviewOnly(event.target.checked); setOffset(0);}} />À réexaminer seulement</label>}
    </div>
    <p className="workspace-meta">{mode === "proposals" ? "Informations dont la source reste à rattacher ou à examiner." : demoted ? "Ces informations sont conservées dans l’historique et ne servent plus de vérités à l’assistant." : "Les informations des sources rattachées sont retenues par défaut. Déclassez une information si elle est erronée ou inapplicable."}</p>
    {changeError&&<p role="alert" className="workspace-view-error">{changeError}</p>}
    <ViewState loading={state.loading} error={state.error} count={state.page.items.length} retry={state.reload} empty={mode === "proposals" ? "Aucune proposition en attente" : demoted ? "Aucune information déclassée pour ce périmètre" : "Aucune information retenue pour ce périmètre"}>
      <ul className="workspace-knowledge-list">{state.page.items.map(item => <li key={item.id} className="workspace-knowledge-card">
        <header><div><span className="workspace-eyebrow">{KIND[item.kind] || item.kind} · {item.project_code}</span><h2>{item.subject}</h2></div><StateLabel status={item.status} /></header>
        <p className="workspace-preserve">{item.value}</p>
        {mode === "knowledge" && <p className="workspace-meta">Version {item.version || 1} · {item.validation_mode==='default'?'Retenue par défaut':'Confirmation humaine'} · {dateLabel(item.validated_at)}</p>}
        {mode === 'knowledge' && !demoted && item.context?.needs_review && <details className="workspace-meta"><summary>À réexaminer</summary><p>{item.context.review_messages.join(' ')}</p></details>}
        <div className="workspace-citations">{item.citations.map((citation, index) => <button type="button" key={index} onClick={() => setProof({id: citation.source_id, citations: item.citations})}><Glyph d={P.openExt} size={15} />{citation.title || `Source ${index + 1}`}</button>)}{!item.citations.length && <span className="workspace-meta">Aucune source consultable</span>}</div>
        <footer>{item.erp_projects.map(link => <button type="button" key={link.id} onClick={() => onOpenProject(link.id, "connaissance")}>Projet {link.code}</button>)}{!item.erp_projects.length && <span className="workspace-meta">Projet Brain sans liaison ERP</span>}
          {mode === "proposals" && <button type="button" className="workspace-primary" onClick={() => setReview(item)}>Examiner et corriger</button>}
          {mode === "knowledge" && <button type="button" disabled={!!changing} onClick={()=>void change(item)}>{changing===item.id?'Enregistrement…':demoted?'Rétablir':'Déclasser'}</button>}
          {mode === 'knowledge' && !demoted && item.context?.can_confirm && <button type="button" disabled={!!changing} onClick={() => void confirm(item)}>Confirmer après relecture</button>}
        </footer>
      </li>)}</ul>
    </ViewState>
    <Pagination offset={offset} total={state.page.total} loading={state.loading} setOffset={setOffset} />
    {review && <ProposalReview item={review} onClose={() => setReview(null)} onSaved={() => {setReview(null); state.reload();}} />}
    {proof && <SourceInspector sourceId={proof.id} evidence={proof.citations} onClose={() => setProof(null)} />}
  </section>;
}
