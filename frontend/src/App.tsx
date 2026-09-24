import { useCallback, useEffect, useState } from "react";
import { Button } from "./components/Button";
import { EmptyState } from "./components/EmptyState";
import { ErrorState } from "./components/ErrorState";
import { IconButton } from "./components/IconButton";
import { LoadingState } from "./components/LoadingState";
import { PageHeader } from "./components/PageHeader";
import { Sidebar } from "./components/Sidebar";
import { EditProjectDialog } from "./features/projects/EditProjectDialog";
import { DocumentsWorkspace } from "./features/documents/DocumentsWorkspace";
import { SearchWorkspace } from "./features/search/SearchWorkspace";
import { NewProjectDialog } from "./features/projects/NewProjectDialog";
import { ProjectList } from "./features/projects/ProjectList";
import { projectsApi } from "./services/api";
import type { Project } from "./types/projects";

export function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project>();
  const [editing, setEditing] = useState<Project>();
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  const loadProjects = useCallback(async () => {
    setLoading(true); setError(undefined);
    try { const items = await projectsApi.list(); setProjects(items); setSelected((current) => items.find((item) => item.id === current?.id) ?? items[0]); }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to connect to the local service."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void loadProjects(); }, [loadProjects]);
  async function createProject(name: string) { const project = await projectsApi.create(name); setProjects((items) => [project, ...items]); setSelected(project); }
  async function renameProject(name: string) { if (!editing) return; const updated = await projectsApi.update(editing.id, name); setProjects((items) => items.map((item) => item.id === updated.id ? updated : item)); setSelected(updated); }
  async function deleteProject() { if (!editing) return; await projectsApi.remove(editing.id); setProjects((items) => { const remaining = items.filter((item) => item.id !== editing.id); setSelected(remaining[0]); return remaining; }); }
  return <div className="app-shell"><Sidebar><div className="brand"><span className="brand-mark">DI</span><span>Document Intelligence</span></div><div className="sidebar-label">Your Projects</div><NewProjectDialog onCreate={createProject} /><ProjectList projects={projects} selectedId={selected?.id} onSelect={setSelected} /><div className="sidebar-footer"><Button variant="quiet">Settings</Button></div></Sidebar><main>{loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => void loadProjects()} /> : selected ? <ProjectWorkspace project={selected} onEdit={() => setEditing(selected)} /> : <Home />}</main>{editing && <EditProjectDialog project={editing} onSave={renameProject} onDelete={deleteProject} onClose={() => setEditing(undefined)} />}</div>;
}
function Home() { return <EmptyState eyebrow="Workspace" title="Your research begins with a project."><p>Create a project to organize a collection of documents. Import, search, and answers will arrive in later phases.</p></EmptyState>; }
function ProjectWorkspace({ project, onEdit }: { project: Project; onEdit: () => void }) {
  const [section, setSection] = useState<"documents" | "search" | "ask">("documents");
  useEffect(() => setSection("documents"), [project.id]);
  return <section><PageHeader eyebrow="Project workspace" title={project.name} actions={<IconButton aria-label="Edit project" title="Edit project" onClick={onEdit}>•••</IconButton>} />
    <nav className="workspace-tabs" aria-label="Project sections">
      {(["documents", "search", "ask"] as const).map((tab) => <button key={tab} aria-current={section === tab ? "page" : undefined} onClick={() => setSection(tab)}>{tab[0].toUpperCase() + tab.slice(1)}</button>)}
    </nav>
    <div hidden={section !== "documents"}><DocumentsWorkspace key={project.id} project={project} /></div><div hidden={section !== "search"}><SearchWorkspace key={project.id + "search"} project={project} mode="search" active={section === "search"} /></div><div hidden={section !== "ask"}><SearchWorkspace key={project.id + "ask"} project={project} mode="ask" active={section === "ask"} /></div>
  </section>;
}
