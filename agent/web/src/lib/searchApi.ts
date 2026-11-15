import { request } from './http';

export type SearchFilters = {q: string; project_id: string; source_type: string; after: string; before: string; offset: number};
export type EvidenceHit = {
  id: string; kind: 'source' | 'knowledge'; source_id: string | null; source_type: string;
  project_id: string; project_code: string; title: string; author: string | null; date: string;
  excerpt: string; methods: string[]; level: string; semantic_score: number | null;
};
export type EvidencePage = {items: EvidenceHit[]; total: number; offset: number; limit: number; has_next: boolean;
  semantic_status: string; warnings: string[]; sources: number; indexed_sources: number};
export function searchEvidence(filters: SearchFilters, signal?: AbortSignal) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {if (value !== '') params.set(key, String(value));});
  return request<EvidencePage>(`/v1/search?${params}`, {signal}, 45_000);
}
