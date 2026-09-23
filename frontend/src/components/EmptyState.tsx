import type { ReactNode } from "react";
export function EmptyState({ eyebrow, title, children }: { eyebrow: string; title: string; children: ReactNode }) { return <section className="empty-state"><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><div className="empty-copy">{children}</div></section>; }
