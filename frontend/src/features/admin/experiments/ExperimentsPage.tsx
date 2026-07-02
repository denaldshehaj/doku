/* Admin — RAG vs no-RAG experiment harness: batch runs with live progress,
 * aggregate metric cards, inline manual evaluation, CSV export for the thesis. */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Clock3, Download, Eye, FlaskConical, Play, Target, Trash2, TriangleAlert,
} from "lucide-react";
import { ApiError } from "@/api/client";
import { experimentsApi } from "@/api/endpoints";
import type { ExperimentRow } from "@/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Input } from "@/components/ui/fields";
import { Modal } from "@/components/ui/Modal";
import { EmptyState, ProgressBar, Skeleton } from "@/components/ui/misc";
import { TableShell, Td, Th, Tr } from "@/components/shared/DataTable";
import { StatCard } from "@/components/shared/StatCard";
import { PageHeader } from "@/components/shared/PageHeader";
import { useToast } from "@/providers/ToastProvider";
import { useTask } from "@/lib/useTask";
import { formatPercent, formatSeconds, truncate } from "@/lib/format";

function AnswersModal({ row, onClose }: { row: ExperimentRow; onClose: () => void }) {
  return (
    <Modal open onClose={onClose} title={truncate(row.question, 80)} width="max-w-4xl">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 p-4 dark:border-slate-700">
          <p className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-700 dark:text-slate-200">
            Pa RAG <Badge variant="warning">{formatSeconds(row.time_without_rag)}</Badge>
          </p>
          <p className="whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">
            {row.answer_without_rag || "—"}
          </p>
        </div>
        <div className="rounded-xl border border-brand-200 bg-brand-50/40 p-4 dark:border-brand-800 dark:bg-brand-950/40">
          <p className="mb-2 flex items-center justify-between text-sm font-semibold text-slate-700 dark:text-slate-200">
            Me RAG
            <span className="flex gap-1.5">
              {row.has_sources && <Badge variant="success">Me burime</Badge>}
              <Badge variant="brand">{formatSeconds(row.time_with_rag)}</Badge>
            </span>
          </p>
          <p className="whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">
            {row.answer_with_rag || "—"}
          </p>
        </div>
      </div>
    </Modal>
  );
}

/** One result row with inline manual-evaluation controls. */
function ResultRow({ row, onView, onDelete }: {
  row: ExperimentRow;
  onView: () => void;
  onDelete: () => void;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [accNo, setAccNo] = useState(row.manual_accuracy_without_rag?.toString() ?? "");
  const [accRag, setAccRag] = useState(row.manual_accuracy_with_rag?.toString() ?? "");
  const [hallNo, setHallNo] = useState(row.hallucination_without_rag ?? "");
  const [hallRag, setHallRag] = useState(row.hallucination_with_rag ?? "");
  const [notes, setNotes] = useState(row.notes ?? "");

  const dirty =
    accNo !== (row.manual_accuracy_without_rag?.toString() ?? "") ||
    accRag !== (row.manual_accuracy_with_rag?.toString() ?? "") ||
    hallNo !== (row.hallucination_without_rag ?? "") ||
    hallRag !== (row.hallucination_with_rag ?? "") ||
    notes !== (row.notes ?? "");

  const save = useMutation({
    mutationFn: () => experimentsApi.patch(row.id, {
      manual_accuracy_without_rag: accNo ? Number(accNo) : null,
      manual_accuracy_with_rag: accRag ? Number(accRag) : null,
      hallucination_without_rag: hallNo || null,
      hallucination_with_rag: hallRag || null,
      notes: notes || null,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["experiments"] });
      queryClient.invalidateQueries({ queryKey: ["experiments-summary"] });
      toast("success", "Vlerësimi u ruajt");
    },
    onError: (err) => toast("error", "Ruajtja dështoi",
                            err instanceof ApiError ? err.message : undefined),
  });

  const scoreSelect = (value: string, onChange: (v: string) => void, label: string) => (
    <select value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}
            className="h-8 w-14 rounded-md border border-slate-300 bg-white px-1 text-center text-xs dark:border-slate-700 dark:bg-slate-900">
      <option value="">—</option>
      {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}
    </select>
  );

  const hallSelect = (value: string, onChange: (v: string) => void, label: string) => (
    <select value={value} onChange={(e) => onChange(e.target.value)} aria-label={label}
            className="h-8 w-16 rounded-md border border-slate-300 bg-white px-1 text-xs dark:border-slate-700 dark:bg-slate-900">
      <option value="">—</option>
      <option value="Po">Po</option>
      <option value="Jo">Jo</option>
    </select>
  );

  return (
    <Tr>
      <Td className="max-w-[16rem]">
        <p className="truncate text-sm text-slate-700 dark:text-slate-200" title={row.question}>
          {row.question}
        </p>
        <p className="mt-0.5 text-[11px] text-slate-400">
          #{row.id} · {row.chunks_used ?? 0} copëza · {row.has_sources ? "me" : "pa"} citime
        </p>
      </Td>
      <Td className="whitespace-nowrap tabular-nums text-xs">
        {formatSeconds(row.time_without_rag)} / {formatSeconds(row.time_with_rag)}
      </Td>
      <Td>
        <span className="flex items-center gap-1">
          {scoreSelect(accNo, setAccNo, `Saktësia pa RAG #${row.id}`)}
          {scoreSelect(accRag, setAccRag, `Saktësia me RAG #${row.id}`)}
        </span>
      </Td>
      <Td>
        <span className="flex items-center gap-1">
          {hallSelect(hallNo, setHallNo, `Halucinacion pa RAG #${row.id}`)}
          {hallSelect(hallRag, setHallRag, `Halucinacion me RAG #${row.id}`)}
        </span>
      </Td>
      <Td className="hidden xl:table-cell">
        <input value={notes} onChange={(e) => setNotes(e.target.value)}
               aria-label={`Shënime #${row.id}`} placeholder="Shënime…"
               className="h-8 w-36 rounded-md border border-slate-300 bg-white px-2 text-xs dark:border-slate-700 dark:bg-slate-900" />
      </Td>
      <Td>
        <div className="flex items-center justify-end gap-0.5">
          {dirty && (
            <Button size="sm" variant="secondary" onClick={() => save.mutate()}
                    loading={save.isPending}>
              Ruaj
            </Button>
          )}
          <button onClick={onView} title="Shiko përgjigjet" aria-label={`Shiko përgjigjet #${row.id}`}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800">
            <Eye className="h-4 w-4" aria-hidden />
          </button>
          <button onClick={onDelete} title="Fshi" aria-label={`Fshi rezultatin #${row.id}`}
                  className="rounded-lg p-1.5 text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950">
            <Trash2 className="h-4 w-4" aria-hidden />
          </button>
        </div>
      </Td>
    </Tr>
  );
}

