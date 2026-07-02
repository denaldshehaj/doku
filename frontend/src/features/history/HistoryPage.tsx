/* Historiku im — personal Q&A/summary history with client-side search and
 * expandable rows (answer + sources + re-export for grounded answers). */
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronDown, Download, Search } from "lucide-react";
import { ApiError } from "@/api/client";
import { chatApi, historyApi } from "@/api/endpoints";
import type { HistoryRow } from "@/api/types";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Input, Select } from "@/components/ui/fields";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { PageHeader } from "@/components/shared/PageHeader";
import { useToast } from "@/providers/ToastProvider";
import { cx, formatDateTime, formatSeconds } from "@/lib/format";

const MODE_LABEL: Record<string, string> = {
  rag: "Pyetje (RAG)", no_rag: "Pa RAG", summary: "Përmbledhje",
};

function HistoryItem({ row }: { row: HistoryRow }) {
  const [open, setOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const { toast } = useToast();

  const onExport = async () => {
    setExporting(true);
    try {
      await chatApi.exportAnswer(row.id);
      toast("success", "U shkarkua", "Përgjigjja u eksportua në Word (.docx).");
    } catch (err) {
      toast("error", "Eksporti dështoi",
            err instanceof ApiError ? err.message : undefined);
    } finally {
      setExporting(false);
    }
  };

  return (
    <li>
      <button onClick={() => setOpen((v) => !v)} aria-expanded={open}
              className="flex w-full items-center gap-3 px-4 py-3 text-left hover:bg-slate-50 sm:px-5 dark:hover:bg-slate-800/50">
        <ChevronDown className={cx("h-4 w-4 shrink-0 text-slate-400 transition-transform",
                                   open && "rotate-180")} aria-hidden />
        <span className="min-w-0 flex-1 truncate text-sm text-slate-700 dark:text-slate-200">
          {row.question}
        </span>
        <Badge variant={row.mode === "summary" ? "brand" : "neutral"} className="shrink-0">
          {MODE_LABEL[row.mode] ?? row.mode}
        </Badge>
        <span className="hidden shrink-0 text-xs tabular-nums text-slate-400 sm:block dark:text-slate-500">
          {formatDateTime(row.created_at)}
        </span>
      </button>
      {open && (
        <div className="border-t border-slate-100 bg-slate-50/60 px-4 py-4 sm:px-12 dark:border-slate-800 dark:bg-slate-900/40">
          <p className="whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-300">
            {row.answer || "—"}
          </p>
          {row.sources.length > 0 && (
            <div className="mt-3 space-y-1">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Burimet:</p>
              {row.sources.map((s) => (
                <p key={s.n} className="text-xs text-slate-500 dark:text-slate-400">
                  [{s.n}] {s.title || s.filename} · {s.document_type} · faqe {s.page}{" "}
                  <span className="text-emerald-600 dark:text-emerald-400">({s.score.toFixed(2)})</span>
                </p>
              ))}
            </div>
          )}
          <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-slate-400 dark:text-slate-500">
            {row.response_time !== null && <span>⏱ {formatSeconds(row.response_time)}</span>}
            <span className="sm:hidden">{formatDateTime(row.created_at)}</span>
            {row.mode === "rag" && row.answer && (
              <button onClick={onExport} disabled={exporting}
                      className="inline-flex items-center gap-1 font-medium text-brand-700 hover:underline disabled:opacity-50 dark:text-brand-300">
                <Download className="h-3.5 w-3.5" aria-hidden />
                {exporting ? "Duke eksportuar…" : "Eksporto në Word"}
              </button>
            )}
          </div>
        </div>
      )}
    </li>
  );
}

export default function HistoryPage() {
  const [search, setSearch] = useState("");
  const [mode, setMode] = useState("");
  const history = useQuery({ queryKey: ["history", 200], queryFn: () => historyApi.list(200) });

  const filtered = useMemo(() => {
    if (!history.data) return [];
    const kw = search.trim().toLowerCase();
    return history.data.filter((r) =>
      (!mode || r.mode === mode) &&
      (!kw || r.question.toLowerCase().includes(kw) ||
        (r.answer ?? "").toLowerCase().includes(kw)));
  }, [history.data, search, mode]);

  return (
    <>
      <PageHeader title="Historiku im"
                  subtitle="Pyetjet, përgjigjet dhe përmbledhjet e tua të mëparshme." />

      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
          <Input aria-label="Kërko në historik" placeholder="Kërko në pyetje ose përgjigje…"
                 className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="sm:w-48">
          <Select aria-label="Filtro sipas llojit" value={mode}
                  onChange={(e) => setMode(e.target.value)}>
            <option value="">Të gjitha llojet</option>
            <option value="rag">Pyetje (RAG)</option>
            <option value="summary">Përmbledhje</option>
          </Select>
        </div>
      </div>

      <Card>
        {history.isPending ? (
          <div className="space-y-3 p-5">
            {[0, 1, 2, 3, 4].map((i) => <Skeleton key={i} className="h-8 w-full" />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState title={history.data?.length ? "Asnjë rezultat për filtrat e zgjedhur"
                                                  : "Ende pa aktivitet"}
                      description={history.data?.length
                        ? "Provo një kërkim tjetër ose pastro filtrat."
                        : "Pyetjet dhe përmbledhjet e tua do të shfaqen këtu."} />
        ) : (
          <ul className="divide-y divide-slate-100 dark:divide-slate-800">
            {filtered.map((r) => <HistoryItem key={r.id} row={r} />)}
          </ul>
        )}
      </Card>
    </>
  );
}
