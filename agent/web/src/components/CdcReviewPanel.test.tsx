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
  return render(<section className={`mac-window${inactive ? " inactive" : ""}`}>
    <CdcReviewPanel projectId="test" items={items} review={null}
      reviewKind="all" setReviewKind={vi.fn()} reviewStatus="all" setReviewStatus={vi.fn()}
      reviewQuery="" setReviewQuery={vi.fn()} selected={new Set()} setSelected={vi.fn()}
      refresh={vi.fn()} reloadReview={vi.fn()} />
  </section>);
}

describe("Revue CDC", () => {
  it("conserve l’élément courant quand l’enregistrement échoue", async () => {
    vi.spyOn(api, "patchCdcItem").mockRejectedValue(new Error("Échec de sauvegarde"));
    const alert = vi.spyOn(window, "alert").mockImplementation(() => {});
    panel();
    fireEvent.click(screen.getByRole("option", { name: /Premier/ }));
    fireEvent.keyDown(window, { key: "c" });
    await waitFor(() => expect(alert).toHaveBeenCalled());
    expect((screen.getByLabelText("Titre") as HTMLInputElement).value).toBe("Premier");
  });
  it("ignore les raccourcis dans une fenêtre inactive", () => {
    const patch = vi.spyOn(api, "patchCdcItem").mockResolvedValue({});
    panel(true);
    fireEvent.click(screen.getByRole("option", { name: /Premier/ }));
    fireEvent.keyDown(window, { key: "c" });
    expect(patch).not.toHaveBeenCalled();
  });
  it("passe à l’élément suivant après une sauvegarde réussie", async () => {
    vi.spyOn(api, "patchCdcItem").mockResolvedValue({});
    panel();
    fireEvent.click(screen.getByRole("option", { name: /Premier/ }));
    fireEvent.keyDown(window, { key: "c" });
    await waitFor(() => expect((screen.getByLabelText("Titre") as HTMLInputElement).value).toBe("Deuxième"));
  });
});
