import { useState, type ReactNode } from "react";
import { documentsApi } from "../services/api";
import type { Passage } from "../types/search";
import { Button } from "./Button";
import { Icon } from "./Icon";

export function EvidenceBlock({ projectId, passage, number, anchorPrefix = "evidence", diagnostics }: {
  projectId: string; passage: Passage; number?: number; anchorPrefix?: string; diagnostics?: ReactNode;
}) {
  const [error, setError] = useState<string>();
  function openSource() {
    if (passage.file_type === "pdf" && passage.page_number) {
      window.open(documentsApi.originalUrl(projectId, passage.document_id, passage.page_number), "_blank", "noopener");
    } else if (window.documentIntelligence?.openOriginal) {
      void window.documentIntelligence.openOriginal(projectId, passage.document_id, passage.file_type)
        .then((message) => { if (message) setError(message); });
    } else {
      window.open(documentsApi.originalUrl(projectId, passage.document_id), "_blank", "noopener");
    }
  }
  const match = passage.match_type === "keyword" ? "Exact terms" : passage.match_type === "semantic" ? "Related meaning" : passage.match_type ? "Exact + related" : null;
  return <article className="evidence-item" id={number ? `${anchorPrefix}-${number}` : undefined} tabIndex={number ? -1 : undefined}>
    <div className="evidence-meta"><Icon name="document" size={16} />{number && <span className="citation-number">[{number}]</span>}<strong>{passage.display_name}</strong><span className="source-location">{passage.label}</span>{match && <span className="match-type">{match}</span>}</div>
    <p className="evidence-excerpt">{passage.text}</p>
    {diagnostics}
    <details className="citation-metadata"><summary>Citation and metadata</summary><dl><div><dt>Document</dt><dd>{passage.display_name}</dd></div><div><dt>Source</dt><dd>{passage.label}</dd></div>{passage.page_number && <div><dt>Page</dt><dd>{passage.page_number}</dd></div>}{passage.paragraph_number && <div><dt>Paragraph</dt><dd>{passage.paragraph_number}</dd></div>}{passage.chunk_index !== undefined && <div><dt>Chunk</dt><dd>{passage.chunk_index + 1}</dd></div>}{passage.start_offset !== undefined && <div><dt>Source offsets</dt><dd>{passage.start_offset}–{passage.end_offset}</dd></div>}{passage.index_version && <div><dt>Index version</dt><dd>{passage.index_version}</dd></div>}</dl></details>
    <div className="evidence-actions"><Button variant="quiet" icon="open" onClick={openSource}>Open source{passage.page_number ? ` Â· page ${passage.page_number}` : ""}</Button></div>
    {error && <p className="inline-error" role="alert">{error}</p>}
  </article>;
}

