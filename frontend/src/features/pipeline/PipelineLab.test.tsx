import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { PipelineLab } from "./PipelineLab";
import { documentsApi, pipelineApi, searchApi } from "../../services/api";
import type { PipelineState, Plugin } from "../../types/pipeline";

afterEach(() => vi.restoreAllMocks());

const project = { id: "11111111-1111-4111-8111-111111111111", name: "Research", description: null, created_at: "2026-01-01", updated_at: "2026-01-01" };
const registry: Plugin[] = [
  { id: "sliding_window", category: "chunking", name: "Sliding Window", description: "", capabilities: {}, schema: [{ key: "chunk_size", label: "Chunk size", type: "number" }] },
  { id: "semantic", category: "chunking", name: "Semantic", description: "", capabilities: {}, schema: [{ key: "sensitivity", label: "Sensitivity", type: "slider" }] },
  { id: "fastembed_bge_small", category: "embeddings", name: "BGE Small", description: "", capabilities: {}, schema: [] },
  { id: "chroma", category: "vector_stores", name: "Chroma", description: "", capabilities: {}, schema: [] },
  { id: "hybrid", category: "retrieval", name: "Hybrid", description: "", capabilities: {}, schema: [] },
  { id: "rrf", category: "fusion", name: "RRF", description: "", capabilities: {}, schema: [] },
  { id: "off", category: "rerankers", name: "Off", description: "", capabilities: {}, schema: [] },
  { id: "llamacpp", category: "llm_providers", name: "Local Qwen", description: "", capabilities: { local: true }, schema: [] }
];
const effective = {
  document: { chunking: { plugin: "sliding_window", unit: "characters", chunk_size: 900, overlap: 120, preserve_segments: true, preserve_headings: true, sensitivity: 0.35, min_chunk_size: 200, max_chunk_size: 900, chunk_by: "topic" }, embedding: { plugin: "fastembed_bge_small", model: "BAAI/bge-small-en-v1.5" }, vector_store: { plugin: "chroma", distance: "l2" } },
  search: { retrieval: "hybrid", keyword_candidates: 30, semantic_candidates: 30, result_limit: 12, fusion: "rrf", rrf_constant: 40, keyword_weight: 0.5, semantic_weight: 0.5, similarity_threshold: null, max_chunks_per_document: null, reranker: "off" },
  ask: { provider: "llamacpp", model: "qwen2.5-1.5b-instruct-q4_k_m.gguf", context_tokens: 4096, temperature: 0, max_output_tokens: 300, seed: 42, history: false, stream: false, grounding: "sources_only", evidence_candidates: 12, evidence_count: 3, evidence_characters: 4800, require_citations: true, answer_style: "concise" }
} as const;

function setup() {
  const state = { defaults: effective, overrides: {}, effective } as unknown as PipelineState;
  vi.spyOn(pipelineApi, "state").mockResolvedValue(state);
  vi.spyOn(pipelineApi, "indexStatus").mockResolvedValue([]);
  vi.spyOn(pipelineApi, "ensureIndex").mockResolvedValue({ status: "indexing" });
  vi.spyOn(pipelineApi, "providers").mockResolvedValue([]);
  vi.spyOn(documentsApi, "list").mockResolvedValue([]);
  vi.spyOn(searchApi, "models").mockResolvedValue({ embeddings: { status: "ready", error: null, name: "BGE", size_mb: 70, source: "" }, answers: { status: "ready", error: null, name: "Qwen", size_mb: 1070, source: "", models: [] } });
  return state;
}

test("saves document settings without starting reindexing", async () => {
  const state = setup();
  const save = vi.spyOn(pipelineApi, "save").mockResolvedValue(state);
  render(<PipelineLab project={project} registry={registry} />);
  expect(await screen.findByText("Chunk size")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText(/^Chunking strategy/), { target: { value: "semantic" } });
  expect(await screen.findByText("Sensitivity")).toBeInTheDocument();
  expect(screen.queryByText("Chunk size")).not.toBeInTheDocument();
  expect(screen.getByText("Changes are drafts until you select Save. Search and Ask changes apply after saving.")).toBeInTheDocument();
  expect(screen.getByText("Saved Document changes take effect when you select Re-chunk & re-index for a document in Documents.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(save).toHaveBeenCalledWith(project.id, { document: { chunking: { plugin: "semantic" } } }));
  expect(pipelineApi.ensureIndex).not.toHaveBeenCalled();
  expect(await screen.findByText("Settings saved. Document changes will be used the next time you re-chunk and re-index a document.")).toBeInTheDocument();
});

test("keeps edits pending until Save is selected", async () => {
  const state = setup();
  const save = vi.spyOn(pipelineApi, "save").mockResolvedValue(state);
  render(<PipelineLab project={project} registry={registry} />);
  const size = await screen.findByLabelText("Chunk size");
  fireEvent.change(size, { target: { value: "901" } });
  await act(async () => { await new Promise((resolve) => window.setTimeout(resolve, 700)); });
  expect(save).not.toHaveBeenCalled();
  expect(size).toHaveValue(901);
});

test("leaving with a draft does not save it", async () => {
  const state = setup();
  const save = vi.spyOn(pipelineApi, "save").mockResolvedValue(state);
  const view = render(<PipelineLab project={project} registry={registry} />);
  fireEvent.change(await screen.findByLabelText("Chunk size"), { target: { value: "904" } });
  view.unmount();
  expect(save).not.toHaveBeenCalled();
});
