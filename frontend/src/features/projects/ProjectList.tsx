import type { Project } from "../../types/projects";
import { Icon } from "../../components/Icon";

interface Props { projects: Project[]; selectedId?: string; collapsed?: boolean; onSelect: (project: Project) => void; onSwitch?: () => void }
export function ProjectList({ projects, selectedId, collapsed = false, onSelect, onSwitch }: Props) {
  return <nav aria-label="Projects" className="project-list">
    {projects.map((project) => {
      const selected = selectedId === project.id;
      const switcher = selected && collapsed;
      const label = switcher ? `Switch project, current ${project.name}` : project.name;
      return <button className={selected ? "project selected" : "project"} aria-label={label} title={label} aria-current={selected ? "page" : undefined} key={project.id} onClick={() => switcher ? onSwitch?.() : onSelect(project)}><Icon name="project" size={16} /><span>{project.name}</span>{switcher && <Icon name="chevronDown" size={10} className="project-switch-indicator" />}</button>;
    })}
  </nav>;
}
