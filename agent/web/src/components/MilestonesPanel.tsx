import { useEffect, useRef, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import { milestoneApi, type DateField, type Milestone, type MilestoneCandidate, type MilestoneChange,
  type MilestoneEvidence, type MilestoneReview } from "../lib/milestones";
import { SourceInspector } from "./SourceInspector";
import { Glyph, P } from "../os/icons";
import "../milestones.css";

const fields: DateField[] = ["contractual_date", "forecast_date", "actual_date"];
const labels = {contractual_date: "Contractuelle", forecast_date: "Prévisionnelle", actual_date: "Réelle"};
const format = (value: string) => value ? value.split("-").reverse().join("/") : "À renseigner";
const errorMessage = (error: unknown) => error instanceof Error ? error.message : String(error);
const emptyReview = (): MilestoneReview => ({candidates: [], pending_total: 0, job: null});

export function MilestonesPanel({projectId, rows, refresh, active = true,reviewOnly=false,canEdit=true,expectedRevision,renderTarget}: {
  projectId: string; rows: Milestone[]; refresh: () => void; active?: boolean;reviewOnly?:boolean;canEdit?:boolean;expectedRevision?:number;
  renderTarget?:(candidate:MilestoneCandidate,value:string,onChange:(id:string)=>void)=>ReactNode;
}) {
  const [review, setReview] = useState<MilestoneReview>(emptyReview);
  const [title, setTitle] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  const [source, setSource] = useState<MilestoneEvidence | null>(null);
  const [history, setHistory] = useState<{title: string; rows: MilestoneChange[]} | null>(null);
  const [targets, setTargets] = useState<Record<string, string>>({});
  const revision = useRef(0);
  const refreshRef = useRef(refresh);
  refreshRef.current = refresh;
  useEffect(() => {
    revision.current += 1;
    setReview(emptyReview()); setError(""); setTitle(""); setHistory(null); setSource(null); setTargets({}); setBusy("");
  }, [projectId]);
  useEffect(() => {
    if (!active) return;
    let live = true, loading=false, timer: ReturnType<typeof setTimeout>|undefined, previousJob = "",previousPlanningRevision:number|undefined;
    let controller:AbortController|null=null;
    const stop=()=>{clearTimeout(timer);timer=undefined;controller?.abort();controller=null;loading=false;};
    const load = async (quiet=false) => {
      if(!live||document.hidden||loading)return;
      controller?.abort();const current=new AbortController();controller=current;loading=true;
      try {
        const value = await (quiet?milestoneApi.review(projectId,current.signal,true):milestoneApi.review(projectId,current.signal));
        if (!live||current.signal.aborted) return;
        setReview(value);
        const currentJob = JSON.stringify([value.job?.id, value.job?.status, value.job?.processed]);
        if (previousJob && previousJob !== currentJob) refreshRef.current();
        previousJob = currentJob;
        if(previousPlanningRevision!==undefined&&previousPlanningRevision!==value.planning_revision)refreshRef.current();
        previousPlanningRevision=value.planning_revision;
      } catch (cause) {if (live&&!current.signal.aborted) setError(errorMessage(cause));}
      finally {if(controller===current){loading=false;if(live&&!document.hidden)timer=setTimeout(()=>void load(true),4000);}}
    };
    const visibility=()=>{if(document.hidden){stop();return;}clearTimeout(timer);timer=undefined;void load(true);};
    document.addEventListener('visibilitychange',visibility);
    if(!document.hidden)void load();
    return () => {live=false;document.removeEventListener('visibilitychange',visibility);stop();};
  }, [projectId, active]);
  const run = async (key: string, action: () => Promise<unknown>) => {
    if (busy) return;
    const currentRevision = revision.current;
    setBusy(key); setError("");
    try {
      await action();
      if (currentRevision !== revision.current) return;
      refreshRef.current();
      const value = await milestoneApi.review(projectId);
      if (currentRevision === revision.current) setReview(value);
    } catch (cause) {if (currentRevision === revision.current) setError(errorMessage(cause));}
    finally {if (currentRevision === revision.current) setBusy("");}
  };
  const openEvidence = (evidence: MilestoneEvidence) => {
    if (evidence.source_id) setSource(evidence);
    else if (evidence.kind === "network" && evidence.path) void run("open", () => api.openPath(evidence.path!, projectId));
  };
  const editDate = (milestone: Milestone, field: DateField, input: HTMLInputElement) => {
    const previous = milestone[field] || "", value = input.value;
    if (value === previous) return;
    void run(milestone.id, async () => {
      try {await api.patchMilestone(projectId, milestone.id, {[field]: value});}
      catch (cause) {input.value = previous; throw cause;}
    });
  };
  const dateEvidence = (evidence?: MilestoneEvidence) => evidence && <details className="milestone-proof">
    <summary>{evidence.kind === "manual" ? "Saisie manuelle" : "Source de la date"}</summary>
    <span>{evidence.label}</span>{evidence.quote && <blockquote>{evidence.quote}</blockquote>}
    {(evidence.source_id || evidence.kind === "network") && <button className="button secondary" type="button" onClick={() => openEvidence(evidence)}>Consulter la source</button>}
  </details>;
  const decide = (candidate: MilestoneCandidate, decision: "accept" | "reject") => {
    const targetId = targets[candidate.id] ?? candidate.milestone_id ?? "";
    const current = targetId===candidate.milestone_id ? candidate.current_value : targetId ? rows.find(m => m.id === targetId)?.[candidate.date_type] || "" : "";
    void run(candidate.id, () => milestoneApi.decide(projectId, candidate.id, {
      decision, expected_value: current, milestone_id: targetId || null,...(expectedRevision===undefined?{}:{expected_revision:expectedRevision}),
    }));
  };
  const job = review.job;
  const scanning = !!job && ["queued", "running"].includes(job.status);
  return <section className="milestones-panel" aria-label="Jalons du projet">
    <header className="milestones-heading"><div><h3>Jalons du projet</h3>
      <p>Engagement contractuel, dernière prévision et réalisation constatée. Chaque date garde sa source et son historique.</p></div>
      {canEdit&&<button className="button primary" disabled={!!busy || scanning} onClick={() => void run("scan", () => milestoneApi.scan(projectId))}>
        <Glyph d={P.sync} />{scanning ? "Recherche en cours…" : "Rechercher les dates"}</button>}
    </header>
    <p className="milestones-note">L’agent recherche automatiquement toutes les 5 minutes dans les sources du projet et ses liens réseau. Les dates proposées attendent votre validation.</p>
    {error && <div role="alert" className="milestones-error">{error}</div>}
    {job && <div className="milestones-scan" role="status"><strong>{job.status === "queued" ? "Recherche en attente" : job.status === "running" ? "Analyse des sources" : job.status === "failed" ? "Recherche à reprendre" : "Dernière recherche terminée"}</strong>
      <span>{job.processed} / {job.total} passages traités · {job.proposed} proposition(s)</span>
      {job.status === "running" && <progress aria-label="Avancement de la recherche des jalons" value={job.total ? job.processed : undefined} max={job.total || 1} />}
      {job.error && <p>{job.error}</p>}
      {!!job.warnings.length && <details><summary>{job.warnings.length} point(s) à vérifier dans les sources</summary><ul>{job.warnings.map((warning, i) => <li key={i}>{warning}</li>)}</ul></details>}
    </div>}
    {!reviewOnly&&<><div className="milestone-table-scroll"><table className="data-table milestone-dates"><caption>Écart = date réelle, ou prévisionnelle, moins date contractuelle ; un écart positif indique un retard.</caption>
      <thead><tr><th>Jalon</th>{fields.map(field => <th key={field}>{labels[field]}</th>)}<th>Écart</th><th>État / historique</th></tr></thead>
      <tbody>{rows.map(m => <tr key={m.id}>
        <td><input className="input milestone-title" aria-label={`Nom du jalon ${m.title}`} defaultValue={m.title} key={m.title}
          disabled={!!busy||!canEdit} onBlur={e => {const value = e.currentTarget.value.trim(); if (value && value !== m.title) void run(m.id, () => api.patchMilestone(projectId, m.id, {title: value}));}} /></td>
        {fields.map(field => <td key={field}><input className="input" type="date" aria-label={`${labels[field]} · ${m.title}`} key={`${m.id}-${field}-${m[field]}`}
          defaultValue={m[field] || ""} disabled={!!busy||!canEdit} onBlur={e => editDate(m, field, e.currentTarget)} />
          {dateEvidence(m.date_sources?.[field])}</td>)}
        <td><span className={(m.variance_days ?? 0) > 0 ? "milestone-delay" : "milestone-ahead"}>{m.variance_days == null ? "—" : `${m.variance_days > 0 ? "+" : ""}${m.variance_days} j`}</span></td>
        <td><span className={`badge ${m.state === "overdue" ? "danger" : m.actual_date ? "ok" : "neutral"}`}>{m.actual_date ? "Réalisé" : m.state === "overdue" ? "En retard" : m.due_date ? "Planifié" : "À renseigner"}</span>
          <button className="milestone-history-button" type="button" disabled={!!busy} onClick={() => {const current = revision.current; void run("history", async () => {const changes = await milestoneApi.history(projectId, m.id); if (current === revision.current) setHistory({title: m.title, rows: changes});});}}>Historique</button></td>
      </tr>)}</tbody>
    </table></div>
    {canEdit&&<form className="inline-form" onSubmit={e => {e.preventDefault(); if (title.trim()) void run("add", async () => {await api.addMilestone(projectId, title.trim(), ""); setTitle("");});}}>
      <input className="input" placeholder="Ajouter un jalon spécifique" aria-label="Nouveau jalon" value={title} onChange={e => setTitle(e.target.value)} />
      <button className="button secondary" disabled={!title.trim() || !!busy}>Ajouter un jalon</button>
    </form>}</>}
    {history && <section className="milestone-history" aria-label={`Historique · ${history.title}`}><header><h4>Historique · {history.title}</h4><button className="button secondary" type="button" onClick={() => setHistory(null)}>Fermer</button></header>
      {!history.rows.length ? <p>Aucune modification enregistrée depuis l’activation du suivi.</p> : history.rows.map(change => <div key={change.id}>
        <strong>{labels[change.field as DateField] || "Nom"} : {change.previous || "Non renseigné"} → {change.value || "Non renseigné"}</strong>
        <small>{new Date(change.created_at).toLocaleString("fr-FR")} · {change.evidence.label}</small>{change.evidence.quote && <blockquote>{change.evidence.quote}</blockquote>}
      </div>)}
    </section>}
    <section className="milestone-candidates" aria-label="Dates proposées"><h4>Dates proposées <span className="badge neutral">{review.pending_total}</span></h4>
      {!review.pending_total && <p>Aucune date à valider. L’agent conserve les champs vides lorsqu’il ne trouve pas de preuve suffisamment explicite.</p>}
      {review.pending_total > review.candidates.length && <p>Les {review.candidates.length} propositions les plus récentes sont affichées. Les suivantes apparaîtront après validation.</p>}
      {review.candidates.map(candidate => {
        const targetId = targets[candidate.id] ?? candidate.milestone_id ?? "";
        const current = targetId===candidate.milestone_id ? candidate.current_value : rows.find(m => m.id === targetId)?.[candidate.date_type] || "";
        const conflict = !!current && current !== candidate.date;
        return <article key={candidate.id} className={conflict ? "milestone-candidate conflict" : "milestone-candidate"}>
          <header><strong>{candidate.title} · {labels[candidate.date_type]} : {format(candidate.date)}</strong><span className="badge neutral">À valider</span></header>
          <p>{candidate.evidence.label} · confiance {Math.round(candidate.confidence * 100)} %</p>
          <blockquote>{candidate.quote}</blockquote>
          {conflict && <p className="milestone-delay">La date enregistrée est {format(current)}. Valider remplacera cette date et conservera son historique.</p>}
          <div className="milestone-candidate-actions">{renderTarget?renderTarget(candidate,targetId,id=>setTargets(value=>({...value,[candidate.id]:id}))):<label>Jalon cible <select className="input" aria-label={`Jalon cible · ${candidate.id}`} value={targetId} disabled={!canEdit} onChange={e => setTargets(value => ({...value, [candidate.id]: e.target.value}))}>
            <option value="">Créer « {candidate.title} »</option>{rows.map(m => <option key={m.id} value={m.id}>{m.title}</option>)}</select></label>}
            {canEdit&&<>
            <button className="button primary" type="button" disabled={!!busy} onClick={() => decide(candidate, "accept")}>{conflict ? "Valider le remplacement" : "Valider la date"}</button>
            <button className="button secondary" type="button" disabled={!!busy} onClick={() => decide(candidate, "reject")}>Écarter</button></>}
            {(candidate.evidence.source_id || candidate.evidence.kind === "network") && <button className="button secondary" type="button" onClick={() => openEvidence({...candidate.evidence, quote: candidate.quote})}>Consulter la source</button>}
          </div>
        </article>;
      })}
    </section>
    {source?.source_id && <SourceInspector sourceId={source.source_id} evidence={[{source_id: source.source_id, title: source.label, excerpt: source.quote || ""}]} onClose={() => setSource(null)} />}
  </section>;
}
