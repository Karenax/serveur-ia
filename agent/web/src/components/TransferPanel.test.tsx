import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { api } from "../lib/api";
import { TransferPanel } from "./TransferPanel";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("propose le téléchargement de la version historique et garde son aperçu", async () => {
  vi.spyOn(api, "deliveries").mockResolvedValue([
    {id:"saved", version:2, draft:false, file:"transfert.md", sha256:"", created_at:"2026-11-15T12:00:00Z"},
  ]);
  const read = vi.spyOn(api, "delivery").mockResolvedValue({
    version:2, markdown:"Preuve CDC — cdc-recette.pdf, révision R1, page 2", snapshot:{},
  });
  render(<TransferPanel projectId="proj" />);
  const download = await screen.findByRole("link", {name:"Télécharger la version 2"});
  expect(download.getAttribute("href")).toBe("/api/v1/projects/proj/cdc/deliveries/saved/download");
  expect(download.hasAttribute("download")).toBe(true);
  fireEvent.click(screen.getByRole("button", {name:/Version 2/}));
  await screen.findByText("Preuve CDC — cdc-recette.pdf, révision R1, page 2");
  expect(read).toHaveBeenCalledWith("proj","saved");
});
