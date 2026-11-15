import {afterEach, expect, it, vi} from "vitest";
import {act, cleanup, fireEvent, render, screen, waitFor} from "@testing-library/react";
import {api} from "../lib/api";
import {MemoryRetryButton} from "./MemoryRetryButton";

vi.mock("../lib/api", () => ({api: {brainRetryMemory: vi.fn()}}));
afterEach(() => {cleanup(); vi.clearAllMocks();});

it("montre l’attente, bloque les doubles clics puis affiche les échecs retournés par le moteur", async () => {
  let finish!: (value: {indexed: number; failed: number; forgotten: number}) => void;
  vi.mocked(api.brainRetryMemory).mockReturnValue(new Promise(resolve => {finish = resolve;}));
  const refresh = vi.fn().mockResolvedValue(undefined);
  render(<MemoryRetryButton projectId="p1" onComplete={refresh}/>);
  fireEvent.click(screen.getByRole("button"));
  expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByRole("status").textContent).toContain("Reprise en cours");
  fireEvent.click(screen.getByRole("button"));
  expect(api.brainRetryMemory).toHaveBeenCalledTimes(1);
  await act(async () => finish({indexed: 2, failed: 3, forgotten: 1}));
  expect(screen.getByRole("alert").textContent).toContain("2 indexée(s), 3 en échec");
  expect(refresh).toHaveBeenCalledTimes(1);
  expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(false);
});

it("signale une reprise vide sans faire croire à une indexation réussie", async () => {
  vi.mocked(api.brainRetryMemory).mockResolvedValue({indexed: 0, failed: 0, forgotten: 0});
  render(<MemoryRetryButton projectId="p1" onComplete={vi.fn().mockResolvedValue(undefined)}/>);
  fireEvent.click(screen.getByRole("button"));
  await waitFor(() => expect(screen.getByRole("status").textContent).toContain("0 indexée(s)"));
});

it("affiche une erreur de requête et permet une nouvelle tentative", async () => {
  vi.mocked(api.brainRetryMemory).mockRejectedValue(new Error("Délai dépassé"));
  const refresh = vi.fn();
  render(<MemoryRetryButton projectId="p1" onComplete={refresh}/>);
  fireEvent.click(screen.getByRole("button"));
  expect((await screen.findByRole("alert")).textContent).toContain("Reprise non confirmée : Délai dépassé");
  expect(refresh).not.toHaveBeenCalled();
  expect((screen.getByRole("button") as HTMLButtonElement).disabled).toBe(false);
});
