export interface ActivityEvent {
  id: string;
  project_id: string;
  document_id: string | null;
  action: string;
  level: "info" | "error";
  message: string;
  details: Record<string, unknown>;
  duration_ms: number | null;
  created_at: string;
}