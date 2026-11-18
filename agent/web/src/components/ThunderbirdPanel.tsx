import { useEffect, useRef, useState } from "react";
import { request } from "../lib/http";
import { withActivity } from '../lib/asyncActivity';
import "../thunderbird.css";

type Status = {
  connected: boolean; last_seen?: string; reply_only?: boolean;
  mail_config?: { source: string; folder_ids: string[] | null };
  accounts?: { id: string; name: string; identities: { id: string; email: string; name: string }[] }[];
  folders?: { id: string; name: string; path: string; account_id: string }[];
  sync?: { imported?: number; duplicates?: number; errors?: number; last_error?: string; folder_ids?: string[]; running?: boolean; more_pending?: boolean };
  jobs?: { id: string; kind: string; status: string; result: { error?: string; opened?: boolean; draft_ids?: number[] } }[];
};
export type ThunderbirdReply = { sourceId: string; sender: string; subject: string };
const BASE = "/v1/thunderbird";
const EXTENSION = "/api/v1/kiara/thunderbird-extension";
type Extension = { version: string; managed: boolean; restart_required?: boolean; update_available?: boolean; manual_path?: string };

export function ThunderbirdPanel({ reply, onUpdated, compose = false, extensionOnly = false, active = true }: { reply?: ThunderbirdReply; onUpdated?: () => void; compose?: boolean; extensionOnly?: boolean; active?:boolean }) {
  if (extensionOnly) return <ThunderbirdExtension />;
  return <ThunderbirdMail reply={reply} onUpdated={onUpdated} compose={compose} active={active} />;
}