export default function ExperimentsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [customQuestion, setCustomQuestion] = useState("");
  const [viewing, setViewing] = useState<ExperimentRow | null>(null);
  const [deleting, setDeleting] = useState<ExperimentRow | null>(null);
  const [confirmBatch, setConfirmBatch] = useState(false);

  const results = useQuery({ queryKey: ["experiments"], queryFn: () => experimentsApi.list() });
  const samples = useQuery({ queryKey: ["experiment-samples"], queryFn: experimentsApi.samples });
  const summary = useQuery({ queryKey: ["experiments-summary"], queryFn: experimentsApi.summary });

  const refresh = () => {
    queryClient.invalidateQueries({ queryKey: ["experiments"] });
    queryClient.invalidateQueries({ queryKey: ["experiments-summary"] });
  };

  const runner = useTask((t) => {
    refresh();
    if (t.status === "done") {
      const r = t.result as { done?: number; failed?: { question: string; error: string }[] } | null;
      const failed = r?.failed?.length ?? 0;
      toast(failed ? "info" : "success", `U ekzekutuan ${r?.done ?? 0} pyetje`,
            failed ? `${failed} dështuan — kontrollo Ollama-n.` : undefined);
    } else {
      toast("error", "Eksperimenti dështoi", t.error ?? undefined);
    }
  });

  const start = async (questions: string[]) => {
    try {
      runner.track(await experimentsApi.run(questions));
    } catch (err) {
      toast("error", "Nuk u nis eksperimenti",
            err instanceof ApiError ? err.message : undefined);
    }
  };

  const remove = useMutation({
    mutationFn: (id: number) => experimentsApi.delete(id),
    onSuccess: () => {
      refresh();
      toast("success", "Rezultati u fshi");
      setDeleting(null);
    },
    onError: () => setDeleting(null),
  });

  const exportCsv = async () => {
    try {
      await experimentsApi.exportCsv();
      toast("success", "CSV u shkarkua");
    } catch (err) {
      toast("error", "Eksporti dështoi", err instanceof ApiError ? err.message : undefined);
    }
  };

  const s = summary.data;
  const nSamples = samples.data?.questions.length ?? 0;
  const estSeconds = (samples.data?.avg_run_seconds ?? 90) * nSamples;

  return (
    <>
      <PageHeader title="Eksperimente: RAG kundrejt pa-RAG"
                  subtitle="Krahaso përgjigjet me dhe pa RAG, vlerëso manualisht saktësinë e halucinacionin, dhe eksporto për kapitullin e rezultateve."
                  actions={
                    <Button variant="outline" onClick={exportCsv}
                            disabled={!results.data?.length}>
                      <Download className="h-4 w-4" aria-hidden />
                      Eksporto CSV
                    </Button>
                  } />

      {/* Aggregate metrics (auto-measured + manual where evaluated) */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Pyetje të ekzekutuara" value={s?.total} icon={FlaskConical}
                  loading={summary.isPending} />
        <StatCard label="Koha mesatare (pa / me RAG)"
                  value={s ? `${formatSeconds(s.avg_time_without_rag)} / ${formatSeconds(s.avg_time_with_rag)}` : undefined}
                  icon={Clock3} loading={summary.isPending} />
        <StatCard label="Saktësia mesatare (pa / me RAG)"
                  value={s ? `${s.avg_accuracy_without_rag ?? "—"} / ${s.avg_accuracy_with_rag ?? "—"}` : undefined}
                  icon={Target} loading={summary.isPending}
                  hint="Vlerësim manual 1–5" />
        <StatCard label="Halucinacione (pa / me RAG)"
                  value={s ? `${formatPercent(s.hallucination_rate_without_rag)} / ${formatPercent(s.hallucination_rate_with_rag)}` : undefined}
                  icon={TriangleAlert} loading={summary.isPending}
                  hint="Nga vlerësimi manual Po/Jo" />
      </div>

      {/* Run controls */}
      <Card className="mt-6">
        <CardHeader title="Ekzekuto eksperiment"
                    subtitle={`${nSamples} pyetje testuese në tests/sample_questions.csv`} />
        <CardBody className="space-y-4">
          {runner.task && runner.running ? (
            <ProgressBar value={runner.task.progress}
                         label={runner.task.message || "Duke ekzekutuar…"} />
          ) : (
            <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
              <Button onClick={() => setConfirmBatch(true)} disabled={nSamples === 0}>
                <Play className="h-4 w-4" aria-hidden />
                Ekzekuto të gjitha pyetjet testuese
              </Button>
              <div className="flex flex-1 items-end gap-2">
                <div className="flex-1">
                  <Input label="Ose një pyetje e vetme" value={customQuestion}
                         placeholder="Shkruaj pyetjen…"
                         onChange={(e) => setCustomQuestion(e.target.value)} />
                </div>
                <Button variant="outline"
                        disabled={!customQuestion.trim()}
                        onClick={() => { start([customQuestion.trim()]); setCustomQuestion(""); }}>
                  Ekzekuto
                </Button>
              </div>
            </div>
          )}
        </CardBody>
      </Card>

      {/* Results table */}
      <Card className="mt-6">
        <CardHeader title="Rezultatet"
                    subtitle="Vlerëso saktësinë (1–5) dhe halucinacionin (Po/Jo) për secilën përgjigje — kolonat: pa RAG / me RAG" />
        {results.isPending ? (
          <div className="space-y-3 p-5">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-9 w-full" />)}
          </div>
        ) : !results.data?.length ? (
          <EmptyState title="Ende pa rezultate"
                      description="Ekzekuto pyetjet testuese ose një pyetje të vetme më sipër." />
        ) : (
          <TableShell ariaLabel="Rezultatet e eksperimenteve">
            <thead>
              <tr>
                <Th>Pyetja</Th>
                <Th>Koha (pa/me)</Th>
                <Th>Saktësia (pa/me)</Th>
                <Th>Halucinacion (pa/me)</Th>
                <Th className="hidden xl:table-cell">Shënime</Th>
                <Th><span className="sr-only">Veprime</span></Th>
              </tr>
            </thead>
            <tbody>
              {results.data.map((r) => (
                <ResultRow key={`${r.id}-${r.notes}-${r.manual_accuracy_with_rag}`} row={r}
                           onView={() => setViewing(r)} onDelete={() => setDeleting(r)} />
              ))}
            </tbody>
          </TableShell>
        )}
      </Card>

      {viewing && <AnswersModal row={viewing} onClose={() => setViewing(null)} />}
      <ConfirmDialog open={confirmBatch}
                     title="Ekzekuto të gjitha pyetjet testuese?"
                     message={
                       <>
                         Do të ekzekutohen <strong>{nSamples} pyetje</strong>, secila dy herë
                         (me dhe pa RAG), me modelin lokal. Kohëzgjatja e parashikuar:{" "}
                         <strong>~{formatSeconds(estSeconds)}</strong>. Mund të vazhdosh të
                         përdorësh sistemin ndërkohë.
                       </>
                     }
                     confirmLabel="Nis eksperimentin"
                     onConfirm={() => {
                       setConfirmBatch(false);
                       if (samples.data) start(samples.data.questions);
                     }}
                     onCancel={() => setConfirmBatch(false)} />
      <ConfirmDialog open={deleting !== null} danger
                     title="Fshi rezultatin?"
                     message={<>Rezultati #{deleting?.id} do të fshihet përfundimisht.</>}
                     confirmLabel="Fshi"
                     loading={remove.isPending}
                     onConfirm={() => deleting && remove.mutate(deleting.id)}
                     onCancel={() => setDeleting(null)} />
    </>
  );
}
