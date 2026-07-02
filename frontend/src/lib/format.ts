/** Small shared formatting helpers. */

/** Join class names, skipping falsy values. */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/** SQLite stores datetime('now') in UTC ("YYYY-MM-DD HH:MM:SS") — parse as UTC
 * and render in the user's local timezone. */
export function formatDateTime(sqliteUtc: string | null | undefined): string {
  if (!sqliteUtc) return "—";
  const date = new Date(sqliteUtc.replace(" ", "T") + "Z");
  if (Number.isNaN(date.getTime())) return sqliteUtc;
  return date.toLocaleString("sq-AL", {
    day: "2-digit", month: "2-digit", year: "numeric",
    hour: "2-digit", minute: "2-digit",
  });
}

export function formatDate(sqliteUtc: string | null | undefined): string {
  if (!sqliteUtc) return "—";
  const date = new Date(sqliteUtc.replace(" ", "T") + "Z");
  if (Number.isNaN(date.getTime())) return sqliteUtc.slice(0, 10);
  return date.toLocaleDateString("sq-AL", { day: "2-digit", month: "2-digit", year: "numeric" });
}

export function formatSeconds(s: number | null | undefined): string {
  if (s === null || s === undefined) return "—";
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${Math.round(s % 60)}s`;
}

export function formatPercent(v: number | null | undefined): string {
  if (v === null || v === undefined) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

export function truncate(text: string, max: number): string {
  return text.length > max ? text.slice(0, max - 1) + "…" : text;
}
