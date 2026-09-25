import { FormEvent, useState } from "react";
import { Button } from "../../components/Button";
import { Dialog } from "../../components/Dialog";
import { Input } from "../../components/Input";
import type { Project } from "../../types/projects";

export function EditProjectDialog({ project, onSave, onDelete, onClose }: { project: Project; onSave: (name: string) => Promise<void>; onDelete: () => Promise<void>; onClose: () => void }) {
  const [name, setName] = useState(project.name); const [saving, setSaving] = useState(false); const [confirming, setConfirming] = useState(false);
  async function submit(event: FormEvent) { event.preventDefault(); if (!name.trim()) return; setSaving(true); try { await onSave(name.trim()); onClose(); } finally { setSaving(false); } }
  async function remove() { setSaving(true); try { await onDelete(); onClose(); } finally { setSaving(false); } }
  return <Dialog title="Project settings" onSubmit={submit} onClose={onClose}><label>Project name<Input value={name} maxLength={120} onChange={(event) => setName(event.target.value)} /></label><div className="dialog-actions dialog-actions-spread">{confirming ? <><span className="confirm-copy">Delete this project?</span><Button type="button" icon="delete" variant="danger" onClick={remove} disabled={saving}>Delete</Button></> : <Button type="button" icon="delete" variant="danger" onClick={() => setConfirming(true)}>Delete project</Button>}<span className="dialog-actions"><Button type="button" onClick={onClose}>Cancel</Button><Button variant="primary" disabled={saving}>{saving ? "Saving…" : "Save changes"}</Button></span></div></Dialog>;
}
