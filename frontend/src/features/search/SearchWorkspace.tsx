import { FormEvent, useEffect, useState } from "react";
import { Button } from "../../components/Button";
import { EvidenceBlock } from "../../components/EvidenceBlock";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { Icon } from "../../components/Icon";
import { searchApi } from "../../services/api";
import type { Project } from "../../types/projects";
import type { Answer, IndexState, Models, Passage } from "../../types/search";

export function SearchWorkspace({ project, mode, active = true }: { project: Project; mode: "search" | "ask"; active?: boolean }) {
  const [query, setQuery] = useState("");
  const queryId = mode === "ask" ? "project-ask-query" : "project-search-query";
  const [results, setResults] = useState<Passage[]>([]);
  const [answer, setAnswer] = useState<Answer>();
  const [models, setModels] = useState<Models>();
  const [indexes, setIndexes] = useState<IndexState[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();
  const [searched, setSearched] = useState(false);
  const fastRefresh = indexes.some((item) => item.document_status === "ready" && item.status !== "ready") ||
    models?.answers.status === "downloading" || models?.embeddings.status === "downloading";

  useEffect(() => {
    let mounted = true;
    void Promise.all([searchApi.models(), searchApi.status(project.id)])
      .then(([nextModels, nextIndexes]) => { if (mounted) { setModels(nextModels); setIndexes(nextIndexes); } })
      .catch((cause) => { if (mounted) setError(cause instanceof Error ? cause.message : "Unable to load search status."); });
    return () => { mounted = false; };
  }, [project.id, active]);

  useEffect(() => {
    if (!active || loading) return;
    let mounted = true;
    const timer = window.setInterval(() => {
      void Promise.all([searchApi.models(), searchApi.status(project.id)])
        .then(([nextModels, nextIndexes]) => { if (mounted) { setModels(nextModels); setIndexes(nextIndexes); } })
        .catch(() => undefined);
    }, fastRefresh ? 2500 : 15000);
    return () => { mounted = false; window.clearInterval(timer); };
  }, [project.id, active, loading, fastRefresh]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (loading || !query.trim()) return;
    setLoading(true); setError(undefined); setSearched(true); setAnswer(undefined); setResults([]);
    try {
      if (mode === "ask") setAnswer(await searchApi.ask(project.id, query.trim()));
      else setResults((await searchApi.search(project.id, query.trim())).results);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "The request failed."); }
    finally { setLoading(false); }
  }
  async function setup(kind: "embeddings" | "answers") {
    setError(undefined);
    try { await searchApi.setup(kind); setModels(await searchApi.models()); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Model setup could not start."); }
  }
  async function rebuild() {
    setError(undefined);
    try { await searchApi.rebuild(project.id); setIndexes(await searchApi.status(project.id)); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Could not rebuild the index."); }
  }
  const relevant = indexes.filter((item) => item.document_status === "ready");
  const pending = relevant.filter((item) => item.status !== "ready");
  const model = mode === "ask" ? models?.answers : models?.embeddings;
  return <section className="search-workspace">
    <div className="documents-heading section-heading"><div><p className="eyebrow">Workspace</p><h2>{mode === "ask" ? "Ask" : "Search"}</h2><p>{mode === "ask" ? "Answers grounded in this project's documents." : "Find source passages by exact terms or related meaning."}</p></div>{mode === "search" && <Button variant="secondary" icon="refresh" onClick={() => void rebuild()}>Rebuild index</Button>}</div>
    {model && model.status !== "ready" && <div className="model-setup">
      <Icon name="model" size={20} /><div><strong>{mode === "ask" ? "Local answer model" : "Semantic search model"}</strong><p>{mode === "ask" ? "Qwen2.5 1.5B, Apache 2.0. About 1.1 GB download; allow roughly 3 GB RAM. Search works without it." : "BGE-small English, MIT. About 70 MB download and disk space. Exact-term search works without it."}</p><small>Source: <a href={model.source} target="_blank" rel="noreferrer">{model.name}</a>. Download once; runs offline afterward.</small>{model.error && <p role="alert">{model.error}</p>}</div>
      <Button onClick={() => void setup(mode === "ask" ? "answers" : "embeddings")} disabled={model.status === "downloading"}>{model.status === "downloading" ? "Downloading…" : model.status === "failed" ? "Retry setup" : "Set up locally"}</Button>
    </div>}
    {pending.length > 0 && <div className="index-notice" role="status">{pending.some((item) => item.status === "indexing") ? "Indexing readable documents…" : `${pending.length} readable document(s) need indexing.`}</div>}
    {indexes.length > 0 && relevant.length === 0 && <p>There are no readable documents yet. Scanned or failed files cannot be searched.</p>}
    <form className="search-form" onSubmit={(event) => void submit(event)}>
      <label htmlFor={queryId}>{mode === "ask" ? "Question" : "Search terms"}</label>
      <div><input id={queryId} disabled={loading} className="input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={mode === "ask" ? "What do these documents say about…" : "Search this project"} /><Button variant="primary" icon={mode === "ask" ? "ask" : "search"} disabled={loading || !query.trim() || (mode === "ask" && model?.status !== "ready")}>{mode === "ask" ? "Ask" : "Search"}</Button></div>
    </form>
    {error && <ErrorState message={error} retry={() => { setError(undefined); }} />}
    {loading ? <LoadingState label={mode === "ask" ? "Reading evidence and drafting an answer…" : "Searching passages…"} /> : mode === "search" ? searched && results.length === 0 ? <div className="search-empty"><Icon name="search" size={22} /><strong>No matching passages</strong><p>Try different terms or add more readable documents.</p></div> : <div className="evidence-list">{results.map((item) => <EvidenceBlock key={item.id} projectId={project.id} passage={item} />)}</div> :
      answer && <div className="answer-panel"><h3>{answer.supported ? "Answer" : "Unable to verify an answer"}</h3><p className="answer-text">{answer.answer.split(/(\[\d+\])/g).map((part, index) => {
        const number = /^\[(\d+)\]$/.exec(part)?.[1];
        return number && answer.evidence.some((item) => item.number === Number(number))
          ? <button className="citation-link" key={index} aria-label={`View source ${number}`} onClick={() => { const target = document.getElementById(`evidence-${number}`); target?.scrollIntoView({ behavior: "smooth", block: "center" }); target?.focus(); }}>{part}</button>
          : <span key={index}>{part}</span>;
      })}</p>{answer.evidence.length > 0 && <><h3>Supporting passages</h3><div className="evidence-list">{answer.evidence.map((item) => <EvidenceBlock key={item.passage.id} projectId={project.id} passage={item.passage} number={item.number} />)}</div></>}</div>}
  </section>;
}
