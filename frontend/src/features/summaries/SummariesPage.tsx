/* Përmbledhje — pick an active document + one of the 4 formats, generate with
 * the local LLM, export to Word. Result carries the verification disclaimer. */
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, NotebookPen } from "lucide-react";
import { ApiError } from "@/api/client";
import { documentsApi, metaApi, summariesApi } from "@/api/endpoints";
import type { SummaryResult } from "@/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Select } from "@/components/ui/fields";
import { Alert, EmptyState, Skeleton } from "@/components/ui/misc";
import { PageHeader } from "@/components/shared/PageHeader";
import { useToast } from "@/providers/ToastProvider";
import { cx } from "@/lib/format";

const FORMAT_HINTS: Record<string, string> = {
  "E shkurtër": "3–4 fjali me thelbin e dokumentit.",
  "E detajuar": "Përmbledhje e plotë dhe gjithëpërfshirëse.",
  "Pika kryesore": "Listë me pikat më të rëndësishme.",
  "Për vendimmarrje institucionale": "Qëllimi, detyrimet kryesore dhe rekomandime.",
};

export default function SummariesPage() {
  const { toast } = useToast();
  const [documentId, setDocumentId] = useState("");
  const [format, setFormat] = useState("E shkurtër");
  const [result, setResult] = useState<SummaryResult | null>(null);
  const [exporting, setExporting] = useState(false);

  const meta = useQuery({ queryKey: ["meta"], queryFn: metaApi.meta });
  const docs = useQuery({
    queryKey: ["documents", "active"],
    queryFn: () => documentsApi.list({ activeOnly: true }),
  });

  const generate = useMutation({
    mutationFn: () => summariesApi.generate(Number(documentId), format),
    onSuccess: setResult,
    onError: (err) => {
      const isOllama = err instanceof ApiError && err.code === "ollama_unavailable";
      toast("error", isOllama ? "Modeli lokal nuk është aktiv" : "Gjenerimi dështoi",
            err instanceof ApiError ? err.message : "Provo përsëri.");
    },
  });

  const onExport = async () => {
    if (!result) return;
    setExporting(true);
    try {
      await summariesApi.export(result.document_id, result.format, result.summary);
      toast("success", "U shkarkua", "Përmbledhja u eksportua në Word (.docx).");
    } catch (err) {
      toast("error", "Eksporti dështoi", err instanceof Error ? err.message : undefined);
    } finally {
      setExporting(false);
    }
  };

  const formats = meta.data?.summary_formats ?? Object.keys(FORMAT_HINTS);
  const noActiveDocs = docs.isSuccess && docs.data.length === 0;

  return (
    <>
      <PageHeader title="Përmbledhje Dokumenti"
                  subtitle="Gjenero një përmbledhje të strukturuar në shqip për një dokument të korpusit." />

      {noActiveDocs ? (
        <Card>
          <EmptyState title="Nuk ka dokumente aktive"
                      description="Administratori duhet të ngarkojë dhe aktivizojë dokumente më parë." />
        </Card>
      ) : (
        <div className="grid gap-5 lg:grid-cols-[22rem_1fr]">
          <Card className="self-start">
            <CardHeader title="Zgjedhjet" subtitle="Dokumenti dhe formati i përmbledhjes" />
            <CardBody className="space-y-4">
              {docs.isPending ? (
                <Skeleton className="h-10 w-full" />
              ) : (
                <Select label="Dokumenti" value={documentId}
                        onChange={(e) => setDocumentId(e.target.value)}>
                  <option value="">— Zgjidh dokumentin —</option>
                  {(docs.data ?? []).map((d) => (
                    <option key={d.id} value={d.id}>{d.title || d.filename}</option>
                  ))}
                </Select>
              )}

              <fieldset>
                <legend className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300">
                  Formati
                </legend>
                <div className="space-y-2">
                  {formats.map((f) => (
                    <label key={f}
                           className={cx(
                             "flex cursor-pointer items-start gap-2.5 rounded-xl border p-3 transition-colors",
                             format === f
                               ? "border-brand-400 bg-brand-50 dark:border-brand-600 dark:bg-brand-950"
                               : "border-slate-200 hover:border-slate-300 dark:border-slate-700")}>
                      <input type="radio" name="format" value={f} checked={format === f}
                             onChange={() => setFormat(f)} className="mt-1 accent-brand-700" />
                      <span>
                        <span className="block text-sm font-medium text-slate-800 dark:text-slate-100">{f}</span>
                        <span className="block text-xs text-slate-500 dark:text-slate-400">
                          {FORMAT_HINTS[f] ?? ""}
                        </span>
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>

              <Button className="w-full" size="lg" loading={generate.isPending}
                      disabled={!documentId} onClick={() => generate.mutate()}>
                <NotebookPen className="h-4 w-4" aria-hidden />
                Gjenero përmbledhjen
              </Button>
              {generate.isPending && (
                <p className="text-center text-xs text-slate-400" role="status">
                  Dokumenti po lexohet dhe përmblidhet nga modeli lokal — mund të
                  zgjasë deri në disa minuta për dokumente të gjata.
                </p>
              )}
            </CardBody>
          </Card>

          <Card className="self-start">
            <CardHeader title={result ? result.title || result.filename : "Rezultati"}
                        subtitle={result ? undefined : "Përmbledhja do të shfaqet këtu"}
                        actions={result && (
                          <>
                            <Badge variant="brand">{result.format}</Badge>
                            <Button variant="outline" size="sm" onClick={onExport} loading={exporting}>
                              <Download className="h-4 w-4" aria-hidden /> .docx
                            </Button>
                          </>
                        )} />
            <CardBody>
              {generate.isPending ? (
                <div className="space-y-2.5">
                  {[0, 1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} className={i === 4 ? "h-4 w-2/3" : "h-4 w-full"} />
                  ))}
                </div>
              ) : result ? (
                <>
                  <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700 dark:text-slate-300">
                    {result.summary}
                  </p>
                  <div className="mt-4">
                    <Alert variant="info">
                      Kjo përmbledhje është gjeneruar automatikisht dhe duhet
                      verifikuar me dokumentin origjinal.
                    </Alert>
                  </div>
                </>
              ) : (
                <EmptyState title="Ende pa përmbledhje"
                            description="Zgjidh një dokument dhe formatin, pastaj shtyp «Gjenero përmbledhjen»." />
              )}
            </CardBody>
          </Card>
        </div>
      )}
    </>
  );
}
