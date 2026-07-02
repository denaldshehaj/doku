/** Central HTTP client. Every request in the app goes through here so that
 * error shaping, 401 handling, and downloads behave identically everywhere.
 * Auth is an httpOnly session cookie — same-origin, sent automatically. */

export class ApiError extends Error {
  status: number;
  code: string | null;

  constructor(status: number, message: string, code: string | null = null) {
    super(message);
    this.status = status;
    this.code = code;
  }
}

/** Fired on any 401 so AuthProvider can drop the stale user and show /login. */
export const UNAUTHORIZED_EVENT = "doku:unauthorized";

function extractError(status: number, body: unknown): ApiError {
  // FastAPI errors are {detail: string} or {detail: {code, message}}.
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return new ApiError(status, detail);
    if (detail && typeof detail === "object") {
      const d = detail as { code?: string; message?: string };
      return new ApiError(status, d.message ?? "Gabim i panjohur.", d.code ?? null);
    }
  }
  return new ApiError(status, `Gabim serveri (${status}).`);
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { credentials: "same-origin", ...init });
  } catch {
    throw new ApiError(0, "Serveri lokal nuk po përgjigjet. Kontrollo që API-ja është e ndezur.");
  }

  if (res.status === 401) {
    window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
  }

  const isJson = res.headers.get("content-type")?.includes("application/json");
  const body = isJson ? await res.json().catch(() => null) : null;
  if (!res.ok) throw extractError(res.status, body);
  return body as T;
}

const json = (data: unknown): RequestInit => ({
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(data),
});

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: "POST", ...(data !== undefined ? json(data) : {}) }),
  patch: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PATCH", ...json(data) }),
  put: <T>(path: string, data: unknown) =>
    request<T>(path, { method: "PUT", ...json(data) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  postForm: <T>(path: string, form: FormData) =>
    request<T>(path, { method: "POST", body: form }),
};

/** Call a file endpoint (GET, or POST with an optional JSON body) and trigger
 * a browser download from the blob. The single download path for the app. */
export async function downloadFile(path: string, method: "GET" | "POST" = "POST",
                                   body?: unknown): Promise<void> {
  const res = await fetch(path, {
    method,
    credentials: "same-origin",
    ...(body !== undefined ? json(body) : {}),
  });
  if (res.status === 401) window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw extractError(res.status, body);
  }
  const disposition = res.headers.get("content-disposition") ?? "";
  // filename*=UTF-8''… wins over filename="…" when both are present.
  const utf8Match = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  const plainMatch = /filename="?([^";]+)"?/i.exec(disposition);
  const filename = utf8Match
    ? decodeURIComponent(utf8Match[1])
    : (plainMatch?.[1] ?? "doku-eksport");

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
