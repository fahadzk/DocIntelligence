import { useCallback, useEffect, useState } from "react";
import { useAppearance } from "./appearance";
import { Button } from "./components/Button";
import { EmptyState } from "./components/EmptyState";
import { ErrorState } from "./components/ErrorState";
import { Icon } from "./components/Icon";
import { IconButton } from "./components/IconButton";
import { LoadingState } from "./components/LoadingState";
import { Sidebar } from "./components/Sidebar";
import { DocumentsWorkspace } from "./features/documents/DocumentsWorkspace";
import { PipelineLab } from "./features/pipeline/PipelineLab";
import { EditProjectDialog } from "./features/projects/EditProjectDialog";
import { NewProjectDialog } from "./features/projects/NewProjectDialog";
import { ProjectList } from "./features/projects/ProjectList";
import { SearchWorkspace } from "./features/search/SearchWorkspace";
import { SettingsPage } from "./features/settings/SettingsPage";
import { documentsApi, pipelineApi, projectsApi } from "./services/api";
import type { DocumentItem } from "./types/documents";
import type { Plugin } from "./types/pipeline";
import type { Project } from "./types/projects";

type View = "overview" | "documents" | "search" | "ask" | "lab" | "settings";
const navigation = [
  { id: "overview", label: "Overview", icon: "overview" },
  { id: "documents", label: "Documents", icon: "document" },
  { id: "search", label: "Search", icon: "search" },
  { id: "ask", label: "Ask", icon: "ask" },
] as const;
const SIDEBAR_KEY = "document-intelligence.sidebar-pinned";

function storedSidebarPinned(): boolean {
  try { return window.localStorage.getItem(SIDEBAR_KEY) !== "false"; }
  catch { return true; }
}

export function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState<Project>();
  const [editing, setEditing] = useState<Project>();
  const [view, setView] = useState<View>("documents");
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  const [registry, setRegistry] = useState<Plugin[]>([]);
  const [registryError, setRegistryError] = useState<string>();
  const [sidebarPinned, setSidebarPinned] = useState(storedSidebarPinned);
  const appearance = useAppearance();

  function toggleSidebar() {
    setSidebarPinned((current) => {
      const next = !current;
      try { window.localStorage.setItem(SIDEBAR_KEY, String(next)); } catch { /* Keep the current session state. */ }
      return next;
    });
  }

  const loadProjects = useCallback(async () => {
    setLoading(true); setError(undefined);
    try {
      const items = await projectsApi.list();
      setProjects(items);
      setSelected((current) => items.find((item) => item.id === current?.id) ?? items[0]);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to connect to the local service."); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void loadProjects(); }, [loadProjects]);
  useEffect(() => {
    void pipelineApi.registry().then((result) => setRegistry(result.plugins))
      .catch((cause) => setRegistryError(cause instanceof Error ? cause.message : "Unable to load Pipeline Lab plugins."));
  }, []);

  async function createProject(name: string) {
    const project = await projectsApi.create(name);
    setProjects((items) => [project, ...items]); setSelected(project); setView("documents");
  }
  async function renameProject(name: string) {
    if (!editing) return;
    const updated = await projectsApi.update(editing.id, name);
    setProjects((items) => items.map((item) => item.id === updated.id ? updated : item)); setSelected(updated);
  }
  async function deleteProject() {
    if (!editing) return;
    await projectsApi.remove(editing.id);
    const remaining = projects.filter((item) => item.id !== editing.id);
    setProjects(remaining); setSelected(remaining[0]); setView("documents");
  }
  function selectProject(project: Project) { setSelected(project); setView("documents"); }

  return <div className={`app-shell${sidebarPinned ? "" : " sidebar-unpinned"}`}><Sidebar>
    <div className="brand" title="Document Intelligence"><span className="brand-mark"><Icon name="book" size={18} /></span><span className="brand-name">Document Intelligence</span><IconButton className="sidebar-peek-pin" aria-label="Pin sidebar open" title="Pin sidebar open" onClick={toggleSidebar}><Icon name="pin" size={17} /></IconButton></div>
    <div className="sidebar-projects"><div className="sidebar-section-heading"><span className="sidebar-section-title">Projects</span><NewProjectDialog onCreate={createProject} /></div>
      <ProjectList projects={projects} selectedId={selected?.id} collapsed={!sidebarPinned} onSelect={selectProject} onSwitch={toggleSidebar} /></div>
    {selected && <><nav className="side-nav" aria-label="Workspace navigation"><p className="sidebar-label">Workspace</p>
      {navigation.map((item) => <button key={item.id} className="side-nav-item" aria-label={item.label} title={item.label} aria-current={view === item.id ? "page" : undefined} onClick={() => setView(item.id)}><Icon name={item.icon} /><span>{item.label}</span></button>)}
      <p className="sidebar-label sidebar-label-spaced">Advanced</p>
      <button className="side-nav-item" aria-label="Pipeline Lab" title="Pipeline Lab" aria-current={view === "lab" ? "page" : undefined} onClick={() => setView("lab")}><Icon name="lab" /><span>Pipeline Lab</span></button>
    </nav></>}
    <div className="sidebar-footer"><button className="side-nav-item" aria-label="Settings" title="Settings" aria-current={view === "settings" ? "page" : undefined} onClick={() => setView("settings")}><Icon name="settings" /><span>Settings</span></button></div>
  </Sidebar><main id="main-content">
    <div className="main-toolbar"><IconButton className="sidebar-pin" aria-label={sidebarPinned ? "Collapse sidebar" : "Keep sidebar expanded"} aria-pressed={sidebarPinned} title={sidebarPinned ? "Collapse sidebar (hover to expand)" : "Keep sidebar expanded"} onClick={toggleSidebar}><Icon name={sidebarPinned ? "panelContract" : "panelExpand"} size={18} /></IconButton></div>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} retry={() => void loadProjects()} /> : <>
      <div hidden={view !== "settings"}><SettingsPage theme={appearance.preference} onThemeChange={appearance.setPreference} /></div>
      {selected ? <div hidden={view === "settings"}><ProjectWorkspace key={selected.id} project={selected} view={view} onNavigate={setView} onEdit={() => setEditing(selected)} registry={registry} registryError={registryError} /></div> : view !== "settings" && <Home />}
    </>}
  </main>{editing && <EditProjectDialog project={editing} onSave={renameProject} onDelete={deleteProject} onClose={() => setEditing(undefined)} />}</div>;
}

