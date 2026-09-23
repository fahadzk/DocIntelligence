import { FormEvent, useState } from "react";
import { Button } from "../../components/Button";
import { Dialog } from "../../components/Dialog";
import { Input } from "../../components/Input";
interface Props { onCreate: (name: string) => Promise<void> }
export function NewProjectDialog({ onCreate }: Props) {
  const [open, setOpen] = useState(false); const [name, setName] = useState(""); const [saving, setSaving] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); if (!name.trim()) return; setSaving(true); try { await onCreate(name.trim()); setName(""); setOpen(false); } finally { setSaving(false); } }
  return <>{open && <Dialog title="New project" onSubmit={submit}><label>Project name<Input autoFocus value={name} maxLength={120} onChange={(e) => setName(e.target.value)} placeholder="e.g. Case Files" /></label><div className="dialog-actions"><Button type="button" onClick={() => setOpen(false)}>Cancel</Button><Button variant="primary" disabled={saving}>{saving ? "Creating…" : "Create project"}</Button></div></Dialog>}<Button variant="primary" className="new-project" onClick={() => setOpen(true)}>+ New project</Button></>;
}
