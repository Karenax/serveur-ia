import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ClassifiedMailList } from "./ClassifiedMailList";
import { api } from "../lib/api";
afterEach(cleanup);

it("permet de reclasser un mail déjà classé dans DIVERS", async () => {
  vi.spyOn(api, "brainSources").mockResolvedValue([{ source_id: "source", author: "audit", project_id: "divers", metadata: { subject: "À reclasser" } }]);
  const assign = vi.spyOn(api, "brainReassignSource").mockResolvedValue({});
  render(<ClassifiedMailList projects={[{ id: "divers", code: "DIVERS", name: "Divers" }, { id: "project", code: "P1", name: "Projet" }]} />);
  const select = await screen.findByLabelText("Projet de À reclasser");
  fireEvent.change(select, { target: { value: "project" } });
  fireEvent.click(screen.getByRole("button", { name: "Valider le reclassement" }));
  await waitFor(() => expect(assign).toHaveBeenCalledWith("source", "project"));
  expect(screen.getByRole("link", { name: "Télécharger la source originale" }).getAttribute("href")).toBe("/v1/sources/source/raw");
});
