/** Shared UI feedback. Tracking never changes or retries the underlying operation. */
export type ActivityOptions = { delayMs?: number };
export type ActivitySnapshot = { label: string; labels: readonly string[] } | null;

type Activity = { label: string; visible: boolean; timer?: ReturnType<typeof setTimeout> };
const activities = new Map<symbol, Activity>();
const listeners = new Set<() => void>();
let snapshot: ActivitySnapshot = null;

function publish() {
  const labels = [...new Set([...activities.values()].filter(activity => activity.visible).map(activity => activity.label))];
  if ((snapshot?.labels.join('\n') ?? '') === labels.join('\n')) return;
  snapshot = labels.length ? { label: labels[0], labels } : null;
  listeners.forEach(listener => listener());
}

export function subscribeActivity(listener: () => void) {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
}

export function getActivitySnapshot(): ActivitySnapshot { return snapshot; }

/** Start before the first await; call the returned function in finally. */
export function beginActivity(label: string, { delayMs = 0 }: ActivityOptions = {}): () => void {
  const id = Symbol('activity');
  const activity: Activity = { label: label.trim() || 'Travail en cours…', visible: delayMs <= 0 };
  activities.set(id, activity);
  if (!activity.visible) {
    activity.timer = setTimeout(() => { activity.visible = true; publish(); }, delayMs);
  }
  publish();
  return () => {
    if (!activities.has(id)) return;
    if (activity.timer !== undefined) clearTimeout(activity.timer);
    activities.delete(id);
    publish();
  };
}

export async function withActivity<T>(label: string, operation: () => Promise<T>, options?: ActivityOptions): Promise<T> {
  const finish = beginActivity(label, options);
  try { return await operation(); }
  finally { finish(); }
}

/** Labels contain categories only: never expose IDs, request bodies or query text. */
export function requestActivityLabel(url: string, method = 'GET'): string {
  const path = url.split('?')[0].toLowerCase();
  const reading = ['GET', 'HEAD'].includes(method.toUpperCase());
  if (/\/cdc(?:\/|$)/.test(path)) return reading ? 'Chargement du CDC…' : 'Mise à jour du CDC…';
  if (/backup|\/backups|\/restore/.test(path)) return reading ? 'Vérification des sauvegardes…' : 'Sauvegarde ou restauration en cours…';
  if (/transcrib|transcription/.test(path)) return 'Transcription en cours…';
  if (/\/search|\/retrieval/.test(path)) return 'Recherche en cours…';
  if (/\/chat|\/answer|\/enhance|\/analy|\/ai-test|\/memory-test/.test(path)) return 'Traitement IA en cours…';
  if (/\/upload|\/import|\/ingest|\/scan/.test(path)) return 'Import en cours…';
  if (/\/export|\/download|\/pdf|\/prepare-copy/.test(path)) return 'Préparation du fichier…';
  if (/\/notes(?:\/|$)/.test(path)) return reading ? 'Chargement des notes…' : 'Enregistrement de la note…';
  if (/\/documents|\/deliverables/.test(path)) return reading ? 'Chargement des documents…' : 'Mise à jour des documents…';
  if (/\/settings|\/config/.test(path)) return reading ? 'Chargement des réglages…' : 'Enregistrement des réglages…';
  return reading ? 'Chargement en cours…' : 'Travail en cours…';
}

/** Ordinary reads, polling and small edits use feedback in their own screen. */
export function automaticRequestActivity(url:string,method='GET'):string|false {
  if(['GET','HEAD','OPTIONS','DELETE'].includes(method.toUpperCase()))return false;
  const path=url.split('?')[0].toLowerCase();
  return /\/(?:upload|import|ingest|scan|export|download|prepare-copy|prepare|generate|render|pdf|transcrib\w*|analy\w*|chat|answer|enhance\w*|ocr|rebuild|recovery|restore|backups?|test)(?:\/|$)/.test(path)
    ?requestActivityLabel(url,method):false;
}
