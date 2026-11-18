import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { CdcReviewPanel } from "./CdcReviewPanel";
import { api, type CdcItem } from "../lib/api";

afterEach(cleanup);

const items: CdcItem[] = ["Premier", "Deuxième"].map((title, index) => ({
  id: String(index), title, human_id: `EXI-00${index}`, kind: "requirement", source_quote: title,
  physical_page: 1, modality: "mandatory", priority: "unclassified", confidence: 1,
  estimated_hours: 0, knowledge_status: "candidate", evidence: [],
}));

function panel(inactive = false) {
  return render(<section hidden={inactive}>
    <CdcReviewPanel projectId="test" items={items} review={null}
      reviewKind="all" setReviewKind={vi.fn()} reviewStatus="all" setReviewStatus={vi.fn()}
      reviewQuery="" setReviewQuery={vi.fn()} selected={new Set()} setSelected={vi.fn()}
      refresh={vi.fn()} reloadReview={vi.fn()} />
  </section>);
}

describe("Revue CDC", () => {
  it("permet de parcourir la liste au clavier avec un élément actif annoncé", () => {
    panel();
    expect(screen.getByRole("grid",{name:"Éléments CDC"})).toBeTruthy();
    const first=screen.getByRole("row",{name:/Premier/});
    expect(first.tabIndex).toBe(0);
    first.focus();
    expect(document.activeElement).toBe(first);
    fireEvent.keyDown(first,{key:"ArrowDown"});
    const second=screen.getByRole("row",{name:/Deuxième/});
    expect(second.getAttribute("aria-selected")).toBe("true");
    expect(document.activeElement).toBe(second);
    expect(first.tabIndex).toBe(-1);
    expect(second.tabIndex).toBe(0);
    expect(second.getAttribute("aria-label")).toContain("EXI-001 · Deuxième · Candidat · 2 sur 2");
    expect((screen.getByLabelText("Titre") as HTMLInputElement).value).toBe("Deuxième");
    fireEvent.keyDown(second,{key:"Home"});
    expect(document.activeElement).toBe(first);
    expect((screen.getByLabelText("Titre") as HTMLInputElement).value).toBe("Premier");
    fireEvent.keyDown(first,{key:"j"});
    expect(document.activeElement).toBe(second);
    fireEvent.keyDown(second,{key:"k"});
    expect(document.activeElement).toBe(first);
  });
  it("conserve l’élément courant quand l’enregistrement échoue", async () => {
    vi.spyOn(api, "patchCdcItem").mockRejectedValue(new Error("Échec de sauvegarde"));
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    panel();
    fireEvent.click(screen.getByRole("row", { name: /Premier/ }));
    fireEvent.keyDown(window, { key: "c" });
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect((screen.getByLabelText("Titre") as HTMLInputElement).value).toBe("Premier");
  });
  it("préserve le texte non enregistré quand le clavier change de ligne", () => {
    panel();
    fireEvent.change(screen.getByLabelText("Titre"), {target: {value: "Modification non enregistrée"}});
    const first = screen.getByRole("row", {name: /Premier/});
    first.focus();
    fireEvent.keyDown(first, {key: "ArrowDown"});
    expect((screen.getByLabelText("Titre") as HTMLInputElement).value).toBe("Deuxième");
    const second = screen.getByRole("row", {name: /Deuxième/});
    fireEvent.keyDown(second, {key: "ArrowUp"});
    expect((screen.getByLabelText("Titre") as HTMLInputElement).value).toBe("Modification non enregistrée");
  });
  it("ignore les raccourcis quand la revue reste montée dans un onglet masqué", () => {
    const patch = vi.spyOn(api, "patchCdcItem").mockResolvedValue({});
    panel(true);
    fireEvent.click(screen.getByText("Premier", { exact: true }));
    fireEvent.keyDown(window, { key: "c" });
    expect(patch).not.toHaveBeenCalled();
  });
  it("passe à l’élément suivant après une sauvegarde réussie", async () => {
    vi.spyOn(api, "patchCdcItem").mockResolvedValue({});
    panel();
    fireEvent.click(screen.getByRole("row", { name: /Premier/ }));
    fireEvent.keyDown(window, { key: "c" });
    await waitFor(() => expect((screen.getByLabelText("Titre") as HTMLInputElement).value).toBe("Deuxième"));
  });
});
