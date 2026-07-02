/** Typed endpoint functions, grouped by domain. One place to see the whole
 * API surface the frontend consumes. */
import { api, downloadFile } from "./client";
import type {
  Answer, AskPayload, AuditRow, DashboardStats, DocumentFilters, DocumentRow,
  ExperimentRow, ExperimentSummary, HistoryRow, Meta, ReportsData,
  SummaryResult, SystemStatus, TaskInfo, User, UserRow,
} from "./types";

// --- Auth --------------------------------------------------------------------
export const authApi = {
  login: (username: string, password: string) =>
    api.post<User>("/api/auth/login", { username, password }),
  logout: () => api.post<{ ok: boolean }>("/api/auth/logout"),
  /** 200 with the user, or 200/null when no session exists (no console 401). */
  me: () => api.get<User | null>("/api/auth/me"),
  changePassword: (newPassword: string) =>
    api.post<User>("/api/auth/change-password", { new_password: newPassword }),
};

// --- Meta / dashboard / system -------------------------------------------------
export const metaApi = {
  meta: () => api.get<Meta>("/api/meta"),
  dashboard: () => api.get<DashboardStats>("/api/dashboard"),
  systemStatus: () => api.get<SystemStatus>("/api/system/status"),
  setModel: (model: string) =>
    api.put<{ active_model: string }>("/api/system/model", { model }),
};

// --- Chat / RAG -----------------------------------------------------------------
export interface StreamCallbacks {
  onDelta: (text: string) => void;
  onRefusal: (answer: Answer) => void;
  onDone: (answer: Answer) => void;
  onError: (message: string, code?: string) => void;
}

export const chatApi = {
  ask: (payload: AskPayload) => api.post<Answer>("/api/chat/ask", payload),
  exportAnswer: (rowId: number) => downloadFile(`/api/chat/${rowId}/export`),

  /** Streaming ask over SSE (fetch + ReadableStream — EventSource can't POST).
   * Exactly one terminal callback fires: onRefusal, onDone or onError. */
  askStream: async (payload: AskPayload, cb: StreamCallbacks): Promise<void> => {
    let res: Response;
    try {
      res = await fetch("/api/chat/ask-stream", {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch {
      cb.onError("Serveri lokal nuk po përgjigjet.");
      return;
    }
    if (!res.ok || !res.body) {
      const body = await res.json().catch(() => null);
      const detail = (body as { detail?: unknown } | null)?.detail;
      cb.onError(typeof detail === "string" ? detail : `Gabim serveri (${res.status}).`);
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let terminal = false;

    const handle = (frame: string) => {
      let event = "message";
      const dataLines: string[] = [];
      for (const line of frame.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7).trim();
        else if (line.startsWith("data: ")) dataLines.push(line.slice(6));
      }
      if (dataLines.length === 0) return;
      const data = JSON.parse(dataLines.join("\n"));
      if (event === "delta") {
        cb.onDelta((data as { t: string }).t);
      } else if (event === "refusal") {
        terminal = true;
        cb.onRefusal(data as Answer);
      } else if (event === "done") {
        terminal = true;
        cb.onDone(data as Answer);
      } else if (event === "error") {
        terminal = true;
        const e = data as { message?: string; code?: string };
        cb.onError(e.message ?? "Gabim gjatë gjenerimit.", e.code);
      }
    };

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx: number;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          if (frame.trim()) handle(frame);
        }
      }
      if (!terminal) cb.onError("Lidhja u mbyll pa përfunduar përgjigjen.");
    } catch {
      if (!terminal) cb.onError("Lidhja me serverin u ndërpre gjatë përgjigjes.");
    }
  },
};

// --- Summaries -------------------------------------------------------------------
export const summariesApi = {
  generate: (documentId: number, format: string) =>
    api.post<SummaryResult>("/api/summaries", { document_id: documentId, format }),
  export: (documentId: number, format: string, summary: string) =>
    downloadFile("/api/summaries/export", "POST",
                 { document_id: documentId, format, summary }),
};

// --- History ------------------------------------------------------------------------
export const historyApi = {
  list: (limit = 100) => api.get<HistoryRow[]>(`/api/history?limit=${limit}`),
};

// --- Documents -------------------------------------------------------------------------
export interface DocumentQuery {
  activeOnly?: boolean;
  docType?: string;
  year?: number;
  institution?: string;
  q?: string;
}

