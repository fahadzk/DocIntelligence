import type { FormEvent, ReactNode } from "react";

export function Dialog({ title, children, onSubmit }: { title: string; children: ReactNode; onSubmit: (event: FormEvent) => void }) {
  return <div className="dialog-backdrop" role="presentation"><form className="dialog" onSubmit={onSubmit} aria-label={title}><h2>{title}</h2>{children}</form></div>;
}
