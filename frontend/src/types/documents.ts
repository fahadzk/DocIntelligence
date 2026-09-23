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

export interface ImportOutcome {
  filename: string;
  document: DocumentItem | null;
  error_code: string | null;
  error_message: string | null;
}
