import {useState} from "react";
import {api} from "../lib/api";

export function MemoryRetryButton({projectId, onComplete}: {projectId: string; onComplete: () => Promise<void>}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const retry = async () => {
    if (busy) return;
    setBusy(true);
    setFailed(false);
    setMessage("Reprise en cours… L’indexation peut prendre plusieurs minutes.");
    try {
      const result = await api.brainRetryMemory(projectId);
      setFailed(result.failed > 0);
      setMessage(`Reprise terminée : ${result.indexed} indexée(s), ${result.failed} en échec, ${result.forgotten} projection(s) obsolète(s) purgée(s).${result.failed ? " Le moteur mémoire reste en erreur ; les classements sont conservés." : ""}`);
      try { await onComplete(); }
      catch { setMessage(value => value + " Les compteurs n’ont pas pu être actualisés ; rechargez le projet."); }
    } catch (error) {
      setFailed(true);
      setMessage(`Reprise non confirmée : ${error instanceof Error ? error.message : String(error)}. Les classements sont conservés.`);
    } finally { setBusy(false); }
  };
  return <span>
    <button type="button" className="button" disabled={busy} onClick={() => void retry()}>{busy ? "Reprise en cours…" : "Reprendre les projections"}</button>
    {message && <span role={failed ? "alert" : "status"} style={{display: "block"}}>{message}</span>}
  </span>;
}
