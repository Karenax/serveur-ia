import { useEffect, useMemo, useRef, useState } from "react";
import { api, type CdcItem, type CdcReview } from "../lib/api";
import { Badge, EmptyState } from "./Ui";
import { Glyph, P } from "../os/icons";
const STATUS_LABELS: Record<string, string> = {
  candidate: "Candidat",
  confirmed: "Confirmé",
  to_confirm: "À confirmer",
  not_provided: "Non fourni",
  contradictory: "Contradictoire",
  rejected: "Rejeté",
  superseded: "Remplacé",
};
const STATUS_TONES: Record<string, string> = {
  confirmed: "info",
  contradictory: "danger",
  to_confirm: "warning",
  candidate: "neutral",
  rejected: "danger",
  not_provided: "warning",
  superseded: "neutral",
};
const STATUS_ACTIONS: { value: string; label: string; tone: string; key: string }[] = [
  { value: "confirmed", label: "Confirmer", tone: "primary", key: "c" },
  { value: "to_confirm", label: "À confirmer", tone: "secondary", key: "t" },
  { value: "not_provided", label: "Non fourni", tone: "secondary", key: "n" },
  { value: "contradictory", label: "Contradiction", tone: "secondary", key: "x" },
  { value: "rejected", label: "Rejeter", tone: "secondary", key: "r" },
];
const KIND_LABELS: Record<string, string> = {
  function: "Fonction",
  constraint: "Contrainte",
  requirement: "Exigence",
  data: "Donnée",
  interface: "Interface",
  open_point: "Point ouvert",
};

