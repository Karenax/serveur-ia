import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { api, type CdcJob } from "../lib/api";
import { CdcJobsPanel } from "./CdcJobsPanel";
import { TransferPanel } from "./TransferPanel";

afterEach(() => {cleanup(); vi.restoreAllMocks();});

const job: CdcJob = {id: "j1", project_id: "p1", source_id: "s1", status: "failed", completed_batches: 2,
  total_batches: 4, progress: 48, cancel_requested: false, result: {}, error: "Interruption",
  created_at: "2026-10-02T10:00:00Z", updated_at: "2026-10-02T10:00:00Z"};

it("propose une reprise après échec et une annulation différée pendant le lot", () => {
  const onRetry = vi.fn(), onCancel = vi.fn();
  const view = render(<CdcJobsPanel jobs={[job]} error="" onRetry={onRetry} onCancel={onCancel} />);
  expect(screen.getByText(/2\/4 lots/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", {name: "Reprendre"}));
  expect(onRetry).toHaveBeenCalledWith("j1");
  view.rerender(<CdcJobsPanel jobs={[{...job, status: "running", cancel_requested: true}]} error="" onRetry={onRetry} onCancel={onCancel} />);
  expect((screen.getByRole("button", {name: "Annulation demandée…"}) as HTMLButtonElement).disabled).toBe(true);
  expect(onCancel).not.toHaveBeenCalled();
});

it("relit une ancienne version et crée une nouvelle version sans écraser l'historique", async () => {
  const version = {id: "v1", kind: "transfer-be", version: 1, draft: true, created_at: "2026-10-02T10:00:00Z", sha256: "hash", file: "v1.md"};
  vi.spyOn(api, "deliveries").mockResolvedValue([version]);
  vi.spyOn(api, "delivery").mockResolvedValue({...version, markdown: "Exigences de la version 1", snapshot: {}});
  const transfer = vi.spyOn(api, "transfer").mockResolvedValue({markdown: "Nouvelle version 2", version: 2});
  render(<TransferPanel projectId="p1" />);
  fireEvent.click(await screen.findByRole("button", {name: /Version 1/}));
  await screen.findByText("Exigences de la version 1");
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(screen.getByRole("button", {name: /Générer une nouvelle version/}));
  await screen.findByText("Nouvelle version 2");
  await waitFor(() => expect(transfer).toHaveBeenCalledWith("p1", true));
  expect(screen.getByRole("button", {name: /Version 1/})).toBeTruthy();
});
