import type { Project } from "../../types/projects";

interface Props { projects: Project[]; selectedId?: string; onSelect: (project: Project) => void }
export function ProjectList({ projects, selectedId, onSelect }: Props) {
  return <nav aria-label="Projects" className="project-list">
    {projects.map((project) => <button className={selectedId === project.id ? "project selected" : "project"} key={project.id} onClick={() => onSelect(project)}>{project.name}</button>)}
  </nav>;
}
