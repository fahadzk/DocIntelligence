import { useCallback, useEffect, useRef, useState } from "react";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/EmptyState";
import { ErrorState } from "../../components/ErrorState";
import { LoadingState } from "../../components/LoadingState";
import { Icon } from "../../components/Icon";
import { documentsApi } from "../../services/api";
import type { DocumentItem, Segment } from "../../types/documents";
import type { Project } from "../../types/projects";

export function DocumentsWorkspace({ project }: { project: Project }) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<DocumentItem>();
  const [segments, setSegments] = useState<Segment[]>([]);
  const [contentLoading, setContentLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string>();
  const [notices, setNotices] = useState<string[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [sort, setSort] = useState<"recent" | "name">("recent");
  const picker = useRef<HTMLInputElement>(null);
  const selectedId = selected?.id;
  const selectedStatus = selected?.status;
  const refresh = useCallback(async () => {
    try {
      const items = await documentsApi.list(project.id);
      setDocuments(items);
      setSelected((current) => items.find((item) => item.id === current?.id));
      setError(undefined);
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Unable to load documents."); }
    finally { setLoading(false); }
  }, [project.id]);
  useEffect(() => { setLoading(true); setDocuments([]); setSelected(undefined); void refresh(); }, [refresh]);
  useEffect(() => {
    if (!documents.some((item) => item.status === "processing")) return;
    const timer = window.setInterval(() => void refresh(), 1000);
    return () => window.clearInterval(timer);
  }, [documents, refresh]);
  useEffect(() => {
    if (!selectedId || selectedStatus !== "ready") { setSegments([]); setContentLoading(false); return; }
    let active = true;
    setContentLoading(true);
    documentsApi.chunks(project.id, selectedId).then((result) => { if (active) setSegments(result); }).catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "Unable to read document."); }).finally(() => { if (active) setContentLoading(false); });
    return () => { active = false; };
  }, [project.id, selectedId, selectedStatus]);
  async function importFiles(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true); setNotices([]);
    try {
      const result = await documentsApi.import(project.id, files);
      setNotices(result.filter((item) => item.error_message).map((item) => `${item.filename}: ${item.error_message}`));
      await refresh();
      const first = result.find((item) => item.document)?.document;
      if (first) {
        const latest = await documentsApi.get(project.id, first.id);
        setDocuments((items) => items.map((item) => item.id === latest.id ? latest : item));
        setSelected(latest);
      }
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Import failed."); }
    finally { setUploading(false); if (picker.current) picker.current.value = ""; }
  }
  async function retry() { if (!selected) return; try { await documentsApi.retry(project.id, selected.id); await refresh(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Retry failed."); } }
  async function reindex() { if (!selected) return; try { await documentsApi.reindex(project.id, selected.id); setNotices(["Re-chunking and re-indexing " + selected.display_name + " using this project configuration."]); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not reindex document."); } }
  async function reembed() { if (!selected) return; try { await documentsApi.reembed(project.id, selected.id); setNotices(["Regenerating embeddings for " + selected.display_name + ". Existing chunks are retained."]); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not regenerate embeddings."); } }
  async function refreshChunks() { if (!selected) return; setContentLoading(true); try { setSegments(await documentsApi.chunks(project.id, selected.id)); setNotices(["Chunk view refreshed."]); } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not refresh chunks."); } finally { setContentLoading(false); } }
  async function remove() { if (!selected) return; try { await documentsApi.remove(project.id, selected.id); setSelected(undefined); setConfirmDelete(false); await refresh(); } catch (cause) { setError(cause instanceof Error ? cause.message : "Delete failed."); } }
  function openOriginal(page?: number) {
    if (!selected) return;
    if (window.documentIntelligence?.openOriginal && !page) void window.documentIntelligence.openOriginal(project.id, selected.id, selected.file_type).then((message) => { if (message) setError(message); });
    else window.open(documentsApi.originalUrl(project.id, selected.id, page), "_blank", "noopener");
  }
  const formatSize = (bytes: number) => bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`;
  const sorted = [...documents].sort((left, right) => sort === "name" ? left.display_name.localeCompare(right.display_name) : right.created_at.localeCompare(left.created_at));
  return <section className="documents-workspace">
    <div className="documents-heading section-heading"><div><p className="eyebrow">Workspace</p><h2>Documents</h2><p>{loading ? "Loading source materialâ€¦" : `${documents.length} ${documents.length === 1 ? "document" : "documents"} in this project`}</p></div>{documents.length > 0 && <Button variant="primary" icon="upload" onClick={() => picker.current?.click()} disabled={uploading}>{uploading ? "Addingâ€¦" : "Add documents"}</Button>}</div>
    <input ref={picker} className="visually-hidden" type="file" multiple accept=".pdf,.docx,.txt,.md,.markdown,text/plain,application/pdf" aria-label="Choose documents" onChange={(event) => void importFiles(event.target.files)} />
    {notices.length > 0 && <div className="import-notices" role="status">{notices.map((notice) => <p key={notice}>{notice}</p>)}</div>}
    {error && <ErrorState message={error} retry={() => void refresh()} />}
    {loading ? <LoadingState label="Loading documentsâ€¦" /> : documents.length === 0 ? <EmptyState eyebrow="Documents" title="No documents yet" icon="document"><p>Import a PDF, Word document, text file, or Markdown file to begin.</p><Button variant="primary" icon="upload" onClick={() => picker.current?.click()}>Add documents</Button></EmptyState> :
    <div className="documents-layout"><div className="documents-list" aria-label="Documents"><div className="list-toolbar"><span>Files</span><label>Sort <select className="compact-select" value={sort} onChange={(event) => setSort(event.target.value as "recent" | "name")}><option value="recent">Newest first</option><option value="name">Name</option></select></label></div>{sorted.map((item) => <button key={item.id} className={selected?.id === item.id ? "document-row selected" : "document-row"} aria-current={selected?.id === item.id ? "true" : undefined} onClick={() => { setSelected(item); setConfirmDelete(false); }}><Icon name="document" size={18} /><span className="document-row-main"><strong>{item.display_name}</strong><small>{item.file_type.toUpperCase()} Â· {new Date(item.created_at).toLocaleDateString()}</small></span><span className={`document-status status-${item.status}`}>{item.stage === "extracting" ? "Extracting text" : item.status === "ready" ? "Ready" : item.status === "failed" ? "Needs attention" : item.stage}</span></button>)}</div>
    <div className="document-detail">{selected ? <><div className="detail-header"><div><p className="eyebrow">{selected.file_type.toUpperCase()} Â· {formatSize(selected.size_bytes)}</p><h3>{selected.display_name}</h3></div><div className="document-actions"><Button icon="open" onClick={() => openOriginal()}>Open original</Button><Button variant="secondary" icon="refresh" onClick={() => void refreshChunks()} disabled={contentLoading}>Refresh chunks</Button><Button onClick={() => void reindex()}>Re-chunk & re-index</Button><Button variant="secondary" onClick={() => void reembed()}>Regenerate embeddings</Button></div></div>
      {selected.status === "processing" ? <LoadingState label="Extracting readable textâ€¦" /> : selected.status === "failed" ? <div className="document-failure"><strong>Could not process this document</strong><p>{selected.error_message}</p>{["INTERRUPTED", "PROCESSING_ERROR"].includes(selected.error_code ?? "") && <Button onClick={() => void retry()}>Retry</Button>}</div> : contentLoading ? <LoadingState label="Loading extracted textâ€¦" /> : <div className="document-text"><p className="chunking-note">Showing chunks generated with this project configuration.</p>{segments.length === 0 && <p>Indexing is in progress. Chunks will appear here when it finishes.</p>}{segments.map((segment, chunkIndex) => <section key={chunkIndex} className="text-segment"><div className="segment-label">Chunk {chunkIndex + 1} / {segment.label}{segment.page_number && <button onClick={() => openOriginal(segment.page_number ?? undefined)}>Open page {segment.page_number}</button>}</div><p>{segment.text}</p></section>)}</div>}
      <div className="detail-footer">{confirmDelete ? <><span>Delete this document and its stored copy?</span><Button variant="danger" icon="delete" onClick={() => void remove()}>Delete document</Button><Button onClick={() => setConfirmDelete(false)}>Cancel</Button></> : <Button variant="quiet" icon="delete" onClick={() => setConfirmDelete(true)}>Delete document</Button>}</div>
    </> : <div className="select-document"><Icon name="document" size={24} /><p>Select a document to inspect its generated chunks and source metadata.</p></div>}</div></div>}
  </section>;
}




