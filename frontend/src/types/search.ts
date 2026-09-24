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
}
export interface Models { embeddings: ModelState; answers: ModelState }
export interface Answer {
  answer: string;
  supported: boolean;
  evidence: { number: number; passage: Passage }[];
}
