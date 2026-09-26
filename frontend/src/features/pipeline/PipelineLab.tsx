import { useEffect, useRef, useState } from "react";
import { Button } from "../../components/Button";
import { EvidenceBlock } from "../../components/EvidenceBlock";
import { ErrorState } from "../../components/ErrorState";
import { Icon } from "../../components/Icon";
import { LoadingState } from "../../components/LoadingState";
import { documentsApi, pipelineApi, searchApi } from "../../services/api";
import type { DocumentItem } from "../../types/documents";
import type { Project } from "../../types/projects";
import type { Plugin, PluginField, PipelineSettings, PipelineState, PipelineTab, ChunkPreview, LabPassage, LabIndexState } from "../../types/pipeline";
import type { Models } from "../../types/search";

function automaticSaveEnabled() { return false; }

function difference(base: unknown, current: unknown): unknown {
  if (!base || !current || typeof base !== "object" || typeof current !== "object") return Object.is(base, current) ? undefined : current;
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(current)) {
    const changed = difference((base as Record<string, unknown>)[key], value);
    if (changed !== undefined) result[key] = changed;
  }
  return Object.keys(result).length ? result : undefined;
}

function pluginFor(registry: Plugin[], category: string, id: string): Plugin | undefined {
  return registry.find((item) => item.category === category && item.id === id);
}

function SchemaFields({ plugin, values, defaults, onChange, models = [] }: {
  plugin?: Plugin; values: Record<string, unknown>; onChange: (key: string, value: unknown) => void;
  defaults?: Record<string, unknown>; models?: { id: string; name: string }[];
}) {
  if (!plugin) return null;
  return <div className="lab-fields">{plugin.schema.map((field: PluginField) => {
    const value = values[field.key];
    const id = `${plugin.category}-${plugin.id}-${field.key}`;
    const changed = defaults && !Object.is(value, defaults[field.key]);
    if (field.type === "boolean") return <label className="lab-toggle" key={id} htmlFor={id}><input id={id} type="checkbox" checked={Boolean(value)} disabled={field.readonly} onChange={(event) => onChange(field.key, event.target.checked)} />{field.label}{changed && <span className="setting-state">Custom</span>}</label>;
    if (field.type === "select" || field.type === "model_select") {
      const options = field.type === "model_select" ? models : (field.options ?? []).map((item) => ({ id: item, name: item.replaceAll("_", " ") }));
      return <label key={id} htmlFor={id}><span className="field-label">{field.label}{changed && <span className="setting-state">Custom</span>}</span><select id={id} className="input" value={String(value ?? "")} onChange={(event) => onChange(field.key, event.target.value)}><option value="" disabled>Choose an option</option>{options.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>;
    }
    if (field.type === "slider" || (field.type === "number" && ["chunk_size", "overlap"].includes(field.key) && field.min !== undefined && field.max !== undefined)) return <div className="lab-slider-field" key={id}><label htmlFor={id}><span className="field-label">{field.label}{changed && <span className="setting-state">Custom</span>}</span></label><div className="lab-slider-row"><input id={id} type="range" min={field.min} max={field.max} step={field.step ?? (field.type === "slider" ? 0.05 : 1)} value={Number(value ?? field.min ?? 0)} onChange={(event) => onChange(field.key, Number(event.target.value))} /><input className="input" type="number" aria-label={`${field.label} precise value`} min={field.min} max={field.max} step={field.step ?? (field.type === "slider" ? 0.05 : 1)} value={value === null || value === undefined ? "" : String(value)} onChange={(event) => onChange(field.key, event.target.value === "" ? null : Number(event.target.value))} /></div><small>{field.min}–{field.max}</small></div>;
    return <label key={id} htmlFor={id}><span className="field-label">{field.label}{changed && <span className="setting-state">Custom</span>}</span><input id={id} className="input" type={field.type === "text" ? "text" : "number"} min={field.min} max={field.max} step={field.step ?? 1} value={value === null || value === undefined ? "" : String(value)} onChange={(event) => onChange(field.key, event.target.value === "" ? null : field.type === "text" ? event.target.value : Number(event.target.value))} /></label>;
  })}</div>;
}

function PassageCard({ item, projectId, number, inspector = false }: { item: LabPassage; projectId: string; number?: number; inspector?: boolean }) {
  const measures = [
    ["Final rank", item.final_rank], ["Semantic rank", item.semantic_rank], ["Keyword rank", item.keyword_rank],
    ["Semantic L2 distance", item.semantic_score], ["Keyword BM25", item.keyword_score],
    ["Fusion score", item.fusion_score], ["Reranker term matches", item.reranker_score]
  ].filter(([, value]) => value !== null && value !== undefined);
  return <EvidenceBlock projectId={projectId} passage={item} number={number} anchorPrefix="lab-evidence" diagnostics={inspector && <dl className="lab-inspector"><div><dt>Chunk</dt><dd className="technical-value">{item.id.slice(0, 12)}</dd></div>{measures.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{typeof value === "number" && !Number.isInteger(value) ? value.toFixed(4) : value}</dd></div>)}</dl>} />;
}

