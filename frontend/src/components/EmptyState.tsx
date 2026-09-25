import type { ReactNode } from "react";
import { Icon, type IconName } from "./Icon";
export function EmptyState({ eyebrow, title, children, icon = "document" }: { eyebrow: string; title: string; children: ReactNode; icon?: IconName }) {
  return <section className="empty-state"><span className="empty-icon"><Icon name={icon} size={24} /></span><p className="eyebrow">{eyebrow}</p><h2>{title}</h2><div className="empty-copy">{children}</div></section>;
}
