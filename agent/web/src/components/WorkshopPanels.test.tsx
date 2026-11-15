import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import { BomPanel } from "./WorkshopPanels";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("ouvre le sélecteur depuis le bouton et garde les lignes visibles si l'import échoue", async () => {
  const load = vi.spyOn(api, "bom").mockResolvedValue({count:1, lines:[
    {id:"bom1", reference:"REF", designation:"Tôle", quantity:2, supplier:"Atelier", status:"todo"},
  ]});
  const upload = vi.spyOn(api, "importBomCsv")
    .mockRejectedValueOnce(new Error("Quantité invalide à la ligne 3"))
    .mockResolvedValueOnce({created:1});
  render(<BomPanel projectId="project-id" />);

  const button = await screen.findByRole("button", {name:"Importer un CSV"});
  const input = screen.getByLabelText("Fichier de nomenclature CSV") as HTMLInputElement;
  const picker = vi.spyOn(input, "click").mockImplementation(() => {});
  button.focus();
  expect(document.activeElement).toBe(button);
  fireEvent.click(button);
  expect(picker).toHaveBeenCalledOnce();

  const file = new File(["Référence;Désignation\nREF;Tôle"], "atelier.csv", {type:"text/csv"});
  fireEvent.change(input, {target:{files:[file]}});
  expect((await screen.findByRole("alert")).textContent).toBe("Quantité invalide à la ligne 3");
  expect(screen.getByText("Tôle")).toBeTruthy();
  expect(load).toHaveBeenCalledTimes(1);

  fireEvent.change(input, {target:{files:[file]}});
  await screen.findByText("1 ligne importée.");
  expect(upload.mock.calls).toEqual([["project-id",file], ["project-id",file]]);
  expect(load).toHaveBeenCalledTimes(2);
});