export function CdcReviewPanel(props: {
  projectId: string;
  items: CdcItem[];
  review: CdcReview | null;
  reviewKind: string;
  setReviewKind: (v: string) => void;
  reviewStatus: string;
  setReviewStatus: (v: string) => void;
  reviewQuery: string;
  setReviewQuery: (v: string) => void;
  selected: Set<string>;
  setSelected: (v: Set<string>) => void;
  refresh: () => void;
  reloadReview: () => void;
}) {
  const [busy, setBusy] = useState("");
  const [drafts, setDrafts] = useState<Record<string, Partial<CdcItem>>>({});
  const [focusId, setFocusId] = useState<string | null>(null);
  const [evSel, setEvSel] = useState(0);
  const [evPages, setEvPages] = useState<Record<string, any[]>>({});
  const [filterOpen,setFilterOpen]=useState(()=>window.innerWidth>670);
  useEffect(()=>{const query=window.matchMedia?.('(min-width:671px)');const resized=()=>setFilterOpen(query?query.matches:window.innerWidth>670);window.addEventListener('resize',resized);query?.addEventListener('change',resized);return()=>{window.removeEventListener('resize',resized);query?.removeEventListener('change',resized);};},[]);
  const [compact, setCompact] = useState(false);
  const reviewRoot = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    const q = props.reviewQuery.trim().toLowerCase();
    return props.items.filter((i) => {
      if (props.reviewKind !== "all" && i.kind !== props.reviewKind) return false;
      const status = i.knowledge_status || "candidate";
      if (props.reviewStatus === "pending") {
        if (status !== "candidate") return false;
      } else if (props.reviewStatus === "active") {
        if (status === "rejected" || status === "superseded") return false;
      } else if (props.reviewStatus !== "all" && status !== props.reviewStatus) {
        return false;
      }
      if (q && !`${i.human_id || ""} ${i.title} ${i.normalized_wording || ""} ${i.source_quote}`.toLowerCase().includes(q)) {
        return false;
      }
      return true;
    });
  }, [props.items, props.reviewKind, props.reviewStatus, props.reviewQuery]);

  // Comptes par type / statut pour les pastilles de filtre.
  const counts = useMemo(() => {
    const byKind: Record<string, number> = {};
    const byStatus: Record<string, number> = {};
    for (const i of props.items) {
      byKind[i.kind] = (byKind[i.kind] || 0) + 1;
      const s = i.knowledge_status || "candidate";
      byStatus[s] = (byStatus[s] || 0) + 1;
    }
    return { byKind, byStatus };
  }, [props.items]);

  const focusKey = filtered.map((i) => i.id).join(",");
  useEffect(() => {
    if (!filtered.length) {
      if (focusId !== null) setFocusId(null);
      return;
    }
    if (!filtered.some((i) => i.id === focusId)) {
      setFocusId(filtered[0].id);
      setEvSel(0);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusKey]);

  useEffect(() => {
    setEvSel(0);
  }, [focusId]);

  const focus = filtered.find((i) => i.id === focusId) ?? null;

  const patch = async (item: CdcItem, body: object) => {
    setBusy(item.id);
    try {
      await api.patchCdcItem(props.projectId, item.id, body);
      setDrafts((d) => {
        const next = { ...d };
        delete next[item.id];
        return next;
      });
      await props.refresh();
      await props.reloadReview();
      return true;
    } catch (e: any) {
      alert(String(e.message || e));
      return false;
    } finally {
      setBusy("");
    }
  };

  const patchAdvance = async (item: CdcItem, body: object) => {
    const idx = filtered.findIndex((x) => x.id === item.id);
    const next = filtered[idx + 1] ?? null;
    const saved = await patch(item, body);
    if (saved && next && next.id !== item.id) {
      setFocusId(next.id);
      setEvSel(0);
    }
  };

  const bulk = async (status: string) => {
    const ids = Array.from(props.selected);
    if (!ids.length) return;
    setBusy("bulk");
    try {
      await api.bulkCdcStatus(props.projectId, ids, status);
      props.setSelected(new Set());
      props.refresh();
      props.reloadReview();
    } catch (e: any) {
      alert(String(e.message || e));
    } finally {
      setBusy("");
    }
  };

  const toggle = (id: string) => {
    const next = new Set(props.selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    props.setSelected(next);
  };

  const loadEvPages = async (sourceId: string | undefined) => {
    if (!sourceId || evPages[sourceId]) return;
    try {
      const pages = await api.cdcPages(props.projectId, sourceId);
      setEvPages((p) => ({ ...p, [sourceId]: pages }));
    } catch {
      /* le panneau affiche quand même la citation */
    }
  };

  useEffect(() => {
    const ev = focus && (focus.evidence || [])[evSel];
    if (ev?.source_id) void loadEvPages(ev.source_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focus?.id, evSel]);

  // Navigation clavier : j/k = élément suivant/précédent,
  // c = confirmer, t = à confirmer, n = non fourni, x = contradiction, r = rejeter.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (reviewRoot.current?.closest(".mac-window")?.classList.contains("inactive")) return;
      const t = e.target as HTMLElement;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === "j" || e.key === "k") {
        if (!filtered.length) return;
        const idx = filtered.findIndex((x) => x.id === focusId);
        const dir = e.key === "j" ? 1 : -1;
        const next = filtered[(idx + dir + filtered.length) % filtered.length];
        setFocusId(next.id);
        setEvSel(0);
        return;
      }
      const item = filtered.find((x) => x.id === focusId);
      if (!item || busy) return;
      if (e.key === "c") void patchAdvance(item, { knowledge_status: "confirmed" });
      else if (e.key === "t") void patchAdvance(item, { knowledge_status: "to_confirm" });
      else if (e.key === "n") void patchAdvance(item, { knowledge_status: "not_provided" });
      else if (e.key === "x") void patchAdvance(item, { knowledge_status: "contradictory" });
      else if (e.key === "r") void patchAdvance(item, { knowledge_status: "rejected" });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [focusKey, focusId, busy]);

  const draftOf = (i: CdcItem) => drafts[i.id] || {};

  const mark = (text: string, q: string) => {
    const needle = q.trim();
    if (!text || needle.length < 3) return text;
    const at = text.toLowerCase().indexOf(needle.toLowerCase());
    if (at < 0) return text;
    return (<>{text.slice(0, at)}<mark>{text.slice(at, at + needle.length)}</mark>{text.slice(at + needle.length)}</>);
  };

  if (!props.items.length) {
    return (
      <EmptyState
        title="Aucun élément à valider"
        detail="Ajoutez un CDC puis lancez son analyse dans Documents client."
      />
    );
  }

  const total = props.review?.total ?? props.items.length;
  const reviewed = props.review?.reviewed ?? props.items.filter((i) => (i.knowledge_status || "candidate") !== "candidate").length;
  const remaining = total - reviewed;
  const statusOrder = ["confirmed", "to_confirm", "not_provided", "contradictory", "rejected", "superseded", "candidate"] as const;
  const activeCount = total - (counts.byStatus.rejected || 0) - (counts.byStatus.superseded || 0);
  const focusStatus = focus ? focus.knowledge_status || "candidate" : "candidate";
  const focusDraft = focus ? draftOf(focus) : {};
  const focusDirty = focus ? Object.keys(focusDraft).length > 0 : false;

  return (
    <div className="cdc-panel">
      <div className="cdc-toolbar">
        <div className="cdc-progress-inline">
          <b>{reviewed}/{total}</b>
          <progress className="cdc-progress-bar" max={Math.max(1,total)} value={reviewed} aria-label={`${reviewed} éléments examinés sur ${total}`} />
          <span>{remaining} à traiter · {filtered.length} affichés</span>
        </div>
        <div className="cdc-filters">
          <input
            className="input"
            aria-label="Rechercher une exigence" placeholder="Rechercher (id, titre, citation)…"
            value={props.reviewQuery}
            onChange={(e) => props.setReviewQuery(e.target.value)}
            style={{ width: 200 }}
          />
          <label><input type="checkbox" checked={compact} onChange={(e) => setCompact(e.target.checked)} /> Compact</label>
        </div>
      </div>
      <details className="cdc-filter-disclosure" open={filterOpen} onToggle={e=>setFilterOpen(e.currentTarget.open)}><summary>Filtres · {props.reviewKind==='all'?'Tous les types':KIND_LABELS[props.reviewKind]} · {props.reviewStatus==='pending'?'À valider':STATUS_LABELS[props.reviewStatus]||'Tous les statuts'}</summary><div className="cdc-chips" role="group" aria-label="Filtrer par type et statut">
        {Object.keys(KIND_LABELS).filter((k) => counts.byKind[k]).map((k) => (
          <button
            key={k}
            type="button"
            className={`cdc-chip${props.reviewKind === k ? " active" : ""}`}
            onClick={() => props.setReviewKind(props.reviewKind === k ? "all" : k)}
          >
            {KIND_LABELS[k]} <b>{counts.byKind[k]}</b>
          </button>
        ))}
        <span className="cdc-chips-divider" aria-hidden="true" />
        <button
          type="button"
          className={`cdc-chip alert${props.reviewStatus === "pending" ? " active" : ""}`}
          onClick={() => props.setReviewStatus("pending")}
        >
          À valider <b>{counts.byStatus.candidate || 0}</b>
        </button>
        {statusOrder.filter((s) => s !== "candidate" && counts.byStatus[s]).map((s) => (
          <button
            key={s}
            type="button"
            className={`cdc-chip${props.reviewStatus === s ? " active" : ""}`}
            onClick={() => props.setReviewStatus(props.reviewStatus === s ? "all" : s)}
          >
            {STATUS_LABELS[s]} <b>{counts.byStatus[s]}</b>
          </button>
        ))}
        <button
          type="button"
          className={`cdc-chip${props.reviewStatus === "active" ? " active" : ""}`}
          onClick={() => props.setReviewStatus("active")}
        >
          Actifs <b>{activeCount}</b>
        </button>
        <button
          type="button"
          className={`cdc-chip${props.reviewStatus === "all" && props.reviewKind === "all" ? " active" : ""}`}
          onClick={() => { props.setReviewStatus("all"); props.setReviewKind("all"); }}
        >
          Tout voir <b>{total}</b>
        </button>
      </div></details>

      {props.selected.size > 0 && (
        <div className="cdc-bulk">
          <b>{props.selected.size} sélectionné(s)</b>
          <button className="button primary" disabled={busy === "bulk"} onClick={() => bulk("confirmed")}>
            Confirmer
          </button>
          <button className="button" disabled={busy === "bulk"} onClick={() => bulk("to_confirm")}>
            À confirmer
          </button>
          <button className="button" disabled={busy === "bulk"} onClick={() => bulk("rejected")}>
            Rejeter
          </button>
          <button className="button secondary" onClick={() => props.setSelected(new Set())}>✕</button>
        </div>
      )}

      <div ref={reviewRoot} className={`cdc-review-grid${compact ? " compact" : ""}`}>
        <div className="cdc-item-list cdc-list-virtual" role="listbox" aria-label="Éléments CDC">
          <div className="cdc-item-columns"><span>ID</span><span>Élément</span><span>Prio</span><span></span></div>
          {filtered.map((i) => {
            const status = i.knowledge_status || "candidate";
            return (
              <div
                key={i.id}
                role="option"
                aria-selected={focus?.id === i.id}
                className={`cdc-item-row${focus?.id === i.id ? " selected" : ""}`}
                onClick={() => setFocusId(i.id)}
              >
                <span><em>{i.human_id || "—"}</em></span>
                <span>
                  {mark(i.title, props.reviewQuery)}
                  <small className={`row-status ${status}`}>{STATUS_LABELS[status] || status} · p{i.physical_page}</small>
                </span>
                <span>
                  <span className={`cdc-priority ${i.priority}`}>{i.priority === "unclassified" ? "–" : i.priority.toUpperCase()}</span>
                </span>
                <span>
                  <input
                    type="checkbox"
                    checked={props.selected.has(i.id)}
                    onChange={(e) => { e.stopPropagation(); toggle(i.id); }}
                    onClick={(e) => e.stopPropagation()}
                    aria-label={`Sélectionner ${i.human_id || i.title}`}
                  />
                </span>
              </div>
            );
          })}
          {!filtered.length && (
            <div className="cdc-empty-filter">Aucun élément avec ces filtres.</div>
          )}
        </div>

        <div className="cdc-evidence-pane">
          <header>Preuves <span>{focus ? (focus.evidence || []).length : ""}</span></header>
          {!focus ? (
            <p className="cdc-no-evidence">Sélectionne un élément dans la liste.</p>
          ) : (focus.evidence || []).length === 0 ? (
            <p className="cdc-no-evidence">Aucune preuve enregistrée pour cet élément.</p>
          ) : (
            <>
              <div className="cdc-evidence-list">
                {(focus.evidence || []).map((e, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className={evSel === idx ? "selected" : ""}
                    onClick={() => { setEvSel(idx); void loadEvPages(e.source_id); }}
                  >
                    <span>{e.locator}</span>
                    <q>{mark(e.quote, props.reviewQuery)}</q>
                  </button>
                ))}
              </div>
              {(() => {
                const ev = (focus.evidence || [])[evSel];
                if (!ev) return null;
                const pages = ev.source_id ? evPages[ev.source_id] : undefined;
                if (pages === undefined) {
                  return <p><small>Chargement de la page source…</small></p>;
                }
                const page = pages.find((p: any) => p.physical_page === ev.page);
                if (!page?.text) {
                  return <p><small>Page source indisponible.</small></p>;
                }
                return (
                  <div className="cdc-page-text">
                    <strong>Page {ev.page} — texte extrait</strong>
                    <pre>{mark(page.text, ev.quote.slice(0, 120))}</pre>
                  </div>
                );
              })()}
            </>
          )}
        </div>

        <div className={`cdc-item-editor${focus ? "" : " empty"}`}>
          {!focus ? (
            "Sélectionne un élément dans la liste."
          ) : (
            <>
              <header>
                <span>
                  <strong>{focus.human_id || "—"}</strong>{" "}
                  <small>{KIND_LABELS[focus.kind] || focus.kind} · page {focus.physical_page} · conf. {focus.confidence}</small>
                </span>
                <Badge value={STATUS_LABELS[focusStatus] || focusStatus} tone={STATUS_TONES[focusStatus] || "neutral"} />
              </header>
              <div className="cdc-editor-grid">
                <label className="wide">Titre
                  <input
                    value={focusDraft.title ?? focus.title}
                    onChange={(e) => setDrafts((s) => ({ ...s, [focus.id]: { ...s[focus.id], title: e.target.value } }))}
                  />
                </label>
                <label className="wide">Formulation normalisée
                  <textarea
                    rows={2}
                    value={focusDraft.normalized_wording ?? focus.normalized_wording ?? ""}
                    onChange={(e) => setDrafts((s) => ({ ...s, [focus.id]: { ...s[focus.id], normalized_wording: e.target.value } }))}
                  />
                </label>
                <label>Modalité
                  <select
                    value={focusDraft.modality ?? focus.modality}
                    onChange={(e) => setDrafts((s) => ({ ...s, [focus.id]: { ...s[focus.id], modality: e.target.value } }))}
                  >
                    {["mandatory", "preference", "option", "example", "information", "prohibition", "assumption"].map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </label>
                <label>Priorité
                  <select
                    value={focusDraft.priority ?? focus.priority}
                    onChange={(e) => setDrafts((s) => ({ ...s, [focus.id]: { ...s[focus.id], priority: e.target.value } }))}
                  >
                    {["p1", "p2", "p3", "unclassified"].map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </label>
                <label className="wide">Critère
                  <input
                    value={focusDraft.criterion ?? focus.criterion ?? ""}
                    onChange={(e) => setDrafts((s) => ({ ...s, [focus.id]: { ...s[focus.id], criterion: e.target.value } }))}
                  />
                </label>
                <label>Unité
                  <input
                    value={focusDraft.unit ?? focus.unit ?? ""}
                    onChange={(e) => setDrafts((s) => ({ ...s, [focus.id]: { ...s[focus.id], unit: e.target.value } }))}
                  />
                </label>
                <label>Responsable
                  <input
                    value={focusDraft.responsible_party ?? focus.responsible_party ?? ""}
                    onChange={(e) => setDrafts((s) => ({ ...s, [focus.id]: { ...s[focus.id], responsible_party: e.target.value } }))}
                  />
                </label>
                <label className="wide">Critère d'acceptation
                  <input
                    value={focusDraft.acceptance_criterion ?? focus.acceptance_criterion ?? ""}
                    onChange={(e) => setDrafts((s) => ({ ...s, [focus.id]: { ...s[focus.id], acceptance_criterion: e.target.value } }))}
                  />
                </label>
                <label>Heures
                  <input
                    type="number" step="0.1" min={0}
                    value={focusDraft.estimated_hours ?? focus.estimated_hours ?? 0}
                    onChange={(e) => setDrafts((s) => ({ ...s, [focus.id]: { ...s[focus.id], estimated_hours: Number(e.target.value) } }))}
                  />
                </label>

              </div>
              {focusDirty && (
                <div style={{ padding: "0 10px" }}>
                  <button className="button primary" onClick={() => patch(focus, focusDraft)}>
                    Enregistrer les retouches
                  </button>
                </div>
              )}
              <div className="cdc-decisions">
                {STATUS_ACTIONS.map((a) => (
                  <button
                    key={a.value}
                    type="button"
                    className={a.value === "rejected" ? "danger" : ""}
                    disabled={busy === focus.id || focusStatus === a.value}
                    onClick={() => patchAdvance(focus, { knowledge_status: a.value })}
                  >
                    {a.label}<kbd>{a.key}</kbd>
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
      <p className="cdc-kbd-hint">j/k : élément suivant/précédent · c : confirmer · t : à confirmer · n : non fourni · x : contradiction · r : rejeter</p>
    </div>
  );
}

