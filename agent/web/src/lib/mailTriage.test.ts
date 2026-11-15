import { afterEach, expect, it, vi } from "vitest";
import { api, type TriageResult } from "./api";
import { analyzeMailQueue, type TriageProgress } from "./mailTriage";

afterEach(() => vi.restoreAllMocks());

function stats(total: number, fresh = total) {
  vi.spyOn(api, "brainTriageStats").mockResolvedValue({pending_sources: total, new_sources: fresh,
    queued: 0, divers_project_id: "d", divers_count: 0});
}
function batch(scanned: number, errors = 0): TriageResult {
  return {scanned, triaged: scanned - errors, divers: 0, skipped: 0, force: true,
    errors: Array.from({length: errors}, (_, i) => ({source_id: String(i), error: "Échec simulé"}))};
}

it("ne saute pas de mail réanalysé quand des suggestions à 100 % sortent de la file", async () => {
  stats(7);
  const run=vi.spyOn(api,"brainTriageRun").mockResolvedValueOnce({...batch(5),auto_classified:3})
    .mockResolvedValueOnce(batch(2));
  const result=await analyzeMailQueue(true,()=>false,()=>{});
  expect(run.mock.calls).toEqual([[5,0,true],[2,2,true]]);
  expect(result).toMatchObject({processed:7,autoClassified:3,status:"completed"});
});

it("compte chaque lot sur un total fixe, y compris les mails en erreur", async () => {
  stats(12);
  const run = vi.spyOn(api, "brainTriageRun").mockResolvedValueOnce(batch(5))
    .mockResolvedValueOnce(batch(5, 1)).mockResolvedValueOnce(batch(2));
  const reports: TriageProgress[] = [];
  const final = await analyzeMailQueue(true, () => false, p => reports.push(p));
  expect(reports.map(p => [p.processed, p.total])).toEqual([[0,12], [5,12], [10,12], [12,12], [12,12]]);
  expect(run.mock.calls).toEqual([[5,0,true], [5,5,true], [2,10,true]]);
  expect(final).toMatchObject({processed: 12, total: 12, classified: 11, errors: 1, status: "completed"});
});

it("ne saute pas les nouveaux mails quand la file rétrécit après chaque lot", async () => {
  stats(200, 7);
  const run = vi.spyOn(api, "brainTriageRun").mockResolvedValueOnce(batch(5, 1)).mockResolvedValueOnce(batch(2));
  const final = await analyzeMailQueue(false, () => false, () => {});
  expect(run.mock.calls).toEqual([[5,0,false], [2,1,false]]);
  expect(final).toMatchObject({processed: 7, total: 7, status: "completed"});
});

it("conserve le compteur lors d’une interruption", async () => {
  stats(12);
  let cancelled = false;
  const run = vi.spyOn(api, "brainTriageRun").mockImplementation(async () => {cancelled = true; return batch(5);});
  const final = await analyzeMailQueue(true, () => cancelled, () => {});
  expect(run).toHaveBeenCalledTimes(1);
  expect(final).toMatchObject({processed: 5, total: 12, status: "interrupted"});
});

it("signale une file devenue plus courte sans afficher un faux 100 %", async () => {
  stats(12);
  vi.spyOn(api, "brainTriageRun").mockResolvedValue(batch(3));
  expect(await analyzeMailQueue(true, () => false, () => {}))
    .toMatchObject({processed: 3, total: 12, status: "incomplete"});
});

it("conserve les lots acquis lors d’une coupure de connexion", async () => {
  stats(12);
  vi.spyOn(api, "brainTriageRun").mockResolvedValueOnce(batch(5)).mockRejectedValueOnce(new Error("Connexion coupée"));
  const report = vi.fn();
  await expect(analyzeMailQueue(true, () => false, report)).rejects.toThrow("Connexion coupée");
  expect(report).toHaveBeenLastCalledWith(expect.objectContaining({processed: 5, total: 12, status: "failed"}));
});

it("traite aussi les files de plus de 300 mails", async () => {
  stats(305);
  const run = vi.spyOn(api, "brainTriageRun").mockResolvedValue(batch(5));
  expect(await analyzeMailQueue(true, () => false, () => {})).toMatchObject({processed: 305, total: 305, status: "completed"});
  expect(run).toHaveBeenCalledTimes(61);
});
