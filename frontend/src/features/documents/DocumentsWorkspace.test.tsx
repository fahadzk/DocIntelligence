import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { documentsApi, pipelineApi, searchApi } from "../../services/api";
import type { PipelineState, Plugin } from "../../types/pipeline";
import { DocumentsWorkspace } from "./DocumentsWorkspace";

const project = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "Research",
  description: null,
  created_at: "2026-01-01",
  updated_at: "2026-01-01",
};
const registry: Plugin[] = [
  {
    id: "chroma",
    name: "Chroma",
    description: "",
    category: "vector_stores",
    schema: [],
    capabilities: { location: "local" },
  },
  {
    id: "research_graph",
    name: "Research Neo4j",
    description: "",
    category: "vector_stores",
    schema: [],
    capabilities: { location: "network", driver: "neo4j" },
  },
];
const settings = {
  document: {
    chunking: { plugin: "sliding_window" },
    embedding: {
      plugin: "fastembed_bge_small",
      model: "BAAI/bge-small-en-v1.5",
    },
    vector_store: { plugin: "chroma", distance: "l2" },
  },
  search: {},
  ask: {},
} as PipelineState["effective"];
const state: PipelineState = {
  defaults: settings,
  overrides: {},
  effective: settings,
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(documentsApi, "list").mockResolvedValue([]);
  vi.spyOn(pipelineApi, "state").mockResolvedValue(state);
});

test("selects a configured network vector store from Documents", async () => {
  const save = vi.spyOn(pipelineApi, "save").mockResolvedValue({
    ...state,
    effective: {
      ...settings,
      document: {
        ...settings.document,
        vector_store: { plugin: "research_graph", distance: "l2" },
      },
    },
  });
  render(<DocumentsWorkspace project={project} registry={registry} />);
  const selector = await screen.findByLabelText("Vector storage");
  expect(
    screen.getByRole("option", { name: "Research Neo4j · network" }),
  ).toBeInTheDocument();
  fireEvent.change(selector, { target: { value: "research_graph" } });
  fireEvent.click(screen.getByRole("button", { name: "Save" }));
  await waitFor(() =>
    expect(save).toHaveBeenCalledWith(project.id, {
      document: { vector_store: { plugin: "research_graph", distance: "l2" } },
    }),
  );
  expect(
    await screen.findByText(/Re-chunk and re-index each affected document/),
  ).toBeInTheDocument();
});

test("keeps re-chunk and re-embed independent and displays background failures", async () => {
  const document = {
    id: "22222222-2222-4222-8222-222222222222",
    project_id: project.id,
    display_name: "notes.txt",
    original_filename: "notes.txt",
    file_type: "txt",
    size_bytes: 20,
    content_hash: "hash",
    status: "ready",
    stage: "complete",
    error_code: null,
    error_message: null,
    page_count: null,
    created_at: "2026-01-01",
    updated_at: "2026-01-01",
  } as const;
  vi.mocked(documentsApi.list).mockResolvedValue([document]);
  vi.spyOn(documentsApi, "chunkPage").mockResolvedValue({
    items: [],
    total: 0,
    offset: 0,
    limit: 50,
    has_more: false,
    start_page: null,
    end_page: null,
    page_count: null,
  });
  const rechunk = vi
    .spyOn(documentsApi, "reindex")
    .mockResolvedValue({ status: "chunking" });
  const reembed = vi
    .spyOn(documentsApi, "reembed")
    .mockResolvedValue({ status: "embedding" });
  vi.spyOn(searchApi, "status").mockResolvedValue([
    {
      document_id: document.id,
      display_name: document.display_name,
      document_status: "ready",
      status: "failed",
      stage: "re-chunking",
      error_message:
        "Re-chunking failed due to: provider unavailable. Check the server log for details.",
    },
  ]);

  render(<DocumentsWorkspace project={project} registry={registry} />);
  fireEvent.click(await screen.findByRole("button", { name: /notes\.txt/i }));
  fireEvent.click(await screen.findByRole("button", { name: "Re-chunk" }));

  await waitFor(() =>
    expect(rechunk).toHaveBeenCalledWith(project.id, document.id),
  );
  expect(reembed).not.toHaveBeenCalled();
  expect(
    await screen.findByText(/Re-chunking failed due to: provider unavailable/),
  ).toBeInTheDocument();
});
