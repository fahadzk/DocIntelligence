import type { Project } from "../types/projects";
import type { DocumentItem, ImportOutcome, Segment } from "../types/documents";
import type { Answer, IndexState, ModelState, Models, Passage } from "../types/search";
const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { headers: { "Content-Type": "application/json", ...options?.headers }, ...options });
  if (!response.ok) { const body = await response.json().catch(() => null); throw new Error(body?.detail?.message ?? body?.message ?? "Request failed."); }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}
export const projectsApi = {
  list: () => request<Project[]>("/api/projects"),
  create: (name: string) => request<Project>("/api/projects", { method: "POST", body: JSON.stringify({ name }) }),
  update: (id: string, name: string) => request<Project>(`/api/projects/${id}`, { method: "PATCH", body: JSON.stringify({ name }) }),
  remove: (id: string) => request<void>(`/api/projects/${id}`, { method: "DELETE" })
};

export const documentsApi = {
  list: (projectId: string) => request<DocumentItem[]>(`/api/projects/${projectId}/documents`),
  get: (projectId: string, id: string) => request<DocumentItem>(`/api/projects/${projectId}/documents/${id}`),
  content: (projectId: string, id: string) => request<{ segments: Segment[] }>(`/api/projects/${projectId}/documents/${id}/content`),
  retry: (projectId: string, id: string) => request<DocumentItem>(`/api/projects/${projectId}/documents/${id}/retry`, { method: "POST" }),
  remove: (projectId: string, id: string) => request<void>(`/api/projects/${projectId}/documents/${id}`, { method: "DELETE" }),
  import: async (projectId: string, files: FileList): Promise<ImportOutcome[]> => {
    const form = new FormData();
    Array.from(files).forEach((file) => form.append("files", file));
    const response = await fetch(`${API_URL}/api/projects/${projectId}/documents`, { method: "POST", body: form });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(body?.message ?? "Import failed.");
    }
    return response.json() as Promise<ImportOutcome[]>;
  },
  originalUrl: (projectId: string, id: string, page?: number) =>
    `${API_URL}/api/projects/${projectId}/documents/${id}/original${page ? `#page=${page}` : ""}`
};

export const searchApi = {
  status: (projectId: string) => request<IndexState[]>(`/api/projects/${projectId}/index/status`),
  rebuild: (projectId: string) => request<{ status: string }>(`/api/projects/${projectId}/index/rebuild`, { method: "POST" }),
  search: (projectId: string, query: string) => request<{ results: Passage[] }>(`/api/projects/${projectId}/search`, { method: "POST", body: JSON.stringify({ query }) }),
  ask: (projectId: string, question: string) => request<Answer>(`/api/projects/${projectId}/ask`, { method: "POST", body: JSON.stringify({ question }) }),
  models: () => request<Models>("/api/models"),
  setup: (kind: "embeddings" | "answers") => request<ModelState>(`/api/models/${kind}/setup`, { method: "POST" }),
  evidence: (projectId: string, id: string) => request<Passage>(`/api/projects/${projectId}/evidence/${id}`)
};
