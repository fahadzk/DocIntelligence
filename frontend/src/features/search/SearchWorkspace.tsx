import { FormEvent, useEffect, useState } from "react";
import { Button } from "../../components/Button";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { documentsApi, searchApi } from "../../services/api";
import type { Project } from "../../types/projects";
import type { Answer, IndexState, Models, Passage } from "../../types/search";

function Source({ projectId, passage, number }: { projectId: string; passage: Passage; number?: number }) {
  const [error, setError] = useState<string>();
  function open() {
    if (passage.file_type === "pdf" && passage.page_number) {
      window.open(documentsApi.originalUrl(projectId, passage.document_id, passage.page_number), "_blank", "noopener");
    } else if (window.documentIntelligence?.openOriginal) {
      void window.documentIntelligence.openOriginal(projectId, passage.document_id, passage.file_type).then((message) => { if (message) setError(message); });
    } else {
      window.open(documentsApi.originalUrl(projectId, passage.document_id), "_blank", "noopener");
    }
  }
  return <article className="evidence-item" id={number ? `evidence-${number}` : undefined} tabIndex={number ? -1 : undefined}>
    <div className="evidence-meta">{number && <strong>[{number}] </strong>}{passage.display_name} · {passage.label}{passage.match_type && <span className="match-type">{passage.match_type === "keyword" ? "Exact terms" : passage.match_type === "semantic" ? "Related meaning" : "Exact + related"}</span>}</div>
    <p>{passage.text}</p>
    <Button variant="quiet" onClick={open}>Open original{passage.page_number ? ` at page ${passage.page_number}` : ""}</Button>
    {error && <p role="alert">{error}</p>}
  </article>;
}

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

  useEffect(() => {
    let mounted = true;
    const refresh = () => Promise.all([searchApi.models(), searchApi.status(project.id)])
      .then(([nextModels, nextIndexes]) => { if (mounted) { setModels(nextModels); setIndexes(nextIndexes); } })
      .catch((cause) => { if (mounted) setError(cause instanceof Error ? cause.message : "Unable to load search status."); });
    void refresh();
    const timer = active ? window.setInterval(() => void refresh(), 2500) : undefined;
    return () => { mounted = false; if (timer !== undefined) window.clearInterval(timer); };
  }, [project.id, active]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
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
    <div className="documents-heading"><div><p className="eyebrow">Project / {mode === "ask" ? "Ask" : "Search"}</p><h2>{mode === "ask" ? "Ask your documents" : "Search documents"}</h2><p>{mode === "ask" ? "Answers draw only from passages in this project." : "Find source passages by exact terms or related meaning."}</p></div>{mode === "search" && <Button variant="quiet" onClick={() => void rebuild()}>Rebuild index</Button>}</div>
    {model && model.status !== "ready" && <div className="model-setup">
      <div><strong>{mode === "ask" ? "Local answer model" : "Semantic search model"}</strong><p>{mode === "ask" ? "Qwen2.5 1.5B, Apache 2.0. About 1.1 GB download; allow roughly 3 GB RAM. Search works without it." : "BGE-small English, MIT. About 70 MB download and disk space. Exact-term search works without it."}</p><small>Source: <a href={model.source} target="_blank" rel="noreferrer">{model.name}</a>. Download once; runs offline afterward.</small>{model.error && <p role="alert">{model.error}</p>}</div>
      <Button onClick={() => void setup(mode === "ask" ? "answers" : "embeddings")} disabled={model.status === "downloading"}>{model.status === "downloading" ? "Downloading…" : model.status === "failed" ? "Retry setup" : "Set up locally"}</Button>
    </div>}
    {pending.length > 0 && <div className="index-notice" role="status">{pending.some((item) => item.status === "indexing") ? "Indexing readable documents…" : `${pending.length} readable document(s) need indexing.`}</div>}
    {indexes.length > 0 && relevant.length === 0 && <p>There are no readable documents yet. Scanned or failed files cannot be searched.</p>}
    <form className="search-form" onSubmit={(event) => void submit(event)}>
      <label htmlFor={queryId}>{mode === "ask" ? "Question" : "Search terms"}</label>
      <div><input id={queryId} className="input" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={mode === "ask" ? "What do these documents say about…" : "Search this project"} /><Button variant="primary" disabled={loading || !query.trim() || (mode === "ask" && model?.status !== "ready")}>{mode === "ask" ? "Ask" : "Search"}</Button></div>
    </form>
    {error && <ErrorState message={error} retry={() => { setError(undefined); }} />}
    {loading ? <LoadingState label={mode === "ask" ? "Reading evidence and drafting an answer…" : "Searching passages…"} /> : mode === "search" ? searched && results.length === 0 ? <p className="search-empty">No matching readable passages found. Try different terms or add documents.</p> : <div className="evidence-list">{results.map((item) => <Source key={item.id} projectId={project.id} passage={item} />)}</div> :
      answer && <div className="answer-panel"><h3>{answer.supported ? "Answer" : "Not enough evidence"}</h3><p className="answer-text">{answer.answer.split(/(\[\d+\])/g).map((part, index) => {
        const number = /^\[(\d+)\]$/.exec(part)?.[1];
        return number && answer.evidence.some((item) => item.number === Number(number))
          ? <button className="citation-link" key={index} aria-label={`View source ${number}`} onClick={() => { const target = document.getElementById(`evidence-${number}`); target?.scrollIntoView({ behavior: "smooth", block: "center" }); target?.focus(); }}>{part}</button>
          : <span key={index}>{part}</span>;
      })}</p>{answer.evidence.length > 0 && <><h3>Supporting passages</h3><div className="evidence-list">{answer.evidence.map((item) => <Source key={item.passage.id} projectId={project.id} passage={item.passage} number={item.number} />)}</div></>}</div>}
  </section>;
}
