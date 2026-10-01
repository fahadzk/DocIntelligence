import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '../../components/Button';
import { EmptyState } from '../../components/EmptyState';
import { ErrorState } from '../../components/ErrorState';
import { LoadingState } from '../../components/LoadingState';
import { Icon } from '../../components/Icon';
import { documentsApi } from '../../services/api';
import type { ChunkPage, ChunkQuery, DocumentItem } from '../../types/documents';
import type { Project } from '../../types/projects';

const CHUNK_LIMIT = 50;

export function DocumentsWorkspace({ project }: { project: Project }) {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [selected, setSelected] = useState<DocumentItem>();
  const [chunkPage, setChunkPage] = useState<ChunkPage>();
  const [rangeStart, setRangeStart] = useState(1);
  const [rangeEnd, setRangeEnd] = useState(10);
  const [pageInput, setPageInput] = useState('');
  const [contentLoading, setContentLoading] = useState(false);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string>();
  const [notices, setNotices] = useState<string[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [sort, setSort] = useState<'recent' | 'name'>('recent');
  const picker = useRef<HTMLInputElement>(null);
  const selectedId = selected?.id;
  const selectedStatus = selected?.status;

  const refresh = useCallback(async () => {
    try {
      const items = await documentsApi.list(project.id);
      setDocuments(items);
      setSelected((current) => items.find((item) => item.id === current?.id));
      setError(undefined);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to load documents.');
    } finally {
      setLoading(false);
    }
  }, [project.id]);

  useEffect(() => {
    setLoading(true);
    setDocuments([]);
    setSelected(undefined);
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!documents.some((item) => item.status === 'processing')) return;
    const timer = window.setInterval(() => void refresh(), 1000);
    return () => window.clearInterval(timer);
  }, [documents, refresh]);

  useEffect(() => {
    if (!selectedId || selectedStatus !== 'ready') {
      setChunkPage(undefined);
      setContentLoading(false);
      return;
    }
    let active = true;
    const endPage = selected?.file_type === 'pdf' ? Math.min(10, selected.page_count ?? 10) : undefined;
    const query: ChunkQuery = selected?.file_type === 'pdf' ? { startPage: 1, endPage } : {};
    setRangeStart(1);
    setRangeEnd(endPage ?? 10);
    setPageInput('');
    setContentLoading(true);
    documentsApi.chunkPage(project.id, selectedId, query)
      .then((result) => { if (active) setChunkPage(result); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : 'Unable to read document.'); })
      .finally(() => { if (active) setContentLoading(false); });
    return () => { active = false; };
  }, [project.id, selectedId, selectedStatus, selected?.file_type, selected?.page_count]);

  async function loadChunks(query: ChunkQuery, notice?: string) {
    if (!selected) return;
    setContentLoading(true);
    try {
      const result = await documentsApi.chunkPage(project.id, selected.id, { ...query, limit: CHUNK_LIMIT });
      setChunkPage(result);
      if (result.start_page !== null) setRangeStart(result.start_page);
      if (result.end_page !== null) setRangeEnd(result.end_page);
      setError(undefined);
      if (notice) setNotices([notice]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not load chunks.');
    } finally {
      setContentLoading(false);
    }
  }

  function activeRange(offset = 0): ChunkQuery {
    if (selected?.file_type !== 'pdf') return { offset, limit: CHUNK_LIMIT };
    return {
      startPage: chunkPage?.start_page ?? rangeStart,
      endPage: chunkPage?.end_page ?? rangeEnd,
      offset,
      limit: CHUNK_LIMIT,
    };
  }

  function applyRange() {
    const pageCount = selected?.page_count ?? 0;
    if (rangeStart < 1 || rangeEnd < rangeStart || rangeEnd > pageCount || rangeEnd - rangeStart + 1 > 10) {
      setError(`Choose up to 10 pages between 1 and ${pageCount}.`);
      return;
    }
    setPageInput('');
    void loadChunks({ startPage: rangeStart, endPage: rangeEnd, offset: 0, limit: CHUNK_LIMIT });
  }

  function goToPage() {
    const page = Number(pageInput);
    const pageCount = selected?.page_count ?? 0;
    if (!Number.isInteger(page) || page < 1 || page > pageCount) {
      setError(`Choose a page between 1 and ${pageCount}.`);
      return;
    }
    void loadChunks({ pageNumber: page, offset: 0, limit: CHUNK_LIMIT });
  }

  function moveWindow(start: number) {
    const pageCount = selected?.page_count ?? 0;
    const safeStart = Math.max(1, Math.min(start, pageCount));
    const end = Math.min(safeStart + 9, pageCount);
    setPageInput('');
    void loadChunks({ startPage: safeStart, endPage: end, offset: 0, limit: CHUNK_LIMIT });
  }

  async function importFiles(files: FileList | null) {
    if (!files?.length) return;
    setUploading(true);
    setNotices([]);
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
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Import failed.');
    } finally {
      setUploading(false);
      if (picker.current) picker.current.value = '';
    }
  }

  async function retry() {
    if (!selected) return;
    try {
      await documentsApi.retry(project.id, selected.id);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Retry failed.');
    }
  }

  async function reindex() {
    if (!selected) return;
    try {
      await documentsApi.reindex(project.id, selected.id);
      setNotices([`Re-chunking and re-indexing ${selected.display_name} using this project configuration.`]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not reindex document.');
    }
  }

  async function reembed() {
    if (!selected) return;
    try {
      await documentsApi.reembed(project.id, selected.id);
      setNotices([`Regenerating embeddings for ${selected.display_name}. Existing chunks are retained.`]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not regenerate embeddings.');
    }
  }

  async function remove() {
    if (!selected) return;
    try {
      await documentsApi.remove(project.id, selected.id);
      setSelected(undefined);
      setConfirmDelete(false);
      await refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Delete failed.');
    }
  }

  function openOriginal(page?: number) {
    if (!selected) return;
    if (window.documentIntelligence?.openOriginal && !page) {
      void window.documentIntelligence.openOriginal(project.id, selected.id, selected.file_type)
        .then((message) => { if (message) setError(message); });
    } else {
      window.open(documentsApi.originalUrl(project.id, selected.id, page), '_blank', 'noopener');
    }
  }

  const formatSize = (bytes: number) => bytes < 1024 ? `${bytes} B` : `${(bytes / 1024).toFixed(1)} KB`;
  const sorted = [...documents].sort((left, right) => sort === 'name' ? left.display_name.localeCompare(right.display_name) : right.created_at.localeCompare(left.created_at));
  const chunks = chunkPage?.items ?? [];
  const firstChunk = chunkPage && chunkPage.total > 0 ? chunkPage.offset + 1 : 0;
  const lastChunk = chunkPage ? chunkPage.offset + chunks.length : 0;

  return <section className='documents-workspace'>
    <div className='documents-heading section-heading'><div><p className='eyebrow'>Workspace</p><h2>Documents</h2><p>{loading ? 'Loading source material…' : `${documents.length} ${documents.length === 1 ? 'document' : 'documents'} in this project`}</p></div>{documents.length > 0 && <Button variant='primary' icon='upload' onClick={() => picker.current?.click()} disabled={uploading}>{uploading ? 'Adding…' : 'Add documents'}</Button>}</div>
    <input ref={picker} className='visually-hidden' type='file' multiple accept='.pdf,.docx,.txt,.md,.markdown,text/plain,application/pdf' aria-label='Choose documents' onChange={(event) => void importFiles(event.target.files)} />
    {notices.length > 0 && <div className='import-notices' role='status'>{notices.map((notice) => <p key={notice}>{notice}</p>)}</div>}
    {error && <ErrorState message={error} retry={() => void refresh()} />}
    {loading ? <LoadingState label='Loading documents…' /> : documents.length === 0 ? <EmptyState eyebrow='Documents' title='No documents yet' icon='document'><p>Import a PDF, Word document, text file, or Markdown file to begin.</p><Button variant='primary' icon='upload' onClick={() => picker.current?.click()}>Add documents</Button></EmptyState> :
      <div className='documents-layout'><div className='documents-list' aria-label='Documents'><div className='list-toolbar'><span>Files</span><label>Sort <select className='compact-select' value={sort} onChange={(event) => setSort(event.target.value as 'recent' | 'name')}><option value='recent'>Newest first</option><option value='name'>Name</option></select></label></div>{sorted.map((item) => <button key={item.id} className={selected?.id === item.id ? 'document-row selected' : 'document-row'} aria-current={selected?.id === item.id ? 'true' : undefined} onClick={() => { setSelected(item); setConfirmDelete(false); }}><Icon name='document' size={18} /><span className='document-row-main'><strong>{item.display_name}</strong><small>{item.file_type.toUpperCase()} · {new Date(item.created_at).toLocaleDateString()}</small></span><span className={`document-status status-${item.status}`}>{item.stage === 'extracting' ? 'Extracting text' : item.status === 'ready' ? 'Ready' : item.status === 'failed' ? 'Needs attention' : item.stage}</span></button>)}</div>
      <div className='document-detail'>{selected ? <><div className='detail-header'><div><p className='eyebrow'>{selected.file_type.toUpperCase()} · {formatSize(selected.size_bytes)}</p><h3>{selected.display_name}</h3></div><div className='document-actions'><Button icon='open' onClick={() => openOriginal()}>Open original</Button><Button variant='secondary' icon='refresh' onClick={() => void loadChunks(activeRange(chunkPage?.offset ?? 0), 'Chunk view refreshed.')} disabled={contentLoading}>Refresh chunks</Button><Button onClick={() => void reindex()}>Re-chunk &amp; re-index</Button><Button variant='secondary' onClick={() => void reembed()}>Regenerate embeddings</Button></div></div>
        {selected.status === 'processing' ? <LoadingState label='Extracting readable text…' /> : selected.status === 'failed' ? <div className='document-failure'><strong>Could not process this document</strong><p>{selected.error_message}</p>{['INTERRUPTED', 'PROCESSING_ERROR'].includes(selected.error_code ?? '') && <Button onClick={() => void retry()}>Retry</Button>}</div> : <>
          <div className='chunk-browser-toolbar'>
            {selected.file_type === 'pdf' && <><div className='page-window-nav'><Button variant='quiet' onClick={() => moveWindow((chunkPage?.start_page ?? 1) - 10)} disabled={contentLoading || (chunkPage?.start_page ?? 1) <= 1}>Previous 10 pages</Button><strong>Pages {chunkPage?.start_page ?? rangeStart}–{chunkPage?.end_page ?? rangeEnd} of {selected.page_count}</strong><Button variant='quiet' onClick={() => moveWindow((chunkPage?.end_page ?? 0) + 1)} disabled={contentLoading || (chunkPage?.end_page ?? 0) >= (selected.page_count ?? 0)}>Next 10 pages</Button></div>
              <div className='page-filter-row'><form onSubmit={(event) => { event.preventDefault(); applyRange(); }}><label>Start page<input className='input page-number-input' type='number' min={1} max={selected.page_count ?? undefined} value={rangeStart} onChange={(event) => setRangeStart(Number(event.target.value))} /></label><label>End page<input className='input page-number-input' type='number' min={1} max={selected.page_count ?? undefined} value={rangeEnd} onChange={(event) => setRangeEnd(Number(event.target.value))} /></label><Button type='submit' disabled={contentLoading}>Show range</Button></form><form onSubmit={(event) => { event.preventDefault(); goToPage(); }}><label>Specific page<input className='input page-number-input' type='number' min={1} max={selected.page_count ?? undefined} value={pageInput} placeholder='Page' onChange={(event) => setPageInput(event.target.value)} /></label><Button type='submit' disabled={contentLoading || pageInput === ''}>Go</Button></form></div></>}
            {chunkPage && <div className='chunk-page-summary'><span>Showing chunks {firstChunk}–{lastChunk} of {chunkPage.total}{selected.file_type === 'pdf' ? ' in this page range' : ''}</span><div><Button variant='quiet' onClick={() => void loadChunks(activeRange(Math.max(0, chunkPage.offset - chunkPage.limit)))} disabled={contentLoading || chunkPage.offset === 0}>Previous chunks</Button><Button variant='quiet' onClick={() => void loadChunks(activeRange(chunkPage.offset + chunkPage.limit))} disabled={contentLoading || !chunkPage.has_more}>Next chunks</Button></div></div>}
          </div>
          {contentLoading ? <LoadingState label='Loading chunks…' /> : <div className='document-text'><p className='chunking-note'>Showing chunks generated with this project configuration.</p>{chunks.length === 0 && <p>{chunkPage?.total === 0 ? 'No chunks exist in this page range.' : 'Indexing is in progress. Chunks will appear here when it finishes.'}</p>}{chunks.map((chunk, chunkIndex) => <section key={chunk.id} className='text-segment'><div className='segment-label'>Chunk {(chunkPage?.offset ?? 0) + chunkIndex + 1} / {chunk.label}{chunk.page_number && <button onClick={() => openOriginal(chunk.page_number ?? undefined)}>Open page {chunk.page_number}</button>}</div><p>{chunk.text}</p></section>)}</div>}
        </>}
        <div className='detail-footer'>{confirmDelete ? <><span>Delete this document and its stored copy?</span><Button variant='danger' icon='delete' onClick={() => void remove()}>Delete document</Button><Button onClick={() => setConfirmDelete(false)}>Cancel</Button></> : <Button variant='quiet' icon='delete' onClick={() => setConfirmDelete(true)}>Delete document</Button>}</div>
      </> : <div className='select-document'><Icon name='document' size={24} /><p>Select a document to inspect its generated chunks and source metadata.</p></div>}</div></div>}
  </section>;
}
