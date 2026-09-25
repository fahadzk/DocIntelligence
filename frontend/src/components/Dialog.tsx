import { useEffect, useId, useRef, type FormEvent, type ReactNode } from "react";

export function Dialog({ title, children, onSubmit, onClose }: { title: string; children: ReactNode; onSubmit: (event: FormEvent) => void; onClose?: () => void }) {
  const titleId = useId();
  const dialogRef = useRef<HTMLFormElement>(null);
  useEffect(() => {
    const previouslyFocused = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    if (!dialog?.contains(document.activeElement)) dialog?.querySelector<HTMLElement>("input:not([disabled]), button:not([disabled])")?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") { event.preventDefault(); onClose?.(); }
      if (event.key !== "Tab" || !dialog) return;
      const controls = [...dialog.querySelectorAll<HTMLElement>("input:not([disabled]), button:not([disabled]), select:not([disabled]), textarea:not([disabled]), a[href]")];
      if (!controls.length) return;
      const first = controls[0]; const last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => { window.removeEventListener("keydown", onKeyDown); previouslyFocused?.focus(); };
  }, [onClose]);
  return <div className="dialog-backdrop"><form ref={dialogRef} className="dialog" role="dialog" aria-modal="true" aria-labelledby={titleId} onSubmit={onSubmit}><h2 id={titleId}>{title}</h2>{children}</form></div>;
}
