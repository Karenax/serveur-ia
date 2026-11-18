import {useCallback, useEffect, useRef, type ReactNode} from "react";

export function Modal({title, children, onClose, dirty = false, busy = false}: {title: string; children: ReactNode; onClose: () => void; dirty?: boolean; busy?: boolean}) {
  const panel = useRef<HTMLDivElement>(null);
  const close = useCallback(() => {
    if (busy) return;
    if (!dirty || window.confirm("Les corrections ne sont pas enregistrées. Fermer ce brouillon ?")) onClose();
  }, [busy, dirty, onClose]);
  useEffect(() => {
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    panel.current?.focus();
    return () => {if (previous?.isConnected) previous.focus();};
  }, []);
  useEffect(() => {
    if (!dirty) return;
    const guard = (event: BeforeUnloadEvent) => {event.preventDefault(); event.returnValue = "";};
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [dirty]);
  return <div className="workspace-modal-backdrop">
    <div ref={panel} tabIndex={-1} role="dialog" aria-modal="true" aria-label={title} className="workspace-modal" data-workspace-dirty={dirty ? "true" : undefined}
      onKeyDown={event => {
        if (event.key === "Escape") {event.stopPropagation(); close();}
        if (event.key !== "Tab") return;
        const fields = Array.from(panel.current?.querySelectorAll<HTMLElement>("button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex='0']") || []);
        if (!fields.length) {event.preventDefault(); return;}
        const first = fields[0], last = fields[fields.length - 1];
        if (event.shiftKey && (document.activeElement === first || document.activeElement === panel.current)) {event.preventDefault(); last.focus();}
        if (!event.shiftKey && (document.activeElement === last || document.activeElement === panel.current)) {event.preventDefault(); first.focus();}
      }}>
      <header className="workspace-modal-heading"><h2>{title}</h2><button type="button" aria-label="Fermer" disabled={busy} onClick={close}>×</button></header>
      {children}
    </div>
  </div>;
}