function ThunderbirdExtension() {
  const [extension, setExtension] = useState<Extension>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(true);
  useEffect(() => {
    const controller = new AbortController();
    request<Extension>(EXTENSION, { signal: controller.signal }).then(setExtension)
      .catch(cause => { if (!controller.signal.aborted) setError(String(cause.message || cause)); })
      .finally(() => { if (!controller.signal.aborted) setBusy(false); });
    return () => controller.abort();
  }, []);
  async function install() {
    setError("");
    setBusy(true);
    try {
      setExtension(await request<Extension>(EXTENSION, { method: "POST", body: "{}" }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }
  return <section className="tb-panel" aria-label="Extension Thunderbird">
    <header><strong>Extension Thunderbird</strong></header>
    {error && <p role="alert">{error}</p>}
    {extension?.manual_path ? <>
      <p role="status">Le fichier de l’extension est prêt à être installé dans Thunderbird.</p>
      <p>Dans Thunderbird, ouvrez Modules complémentaires et thèmes, puis choisissez Installer un module depuis un fichier dans le menu en forme d’engrenage.</p>
      <label>Fichier de l’extension <input className="input" readOnly value={extension.manual_path} onFocus={event => event.currentTarget.select()} /></label>
      <button type="button" className="button secondary" disabled={busy} onClick={() => void install()}>Réessayer depuis Kiara</button>
    </> : extension && <>
      <p role="status">{extension.restart_required ? "Rouvrez Thunderbird pour appliquer le changement." : extension.managed ? `Kiara gère l’extension ${extension.version} sur ce poste.` : `L’extension ${extension.version} est disponible pour ce poste.`}</p>
      {(!extension.managed || extension.update_available) && <button type="button" className="button primary" disabled={busy} onClick={() => void install()}>{extension.managed ? "Mettre à jour l’extension" : "Installer l’extension"}</button>}
    </>}
    {busy && <p role="status">Vérification de l’extension…</p>}
  </section>;
}

function ThunderbirdMail({ reply, onUpdated, compose, active }: { reply?: ThunderbirdReply; onUpdated?: () => void; compose: boolean; active:boolean }) {
  const [status, setStatus] = useState<Status | null>(null);
  const [folders, setFolders] = useState<Set<string>>(new Set());
  const initialized = useRef(false);
  const doneJobs = useRef(new Set<string>());
  const updated = useRef(onUpdated); updated.current = onUpdated;
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const operation = useRef(false);
  const [identity, setIdentity] = useState("");
  const [to, setTo] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  useEffect(() => {
    if (reply) {
      setTo(reply.sender.match(/<([^>]+)>/)?.[1] || reply.sender);
      setSubject(/^Re:/i.test(reply.subject) ? reply.subject : `Re: ${reply.subject}`);
    }
  }, [reply?.sourceId]);
  useEffect(() => {
    if(!active)return;
    let disposed=false,loading=false,controller:AbortController|null=null,timer:number|undefined;
    const stop=()=>{window.clearTimeout(timer);timer=undefined;controller?.abort();controller=null;loading=false;};
    const load = async (quiet=false) => {
      if(disposed || loading || document.hidden)return;
      controller?.abort();const current=new AbortController();controller=current;loading=true;
      try {
        const value = await request<Status>(`${BASE}/status`,{signal:current.signal,activity:quiet?false:undefined},20000);
        if (disposed||current.signal.aborted) return;
        setStatus(value);
        if (!initialized.current && value.folders?.length) {
          setFolders(new Set(value.mail_config?.folder_ids ?? value.sync?.folder_ids ?? value.folders.filter(f => /(?:^|\/)INBOX$/i.test(f.path)).map(f => f.id)));
          initialized.current = true;
        }
        for (const job of value.jobs || []) {
          if (job.status === "done" && job.kind === "sync" && !doneJobs.current.has(job.id)) {
            doneJobs.current.add(job.id); updated.current?.();
          }
        }
      } catch (e) { if (!disposed&&!current.signal.aborted) setError(String(e)); }
      finally {if(controller===current){loading=false;if(!disposed&&!document.hidden)timer=window.setTimeout(()=>void load(true),30000);}}
    };
    const visibility=()=>{if(document.hidden){stop();return;}window.clearTimeout(timer);timer=undefined;void load(true);};
    document.addEventListener('visibilitychange',visibility);if(!document.hidden)void load();
    return () => {disposed=true;document.removeEventListener('visibilitychange',visibility);stop();};
  }, [active]);
  const identities = (status?.accounts || []).flatMap(a => a.identities || []);
  const chosenIdentity = identity || identities[0]?.id || "";
  const synchronize = async () => {
    if(operation.current)return;
    operation.current=true;setBusy(true);setError("");setNotice("Synchronisation demandée…");
    try {
      await request(`${BASE}/sync`, { method: "POST", body: JSON.stringify({ folder_ids: [...folders] }) });
      setNotice("Synchronisation demandée. Les dossiers choisis sont conservés dans Réglages → Mails ; la reprise automatique suit ces réglages.");
    } catch (e) { setError(String(e)); }
    finally { operation.current=false;setBusy(false); }
  };
  const prepare = async (openWindow: boolean) => {
    if(operation.current)return;
    operation.current=true;setBusy(true);setError("");setNotice(openWindow ? "Ouverture du message…" : "Création du brouillon…");
    try {
      await withActivity(openWindow?'Préparation du message et des pièces jointes…':'Préparation du brouillon et des pièces jointes…',async()=>{
      if (files.reduce((total, file) => total + file.size, 0) > 20 * 1024 * 1024) throw new Error("20 Mio maximum de pièces jointes");
      const attachments = await Promise.all(files.map(async file => {
        const bytes = new Uint8Array(await file.arrayBuffer());
        let binary = "";
        for (let i = 0; i < bytes.length; i += 8192) binary += String.fromCharCode(...bytes.subarray(i, i + 8192));
        return { name: file.name, content_type: file.type || "application/octet-stream", content_base64: btoa(binary) };
      }));
      await request(`${BASE}/drafts`, { method: "POST", body: JSON.stringify({
        to: to.split(/[;,]/).map(value => value.trim()).filter(Boolean), subject, body,
        identity_id: chosenIdentity, reply_source_id: reply?.sourceId, open_window: openWindow, attachments,
      }) });
      setNotice(openWindow ? "Ouverture demandée dans Thunderbird." : "Création du brouillon demandée dans Thunderbird.");
      });
    } catch (e) { setError(String(e)); }
    finally { operation.current=false;setBusy(false); }
  };
  return <section className="tb-panel" aria-label="Liaison Thunderbird">
    <header><strong>Thunderbird</strong><span className={status?.connected ? "connected" : ""}>{status?.connected ? "Connecté à Kiara" : "En attente de Thunderbird"}</span></header>
    {error && <p role="alert">{error}</p>}{notice && <p role="status">{notice}</p>}
    <div className={`tb-columns${compose || reply ? " tb-composer-first" : ""}`}>
      {status && !status.reply_only && <details className="tb-connection" open={!compose && !reply}><summary>Connexion et synchronisation</summary><details><summary>Dossiers à synchroniser ({folders.size})</summary><div className="tb-folders">
        {(status?.folders || []).map(folder => <label key={folder.id}><input type="checkbox" checked={folders.has(folder.id)}
          onChange={() => setFolders(previous => { const next = new Set(previous); if (next.has(folder.id)) next.delete(folder.id); else next.add(folder.id); return next; })} />
          {status?.accounts?.find(a => a.id === folder.account_id)?.name} · {folder.path || folder.name}</label>)}</div></details>
        <button type="button" className="button primary" disabled={busy || !status?.connected || !folders.size || status?.mail_config?.source === "folder"} onClick={() => void synchronize()}>Synchroniser les dossiers choisis</button>
        {status?.mail_config?.source === "folder" && <p><small>La source active est le dossier EML. Choisissez Thunderbird dans Réglages → Mails pour synchroniser ces dossiers.</small></p>}
        <p><small>{status?.sync?.running ? "Import en cours… " : "Dernier lot : "}{status?.sync?.imported || 0} nouveaux · {status?.sync?.duplicates || 0} doublons
          {status?.sync?.more_pending ? " · suite au prochain passage" : ""}</small></p>
        {status?.sync?.last_error && <p role="alert">{status.sync.last_error}</p>}
        <small>Réception par défaut. Indésirables, corbeille et brouillons exclus. Le classement IA reste à valider dans Mails.</small>
        <details><summary>Dernières commandes</summary>{(status?.jobs || []).map(job => <p key={job.id}>
          {job.kind === "draft" ? "Brouillon" : "Synchronisation"} · {({ queued: "En attente", running: "En cours", done: "Terminé", failed: "Échec", uncertain: "À vérifier dans Thunderbird" } as Record<string, string>)[job.status] || job.status}
          {job.result?.error && ` — ${job.result.error}`}</p>)}</details>
      </details>}
      <details className="tb-composer" open={!!reply || compose}><summary>{reply ? "Préparer une réponse" : "Nouveau message"}</summary>
        <div className="tb-compose">
          <label>Expéditeur<select className="input" aria-label="Expéditeur Thunderbird" value={chosenIdentity} onChange={e => setIdentity(e.target.value)}>
            {!identities.length && <option value="">Aucune identité disponible</option>}{identities.map(i => <option key={i.id} value={i.id}>{i.name} &lt;{i.email}&gt;</option>)}</select></label>
          <label>Destinataires<input className="input" value={to} onChange={e => setTo(e.target.value)} placeholder="adresses séparées par ;" /></label>
          <label>Objet<input className="input" value={subject} onChange={e => setSubject(e.target.value)} /></label>
          <label>Message<textarea className="input" value={body} onChange={e => setBody(e.target.value)} rows={5} /></label>
          <label>Pièces jointes<input type="file" multiple onChange={e => setFiles(Array.from(e.target.files || []))} /></label>
          <div><button type="button" className="button primary" disabled={busy || !status?.connected || !chosenIdentity || !to.trim()} onClick={() => void prepare(false)}>Créer le brouillon</button>
            <button type="button" className="button secondary" disabled={busy || !status?.connected || !chosenIdentity || !to.trim()} onClick={() => void prepare(true)}>Ouvrir dans Thunderbird</button></div>
        </div>
      </details>
    </div>
  </section>;
}
