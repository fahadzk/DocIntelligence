export interface Passage {
  id: string;
  project_id: string;
  document_id: string;
  display_name: string;
  file_type: string;
  label: string;
  page_number: number | null;
  paragraph_number: number | null;
  text: string;
  match_type?: string;
  segment_index?: number;
  chunk_index?: number;
  start_offset?: number;
  end_offset?: number;
  index_version?: string;
}
export interface IndexState {
  document_id: string;
  display_name: string;
  document_status: string;
  status: string | null;
  stage: string | null;
  error_message: string | null;
}
export interface ModelState {
  status: "not_installed" | "downloading" | "ready" | "failed";
  error: string | null;
  name: string;
  size_mb: number;
  source: string;
  models?: { id: string; name: string }[];
}
export interface Models { embeddings: ModelState; answers: ModelState }
export interface Answer {
  answer: string;
  supported: boolean;
  evidence: { number: number; passage: Passage }[];
}


