import {afterEach, expect, it, vi} from "vitest";
import {cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {OperationsPanel} from "./OperationsPanel";
import {api, type OperationsState} from "../lib/api";

afterEach(()=>{cleanup();vi.restoreAllMocks();});
const state:OperationsState={backup:{directory:"backup/current",status:"created",created_at:"2026-10-10T12:00:00Z"},migration_backups:{count:4,bytes:1024**2},disk_free_bytes:20*1024**3,disk_low:false,databases:{brain_bytes:1,erp_bytes:1}};

it("vérifie la sauvegarde puis relit son état en gardant les détails accessibles",async()=>{
  vi.spyOn(api,"operations").mockResolvedValueOnce(state).mockResolvedValue({...state,backup:{...state.backup!,status:"verified",verified_at:"2026-10-11T12:00:00Z"}});
  vi.spyOn(api,"verifyBackup").mockResolvedValue({status:"verified"});
  render(<OperationsPanel/>);
  await screen.findByText("Vérification à effectuer");
  expect(screen.getByText(/Dernière sauvegarde du service Projets/)).toBeTruthy();
  expect(screen.getByText(/brouillons non synchronisés/)).toBeTruthy();
  expect(screen.getByText("Espace disque et sauvegardes de migration").closest("details")).toHaveProperty("open",false);
  fireEvent.click(screen.getByRole("button",{name:"Vérifier la dernière sauvegarde"}));
  await waitFor(()=>expect(api.verifyBackup).toHaveBeenCalledOnce());
  await screen.findByText(/Vérifiée le/);
  fireEvent.click(screen.getByText("Espace disque et sauvegardes de migration"));
  expect(screen.getByText(/4 sauvegarde\(s\) de migration/)).toBeTruthy();
});

it("garde l’espace faible et l’échec de vérification visibles",async()=>{
  vi.spyOn(api,"operations").mockResolvedValue({...state,disk_low:true,backup:{...state.backup!,status:"verification_failed"}});
  render(<OperationsPanel/>);
  expect(await screen.findByRole("alert")).toHaveProperty("textContent","Espace disque faible : 20.0 Go disponibles.");
  expect(screen.getByText("La dernière vérification a échoué")).toBeTruthy();
  expect(screen.getByText("Espace disque et sauvegardes de migration").closest("details")).toHaveProperty("open",false);
});
