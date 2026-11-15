import { useEffect, useState } from "react";
import { api, type OperationsState } from "../lib/api";
import "../progressive-options.css";

export function OperationsPanel() {
  const [data, setData] = useState<OperationsState | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {let disposed = false; api.operations().then(d => {if (!disposed) {setData(d); setError("");}})
    .catch(e => {if (!disposed) setError(String(e.message || e));}); return () => {disposed = true;};}, [attempt]);
  return <section className="card" aria-label="Sauvegardes et maintenance">
    <h3>Sauvegardes et maintenance</h3>
    {error && <p role="alert">{error}</p>}
    {data && <>
      {data.disk_low&&<p role="alert">Espace disque faible : {(data.disk_free_bytes / 1024**3).toFixed(1)} Go disponibles.</p>}
      {!data.disk_low&&data.disk_warning&&<p role="status">Espace disque à surveiller : {(data.disk_free_bytes / 1024**3).toFixed(1)} Go disponibles. Prévoir de la place avant une longue capture ou une sauvegarde.</p>}
      <p>Dernière sauvegarde globale : {data.backup?.created_at ? new Date(data.backup.created_at).toLocaleString("fr-FR") : "Aucune enregistrée"}</p>
      <p>{data.backup?.status === "verification_failed" ? "La dernière vérification a échoué" :
        data.backup?.verified_at ? `Vérifiée le ${new Date(data.backup.verified_at).toLocaleString("fr-FR")}` : "Vérification à effectuer"}</p>
      <button className="button secondary" disabled={busy || !data.backup?.directory} onClick={async () => {
        setBusy(true); setError("");
        try {await api.verifyBackup(); setAttempt(n => n + 1);}
        catch(e) {setError(e instanceof Error ? e.message : String(e)); setAttempt(n => n + 1);}
        finally {setBusy(false);}
      }}>{busy ? "Vérification…" : "Vérifier la dernière sauvegarde"}</button>
      <p>La sauvegarde globale se réalise hors ligne avec la procédure du guide d’exploitation. Les sauvegardes existantes sont conservées.</p>
      <details className="progressive-options"><summary>Espace disque et sauvegardes de migration</summary>
        <p>Espace libre : {(data.disk_free_bytes / 1024**3).toFixed(1)} Go</p>
        <p>{data.migration_backups.count} sauvegarde(s) de migration · {(data.migration_backups.bytes / 1024**2).toFixed(1)} Mo</p>
      </details>
    </>}
    <button className="button secondary" onClick={() => setAttempt(n => n + 1)}>Actualiser l’état</button>
  </section>;
}
