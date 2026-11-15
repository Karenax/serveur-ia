import {kindLabel} from "../lib/businessLabels";
import type { ReactNode } from "react";

// Mêmes noms de classes que XPilot (styles.css / project-workspace.css)
// pour que le look soit identique. Version allégée : sans lucide, sans auth.
export function LoadingState({ label = "Chargement des données" }: { label?: string }) {
  return (
    <div className="state-panel" role="status">
      <strong>{label}…</strong>
    </div>
  );
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div className="state-panel error">
      <div>
        <strong>Impossible de charger cette vue</strong>
        <p>{message}</p>
      </div>
      {retry && (
        <button className="button secondary" onClick={retry}>
          Réessayer
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, detail, action }: { title: string; detail: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <span className="empty-orbit" />
      <strong>{title}</strong>
      <p>{detail}</p>
      {action}
    </div>
  );
}

export function Badge({ value, tone = "neutral" }: { value: string; tone?: string }) {
  return <span className={`badge ${tone}`}>{kindLabel(value)}</span>;
}
