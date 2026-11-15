import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CdcSourceUpload } from "./CdcSourceUpload";
import { api, type CdcSource } from "../lib/api";
import { beginActivity } from "../lib/asyncActivity";

vi.mock("../lib/asyncActivity", () => ({ beginActivity: vi.fn() }));

const source: CdcSource = { id: "source-1", ref: "CDC-1", filename: "Client.pdf", revision: "R1", status: "PRÊTE", pages: 2, size: "1 Ko" };
const file = new File(["CDC fictif"], "Client.pdf", { type: "application/pdf" });
const finish = vi.fn();
const choose = () => fireEvent.change(screen.getByLabelText("Sélectionner un CDC"), { target: { files: [file] } });
const deferred = <T,>() => {
  let resolve!: (result: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((done, fail) => { resolve = done; reject = fail; });
  return { promise, resolve, reject };
};

beforeEach(() => { vi.mocked(beginActivity).mockReturnValue(finish); finish.mockClear(); });
afterEach(() => { cleanup(); vi.restoreAllMocks(); });

describe("Indicateur d’ajout d’un CDC", () => {
  it("s’affiche dès la sélection et couvre l’extraction puis le rechargement effectif de la liste", async () => {
    const upload = deferred<{ source_id: string; message: string }>();
    const refresh = deferred<boolean>();
    const uploadSpy = vi.spyOn(api, "uploadCdc").mockReturnValue(upload.promise);
    const onRefresh = vi.fn(() => refresh.promise);
    const view = render(<CdcSourceUpload projectId="p1" sources={[]} onRefresh={onRefresh} />);
    choose();
    expect(screen.getByRole("status").textContent).toContain("Importation et extraction");
    expect((screen.getByRole("button", { name: "Ajout du CDC en cours…" }) as HTMLButtonElement).disabled).toBe(true);
    expect(beginActivity).toHaveBeenCalledWith("Ajout du CDC au projet");
    choose(); expect(uploadSpy).toHaveBeenCalledTimes(1);
    expect(finish).not.toHaveBeenCalled();
    upload.resolve({ source_id: source.id, message: "2 page(s) extraite(s)" });
    await waitFor(() => expect(onRefresh).toHaveBeenCalledTimes(1));
    expect(screen.getByRole("status").textContent).toContain("Mise à jour de la liste");
    expect(finish).not.toHaveBeenCalled();
    view.rerender(<CdcSourceUpload projectId="p1" sources={[source]} onRefresh={onRefresh} />);
    expect(finish).not.toHaveBeenCalled();
    refresh.resolve(true);
    await screen.findByText("2 page(s) extraite(s)");
    expect(finish).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("progressbar")).toBeNull();
    expect((screen.getByRole("button", { name: "⬆ Ajouter un CDC" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("signale une liste non actualisée et permet sa reprise sans réimporter le document", async () => {
    const upload = vi.spyOn(api, "uploadCdc").mockResolvedValue({ source_id: source.id, message: "CDC enregistré" });
    const nextRefresh = deferred<boolean>();
    const onRefresh = vi.fn<() => Promise<boolean>>().mockResolvedValueOnce(false).mockImplementationOnce(() => nextRefresh.promise);
    const view = render(<CdcSourceUpload projectId="p1" sources={[]} onRefresh={onRefresh} />);
    choose();
    expect((await screen.findByRole("alert")).textContent).toContain("sans réimporter");
    expect(finish).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Actualiser la liste des CDC" }));
    expect(screen.getByRole("status").textContent).toContain("Mise à jour de la liste");
    view.rerender(<CdcSourceUpload projectId="p1" sources={[source]} onRefresh={onRefresh} />);
    nextRefresh.resolve(true);
    await screen.findByText("CDC enregistré");
    expect(upload).toHaveBeenCalledTimes(1);
    expect(onRefresh).toHaveBeenCalledTimes(2);
    expect(finish).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("affiche une erreur d’import et réactive la sélection", async () => {
    vi.spyOn(api, "uploadCdc").mockRejectedValue(new Error("Document illisible : extraction impossible"));
    const refresh = vi.fn();
    render(<CdcSourceUpload projectId="p1" sources={[]} onRefresh={refresh} />);
    choose();
    expect((await screen.findByRole("alert")).textContent).toBe("Document illisible : extraction impossible");
    expect(refresh).not.toHaveBeenCalled();
    expect(finish).toHaveBeenCalledTimes(1);
    expect((screen.getByLabelText("Sélectionner un CDC") as HTMLInputElement).disabled).toBe(false);
    expect(screen.queryByRole("button", { name: "Actualiser la liste des CDC" })).toBeNull();
  });

  it("termine aussi lorsqu’un document déjà enregistré est bien présent dans la liste", async () => {
    vi.spyOn(api, "uploadCdc").mockResolvedValue({ source_id: source.id, status: "duplicate", message: "Ce document est déjà enregistré (même empreinte)." });
    render(<CdcSourceUpload projectId="p1" sources={[source]} onRefresh={vi.fn().mockResolvedValue(true)} />);
    choose();
    await screen.findByText("Ce document est déjà enregistré (même empreinte).");
    expect(finish).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("ne confond pas le retour du rechargement avec l’apparition effective du document", async () => {
    vi.spyOn(api, "uploadCdc").mockResolvedValue({ source_id: source.id, message: "CDC enregistré" });
    render(<CdcSourceUpload projectId="p1" sources={[]} onRefresh={vi.fn().mockResolvedValue(true)} />);
    choose();
    expect((await screen.findByRole("alert")).textContent).toContain("il n’apparaît pas encore dans la liste");
    expect(screen.queryByText("CDC enregistré")).toBeNull();
    expect(screen.getByRole("button", { name: "Actualiser la liste des CDC" })).toBeTruthy();
    expect(finish).toHaveBeenCalledTimes(1);
  });

  it("préserve la confirmation d’enregistrement quand le rechargement rejette", async () => {
    vi.spyOn(api, "uploadCdc").mockResolvedValue({ source_id: source.id, message: "CDC enregistré" });
    render(<CdcSourceUpload projectId="p1" sources={[]} onRefresh={vi.fn().mockRejectedValue(new Error("Réseau indisponible"))} />);
    choose();
    expect((await screen.findByRole("alert")).textContent).toContain("Le CDC est enregistré, mais la liste n’a pas pu être actualisée : Réseau indisponible");
    expect(screen.getByRole("button", { name: "Actualiser la liste des CDC" })).toBeTruthy();
    expect(finish).toHaveBeenCalledTimes(1);
  });

  it("clôture l’indicateur et ignore la réponse tardive lorsqu’on change de projet", async () => {
    const upload = deferred<{ source_id: string }>();
    vi.spyOn(api, "uploadCdc").mockReturnValue(upload.promise);
    const refresh = vi.fn();
    const view = render(<CdcSourceUpload projectId="p1" sources={[]} onRefresh={refresh} />);
    choose();
    view.rerender(<CdcSourceUpload projectId="p2" sources={[]} onRefresh={refresh} />);
    expect(finish).toHaveBeenCalledTimes(1);
    upload.resolve({ source_id: source.id });
    await waitFor(() => expect(screen.queryByRole("progressbar")).toBeNull());
    expect(refresh).not.toHaveBeenCalled();
    expect(finish).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
