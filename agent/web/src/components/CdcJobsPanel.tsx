import type { CdcJob } from "../lib/api";

const labels: Record<CdcJob["status"], string> = {queued: "En attente", running: "En cours", completed: "Terminée",
  failed: "À reprendre", cancelled: "Annulée", interrupted: "Interrompue"};
export function CdcJobsPanel({ jobs, error, onCancel, onRetry }: { jobs: CdcJob[]; error: string;
  onCancel: (id: string) => void; onRetry: (id: string) => void }) {
  return <section className="card" aria-label="Analyses CDC">
    <strong>Analyses et reprises</strong>
    {error && <p role="alert">{error}</p>}
    {!jobs.length && <p>Aucune analyse enregistrée.</p>}
    {jobs.map(job => <div key={job.id} className="inline-form">
      <span>{labels[job.status]} · {job.completed_batches}/{job.total_batches || "?"} lots</span>
      <progress aria-label={`Progression ${job.id}`} value={job.progress} max={100} />
      {job.error && <small>{job.error}</small>}
      {job.status === "completed" && <small>{job.result?.created || 0} élément(s) enregistré(s)</small>}
      {["queued", "running"].includes(job.status) && <button className="button secondary" disabled={job.cancel_requested}
        onClick={() => onCancel(job.id)}>{job.cancel_requested ? "Annulation demandée…" : "Annuler"}</button>}
      {["failed", "cancelled", "interrupted"].includes(job.status) && <button className="button primary"
        onClick={() => onRetry(job.id)}>Reprendre</button>}
    </div>)}
    <small>La fermeture de cette fenêtre ne suspend pas l’analyse. Une annulation prend effet à la fin du lot en cours.</small>
  </section>;
}