export const documentsApi = {
  list: (query: DocumentQuery = {}) => {
    const params = new URLSearchParams();
    if (query.activeOnly) params.set("active_only", "true");
    if (query.docType) params.set("doc_type", query.docType);
    if (query.year) params.set("year", String(query.year));
    if (query.institution) params.set("institution", query.institution);
    if (query.q) params.set("q", query.q);
    const qs = params.toString();
    return api.get<DocumentRow[]>(`/api/documents${qs ? `?${qs}` : ""}`);
  },
  filters: () => api.get<DocumentFilters>("/api/documents/filters"),
  upload: (form: FormData) => api.postForm<DocumentRow>("/api/documents", form),
  patch: (id: number, data: Partial<Pick<DocumentRow,
    "title" | "institution" | "document_type" | "year" | "description">>) =>
    api.patch<DocumentRow>(`/api/documents/${id}`, data),
  setStatus: (id: number, status: "active" | "inactive") =>
    api.post<DocumentRow>(`/api/documents/${id}/status`, { status }),
  delete: (id: number) => api.delete<{ ok: boolean }>(`/api/documents/${id}`),
  reindex: (id: number) => api.post<{ chunks: number }>(`/api/documents/${id}/reindex`),
  reindexAll: () => api.post<TaskInfo>("/api/documents/reindex-all"),
  download: (id: number) => downloadFile(`/api/documents/${id}/file`, "GET"),
  inlineUrl: (id: number) => `/api/documents/${id}/file?inline=true`,
};

// --- Users (admin) ---------------------------------------------------------------------
export const usersApi = {
  list: () => api.get<UserRow[]>("/api/users"),
  create: (data: { username: string; password: string; full_name: string;
                   department: string; role: string }) =>
    api.post<UserRow>("/api/users", data),
  patch: (username: string,
          data: { full_name?: string; department?: string; role?: string;
                  is_active?: boolean }) =>
    api.patch<UserRow>(`/api/users/${encodeURIComponent(username)}`, data),
  setPassword: (username: string, password: string, mustChange: boolean) =>
    api.post<{ ok: boolean }>(`/api/users/${encodeURIComponent(username)}/password`,
      { password, must_change: mustChange }),
  resetPassword: (username: string) =>
    api.post<{ temporary_password: string }>(
      `/api/users/${encodeURIComponent(username)}/reset-password`),
};

// --- Audit (admin) -----------------------------------------------------------------------
export const auditApi = {
  list: (limit = 500) => api.get<AuditRow[]>(`/api/audit?limit=${limit}`),
};

// --- Experiments (admin) --------------------------------------------------------------------
export const experimentsApi = {
  list: (limit = 500) => api.get<ExperimentRow[]>(`/api/experiments?limit=${limit}`),
  samples: () => api.get<{ questions: string[]; avg_run_seconds: number }>("/api/experiments/samples"),
  summary: () => api.get<ExperimentSummary>("/api/experiments/summary"),
  run: (questions: string[]) => api.post<TaskInfo>("/api/experiments/run", { questions }),
  patch: (id: number, data: Partial<Pick<ExperimentRow,
    "manual_accuracy_without_rag" | "manual_accuracy_with_rag" |
    "hallucination_without_rag" | "hallucination_with_rag" | "notes">>) =>
    api.patch<ExperimentRow>(`/api/experiments/${id}`, data),
  delete: (id: number) => api.delete<{ ok: boolean }>(`/api/experiments/${id}`),
  exportCsv: () => downloadFile("/api/experiments/export.csv", "GET"),
};

// --- Reports (admin) ---------------------------------------------------------------------------
export const reportsApi = {
  get: (days: number, username?: string) => {
    const params = new URLSearchParams({ days: String(days) });
    if (username) params.set("username", username);
    return api.get<ReportsData>(`/api/reports?${params}`);
  },
  exportCsv: (days: number, username?: string) => {
    const params = new URLSearchParams({ days: String(days) });
    if (username) params.set("username", username);
    return downloadFile(`/api/reports/export.csv?${params}`, "GET");
  },
};

// --- Tasks -------------------------------------------------------------------------------------
export const tasksApi = {
  get: (id: string) => api.get<TaskInfo>(`/api/tasks/${id}`),
};
