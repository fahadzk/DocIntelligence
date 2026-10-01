export interface DocumentItem {
  id: string;
  project_id: string;
  display_name: string;
  original_filename: string;
  file_type: "pdf" | "docx" | "txt" | "md";
  size_bytes: number;
  content_hash: string;
  status: "processing" | "ready" | "failed";
  stage: string;
  error_code: string | null;
  error_message: string | null;
  page_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface Segment {
  index: number;
  kind: string;
  label: string;
  page_number: number | null;
  paragraph_number: number | null;
  text: string;
}

export interface Chunk extends Segment {
  id: string;
  chunk_index: number;
  start_offset: number;
  end_offset: number;
  index_version: string;
}

export interface ChunkPage {
  items: Chunk[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
  start_page: number | null;
  end_page: number | null;
  page_count: number | null;
}

export interface ChunkQuery {
  pageNumber?: number;
  startPage?: number;
  endPage?: number;
  offset?: number;
  limit?: number;
}

export interface ImportOutcome {
  filename: string;
  document: DocumentItem | null;
  error_code: string | null;
  error_message: string | null;
}
