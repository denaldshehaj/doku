/* Raporte & Statistika (admin) — KPI cards me delta ndaj periudhës paraardhëse,
 * grafikë të përdorimit, aktiviteti për përdorues, eksport CSV dhe version i
 * printueshëm (Print → Save as PDF). Çdo numër vjen nga të dhënat reale të
 * sistemit — asnjë metrikë e fabrikuar. */
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Download, FileCheck2, FileX2, Layers, MessagesSquare, NotebookPen,
  Printer, RefreshCw, ShieldCheck, Timer, TrendingDown, TrendingUp, Users,
} from "lucide-react";
import { ApiError } from "@/api/client";
import { reportsApi } from "@/api/endpoints";
import type { KpiValue } from "@/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Select } from "@/components/ui/fields";
import { EmptyState, Skeleton } from "@/components/ui/misc";
import { DonutChart, HBarChart, LineChart } from "@/components/charts/Charts";
import { TableShell, Td, Th, Tr } from "@/components/shared/DataTable";
import { PageHeader } from "@/components/shared/PageHeader";
import { useToast } from "@/providers/ToastProvider";
import { formatDateTime, formatPercent, formatSeconds } from "@/lib/format";

const PERIODS = [
  { value: 7, label: "7 ditët e fundit" },
  { value: 30, label: "30 ditët e fundit" },
  { value: 90, label: "90 ditët e fundit" },
  { value: 365, label: "Viti i fundit" },
];

function Delta({ kpi }: { kpi: KpiValue }) {
  if (kpi.delta_pct === null || kpi.delta_pct === undefined) return null;
  const up = kpi.delta_pct >= 0;
  const Icon = up ? TrendingUp : TrendingDown;
  return (
    <span className={`flex items-center gap-0.5 text-xs font-medium ${
      up ? "text-emerald-600 dark:text-emerald-400" : "text-red-500 dark:text-red-400"}`}>
      <Icon className="h-3.5 w-3.5" aria-hidden />
      {up ? "+" : ""}{kpi.delta_pct}%
      <span className="font-normal text-slate-400"> vs periudha paraardhëse</span>
    </span>
  );
}

function Kpi({ label, value, icon: Icon, delta, hint, loading }: {
  label: string;
  value: string | number | null | undefined;
  icon: typeof MessagesSquare;
  delta?: KpiValue;
  hint?: string;
  loading: boolean;
}) {
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate text-xs text-slate-500 dark:text-slate-400">{label}</p>
          {loading ? (
            <Skeleton className="mt-2 h-7 w-16" />
          ) : (
            <p className="mt-1 text-xl font-bold tabular-nums text-slate-900 dark:text-slate-50">
              {value ?? "—"}
            </p>
          )}
          {!loading && delta && <div className="mt-1"><Delta kpi={delta} /></div>}
          {!loading && hint && !delta && (
            <p className="mt-1 text-[11px] text-slate-400 dark:text-slate-500">{hint}</p>
          )}
        </div>
        <span className="rounded-lg bg-brand-50 p-2 text-brand-700 dark:bg-brand-950 dark:text-brand-300">
          <Icon className="h-4 w-4" aria-hidden />
        </span>
      </div>
    </Card>
  );
}

