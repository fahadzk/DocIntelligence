import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, expect, test, vi } from "vitest";
import { App } from "./App";

const project = { id: "11111111-1111-4111-8111-111111111111", name: "Research", description: null, created_at: "2026-01-01", updated_at: "2026-01-01" };
const reply = (value: unknown) => ({ ok: true, status: 200, json: async () => value });

beforeEach(() => vi.restoreAllMocks());

test("creates and renames a project", async () => {
  let projects: typeof project[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url.endsWith("/api/projects") && options?.method === "POST") { projects = [project]; return reply(project); }
    if (url.endsWith("/api/projects") && !options?.method) return reply(projects);
    if (url.includes("/documents")) return reply([]);
    if (options?.method === "PATCH") { projects = [{ ...project, name: "Renamed" }]; return reply(projects[0]); }
    throw new Error(`Unexpected request: ${url}`);
  }));
  render(<App />);
  expect(await screen.findByText("Your research begins with a project.")).toBeInTheDocument();
  fireEvent.click(screen.getByText("+ New project"));
  fireEvent.change(screen.getByPlaceholderText("e.g. Case Files"), { target: { value: "Research" } });
  fireEvent.click(screen.getByText("Create project"));
  expect(await screen.findByRole("heading", { name: "Research", level: 1 })).toBeInTheDocument();
  fireEvent.click(screen.getByLabelText("Edit project"));
  fireEvent.change(screen.getByDisplayValue("Research"), { target: { value: "Renamed" } });
  fireEvent.click(screen.getByText("Save changes"));
  expect(await screen.findByRole("heading", { name: "Renamed", level: 1 })).toBeInTheDocument();
});

test("imports and reads a document in the project workspace", async () => {
  const document = { id: "22222222-2222-4222-8222-222222222222", project_id: project.id, display_name: "notes.txt", original_filename: "notes.txt", file_type: "txt", size_bytes: 13, content_hash: "hash", status: "ready", stage: "complete", error_code: null, error_message: null, page_count: null, created_at: "2026-01-01", updated_at: "2026-01-01" };
  let documents: typeof document[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url.endsWith("/api/projects")) return reply([project]);
    if (url.endsWith("/documents") && options?.method === "POST") { documents = [document]; return reply([{ filename: "notes.txt", document, error_code: null, error_message: null }]); }
    if (url.endsWith("/documents")) return reply(documents);
    if (url.endsWith(document.id)) return reply(document);
    if (url.endsWith("/content")) return reply({ segments: [{ index: 0, kind: "paragraph", label: "Paragraph 1", page_number: null, paragraph_number: 1, text: "Readable notes" }] });
    throw new Error(`Unexpected request: ${url}`);
  }));
  render(<App />);
  const input = await screen.findByLabelText("Choose documents");
  fireEvent.change(input, { target: { files: [new File(["Readable notes"], "notes.txt", { type: "text/plain" })] } });
  await waitFor(() => expect(screen.getByText("Readable notes")).toBeInTheDocument());
  expect(screen.getAllByText("notes.txt")).toHaveLength(2);
});
