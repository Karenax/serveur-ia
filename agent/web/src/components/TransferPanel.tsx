import { useEffect, useState } from "react";
import { api, type Delivery } from "../lib/api";
import { AsyncDownloadLink } from "./AsyncDownloadLink";

export function TransferPanel({projectId}: {projectId: string}) {
  const [draft, setDraft] = useState(false);
  const [versions, setVersions] = useState<Delivery[]>([]);
  const [preview, setPreview] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = () => api.deliveries(projectId).then(setVersions);
  useEffect(() => { let disposed = false; api.deliveries(projectId).then(rows => {if (!disposed) setVersions(rows);})
    .catch(e => {if (!disposed) setError(String(e.message || e));}); return () => {disposed = true;}; }, [projectId]);
  return <div>
    <label><input type="checkbox" checked={draft} disabled={busy} onChange={e => setDraft(e.target.checked)} /> Préparer un brouillon (revue non finalisée)</label>
    <button className="button primary" disabled={busy} onClick={async () => {
      setBusy(true); setError("");
      try { const result = await api.transfer(projectId, draft); setPreview(result.markdown); await load(); }
      catch(e) {setError(e instanceof Error ? e.message : String(e));}
      finally {setBusy(false);}
    }}>Générer une nouvelle version du transfert BE</button>
    {error && <p role="alert">{error}</p>}
    <h3>Historique des transferts</h3>
    {!versions.length && <p>Aucune version enregistrée.</p>}
    <ul>{versions.map(v => <li key={v.id}><button className="button secondary" onClick={async () => {
      try {setPreview((await api.delivery(projectId, v.id)).markdown); setError("");}
      catch(e) {setError(e instanceof Error ? e.message : String(e));}
    }}>Version {v.version} · {v.draft ? "Brouillon" : "Final"} · {new Date(v.created_at).toLocaleString("fr-FR")}</button>{" "}
      <AsyncDownloadLink className="button secondary" download aria-label={`Télécharger la version ${v.version}`}
        href={`/api/v1/projects/${projectId}/cdc/deliveries/${v.id}/download`}>
        Télécharger
      </AsyncDownloadLink>
    </li>)}</ul>
    {preview && <pre style={{whiteSpace: "pre-wrap"}}>{preview}</pre>}
  </div>;
}
