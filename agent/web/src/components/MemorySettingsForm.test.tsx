import {afterEach, beforeEach, expect, it, vi} from "vitest";
import {cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {MemorySettingsForm} from "./SettingsForms";
import {api} from "../lib/api";

vi.mock("./MemoryRecovery", () => ({MemoryRecovery: () => <div>File EG2</div>}));
beforeEach(() => {
  vi.spyOn(api, "brainMemorySettings").mockResolvedValue({configured: {
    engine: "eg2", prefix: "pb", embedding_provider: "openai_compatible",
    embedding_endpoint: "http://server:1234", embedding_model: "text-embedding-embeddinggemma-2",
    index_path: "", timeout_s: 120, batch_size: 8},
    active: {health: {data_dir: "storage/eg2/index.db", passages: 123, status: "ok"}}});
  vi.spyOn(api, "saveBrainMemorySettings").mockResolvedValue({});
  vi.spyOn(api, "brainMemoryTest").mockResolvedValue({status: "ok", recall_hits: 1, remember_s: 1.2, recall_s: .3});
});
afterEach(() => {cleanup();vi.restoreAllMocks();});

it("configure le moteur unique EG2 et montre son index persistant", async () => {
  render(<MemorySettingsForm/>);
  await screen.findByText(/123 passages/);
  expect(screen.queryByRole("combobox")).toBeNull();
  expect(screen.getByText("Connexion au service de recherche").closest("details")).toHaveProperty("open",false);
  fireEvent.click(screen.getByText("Connexion au service de recherche"));
  fireEvent.change(screen.getByLabelText("Adresse du serveur de recherche"), {target: {value: "http://new:1234"}});
  fireEvent.click(screen.getByRole("button", {name: "Enregistrer"}));
  await waitFor(() => expect(api.saveBrainMemorySettings).toHaveBeenCalledWith(expect.objectContaining({
    engine: "eg2", embedding_endpoint: "http://new:1234", embedding_model: "text-embedding-embeddinggemma-2"})));
});

it("affiche les mesures du test réel et empêche les doubles demandes", async () => {
  let finish: (value: any) => void = () => {};
  vi.mocked(api.brainMemoryTest).mockReturnValue(new Promise(resolve => {finish = resolve;}));
  render(<MemorySettingsForm/>);
  await screen.findByText(/123 passages/);
  fireEvent.click(screen.getByRole("button", {name: "Tester la recherche"}));
  expect((screen.getByRole("button", {name: "En cours…"}) as HTMLButtonElement).disabled).toBe(true);
  finish({status: "ok", recall_hits: 1, remember_s: 1.2, recall_s: .3});
  await screen.findByText(/Recherche vérifiée/);
  expect(api.brainMemoryTest).toHaveBeenCalledOnce();
});
