import { agentPath } from '../lib/agentRoutes';
import { useEffect, useRef, useState } from "react";
import { api, type Purchases, type Tracking, type Bom } from "../lib/api";
import { Badge, EmptyState, ErrorState, LoadingState } from "./Ui";
const TASK_STATUSES = ["todo", "in_progress", "done"];
export function PurchasesPanel({ projectId }: { projectId: string }) {
  const [data, setData] = useState<Purchases | {error: true} | null>(null);
  useEffect(() => {
    api.purchases(projectId).then(setData).catch(() => setData({ error: true }));
  }, [projectId]);
  if (!data) return <LoadingState label="Chargement des achats" />;
  if ("error" in data) return <ErrorState message="Achats inaccessibles" retry={() => api.purchases(projectId).then(setData)} />;
  if (!data.rows.length) return <EmptyState title="Aucun achat enregistré" detail="Les achats du projet proviennent des exports Sage." action={<a className="button secondary" href={agentPath("/app/imports?connection=sage")}>Ouvrir l’import Sage</a>}/>;
  return (
    <div>
      <table className="data-table compact">
        <tbody>
          <tr><td>Lignes</td><td><b>{data.count}</b></td></tr>
        </tbody>
      </table>
      <table className="data-table compact">
        <thead><tr><th>Fournisseur</th><th>Désignation</th><th>Statut</th><th>Date</th></tr></thead>
        <tbody>
          {data.rows.map((r, i: number) => (
            <tr key={i}>
              <td>{r.supplier || "—"}</td><td>{r.label || "—"}</td>
              <td>{r.status ? <Badge value={r.status} /> : "—"}</td>
              <td>{r.date || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* Pointage : lignes Sage + saisie manuelle + totaux par personne */
export function TrackingPanel({ projectId }: { projectId: string }) {
  const [data, setData] = useState<Tracking | {error: true} | null>(null);
  const [person, setPerson] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [hours, setHours] = useState(0);
  const [label, setLabel] = useState("");
  const load = () => api.tracking(projectId).then(setData).catch(() => setData({ error: true }));
  useEffect(() => {
    load();
  }, [projectId]);
  if (!data) return <LoadingState label="Chargement du pointage" />;
  if ("error" in data) return <ErrorState message="Pointage inaccessible" retry={load} />;
  return (
    <div>
      <table className="data-table compact">
        <tbody>
          <tr><td>Total pointé</td><td><b>{data.total_hours} h</b></td></tr>
          {data.by_person.map((p) => (
            <tr key={p.person}><td>{p.person}</td><td><b>{p.hours} h</b></td></tr>
          ))}
        </tbody>
      </table>
      <div className="inline-form">
        <label className="ux-field">Personne<input className="input" placeholder="Personne" value={person} onChange={(e) => setPerson(e.target.value)} style={{ width: 140 }} /></label>
        <input className="input" type="date" aria-label="Date" value={date} onChange={(e) => setDate(e.target.value)} />
        <input className="input" type="number" min={0} step={0.5} aria-label="Heures" value={hours} onChange={(e) => setHours(parseFloat(e.target.value || "0"))} style={{ width: 90 }} />
        <label className="ux-field">Motif<input className="input" placeholder="Motif" value={label} onChange={(e) => setLabel(e.target.value)} style={{ width: 200 }} /></label>
        <button
          className="button primary"
          onClick={async () => {
            if (!person.trim() || !hours) return;
            await api.addTimeEntry(projectId, { person: person.trim(), date, hours, label: label.trim() });
            setPerson("");
            setLabel("");
            load();
          }}
        >
          + Saisie
        </button>
      </div>
      {!data.entries.length && <p>Aucun pointage enregistré. Ajoutez une saisie ou consultez l’import Sage.</p>}
      <table className="data-table compact" hidden={!data.entries.length}>
        <thead><tr><th>Source</th><th>Personne</th><th>Date</th><th>Motif</th><th>Heures</th></tr></thead>
        <tbody>
          {data.entries.map((e, i: number) => (
            <tr key={i}>
              <td><Badge value={e.source} tone="neutral" /></td>
              <td>{e.person || "—"}</td><td>{e.date || "—"}</td>
              <td>{e.label || "—"}</td><td>{e.hours} h</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* BOM manuelle + import CSV */
export function BomPanel({ projectId }: { projectId: string }) {
  const [data, setData] = useState<Bom | {error: true} | null>(null);
  const [ref, setRef] = useState("");
  const [des, setDes] = useState("");
  const [qty, setQty] = useState(1);
  const fileInput = useRef<HTMLInputElement>(null);
  const [importing, setImporting] = useState(false);
  const [importFeedback, setImportFeedback] = useState<{message: string; error?: boolean} | null>(null);
  const load = () => api.bom(projectId).then(setData).catch(() => setData({ error: true }));
  useEffect(() => {
    load();
  }, [projectId]);
  if (!data) return <LoadingState label="Chargement de la nomenclature" />;
  if ("error" in data) return <ErrorState message="Nomenclature inaccessible" retry={load} />;
  return (
    <div>
      <table className="data-table compact">
        <tbody>
          <tr><td>Lignes</td><td><b>{data.count}</b></td></tr>
        </tbody>
      </table>
      <div className="inline-form">
        <label className="ux-field">Référence<input className="input" placeholder="Réf" value={ref} onChange={(e) => setRef(e.target.value)} style={{ width: 100 }} /></label>
        <label className="ux-field">Désignation<input className="input" placeholder="Désignation" value={des} onChange={(e) => setDes(e.target.value)} style={{ width: 260 }} /></label>
        <input className="input" type="number" min={0} aria-label="Quantité" value={qty} onChange={(e) => setQty(parseFloat(e.target.value || "0"))} style={{ width: 80 }} />
        <button
          className="button primary"
          onClick={async () => {
            if (!des.trim()) return;
            await api.addBomLine(projectId, { reference: ref.trim(), designation: des.trim(), quantity: qty });
            setRef("");
            setDes("");
            load();
          }}
        >
          + Ligne
        </button>
        <button type="button" className="button secondary" disabled={importing}
          onClick={() => fileInput.current?.click()}>
          {importing ? "Import en cours…" : "Importer un CSV"}
        </button>
        <input ref={fileInput} type="file" accept=".csv,text/csv" hidden aria-label="Fichier de nomenclature CSV"
          onChange={async event => {
            const input = event.currentTarget;
            const file = input.files?.[0];
            if (!file || importing) return;
            setImporting(true);
            setImportFeedback(null);
            try {
              const { created } = await api.importBomCsv(projectId, file);
              setImportFeedback({message: created === 1 ? "1 ligne importée." : `${created} lignes importées.`});
              await load();
            } catch (error) {
              setImportFeedback({message: error instanceof Error ? error.message : "Import du CSV impossible.", error: true});
            } finally {
              input.value = "";
              setImporting(false);
            }
          }}
        />
      </div>
      {importFeedback && <p role={importFeedback.error ? "alert" : "status"}>{importFeedback.message}</p>}
      {!data.lines.length && <p>Aucune ligne de nomenclature. Ajoutez une ligne ou importez un CSV.</p>}
      <table className="data-table compact" hidden={!data.lines.length}>
        <thead><tr><th>Réf</th><th>Désignation</th><th>Qté</th><th>Statut</th></tr></thead>
        <tbody>
          {data.lines.map((l) => (
            <tr key={l.id}>
              <td>{l.reference || "—"}</td><td>{l.designation}</td>
              <td>
                <input
                  className="input" type="number" aria-label={`Quantité de ${l.designation || l.reference || 'la ligne'}`} min={0} defaultValue={l.quantity} style={{ width: 80 }}
                  onBlur={async (e) => {
                    const v = parseFloat(e.target.value || "0");
                    if (v !== l.quantity) {
                      await api.patchBomLine(projectId, l.id, { quantity: v });
                      load();
                    }
                  }}
                />
              </td>
              <td>
                <button
                  className="button secondary"
                  onClick={async () => {
                    const next = TASK_STATUSES[(TASK_STATUSES.indexOf(l.status) + 1) % TASK_STATUSES.length] || "todo";
                    await api.patchBomLine(projectId, l.id, { status: next });
                    load();
                  }}
                >
                  {l.status} →
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

