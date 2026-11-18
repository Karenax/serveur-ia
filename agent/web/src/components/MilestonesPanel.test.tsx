import { afterEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { api } from "../lib/api";
import { milestoneApi, type Milestone, type MilestoneReview } from "../lib/milestones";
import { MilestonesPanel } from "./MilestonesPanel";

const originalHidden=Object.getOwnPropertyDescriptor(document,"hidden");
afterEach(() => {cleanup();vi.useRealTimers();vi.restoreAllMocks();if(originalHidden)Object.defineProperty(document,"hidden",originalHidden);else Reflect.deleteProperty(document,"hidden");});
const rows: Milestone[] = [{id: "fat", title: "FAT", due_date: "2026-10-20", contractual_date: "2026-10-18",
  forecast_date: "2026-10-20", actual_date: "", variance_days: 2, state: "scheduled"}];
const review: MilestoneReview = {pending_total: 1, job: null, candidates: [{id: "c1", title: "FAT", date_type: "forecast_date",
  date: "2026-10-22", quote: "FAT reportée au 22/10/2026.", evidence: {kind: "brain", label: "Mail planning", source_id: "s1"},
  confidence: 0.8, current_value: "2026-10-20", conflict: true, milestone_id: "fat"}]};

it("distingue les trois dates, l'écart et le remplacement explicite", async () => {
  vi.spyOn(milestoneApi, "review").mockResolvedValue(review);
  const decide = vi.spyOn(milestoneApi, "decide").mockResolvedValue({});
  const refresh = vi.fn();
  render(<MilestonesPanel projectId="p1" rows={rows} refresh={refresh} />);
  expect((screen.getByLabelText("Contractuelle · FAT") as HTMLInputElement).value).toBe("2026-10-18");
  expect((screen.getByLabelText("Prévisionnelle · FAT") as HTMLInputElement).value).toBe("2026-10-20");
  expect((screen.getByLabelText("Réelle · FAT") as HTMLInputElement).value).toBe("");
  expect(screen.getByText("+2 j")).toBeTruthy();
  expect(await screen.findByText("FAT reportée au 22/10/2026.")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", {name: "Valider le remplacement"}));
  await waitFor(() => expect(decide).toHaveBeenCalledWith("p1", "c1", {
    decision: "accept", expected_value: "2026-10-20", milestone_id: "fat",
  }));
  await waitFor(() => expect(refresh).toHaveBeenCalled());
});

it("enregistre uniquement le champ édité et présente les erreurs", async () => {
  vi.spyOn(milestoneApi, "review").mockResolvedValue({candidates: [], pending_total: 0, job: null});
  const patch = vi.spyOn(api, "patchMilestone").mockRejectedValue(new Error("Source inaccessible"));
  render(<MilestonesPanel projectId="p1" rows={rows} refresh={vi.fn()} />);
  await screen.findByText(/Aucune date à valider/);
  const input = screen.getByLabelText("Réelle · FAT");
  fireEvent.change(input, {target: {value: "2026-10-05"}});
  fireEvent.blur(input);
  await waitFor(() => expect(patch).toHaveBeenCalledWith("p1", "fat", {actual_date: "2026-10-05"}));
  expect((await screen.findByRole("alert")).textContent).toContain("Source inaccessible");
  expect((input as HTMLInputElement).value).toBe("");
});

it("affiche le compteur de recherche et les documents inaccessibles", async () => {
  vi.spyOn(milestoneApi, "review").mockResolvedValue({candidates: [], pending_total: 0, job: {
    id: "j1", status: "running", processed: 2, total: 5, proposed: 1,
    warnings: ["Chemin inaccessible : V:/Affaire"], error: null, updated_at: "2026-10-05",
  }});
  render(<MilestonesPanel projectId="p1" rows={rows} refresh={vi.fn()} />);
  expect(await screen.findByText("2 / 5 passages traités · 1 proposition(s)")).toBeTruthy();
  expect((screen.getByRole("button", {name: /Recherche en cours/}) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText("Chemin inaccessible : V:/Affaire")).toBeTruthy();
  expect((screen.getByRole("progressbar") as HTMLProgressElement).value).toBe(2);
});

it("sépare les résultats de deux projets pendant une requête retardée", async () => {
  let resolve!: (value: MilestoneReview) => void;
  const load = vi.spyOn(milestoneApi, "review").mockReturnValueOnce(new Promise(done => {resolve = done;}))
    .mockResolvedValue({candidates: [], pending_total: 0, job: null});
  const view = render(<MilestonesPanel projectId="p1" rows={rows} refresh={vi.fn()} />);
  view.rerender(<MilestonesPanel projectId="p2" rows={[]} refresh={vi.fn()} />);
  await waitFor(() => expect(load).toHaveBeenCalledWith("p2", expect.any(AbortSignal)));
  resolve(review);
  await waitFor(() => expect(screen.queryByText("FAT reportée au 22/10/2026.")).toBeNull());
});

it("suspend les lectures en arrière-plan et reprend sans appliquer une réponse tardive",async()=>{
  vi.useFakeTimers();Object.defineProperty(document,"hidden",{configurable:true,value:true});
  let finishOld!:(value:MilestoneReview)=>void;
  const read=vi.spyOn(milestoneApi,"review").mockReturnValueOnce(new Promise(resolve=>{finishOld=resolve;}))
    .mockResolvedValue({candidates:[],pending_total:0,job:null});
  render(<MilestonesPanel projectId="p1" rows={rows} refresh={vi.fn()}/>);
  await act(async()=>{});expect(read).not.toHaveBeenCalled();
  Object.defineProperty(document,"hidden",{configurable:true,value:false});
  await act(async()=>{document.dispatchEvent(new Event("visibilitychange"));});
  expect(read).toHaveBeenCalledTimes(1);const first=read.mock.calls[0][1]!;
  Object.defineProperty(document,"hidden",{configurable:true,value:true});
  await act(async()=>{document.dispatchEvent(new Event("visibilitychange"));});
  expect(first.aborted).toBe(true);
  await act(async()=>{await vi.advanceTimersByTimeAsync(45000);});expect(read).toHaveBeenCalledTimes(1);
  Object.defineProperty(document,"hidden",{configurable:true,value:false});
  await act(async()=>{document.dispatchEvent(new Event("visibilitychange"));});
  expect(read).toHaveBeenCalledTimes(2);expect(screen.getByText(/Aucune date à valider/)).toBeTruthy();
  await act(async()=>{finishOld(review);});
  expect(screen.queryByText("FAT reportée au 22/10/2026.")).toBeNull();
});
