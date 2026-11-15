import { useEffect, useRef, useState } from "react";
import { api, type CdcSource } from "../lib/api";
import { beginActivity } from "../lib/asyncActivity";

type Refresh = () => Promise<boolean | void> | boolean | void;
type SavedDocument = { sourceId: string; filename: string; message: string };
type PendingRefresh = SavedDocument & { token: object; refreshSucceeded: boolean };

export function CdcSourceUpload({ projectId, sources, onRefresh }: {
  projectId: string; sources: CdcSource[]; onRefresh: Refresh;
}) {
  const input = useRef<HTMLInputElement>(null);
  const operation = useRef<{ token: object; finish: () => void } | null>(null);
  const [busy, setBusy] = useState<"upload" | "refresh" | null>(null);
  const [filename, setFilename] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [savedDocument, setSavedDocument] = useState<SavedDocument | null>(null);
  const [pendingRefresh, setPendingRefresh] = useState<PendingRefresh | null>(null);

  useEffect(() => {
    setBusy(null); setError(""); setNotice(""); setSavedDocument(null); setPendingRefresh(null);
    return () => { operation.current?.finish(); operation.current = null; };
  }, [projectId]);

  useEffect(() => {
    if (!pendingRefresh || operation.current?.token !== pendingRefresh.token) return;
    // Finish after the imported source is present in the list rendered by the project.
    // An HTTP upload acknowledgement alone does not prove that the list has refreshed.
    const visible = sources.some(source => source.id === pendingRefresh.sourceId);
    operation.current.finish(); operation.current = null;
    setBusy(null); setPendingRefresh(null);
    if (visible) {
      setNotice(pendingRefresh.message); setError(""); setSavedDocument(null);
    } else {
      setError(pendingRefresh.refreshSucceeded
        ? "Le CDC est enregistré, mais il n’apparaît pas encore dans la liste. Actualise la liste sans réimporter le fichier."
        : "Le CDC est enregistré, mais la liste n’a pas pu être actualisée. Réessaie l’actualisation sans réimporter le fichier.");
    }
  }, [pendingRefresh, sources]);

  const start = (label: string) => {
    if (operation.current) return null;
    const token = {};
    operation.current = { token, finish: beginActivity(label) };
    setError(""); setNotice(""); setPendingRefresh(null);
    return token;
  };

  const fail = (token: object, failure: unknown, recorded: boolean) => {
    if (operation.current?.token !== token) return;
    operation.current.finish(); operation.current = null; setBusy(null);
    const detail = failure instanceof Error ? failure.message : String(failure);
    setError(recorded ? `Le CDC est enregistré, mais la liste n’a pas pu être actualisée : ${detail}` : detail);
  };

  const refreshList = async (token: object, document: SavedDocument) => {
    setBusy("refresh");
    const result = await onRefresh();
    if (operation.current?.token === token) {
      setPendingRefresh({ ...document, token, refreshSucceeded: result !== false });
    }
  };

  const upload = async (file: File) => {
    const token = start("Ajout du CDC au projet");
    if (!token) return;
    setFilename(file.name); setBusy("upload"); setSavedDocument(null);
    let recorded = false;
    try {
      const result: { source_id?: string; message?: string } = await api.uploadCdc(projectId, file);
      if (operation.current?.token !== token) return;
      if (!result.source_id) throw new Error("L’import du CDC n’a pas fourni de confirmation. Actualise la liste avant de réessayer.");
      const document = { sourceId: result.source_id, filename: file.name, message: result.message || "CDC ajouté au projet." };
      recorded = true; setSavedDocument(document);
      await refreshList(token, document);
    } catch (failure) { fail(token, failure, recorded); }
  };

  const retryRefresh = async () => {
    if (!savedDocument) return;
    const token = start("Actualisation de la liste des CDC");
    if (!token) return;
    setFilename(savedDocument.filename);
    try { await refreshList(token, savedDocument); }
    catch (failure) { fail(token, failure, true); }
  };

  return <div aria-busy={busy !== null}>
    <button type="button" className="button primary" disabled={busy !== null} onClick={() => input.current?.click()}>
      {busy ? "Ajout du CDC en cours…" : "⬆ Ajouter un CDC"}
    </button>
    <input ref={input} type="file" aria-label="Sélectionner un CDC" accept=".pdf,.docx,.xlsx,.xlsm,.csv,.txt,.md"
      hidden disabled={busy !== null} onChange={event => {
        const file = event.currentTarget.files?.[0];
        event.currentTarget.value = "";
        if (file) void upload(file);
      }} />
    {busy && <p role="status" aria-live="polite">
      <progress aria-label="Ajout du CDC en cours" /> {busy === "upload" ? "Importation et extraction" : "Mise à jour de la liste"} de « {filename} »…
    </p>}
    {notice && <p role="status">{notice}</p>}
    {error && <p role="alert">{error}</p>}
    {savedDocument && error && <button type="button" className="button secondary" disabled={busy !== null} onClick={() => void retryRefresh()}>
      Actualiser la liste des CDC
    </button>}
  </div>;
}
