import { useEffect, useState } from "react";
import { api, type Actions } from "../lib/api";

export function ActionDashboard({projectId, onOpen, revision}: {projectId?: string; onOpen?: (id: string, tab?: string) => void; revision?: unknown}) {
  const [data, setData] = useState<Actions | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [expanded, setExpanded] = useState(false);
  useEffect(()=>setExpanded(false),[projectId]);
  useEffect(() => {let disposed = false; api.actions(projectId).then(result => {if (!disposed) {setData(result); setError("");}})
    .catch(e => {if (!disposed) setError(String(e.message || e));}); return () => {disposed = true;};}, [projectId, revision, attempt]);
  return <div className="action-dashboard">
    {error && <p role="alert">{error} <button onClick={() => setAttempt(n => n + 1)}>Réessayer</button></p>}
    {data && <>
      {!projectId && <p>{data.pending_mails} mail(s) à classer · échéances des {data.horizon_days} prochains jours</p>}
      {!data.actions.length && <p>Aucune action prioritaire sur les projets actifs.</p>}
      <ul>{(expanded?data.actions:data.actions.slice(0,5)).map((a, i) => <li key={`${a.project_id}-${a.kind}-${i}`}>
        {onOpen ? <button className="button secondary" onClick={() => onOpen(a.project_id, a.tab)}>{a.project_code}</button> : <b>{a.project_code}</b>}
        {" "}{a.title}{a.count > 1 && ` (${a.count})`}{a.due_date && ` · ${a.due_date}`}
      </li>)}</ul>
      {data.actions.length>5&&<button type="button" className="action-dashboard-more" aria-expanded={expanded} onClick={()=>setExpanded(v=>!v)}>{expanded?"Réduire la liste":`Toutes les priorités (${data.actions.length})`}</button>}
    </>}
  </div>;
}
