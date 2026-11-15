import { api } from "./api";

export type TriageProgress = {
  processed: number; total: number; classified: number; divers: number; errors: number; autoClassified?: number;
  status: "running" | "completed" | "interrupted" | "incomplete" | "failed";
};

/** Freeze the denominator at launch; committed batches remain acquired. */
export async function analyzeMailQueue(force: boolean, cancelled: () => boolean,
  onProgress: (progress: TriageProgress) => void): Promise<TriageProgress> {
  const stats = await api.brainTriageStats();
  const progress: TriageProgress = {processed: 0, total: force ? stats.pending_sources : stats.new_sources,
    classified: 0, divers: 0, errors: 0, status: "running"};
  const report = () => onProgress({...progress});
  let offset = 0;
  report();
  try {
    while (progress.processed < progress.total && !cancelled()) {
      const limit = Math.min(5, progress.total - progress.processed);
      const result = await api.brainTriageRun(limit, offset, force);
      progress.processed += result.scanned;
      progress.classified += result.triaged;
      progress.autoClassified = (progress.autoClassified || 0) + (result.auto_classified || 0);
      progress.divers += result.divers;
      progress.errors += result.errors.length;
      // Normal batches remove successful candidates from the next query.
      // Only failed candidates remain eligible and must be skipped this run.
      offset += force ? result.scanned - (result.auto_classified || 0) : result.errors.length;
      report();
      if (result.scanned < limit) break;
    }
    progress.status = progress.processed >= progress.total ? "completed" : cancelled() ? "interrupted" : "incomplete";
    report();
    return {...progress};
  } catch (error) {
    progress.status = "failed";
    report();
    throw error;
  }
}

export function triageProgressMessage(progress: TriageProgress): string {
  const count = `${progress.processed} / ${progress.total} mails traités`;
  const details = `${progress.classified} proposition(s) de classement, dont ${progress.divers} vers DIVERS` +
    (progress.autoClassified ? ` ; ${progress.autoClassified} mail(s) classé(s) automatiquement` : "") +
    (progress.errors ? ` ; ${progress.errors} mail(s) en échec` : "");
  if (progress.status === "running") return `Analyse en cours : ${count} — ${details}.`;
  if (progress.status === "completed") return `Analyse terminée : ${count} — ${details}. Les suggestions sous 100 % restent à valider.`;
  if (progress.status === "interrupted") return `Analyse interrompue : ${count} — ${details}.`;
  if (progress.status === "incomplete") return `Analyse arrêtée : ${count} — la file a changé pendant l’analyse. ${details}.`;
  return `Analyse en erreur : ${count} — ${details}.`;
}
