import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { AsyncDownloadLink } from './AsyncDownloadLink';

type Project = { id: string; code: string; name: string };
type Source = { source_id: string; author: string; project_id: string; metadata: { subject?: string } };

export function ClassifiedMailList({ projects }: { projects: Project[] }) {
  const [rows, setRows] = useState<Source[]>([]);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState("");
  const load = async () => {
    try { setRows(await api.brainSources("resolved", offset)); setError(""); }
    catch (error) { setError(String(error)); }
  };
  useEffect(() => { void load(); }, [offset]);
  const reassign = async (source: Source) => {
    const project = selected[source.source_id];
    if (!project || project === source.project_id) return;
    setBusy(source.source_id);
    try { await api.brainReassignSource(source.source_id, project); await load(); }
    catch (error) { setError(String(error)); }
    finally { setBusy(""); }
  };
  return <section aria-label="Mails classés">
    <h3>Mails classés — consultation et reclassement</h3>
    <p>Un reclassement conserve l’historique et remet les connaissances issues du mail en revue.</p>
    {error && <p role="alert">{error}</p>}
    <table className="data-table compact"><thead><tr><th>Mail</th><th>Projet</th><th>Reclasser</th></tr></thead>
      <tbody>{rows.map(source => <tr key={source.source_id}>
        <td>{source.metadata.subject || "Sans objet"}<br /><small>{source.author}</small><br />
          <AsyncDownloadLink href={`/v1/sources/${source.source_id}/raw`} target="_blank" rel="noreferrer">Télécharger la source originale</AsyncDownloadLink>
        </td>
        <td>{projects.find(p => p.id === source.project_id)?.code || source.project_id}</td>
        <td><select aria-label={`Projet de ${source.metadata.subject || "mail"}`} value={selected[source.source_id] ?? source.project_id}
          onChange={event => setSelected(values => ({ ...values, [source.source_id]: event.target.value }))}>
          {projects.map(project => <option key={project.id} value={project.id}>{project.code} — {project.name}</option>)}
        </select> <button disabled={busy === source.source_id || !selected[source.source_id] || selected[source.source_id] === source.project_id}
          onClick={() => void reassign(source)}>Valider le reclassement</button></td>
      </tr>)}</tbody>
    </table>
    <button disabled={offset === 0} onClick={() => setOffset(n => Math.max(0, n - 100))}>Précédents</button>
    <button disabled={rows.length < 100} onClick={() => setOffset(n => n + 100)}>Suivants</button>
  </section>;
}