export function PipelineLab({ project, registry, registryError, active = true }: { project: Project; registry: Plugin[]; registryError?: string; active?: boolean }) {
  const [tab, setTab] = useState<PipelineTab>("document");
  const [state, setState] = useState<PipelineState>();
  const [effective, setEffective] = useState<PipelineSettings>();
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selectedDocument, setSelectedDocument] = useState("");
  const [indexes, setIndexes] = useState<LabIndexState[]>([]);
  const [models, setModels] = useState<Models>();
  const [providerModels, setProviderModels] = useState<{ id: string; name: string }[]>([]);
  const [providers, setProviders] = useState<{ id: string; configured: boolean }[]>([]);
  const [credentialProvider, setCredentialProvider] = useState("");
  const [credential, setCredential] = useState("");
  const [manageProviders, setManageProviders] = useState(false);
  const [preview, setPreview] = useState<ChunkPreview>();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<LabPassage[]>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [notice, setNotice] = useState<string>();
  const [dirty, setDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"saved" | "pending" | "saving" | "error">("saved");
  const [saveCycle, setSaveCycle] = useState(0);
  const revision = useRef(0);
  const saving = useRef(false);
  const outstanding = useRef<Promise<PipelineState> | null>(null);
  const latest = useRef<{ state?: PipelineState; effective?: PipelineSettings; dirty: boolean }>({ dirty: false });
  latest.current = { state, effective, dirty };

  useEffect(() => () => { if (true) return;
    const snapshot = latest.current;
    if (!snapshot.dirty || !snapshot.state || !snapshot.effective) return;
    void (async () => {
      try { await outstanding.current; } catch { /* Retry the latest settings below. */ }
      const overrides = difference(snapshot.state!.defaults, snapshot.effective!) as Partial<PipelineSettings> | undefined;
      await pipelineApi.save(project.id, overrides ?? {}, true);
    })().catch(() => undefined);
  }, [project.id]);

  useEffect(() => {
    let live = true;
    setState(undefined); setError(undefined);
    Promise.all([pipelineApi.state(project.id), documentsApi.list(project.id), pipelineApi.indexStatus(project.id), searchApi.models(), pipelineApi.providers()])
      .then(([loaded, docs, status, localModels, providerState]) => {
        if (!live) return;
        setState(loaded); setEffective(loaded.effective); setDocuments(docs); setIndexes(status); setModels(localModels); setProviders(providerState);
        setSelectedDocument(docs.find((item) => item.status === "ready")?.id ?? "");
        setCredentialProvider(providerState[0]?.id ?? "");
        void pipelineApi.ensureIndex(project.id);
      }).catch((cause) => { if (live) setError(cause instanceof Error ? cause.message : "Pipeline Lab could not load."); });
    return () => { live = false; };
  }, [project.id]);

  useEffect(() => {
    if (!effective || (effective.ask.provider !== "ollama" && !["openai", "anthropic", "google"].includes(effective.ask.provider))) return;
    let live = true;
    void pipelineApi.models(effective.ask.provider).then((result) => { if (live) setProviderModels(result.models); }).catch(() => { if (live) setProviderModels([]); });
    return () => { live = false; };
  }, [effective?.ask.provider]);

  useEffect(() => {
    if (!effective || !providerModels.length) return;
    setProviderModels([]);
  // Only clear a prior provider's list when the provider actually changes.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effective?.ask.provider]);

  useEffect(() => {
    if (!active || !state || !indexes.some((item) => item.document_status === "ready" && item.status !== "ready")) return;
    const timer = window.setInterval(() => void pipelineApi.indexStatus(project.id).then(setIndexes).catch(() => undefined), 2500);
    return () => window.clearInterval(timer);
  }, [project.id, state, indexes, active]);

  useEffect(() => {
    if (!active || (models?.embeddings.status !== "downloading" && models?.answers.status !== "downloading")) return;
    const timer = window.setInterval(() => void searchApi.models().then(setModels).catch(() => undefined), 3000);
    return () => window.clearInterval(timer);
  }, [models?.embeddings.status, models?.answers.status, active]);

  useEffect(() => {
    if (!active || !state) return;
    void Promise.all([pipelineApi.indexStatus(project.id), searchApi.models()])
      .then(([status, localModels]) => { setIndexes(status); setModels(localModels); })
      .catch(() => undefined);
  }, [active, project.id, state]);

  useEffect(() => {
    if (!state || !effective || !automaticSaveEnabled()) return;
    const timer = window.setTimeout(() => {
      const currentRevision = revision.current;
      saving.current = true;
      setSaveStatus("saving");
      const overrides = difference(state.defaults, effective) as Partial<PipelineSettings> | undefined;
      const request = pipelineApi.save(project.id, overrides ?? {});
      outstanding.current = request;
      void request.then((saved) => {
        setState(saved);
        if (revision.current === currentRevision) {
          setEffective(saved.effective);
          setDirty(false);
          setSaveStatus("saved");
        } else {
          setSaveStatus("pending");
        }
        void pipelineApi.indexStatus(project.id).then(setIndexes).catch(() => undefined);
      }).catch((cause) => {
        if (revision.current !== currentRevision) {
          setSaveStatus("pending");
        } else {
          setError(cause instanceof Error ? cause.message : "Could not save pipeline settings.");
          setSaveStatus("error");
        }
      }).finally(() => {
        outstanding.current = null;
        saving.current = false;
        setSaveCycle((cycle) => cycle + 1);
      });
    }, 650);
    return () => window.clearTimeout(timer);
  }, [project.id, state, effective, dirty, saveStatus, saveCycle]);

  async function applySettings() {
    if (!state || !effective) return;
    const documentChanged = JSON.stringify(state.effective.document) !== JSON.stringify(effective.document);
    setBusy(true); setError(undefined);
    try {
      const overrides = difference(state.defaults, effective) as Partial<PipelineSettings> | undefined;
      const saved = await pipelineApi.save(project.id, overrides ?? {});
      setState(saved); setEffective(saved.effective); setDirty(false); setSaveStatus("saved");
      if (documentChanged) { await pipelineApi.ensureIndex(project.id); setNotice("Settings applied. Reindexing readable documents with the new document pipeline."); }
      else setNotice("Settings applied. Search and Ask will use them immediately.");
      setIndexes(await pipelineApi.indexStatus(project.id));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not apply pipeline settings."); setSaveStatus("error"); }
    finally { setBusy(false); }
  }

  function update(path: string[], value: unknown) {
    revision.current += 1;
    setEffective((previous) => {
      if (!previous) return previous;
      const next = JSON.parse(JSON.stringify(previous)) as PipelineSettings;
      let target = next as unknown as Record<string, unknown>;
      for (const key of path.slice(0, -1)) target = target[key] as Record<string, unknown>;
      target[path[path.length - 1]] = value;
      return next;
    });
    setDirty(true); setSaveStatus("pending"); setError(undefined);
    setPreview(undefined); setResults(undefined); setNotice(undefined);
  }

  async function runPreview() {
    if (!selectedDocument || dirty) return;
    setBusy(true); setError(undefined);
    try { setPreview(await pipelineApi.preview(project.id, selectedDocument)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not preview chunks."); }
    finally { setBusy(false); }
  }

  async function runSearch() {
    if (!query.trim() || dirty) return;
    setBusy(true); setError(undefined);
    try { setResults((await pipelineApi.search(project.id, query.trim())).results); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Search failed."); }
    finally { setBusy(false); }
  }


  async function refreshModels(id: string) {
    setBusy(true); setError(undefined);
    try { setProviderModels((await pipelineApi.models(id)).models); setNotice("Model list refreshed from the provider."); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not refresh models."); }
    finally { setBusy(false); }
  }

  async function saveCredential() {
    if (!credentialProvider || !credential.trim()) return;
    setBusy(true); setError(undefined);
    try {
      await pipelineApi.saveCredential(credentialProvider, credential);
      setCredential(""); setProviders(await pipelineApi.providers());
      setNotice("Credential stored in the operating system credential store.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save credential."); }
    finally { setBusy(false); }
  }

  if (registryError) return <ErrorState message={registryError} retry={() => window.location.reload()} />;
  if (!state || !effective) return error ? <ErrorState message={error} retry={() => window.location.reload()} /> : <LoadingState label="Loading Pipeline Lab…" />;
  const selectedChunker = pluginFor(registry, "chunking", effective.document.chunking.plugin);
  const selectedEmbedding = pluginFor(registry, "embeddings", effective.document.embedding.plugin);
  const selectedStore = pluginFor(registry, "vector_stores", effective.document.vector_store.plugin);
  const selectedRetrieval = pluginFor(registry, "retrieval", effective.search.retrieval);
  const selectedFusion = pluginFor(registry, "fusion", effective.search.fusion);
  const selectedReranker = pluginFor(registry, "rerankers", effective.search.reranker);
  const selectedProvider = pluginFor(registry, "llm_providers", effective.ask.provider);
  const cloud = selectedProvider?.capabilities.local === false;
  const providerUsesRemoteModelList = cloud || effective.ask.provider === "ollama";
  const summary = [
    ["Document", selectedChunker?.name, `${effective.document.chunking.chunk_size} / ${effective.document.chunking.overlap}`, selectedEmbedding?.name, selectedStore?.name],
    ["Search", selectedRetrieval?.name, selectedFusion?.name, `${effective.search.semantic_candidates} semantic + ${effective.search.keyword_candidates} keyword`, `${effective.search.result_limit} results`],
    ["Ask", selectedProvider?.name, effective.ask.grounding === "sources_only" ? "Sources only" : "Sources + model knowledge", `${effective.ask.evidence_count} evidence passages`, effective.ask.require_citations ? "Citations on" : "Citations optional"]
  ];
  return <section className="pipeline-lab"><div className="lab-heading"><div><p className="eyebrow">Advanced workspace</p><h2>Pipeline Lab</h2><p>Configure the document, search, and answer pipeline used throughout this project.</p></div><Button variant="primary" onClick={() => void applySettings()} disabled={!dirty || busy}>Save & Apply</Button><div className="lab-save-state" role="status" aria-live="polite"><span>{saveStatus === "saved" ? "All changes saved" : saveStatus === "saving" ? "Saving changes…" : saveStatus === "error" ? "Changes not saved" : "Changes pending…"}</span>{saveStatus === "error" && <Button onClick={() => { setError(undefined); setSaveStatus("pending"); }}>Retry save</Button>}</div></div>
    <div className="lab-summary" aria-label="Effective pipeline">{summary.map((items, stage) => <div className="lab-summary-stage" key={items[0]}><strong><Icon name={stage === 0 ? "document" : stage === 1 ? "search" : "ask"} size={17} />{items[0]}</strong><span className="lab-summary-main">{items[1]}</span>{items.slice(2).map((item, index) => <span key={index}>{item}</span>)}</div>)}</div>
    {dirty && <p className="lab-unsaved">Changes are drafts until you select Save & Apply. Document changes reindex readable documents; Search and Ask changes apply immediately.</p>}
    {notice && <p className="lab-notice" role="status">{notice}</p>}
    <nav className="workspace-tabs" aria-label="Pipeline Lab sections">{(["document", "search", "ask"] as const).map((item) => <button key={item} aria-current={tab === item ? "page" : undefined} onClick={() => setTab(item)}>{item.toUpperCase()}</button>)}</nav>
    {error && <ErrorState message={error} retry={() => setError(undefined)} />}
    {tab === "document" && <div className="lab-section"><h3>Document pipeline</h3><p>These settings configure the shared document index used by Documents, Search, and Ask.</p>
      <div className="lab-control-grid"><div><label>Chunking strategy <span className="lab-default-badge">{effective.document.chunking.plugin === state.defaults.document.chunking.plugin ? "Default" : "Custom"}</span><select className="input" value={effective.document.chunking.plugin} onChange={(event) => update(["document", "chunking", "plugin"], event.target.value)}>{registry.filter((item) => item.category === "chunking").map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{selectedChunker?.description && <p className="field-help">{selectedChunker.description}</p>}<SchemaFields plugin={selectedChunker} values={effective.document.chunking} defaults={state.defaults.document.chunking} models={models?.answers.models ?? []} onChange={(key, value) => update(["document", "chunking", key], value)} /></div>
        <div><label>Embedding <span className="lab-default-badge">{effective.document.embedding.plugin === state.defaults.document.embedding.plugin ? "Default" : "Custom"}</span><select className="input" value={effective.document.embedding.plugin} onChange={(event) => update(["document", "embedding", "plugin"], event.target.value)}>{registry.filter((item) => item.category === "embeddings").map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{selectedEmbedding?.description && <p className="field-help">{selectedEmbedding.description}</p>}<SchemaFields plugin={selectedEmbedding} values={effective.document.embedding} defaults={state.defaults.document.embedding} onChange={(key, value) => update(["document", "embedding", key], value)} />
        <label>Vector store <span className="lab-default-badge">{effective.document.vector_store.plugin === state.defaults.document.vector_store.plugin ? "Default" : "Custom"}</span><select className="input" value={effective.document.vector_store.plugin} onChange={(event) => update(["document", "vector_store", "plugin"], event.target.value)}>{registry.filter((item) => item.category === "vector_stores").map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{selectedStore?.description && <p className="field-help">{selectedStore.description}</p>}<SchemaFields plugin={selectedStore} values={effective.document.vector_store} defaults={state.defaults.document.vector_store} onChange={(key, value) => update(["document", "vector_store", key], value)} /></div></div>
      {models?.embeddings.status !== "ready" && <div className="lab-notice">Semantic chunking and retrieval need the local embedding model. {models?.embeddings.error && <span>{models.embeddings.error} </span>}<Button disabled={models?.embeddings.status === "downloading"} onClick={() => void searchApi.setup("embeddings").then(() => searchApi.models().then(setModels))}>{models?.embeddings.status === "downloading" ? "Downloading…" : "Set up model"}</Button></div>}
      {effective.document.chunking.plugin === "llm" && models?.answers.status !== "ready" && <div className="lab-notice">LLM chunking needs the local answer model. {models?.answers.error && <span>{models.answers.error} </span>}<Button disabled={models?.answers.status === "downloading"} onClick={() => void searchApi.setup("answers").then(() => searchApi.models().then(setModels))}>{models?.answers.status === "downloading" ? "Downloading…" : "Set up model"}</Button></div>}
      <div className="lab-run-row"><label>Preview document<select className="input" value={selectedDocument} onChange={(event) => setSelectedDocument(event.target.value)}><option value="">Choose a readable document</option>{documents.filter((item) => item.status === "ready").map((item) => <option key={item.id} value={item.id}>{item.display_name}</option>)}</select></label><Button onClick={() => void runPreview()} disabled={!selectedDocument || busy || dirty}>Preview Chunks</Button></div>
      {preview && <div className="lab-output"><h4>{preview.count} {preview.count === 1 ? "chunk" : "chunks"} · {preview.average_characters} characters on average</h4>{preview.samples.map((item) => <div key={item.id} className="lab-chunk"><strong>{item.label} · characters {item.start_offset}–{item.end_offset}</strong><p>{item.text}</p></div>)}</div>}
      <div className="lab-index"><h4>Lab index</h4>{indexes.filter((item) => item.document_status === "ready").map((item) => <p key={item.document_id}>{item.display_name}: {item.status ?? "pending"}{item.error_message ? ` · ${item.error_message}` : ""}</p>)}{indexes.some((item) => item.status === "failed") && <Button onClick={() => void pipelineApi.ensureIndex(project.id).then(() => pipelineApi.indexStatus(project.id)).then(setIndexes).catch((cause) => setError(String(cause)))}>Retry Lab index</Button>}</div>
    </div>}
    {tab === "search" && <div className="lab-section"><h3>Search settings</h3><div className="lab-control-grid"><div><label>Retrieval <span className="lab-default-badge">{effective.search.retrieval === state.defaults.search.retrieval ? "Default" : "Custom"}</span><select className="input" value={effective.search.retrieval} onChange={(event) => update(["search", "retrieval"], event.target.value)}>{registry.filter((item) => item.category === "retrieval").map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{selectedRetrieval?.description && <p className="field-help">{selectedRetrieval.description}</p>}<SchemaFields plugin={selectedRetrieval} values={effective.search} defaults={state.defaults.search} onChange={(key, value) => update(["search", key], value)} /></div>
      <div>{effective.search.retrieval === "hybrid" && <><label>Fusion <span className="lab-default-badge">{effective.search.fusion === state.defaults.search.fusion ? "Default" : "Custom"}</span><select className="input" value={effective.search.fusion} onChange={(event) => update(["search", "fusion"], event.target.value)}>{registry.filter((item) => item.category === "fusion").map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{selectedFusion?.description && <p className="field-help">{selectedFusion.description}</p>}<SchemaFields plugin={selectedFusion} values={effective.search} defaults={state.defaults.search} onChange={(key, value) => update(["search", key], value)} /></>}
        <label>Reranking <span className="lab-default-badge">{effective.search.reranker === state.defaults.search.reranker ? "Default" : "Custom"}</span><select className="input" value={effective.search.reranker} onChange={(event) => update(["search", "reranker"], event.target.value)}>{registry.filter((item) => item.category === "rerankers").map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>{selectedReranker?.description && <p className="field-help">{selectedReranker.description}</p>}<SchemaFields plugin={selectedReranker} values={effective.search} defaults={state.defaults.search} onChange={(key, value) => update(["search", key], value)} /></div></div>
      <form className="search-form" onSubmit={(event) => { event.preventDefault(); void runSearch(); }}><label htmlFor="lab-query">Search this project</label><div><input id="lab-query" className="input" value={query} onChange={(event) => setQuery(event.target.value)} /><Button variant="primary" disabled={!query.trim() || dirty || busy}>Search</Button></div></form>
      {results && <div className="lab-output"><h4>{results.length ? `${results.length} ranked passages` : "No matching passages"}</h4>{results.map((item) => <PassageCard key={item.id} item={item} projectId={project.id} inspector />)}</div>}
    </div>}
    {tab === "ask" && <div className="lab-section"><h3>Answer settings</h3><div className="lab-retrieval-summary"><strong>Retrieval</strong><span>{selectedRetrieval?.name} · {selectedFusion?.name} · {effective.search.semantic_candidates} semantic + {effective.search.keyword_candidates} keyword · {effective.search.result_limit} results · Reranker {selectedReranker?.name}</span><Button variant="quiet" onClick={() => setTab("search")}>Edit Search Settings</Button></div>
      <div className="lab-control-grid"><div><label>Provider<select className="input" value={effective.ask.provider} onChange={(event) => { update(["ask", "provider"], event.target.value); update(["ask", "model"], event.target.value === "llamacpp" ? state.defaults.ask.model : ""); }}><optgroup label="Local">{registry.filter((item) => item.category === "llm_providers" && item.capabilities.local === true).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup><optgroup label="Cloud">{registry.filter((item) => item.category === "llm_providers" && item.capabilities.local === false).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</optgroup></select></label>
        {cloud && <div className="lab-notice">This provider receives the selected passages and your question. Your API key stays in the operating system credential store. <Button onClick={() => setManageProviders((current) => !current)}>Manage Providers</Button></div>}
        {effective.ask.provider === "llamacpp" && models?.answers.status !== "ready" && <div className="lab-notice">The local answer model is not ready. Search remains available. {models?.answers.error && <span>{models.answers.error} </span>}<Button disabled={models?.answers.status === "downloading"} onClick={() => void searchApi.setup("answers").then(() => searchApi.models().then(setModels))}>{models?.answers.status === "downloading" ? "Downloading…" : "Set up local model"}</Button></div>}
        {providerUsesRemoteModelList && <Button onClick={() => void refreshModels(effective.ask.provider)} disabled={busy}>Refresh Models</Button>}
        {selectedProvider?.description && <p className="field-help">{selectedProvider.description}</p>}<SchemaFields plugin={selectedProvider} values={effective.ask} defaults={state.defaults.ask} models={providerUsesRemoteModelList ? providerModels : (models?.answers.models ?? [])} onChange={(key, value) => update(["ask", key], value)} /></div>
        <div><label>Grounding<select className="input" value={effective.ask.grounding} onChange={(event) => update(["ask", "grounding"], event.target.value)}><option value="sources_only">Sources Only</option><option value="sources_plus_model">Sources + Model Knowledge</option></select></label>
          <label>Evidence passages<input className="input" type="number" min={1} max={12} value={effective.ask.evidence_count} onChange={(event) => update(["ask", "evidence_count"], Number(event.target.value))} /></label>
          <label className="lab-toggle"><input type="checkbox" checked={effective.ask.require_citations} onChange={(event) => update(["ask", "require_citations"], event.target.checked)} />Require citations in answer</label>
          <label>Answer style<select className="input" value={effective.ask.answer_style} onChange={(event) => update(["ask", "answer_style"], event.target.value)}><option value="concise">Concise</option><option value="detailed">Detailed</option><option value="bullet_summary">Bullet Summary</option><option value="research">Research</option></select></label></div></div>
      {manageProviders && <div className="lab-provider-manager"><h4>Manage Providers</h4><label>Provider<select className="input" value={credentialProvider} onChange={(event) => setCredentialProvider(event.target.value)}>{providers.map((item) => <option key={item.id} value={item.id}>{pluginFor(registry, "llm_providers", item.id)?.name ?? item.id}{item.configured ? " · configured" : ""}</option>)}</select></label><label>API key<input className="input" type="password" autoComplete="off" value={credential} onChange={(event) => setCredential(event.target.value)} /></label><div className="lab-provider-actions"><Button onClick={() => void saveCredential()} disabled={!credential || busy}>Save key</Button><Button onClick={() => void pipelineApi.testProvider(credentialProvider).then((result) => setNotice(`Connected · ${result.model_count} models available`)).catch((cause) => setError(String(cause)))} disabled={busy}>Test Connection</Button><Button onClick={() => void refreshModels(credentialProvider)} disabled={busy}>Refresh Models</Button><Button variant="quiet" onClick={() => void pipelineApi.removeCredential(credentialProvider).then(() => pipelineApi.providers().then(setProviders))}>Remove key</Button></div></div>}

    </div>}
    {busy && <LoadingState label="Working on this experiment…" />}
  </section>;
}