export default function ReportsPage() {
  const { toast } = useToast();
  const [days, setDays] = useState(30);
  const [username, setUsername] = useState("");
  const [exporting, setExporting] = useState(false);

  const report = useQuery({
    queryKey: ["reports", days, username],
    queryFn: () => reportsApi.get(days, username || undefined),
  });

  const exportCsv = async () => {
    setExporting(true);
    try {
      await reportsApi.exportCsv(days, username || undefined);
      toast("success", "Raporti u shkarkua (CSV)", "Hapet direkt në Excel.");
    } catch (err) {
      toast("error", "Eksporti dështoi", err instanceof ApiError ? err.message : undefined);
    } finally {
      setExporting(false);
    }
  };

  const d = report.data;
  const loading = report.isPending;
  const noData = d && d.kpi.questions.value === 0 && d.kpi.summaries.value === 0;

  return (
    <div id="report-root">
      <PageHeader title="Raporte & Statistika"
                  subtitle="Analiza e përdorimit të sistemit, performancës dhe cilësisë së përgjigjeve — nga të dhënat reale të regjistruara."
                  actions={
                    <span className="flex flex-wrap items-center gap-2 print:hidden">
                      <Button variant="outline" size="md" onClick={() => report.refetch()}
                              disabled={report.isFetching}>
                        <RefreshCw className={`h-4 w-4 ${report.isFetching ? "animate-spin" : ""}`} aria-hidden />
                        Rifresko
                      </Button>
                      <Button variant="outline" onClick={exportCsv} loading={exporting}>
                        <Download className="h-4 w-4" aria-hidden />
                        Eksporto CSV
                      </Button>
                      <Button onClick={() => window.print()}>
                        <Printer className="h-4 w-4" aria-hidden />
                        Printo / PDF
                      </Button>
                    </span>
                  } />

      {/* Filters */}
      <div className="mb-5 flex flex-col gap-3 sm:flex-row print:hidden">
        <div className="sm:w-56">
          <Select aria-label="Periudha" value={days}
                  onChange={(e) => setDays(Number(e.target.value))}>
            {PERIODS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
          </Select>
        </div>
        <div className="sm:w-56">
          <Select aria-label="Filtro sipas përdoruesit" value={username}
                  onChange={(e) => setUsername(e.target.value)}>
            <option value="">Të gjithë përdoruesit</option>
            {(d?.usernames ?? []).map((u) => <option key={u}>{u}</option>)}
          </Select>
        </div>
      </div>

      {/* Print header (visible only on paper) */}
      <div className="hidden print:block">
        <p className="text-sm text-slate-500">
          DOKU — Raport statistikash · {PERIODS.find((p) => p.value === days)?.label}
          {username && ` · Përdoruesi: ${username}`} · Gjeneruar: {d ? formatDateTime(d.generated_at) : ""}
        </p>
      </div>

      {noData ? (
        <Card>
          <EmptyState title="Ende pa aktivitet në këtë periudhë"
                      description="Kur përdoruesit të bëjnë pyetje dhe përmbledhje, statistikat shfaqen këtu." />
        </Card>
      ) : (
        <>
          {/* KPI row */}
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
            <Kpi label="Pyetje gjithsej" value={d?.kpi.questions.value}
                 icon={MessagesSquare} delta={d?.kpi.questions} loading={loading} />
            <Kpi label="Përgjigje të bazuara" value={d?.kpi.answered.value}
                 icon={FileCheck2} loading={loading}
                 hint="Me burime dhe citime" />
            <Kpi label="Refuzime" value={d?.kpi.refused.value}
                 icon={FileX2} delta={d?.kpi.refused} loading={loading} />
            <Kpi label="Norma e refuzimit" value={formatPercent(d?.kpi.refusal_rate)}
                 icon={ShieldCheck} loading={loading}
                 hint="Anti-halucinim: refuzon në vend që të shpikë" />
            <Kpi label="Koha mesatare" value={formatSeconds(d?.kpi.avg_response_time)}
                 icon={Timer} loading={loading}
                 hint={d?.kpi.p95_response_time ? `P95: ${formatSeconds(d.kpi.p95_response_time)}` : undefined} />
            <Kpi label="Përdorues aktivë" value={d?.kpi.active_users.value}
                 icon={Users} loading={loading}
                 hint={`${d?.kpi.summaries.value ?? "—"} përmbledhje · ${d?.kpi.exports_docx.value ?? "—"} eksporte`} />
          </div>

          {/* Charts row 1 */}
          <div className="mt-5 grid gap-5 xl:grid-cols-[1.6fr_1fr]">
            <Card>
              <CardHeader title="Pyetje sipas kohës"
                          subtitle="Pyetjet e bëra dhe refuzimet, ditë pas dite" />
              <CardBody>
                {loading ? <Skeleton className="h-44 w-full" /> : d && (
                  <LineChart ariaLabel="Grafiku i pyetjeve sipas ditëve"
                             labels={d.questions_per_day.map((r) => r.date)}
                             series={[
                               { name: "Pyetje", values: d.questions_per_day.map((r) => r.questions), area: true },
                               { name: "Refuzime", values: d.questions_per_day.map((r) => r.refused), color: "#e11d2e" },
                             ]} />
                )}
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Citime sipas tipit"
                          subtitle="Nga cilat lloje dokumentesh vijnë përgjigjet" />
              <CardBody>
                {loading ? <Skeleton className="h-44 w-full" /> : d && (
                  d.citations_by_type.length === 0
                    ? <EmptyState title="Ende pa citime" />
                    : <DonutChart ariaLabel="Citimet sipas tipit të dokumentit"
                                  data={d.citations_by_type} />
                )}
              </CardBody>
            </Card>
          </div>

          {/* Charts row 2 */}
          <div className="mt-5 grid gap-5 xl:grid-cols-2">
            <Card>
              <CardHeader title="Dokumentet më të përdorura"
                          subtitle="Sipas numrit të citimeve në përgjigje" />
              <CardBody>
                {loading ? <Skeleton className="h-40 w-full" /> : d && (
                  d.top_documents.length === 0
                    ? <EmptyState title="Ende pa dokumente të cituara" />
                    : <HBarChart ariaLabel="Dokumentet më të cituara"
                                 data={d.top_documents.map((t) => ({ label: t.title, count: t.count }))} />
                )}
              </CardBody>
            </Card>
            <Card>
              <CardHeader title="Koha e përgjigjes (trend)"
                          subtitle="Mesatarja ditore në sekonda" />
              <CardBody>
                {loading ? <Skeleton className="h-40 w-full" /> : d && (
                  <LineChart ariaLabel="Trendi i kohës së përgjigjes"
                             labels={d.response_time_per_day.map((r) => r.date)}
                             series={[{ name: "Koha mesatare (s)", area: true,
                                        values: d.response_time_per_day.map((r) => r.avg) }]} />
                )}
              </CardBody>
            </Card>
          </div>

          {/* Tables row */}
          <div className="mt-5 grid gap-5 xl:grid-cols-[1.4fr_1fr]">
            <Card>
              <CardHeader title="Aktiviteti sipas përdoruesit"
                          subtitle="Brenda periudhës së zgjedhur" />
              {loading ? (
                <div className="space-y-3 p-5">
                  {[0, 1, 2].map((i) => <Skeleton key={i} className="h-7 w-full" />)}
                </div>
              ) : d && d.by_user.length === 0 ? (
                <EmptyState title="Pa aktivitet" />
              ) : (
                <TableShell ariaLabel="Aktiviteti sipas përdoruesit">
                  <thead>
                    <tr>
                      <Th>Përdoruesi</Th>
                      <Th>Pyetje</Th>
                      <Th>Refuzime</Th>
                      <Th>Përmbledhje</Th>
                      <Th className="hidden sm:table-cell">Aktiviteti i fundit</Th>
                    </tr>
                  </thead>
                  <tbody>
                    {d?.by_user.map((u) => (
                      <Tr key={u.username}>
                        <Td className="font-medium text-slate-800 dark:text-slate-100">{u.username}</Td>
                        <Td className="tabular-nums">{u.questions}</Td>
                        <Td className="tabular-nums">{u.refused}</Td>
                        <Td className="tabular-nums">{u.summaries}</Td>
                        <Td className="hidden text-xs tabular-nums sm:table-cell">
                          {formatDateTime(u.last_activity)}
                        </Td>
                      </Tr>
                    ))}
                  </tbody>
                </TableShell>
              )}
            </Card>

            <div className="space-y-5">
              <Card>
                <CardHeader title="Pyetje sipas departamentit"
                            subtitle="Nga profili i përdoruesve" />
                <CardBody>
                  {loading ? <Skeleton className="h-24 w-full" /> : d && (
                    d.by_department.length === 0
                      ? <EmptyState title="Pa aktivitet" />
                      : <HBarChart ariaLabel="Pyetjet sipas departamentit"
                                   data={d.by_department.map((x) => ({
                                     label: x.label, count: x.questions }))} />
                  )}
                </CardBody>
              </Card>
              <Card>
                <CardHeader title="Korpusi"
                            subtitle={d ? `${d.documents_total} dokumente · ${d.chunks_total.toLocaleString("sq-AL")} copëza` : undefined} />
                <CardBody>
                  {loading ? <Skeleton className="h-24 w-full" /> : d && (
                    <HBarChart ariaLabel="Dokumentet sipas tipit"
                               data={d.corpus_by_type.map((c) => ({
                                 label: c.label, count: c.active + c.inactive }))} />
                  )}
                </CardBody>
              </Card>
              <Card>
                <CardHeader title="Aktiviteti i sistemit"
                            subtitle="Veprimet nga audit log-u" />
                <CardBody className="max-h-64 overflow-y-auto">
                  {loading ? <Skeleton className="h-24 w-full" /> : (
                    <ul className="space-y-1.5">
                      {d?.activity_by_action.map((a) => (
                        <li key={a.action} className="flex items-center justify-between gap-2 text-xs">
                          <Badge variant="neutral">{a.action}</Badge>
                          <span className="tabular-nums font-semibold text-slate-700 dark:text-slate-200">
                            {a.count.toLocaleString("sq-AL")}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </CardBody>
              </Card>
            </div>
          </div>

          <p className="mt-4 flex items-center gap-1.5 text-xs text-slate-400 dark:text-slate-500 print:hidden">
            <Layers className="h-3.5 w-3.5" aria-hidden />
            Të gjitha shifrat vijnë nga historiku real (chat_history, audit_logs,
            documents) — asnjë metrikë e simuluar.
            <NotebookPen className="ml-3 h-3.5 w-3.5" aria-hidden />
            Për metrikat e eksperimenteve RAG vs pa-RAG shiko faqen «Eksperimentet».
          </p>
        </>
      )}
    </div>
  );
}