function Home() {
  return <EmptyState eyebrow="Workspace" title="Start with a project" icon="project"><p>Create a project to organize, search, and ask questions about your documents.</p></EmptyState>;
}

function ProjectWorkspace({ project, view, onNavigate, onEdit, registry, registryError }: {
  project: Project; view: View; onNavigate: (view: View) => void; onEdit: () => void; registry: Plugin[]; registryError?: string;
}) {
  const [labVisited, setLabVisited] = useState(false);
  useEffect(() => { if (view === "lab") setLabVisited(true); }, [view]);
  return <section className="project-workspace">
    <header className="project-context"><div><p className="eyebrow">Current project</p><h1>{project.name}</h1></div><IconButton aria-label="Edit project" title="Edit project" onClick={onEdit}><Icon name="edit" /></IconButton></header>
    <div hidden={view !== "overview"}><ProjectOverview project={project} onNavigate={onNavigate} /></div>
    <div hidden={view !== "documents"}><DocumentsWorkspace project={project} /></div>
    <div hidden={view !== "search"}><SearchWorkspace project={project} mode="search" active={view === "search"} /></div>
    <div hidden={view !== "ask"}><SearchWorkspace project={project} mode="ask" active={view === "ask"} /></div>
    <div hidden={view !== "lab"}>{labVisited && <PipelineLab project={project} registry={registry} registryError={registryError} active={view === "lab"} />}</div>
  </section>;
}

function ProjectOverview({ project, onNavigate }: { project: Project; onNavigate: (view: View) => void }) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [error, setError] = useState<string>();
  useEffect(() => {
    let mounted = true;
    void documentsApi.list(project.id).then((items) => { if (mounted) setDocuments(items); })
      .catch((cause) => { if (mounted) setError(cause instanceof Error ? cause.message : "Could not load project documents."); });
    return () => { mounted = false; };
  }, [project.id]);
  return <section className="overview-page"><header className="section-heading"><div><p className="eyebrow">Workspace</p><h2>Overview</h2><p>Your source collection at a glance.</p></div></header>
    {error && <ErrorState message={error} />}
    <div className="overview-list"><button onClick={() => onNavigate("documents")}><Icon name="document" /><span><strong>Documents</strong><small>{documents.length} in this project</small></span><Icon name="chevronRight" size={16} /></button>
      <button onClick={() => onNavigate("search")}><Icon name="search" /><span><strong>Search</strong><small>Find passages in your sources</small></span><Icon name="chevronRight" size={16} /></button>
      <button onClick={() => onNavigate("ask")}><Icon name="ask" /><span><strong>Ask</strong><small>Answer with cited evidence</small></span><Icon name="chevronRight" size={16} /></button></div>
    {documents.length === 0 && <p className="overview-note">No documents imported yet. <Button variant="quiet" onClick={() => onNavigate("documents")}>Go to Documents</Button></p>}
  </section>;
}
