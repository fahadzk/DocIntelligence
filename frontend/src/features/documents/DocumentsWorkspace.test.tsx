import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { documentsApi, pipelineApi } from "../../services/api";
import type { PipelineState, Plugin } from "../../types/pipeline";
import { DocumentsWorkspace } from "./DocumentsWorkspace";

const project = { id: "11111111-1111-4111-8111-111111111111", name: "Research", description: null, created_at: "2026-01-01", updated_at: "2026-01-01" };
const registry: Plugin[] = [
  { id: "chroma", name: "Chroma", description: "", category: "vector_stores", schema: [], capabilities: { location: "local" } },
  { id: "research_graph", name: "Research Neo4j", description: "", category: "vector_stores", schema: [], capabilities: { location: "network", driver: "neo4j" } },
];
const settings = {
  document: {
    chunking: { plugin: "sliding_window" },
    embedding: { plugin: "fastembed_bge_small", model: "BAAI/bge-small-en-v1.5" },
    vector_store: { plugin: "chroma", distance: "l2" },
  },
  search: {}, ask: {},
} as PipelineState["effective"];
const state: PipelineState = { defaults: settings, overrides: {}, effective: settings };

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(documentsApi, "list").mockResolvedValue([]);
  vi.spyOn(pipelineApi, "state").mockResolvedValue(state);
});

test("selects a configured network vector store from Documents", async () => {
  const save = vi.spyOn(pipelineApi, "save").mockResolvedValue({
    ...state,
    effective: { ...settings, document: { ...settings.document, vector_store: { plugin: "research_graph", distance: "l2" } } },
  });
  render(<DocumentsWorkspace project={project} registry={registry} />);
  const selector = await screen.findByLabelText("Vector storage");
  expect(screen.getByRole("option", { name: "Research Neo4j · network" })).toBeInTheDocument();
  fireEvent.change(selector, { target: { value: "research_graph" } });
  fireEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() => expect(save).toHaveBeenCalledWith(project.id, {
    document: { vector_store: { plugin: "research_graph", distance: "l2" } },
  }));
  expect(await screen.findByText(/Re-chunk and re-index each affected document/)).toBeInTheDocument();
});
