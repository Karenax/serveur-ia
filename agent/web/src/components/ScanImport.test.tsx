import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { ScanImport } from "../App";
import { api } from "../lib/api";

afterEach(()=>{cleanup();vi.restoreAllMocks();});
function manual() {
  fireEvent.click(screen.getByRole("button",{name:"Manuel"}));
  fireEvent.change(screen.getByPlaceholderText("Code (ex : AIRB25LTH0806-A)"),{target:{value:"TEST-0807"}});
  fireEvent.change(screen.getByPlaceholderText("Titre du projet"),{target:{value:"Projet créé"}});
}
it("attend le rafraîchissement du portefeuille avant de fermer et bloque les doublons", async () => {
  let release!:()=>void;
  const reload=vi.fn(()=>new Promise<void>(resolve=>{release=resolve;}));
  const close=vi.fn();
  const create=vi.spyOn(api,"createProject").mockResolvedValue({id:"created"});
  render(<ScanImport reload={reload} close={close}/>);manual();
  fireEvent.click(screen.getByRole("button",{name:"Créer"}));
  await waitFor(()=>expect(reload).toHaveBeenCalledOnce());
  fireEvent.click(screen.getByRole("button",{name:"Création…"}));
  expect(create).toHaveBeenCalledOnce();expect(close).not.toHaveBeenCalled();
  release();await waitFor(()=>expect(close).toHaveBeenCalledOnce());
});
it("affiche l’échec de création sans perdre les champs ni quitter le formulaire", async () => {
  vi.spyOn(api,"createProject").mockRejectedValue(new Error("Création indisponible"));
  const close=vi.fn(),reload=vi.fn();
  render(<ScanImport reload={reload} close={close}/>);manual();
  fireEvent.click(screen.getByRole("button",{name:"Créer"}));
  await screen.findByText("Création indisponible");
  expect((screen.getByPlaceholderText("Titre du projet") as HTMLInputElement).value).toBe("Projet créé");
  expect(close).not.toHaveBeenCalled();expect(reload).not.toHaveBeenCalled();
});
it("notifie le nouveau parcours après import d’un dossier réseau", async () => {
  vi.spyOn(api,"scanFolder").mockResolvedValue({code:"TEST-0808",title:"Projet importé"});
  vi.spyOn(api,"importFolder").mockResolvedValue({id:"imported"});
  const onCreated=vi.fn().mockResolvedValue(undefined),reload=vi.fn(),close=vi.fn();
  render(<ScanImport reload={reload} close={close} onCreated={onCreated}/>);
  fireEvent.change(screen.getByPlaceholderText(/Chemin réseau/),{target:{value:"C:/fixtures/project"}});
  fireEvent.click(screen.getByRole("button",{name:/Scanner/}));
  fireEvent.click(await screen.findByRole("button",{name:"Importer le projet"}));
  await waitFor(()=>expect(onCreated).toHaveBeenCalledWith("imported"));
  expect(reload).not.toHaveBeenCalled();expect(close).not.toHaveBeenCalled();
});

it("affiche un ancien document contradictoire sans remplacer le code du dossier",async()=>{
  vi.spyOn(api,"scanFolder").mockResolvedValue({code:"AIRB26LTH0205-A",title:"LED 2026",budget_h:0,
    warnings:["TDAO : code AIRB23LTH3146-A différent du dossier AIRB26LTH0205-A."]});
  const importer=vi.spyOn(api,"importFolder").mockResolvedValue({id:"new-project"});
  render(<ScanImport reload={vi.fn()} close={vi.fn()}/>);
  fireEvent.change(screen.getByPlaceholderText(/Chemin réseau/),{target:{value:"V:/06 - AIRBUS LT/AIRB26LTH0205-A - LED 2026"}});
  fireEvent.click(screen.getByRole("button",{name:/Scanner/}));
  await screen.findByRole("alert");
  expect((screen.getByRole("textbox",{name:/^Code$/}) as HTMLInputElement).value).toBe("AIRB26LTH0205-A");
  fireEvent.click(screen.getByRole("button",{name:"Importer le projet"}));
  await waitFor(()=>expect(importer).toHaveBeenCalledWith("V:/06 - AIRBUS LT/AIRB26LTH0205-A - LED 2026","AIRB26LTH0205-A","LED 2026"));
});
