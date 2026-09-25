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
  expect(await screen.findByText("Start with a project")).toBeInTheDocument();
  fireEvent.click(screen.getByText("New project"));
  expect(screen.getByRole("dialog", { name: "New project" })).toBeInTheDocument();
  expect(screen.getByPlaceholderText("e.g. Case Files")).toHaveFocus();
  fireEvent.change(screen.getByPlaceholderText("e.g. Case Files"), { target: { value: "Research" } });
  fireEvent.click(screen.getByText("Create project"));
  expect(await screen.findByRole("heading", { name: "Research", level: 1 })).toBeInTheDocument();
  fireEvent.click(screen.getByLabelText("Edit project"));
  fireEvent.change(screen.getByDisplayValue("Research"), { target: { value: "Renamed" } });
  fireEvent.click(screen.getByText("Save changes"));
  expect(await screen.findByRole("heading", { name: "Renamed", level: 1 })).toBeInTheDocument();
  const newProjectButton = screen.getByRole("button", { name: "New project" });
  newProjectButton.focus();
  fireEvent.click(newProjectButton);
  fireEvent.keyDown(window, { key: "Escape" });
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(newProjectButton).toHaveFocus();
});

test("changes and persists appearance preference", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/api/projects")) return reply([]);
    throw new Error(`Unexpected request: ${url}`);
  }));
  window.localStorage.removeItem("document-intelligence.theme");
  render(<App />);
  await screen.findByText("Start with a project");
  fireEvent.click(screen.getByRole("button", { name: "Settings" }));
  fireEvent.click(screen.getByRole("radio", { name: /Dark/ }));
  expect(document.documentElement.dataset.theme).toBe("dark");
  expect(window.localStorage.getItem("document-intelligence.theme")).toBe("dark");
  fireEvent.click(screen.getByRole("radio", { name: /Light/ }));
  expect(document.documentElement.dataset.theme).toBe("light");
});

test("pins and collapses the sidebar without losing navigation", async () => {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.endsWith("/api/projects")) return reply([project]);
    if (url.includes("/documents")) return reply([]);
    throw new Error(`Unexpected request: ${url}`);
  }));
  window.localStorage.removeItem("document-intelligence.sidebar-pinned");
  const view = render(<App />);
  await screen.findByRole("button", { name: "Documents" });
  fireEvent.click(screen.getByRole("button", { name: "Collapse sidebar" }));
  expect(view.container.querySelector(".app-shell")).toHaveClass("sidebar-unpinned");
  expect(screen.getByRole("button", { name: "Switch project, current Research" })).toBeInTheDocument();
  expect(window.localStorage.getItem("document-intelligence.sidebar-pinned")).toBe("false");
  expect(screen.getByRole("button", { name: "Settings" })).toBeInTheDocument();
  view.unmount();
  const reopened = render(<App />);
  expect(reopened.container.querySelector(".app-shell")).toHaveClass("sidebar-unpinned");
  fireEvent.click(await screen.findByRole("button", { name: "Switch project, current Research" }));
  expect(reopened.container.querySelector(".app-shell")).not.toHaveClass("sidebar-unpinned");
  expect(window.localStorage.getItem("document-intelligence.sidebar-pinned")).toBe("true");
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
  await waitFor(() => expect(screen.getByText("Readable notes")).toBeInTheDocument(), { timeout: 5000 });
  expect(screen.getAllByText("notes.txt")).toHaveLength(2);
});

test("searches and opens cited evidence in the project workspace", async () => {
  const passage = { id: "33333333-3333-4333-8333-333333333333", project_id: project.id,
    document_id: "22222222-2222-4222-8222-222222222222", display_name: "facts.txt",
    file_type: "txt", label: "Paragraph 1", page_number: null, paragraph_number: 1,
    text: "Europa orbits Jupiter.", match_type: "keyword" };
  const ready = { status: "ready", error: null, name: "Local", size_mb: 70, source: "https://huggingface.co" };
  vi.stubGlobal("fetch", vi.fn(async (url: string, options?: RequestInit) => {
    if (url.endsWith("/api/projects")) return reply([project]);
    if (url.endsWith("/documents")) return reply([]);
    if (url.endsWith("/api/models")) return reply({ embeddings: ready, answers: ready });
    if (url.endsWith("/index/status")) return reply([]);
    if (url.endsWith("/search") && options?.method === "POST") return reply({ results: [passage] });
    if (url.endsWith("/ask") && options?.method === "POST") return reply({ answer: "Europa orbits Jupiter [1].", supported: true, evidence: [{ number: 1, passage }] });
    throw new Error(`Unexpected request: ${url}`);
  }));
  render(<App />);
  fireEvent.click((await screen.findAllByRole("button", { name: /^Search$/ }))[0]);
  fireEvent.change(screen.getByLabelText("Search terms"), { target: { value: "Europa" } });
  fireEvent.click(screen.getAllByRole("button", { name: /^Search$/ }).at(-1)!);
  expect(await screen.findByText("Europa orbits Jupiter.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /^Ask$/ }));
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: "Which planet?" } });
  await waitFor(() => expect(screen.getAllByRole("button", { name: /^Ask$/ }).at(-1)).toBeEnabled());
  fireEvent.click(screen.getAllByRole("button", { name: /^Ask$/ }).at(-1)!);
  expect(await screen.findByText("Supporting passages")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "View source 1" })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Question"), { target: { value: "Which moon?" } });
  expect(screen.getByLabelText("Question")).toHaveValue("Which moon?");
  fireEvent.click(screen.getAllByRole("button", { name: /^Ask$/ }).at(-1)!);
  expect(await screen.findByText("Supporting passages")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /^Search$/ }));
  expect(await screen.findByPlaceholderText("Search this project")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /^Ask$/ }));
  expect(screen.getByText("Supporting passages")).toBeInTheDocument();
});
