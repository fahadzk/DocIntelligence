import { FormEvent, useState } from "react";
import { Button } from "../../components/Button";
import { Dialog } from "../../components/Dialog";
import { Input } from "../../components/Input";
interface Props { onCreate: (name: string) => Promise<void> }
export function NewProjectDialog({ onCreate }: Props) {
  const [open, setOpen] = useState(false); const [name, setName] = useState(""); const [saving, setSaving] = useState(false); const [error, setError] = useState<string>();
  async function submit(event: FormEvent) { event.preventDefault(); if (!name.trim()) return; setSaving(true); setError(undefined); try { await onCreate(name.trim()); setName(""); setOpen(false); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not create the project."); } finally { setSaving(false); } }
  return <>{open && <Dialog title="New project" onSubmit={submit} onClose={() => setOpen(false)}><label>Project name<Input value={name} maxLength={120} onChange={(e) => setName(e.target.value)} placeholder="e.g. Case Files" /></label>{error && <p className="form-error" role="alert">{error}</p>}<div className="dialog-actions"><Button type="button" onClick={() => setOpen(false)}>Cancel</Button><Button variant="primary" disabled={saving || !name.trim()}>{saving ? "Creating…" : "Create project"}</Button></div></Dialog>}<Button variant="ghost" icon="add" className="new-project" aria-label="New project" title="New project" onClick={() => setOpen(true)}>New project</Button></>;
}
