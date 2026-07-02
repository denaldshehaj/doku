/** Shared API types — mirrors api/schemas.py on the FastAPI side. */

export type Role = "admin" | "punonjes";

export interface User {
  id: number;
  username: string;
  full_name: string;
  role: Role;
  must_change_password: boolean;
}

export interface Meta {
  document_types: string[];
  institutions: string[];
  upload_types: string[];
  summary_formats: string[];
  min_similarity: number;
  refusal_message: string;
}

export interface DashboardStats {
  active_documents: number;
  total_documents: number;
  chunks: number;
  my_questions: number;
  users_count: number | null;
}

export interface SystemStatus {
  ollama_online: boolean;
  active_model: string;
  models: string[];
}

export interface Source {
  n: number;
  filename: string;
  title: string;
  document_type: string;
  institution: string;
  page: number;
  score: number;
  fragment: string;
}

export interface Answer {
  row_id: number;
  text: string;
  refused: boolean;
  sources: Source[];
  top_score: number;
  response_time: number;
  chunks_used: number;
  min_similarity: number;
}

export interface AskPayload {
  question: string;
  document_id?: number | null;
  doc_type?: string | null;
  institution?: string | null;
  year?: number | null;
  title_kw?: string | null;
}

export interface DocumentRow {
  id: number;
  filename: string;
  original_filename: string | null;
  title: string | null;
  institution: string | null;
  document_type: string | null;
  year: number | null;
  description: string | null;
  uploaded_by: string | null;
  status: "active" | "inactive";
  num_pages: number;
  total_chunks: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentFilters {
  document_types: string[];
  institutions: string[];
  years: number[];
}

export interface SummaryResult {
  document_id: number;
  title: string;
  filename: string;
  format: string;
  summary: string;
}

export interface HistoryRow {
  id: number;
  question: string;
  answer: string | null;
  mode: "rag" | "no_rag" | "summary";
  selected_document_id: number | null;
  sources: Source[];
  response_time: number | null;
  exported_to_word: boolean;
  created_at: string;
}

export interface UserRow {
  id: number;
  username: string;
  full_name: string;
  department: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface AuditRow {
  username: string | null;
  action: string;
  details: string | null;
  created_at: string;
}

export interface ExperimentRow {
  id: number;
  question: string;
  answer_without_rag: string | null;
  answer_with_rag: string | null;
  time_without_rag: number | null;
  time_with_rag: number | null;
  chunks_used: number | null;
  has_sources: boolean;
  manual_accuracy_without_rag: number | null;
  manual_accuracy_with_rag: number | null;
  hallucination_without_rag: string | null;
  hallucination_with_rag: string | null;
  notes: string | null;
  created_at: string;
}

export interface ExperimentSummary {
  total: number;
  avg_time_without_rag: number | null;
  avg_time_with_rag: number | null;
  avg_accuracy_without_rag: number | null;
  avg_accuracy_with_rag: number | null;
  hallucination_rate_without_rag: number | null;
  hallucination_rate_with_rag: number | null;
  with_sources_rate: number | null;
}

export interface TaskInfo {
  id: string;
  name: string;
  status: "running" | "done" | "error";
  progress: number;
  message: string;
  result: Record<string, unknown> | null;
  error: string | null;
}

// --- Reports (admin) --------------------------------------------------------

export interface KpiValue {
  value: number;
  delta_pct?: number | null;
}

export interface ReportsData {
  period_days: number;
  filter_username: string | null;
  generated_at: string;
  kpi: {
    questions: KpiValue;
    answered: KpiValue;
    refused: KpiValue;
    refusal_rate: number | null;
    summaries: KpiValue;
    exports_docx: KpiValue;
    active_users: KpiValue;
    avg_response_time: number | null;
    p95_response_time: number | null;
  };
  documents_total: number;
  chunks_total: number;
  questions_per_day: { date: string; questions: number; refused: number }[];
  response_time_per_day: { date: string; avg: number }[];
  citations_by_type: { label: string; count: number }[];
  top_documents: { title: string; count: number }[];
  by_user: {
    username: string;
    questions: number;
    refused: number;
    summaries: number;
    last_activity: string;
  }[];
  by_department: { label: string; questions: number; refused: number }[];
  corpus_by_type: { label: string; active: number; inactive: number }[];
  activity_by_action: { action: string; count: number }[];
  usernames: string[];
}
