import type { Passage, Answer, IndexState } from "./search";

export type PipelineTab = "document" | "search" | "ask";
export interface PluginField {
  key: string;
  label: string;
  type: "slider" | "number" | "boolean" | "select" | "text" | "model_select";
  options?: string[];
  min?: number;
  max?: number;
  step?: number;
  readonly?: boolean;
}
export interface Plugin {
  id: string;
  name: string;
  description: string;
  category: string;
  schema: PluginField[];
  capabilities: Record<string, boolean | string | number>;
}
export interface PipelineSettings {
  document: {
    chunking: Record<string, string | number | boolean> & { plugin: string };
    embedding: { plugin: string; model: string };
    vector_store: { plugin: string; distance: string };
  };
  search: {
    retrieval: string; keyword_candidates: number; semantic_candidates: number;
    result_limit: number; fusion: string; rrf_constant: number;
    keyword_weight: number; semantic_weight: number;
    similarity_threshold: number | null; max_chunks_per_document: number | null;
    reranker: string;
  };
  ask: {
    provider: string; model: string; context_tokens: number; temperature: number;
    max_output_tokens: number; seed: number; history: boolean; stream: boolean;
    grounding: string; evidence_candidates: number; evidence_count: number;
    evidence_characters: number; require_citations: boolean; answer_style: string;
  };
}
export interface PipelineState {
  defaults: PipelineSettings;
  overrides: Record<string, unknown>;
  effective: PipelineSettings;
}
export interface LabPassage extends Passage {
  final_rank: number;
  keyword_rank?: number | null;
  semantic_rank?: number | null;
  keyword_score?: number | null;
  semantic_score?: number | null;
  fusion_score?: number;
  reranker_score?: number;
  segment_index: number;
  start_offset: number;
  end_offset: number;
}
export interface LabAnswer extends Answer {
  context?: { document: string; label: string; chunk_id: string; text: string; characters: number; page_number: number | null }[];
  background?: string | null;
}
export interface ChunkPreview { count: number; average_characters: number; samples: LabPassage[] }
export type LabIndexState = IndexState;
