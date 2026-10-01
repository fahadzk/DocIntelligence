import { useEffect, useMemo, useState } from "react";
import { Button } from "../../components/Button";
import { pipelineApi } from "../../services/api";
import type { PluginDriver, PluginInstance } from "../../types/pipeline";

const blank = (): PluginInstance => ({ id: "", name: "", category: "", driver: "", location: "local", enabled: true, settings: {} });

export function PluginManager() {
  const [drivers, setDrivers] = useState<PluginDriver[]>([]);
  const [plugins, setPlugins] = useState<PluginInstance[]>([]);
  const [draft, setDraft] = useState<PluginInstance>(blank());
  const [editing, setEditing] = useState<string>();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string>();
  const [error, setError] = useState<string>();

  const load = () => Promise.all([pipelineApi.pluginDrivers(), pipelineApi.pluginInstances()])
    .then(([available, configured]) => {
      setDrivers(available.drivers); setPlugins(configured.plugins);
      setDraft((current) => current.category ? current : initialDraft(available.drivers));
    });
  useEffect(() => { void load().catch((cause) => setError(String(cause))); }, []);
  const categories = useMemo(() => Array.from(new Map(drivers.map((item) => [item.category, item.category_name])).entries()), [drivers]);
  const matching = drivers.filter((item) => item.category === draft.category);
  const selected = matching.find((item) => item.id === draft.driver);

  function initialDraft(items: PluginDriver[], category = items[0]?.category ?? ""): PluginInstance {
    const choice = items.find((item) => item.category === category);
    return { ...blank(), category, driver: choice?.id ?? "", location: choice?.locations[0] ?? "local",
      settings: Object.fromEntries((choice?.schema ?? []).filter((field) => field.default !== undefined).map((field) => [field.key, field.default as string | number | boolean])) };
  }
  function selectCategory(category: string) { setEditing(undefined); setDraft(initialDraft(drivers, category)); setMessage(undefined); setError(undefined); }
  function selectDriver(id: string) {
    const choice = drivers.find((item) => item.category === draft.category && item.id === id);
    if (!choice) return;
    setDraft({ ...draft, driver: id, location: choice.locations[0], settings: Object.fromEntries(choice.schema.filter((field) => field.default !== undefined).map((field) => [field.key, field.default as string | number | boolean])) });
  }
  function setName(name: string) {
    const generated = name.toLowerCase().trim().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 64);
    setDraft({ ...draft, name, id: editing ? draft.id : generated });
  }
  async function test() {
    setBusy(true); setError(undefined); setMessage(undefined);
    try { const result = await pipelineApi.testPlugin(draft); setMessage(`${result.message} · ${result.resource_count} resource${result.resource_count === 1 ? "" : "s"} found`); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Connection test failed."); }
    finally { setBusy(false); }
  }
  async function save() {
    setBusy(true); setError(undefined); setMessage(undefined);
    try {
      if (editing) await pipelineApi.updatePlugin(editing, draft); else await pipelineApi.createPlugin(draft);
      await load(); setPlugins((current) => current.map((item) => item.id === draft.id ? { ...item, active: false, restart_required: true } : item)); setEditing(undefined); setDraft(initialDraft(drivers));
      setMessage("Plugin saved. Restart the backend to load this configuration into Pipeline Lab.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Plugin could not be saved."); }
    finally { setBusy(false); }
  }
  async function remove(id: string) {
    setBusy(true); setError(undefined);
    try { await pipelineApi.deletePlugin(id); await load(); setMessage("Plugin removed. Restart the backend to finish applying this change."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Plugin could not be removed."); }
    finally { setBusy(false); }
  }

  return <div className="lab-section plugin-manager"><h3>Plugins</h3><p>Add reusable LLM, embedding model, and vector-store connections. Configurations are stored locally and loaded when the backend starts.</p>
    {message && <div className="lab-notice">{message}</div>}{error && <div className="error-state">{error}</div>}
    <div className="plugin-list">{plugins.map((item) => <article className="plugin-card" key={item.id}><div><strong>{item.name}</strong><span>{item.category === "llm_providers" ? "LLM" : item.category === "embeddings" ? "EM" : "Vector Store"} · {item.driver} · {item.location}</span><small>{item.active ? "Active" : "Restart required"}{item.enabled ? "" : " · Disabled"}</small></div><div><Button variant="quiet" onClick={() => { setEditing(item.id); setDraft(item); setMessage(undefined); }}>Edit</Button><Button variant="quiet" onClick={() => void remove(item.id)} disabled={busy}>Delete</Button></div></article>)}</div>
    <div className="plugin-editor"><h4>{editing ? "Edit plugin" : "Add plugin"}</h4><div className="lab-control-grid"><div>
      <label>Plugin type<select className="input" value={draft.category} onChange={(event) => selectCategory(event.target.value)} disabled={Boolean(editing)}>{categories.map(([id, name]) => <option value={id} key={id}>{name}</option>)}</select></label>
      <label>Provider / driver<select className="input" value={draft.driver} onChange={(event) => selectDriver(event.target.value)} disabled={Boolean(editing)}>{matching.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
      <label>Name<input className="input" value={draft.name} onChange={(event) => setName(event.target.value)} placeholder={draft.category === "embeddings" ? "Research embeddings" : "Office Ollama"} /></label>
      <label>Plugin ID<input className="input" value={draft.id} onChange={(event) => setDraft({ ...draft, id: event.target.value })} disabled={Boolean(editing)} /></label>
    </div><div>
      {selected && <><p className="field-help">{selected.description}</p><label>Location<select className="input" value={draft.location} onChange={(event) => setDraft({ ...draft, location: event.target.value })}>{selected.locations.map((item) => <option key={item} value={item}>{item[0].toUpperCase() + item.slice(1)}</option>)}</select></label>
      {selected.schema.map((field) => <label key={field.key}>{field.label}<input className="input" type={field.type === "number" ? "number" : field.type === "password" ? "password" : "text"} min={field.min} max={field.max} required={field.required} placeholder={field.placeholder} value={String(draft.settings[field.key] ?? "")} onChange={(event) => setDraft({ ...draft, settings: { ...draft.settings, [field.key]: field.type === "number" ? Number(event.target.value) : event.target.value } })} /></label>)}</>}
      <label className="lab-toggle"><input type="checkbox" checked={draft.enabled} onChange={(event) => setDraft({ ...draft, enabled: event.target.checked })} />Enabled</label>
    </div></div><div className="lab-provider-actions"><Button onClick={() => void test()} disabled={busy || !draft.id || !draft.name}>Test Connection</Button><Button variant="primary" onClick={() => void save()} disabled={busy || !draft.id || !draft.name}>Save Plugin</Button>{editing && <Button variant="quiet" onClick={() => { setEditing(undefined); setDraft(initialDraft(drivers)); }}>Cancel</Button>}</div></div>
  </div>;
}
