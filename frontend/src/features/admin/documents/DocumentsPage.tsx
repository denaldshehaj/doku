/* Admin — document corpus management: upload, filters, status toggle, reindex
 * (one / all with live progress), metadata editing, preview, delete. */
import { useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Download, Eye, FilePlus2, Pencil, Power, RefreshCw, Search, Trash2,
} from "lucide-react";
import { ApiError } from "@/api/client";
import { documentsApi, metaApi } from "@/api/endpoints";
import type { DocumentRow } from "@/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { Input, Select } from "@/components/ui/fields";
import { EmptyState, ProgressBar, Skeleton } from "@/components/ui/misc";
import { TableShell, Td, Th, Tr } from "@/components/shared/DataTable";
import { PageHeader } from "@/components/shared/PageHeader";
import { useToast } from "@/providers/ToastProvider";
import { useTask } from "@/lib/useTask";
import { formatDate } from "@/lib/format";
import { EditMetadataModal, PreviewModal, UploadModal } from "./DocumentModals";

export default function DocumentsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [fType, setFType] = useState("");
  const [fInst, setFInst] = useState("");
  const [fYear, setFYear] = useState("");
  const [uploadOpen, setUploadOpen] = useState(false);
  const [editing, setEditing] = useState<DocumentRow | null>(null);
  const [previewing, setPreviewing] = useState<DocumentRow | null>(null);
  const [deleting, setDeleting] = useState<DocumentRow | null>(null);
  const [reindexingId, setReindexingId] = useState<number | null>(null);

  const meta = useQuery({ queryKey: ["meta"], queryFn: metaApi.meta });
  const filters = useQuery({ queryKey: ["doc-filters"], queryFn: documentsApi.filters });
  const docs = useQuery({
    queryKey: ["documents", { fType, fInst, fYear, search }],
    queryFn: () => documentsApi.list({
      docType: fType || undefined, institution: fInst || undefined,
      year: fYear ? Number(fYear) : undefined, q: search || undefined,
    }),
  });

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ["documents"] });
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    queryClient.invalidateQueries({ queryKey: ["doc-filters"] });
  };

  const reindexAll = useTask((t) => {
    invalidate();
    if (t.status === "done") {
      const r = t.result as { documents?: number; chunks?: number } | null;
      toast("success", "Korpusi u riindeksua",
            `${r?.documents ?? "?"} dokumente, ${r?.chunks ?? "?"} copëza.`);
    } else {
      toast("error", "Riindeksimi dështoi", t.error ?? undefined);
    }
  });

  const startReindexAll = async () => {
    try {
      reindexAll.track(await documentsApi.reindexAll());
    } catch (err) {
      toast("error", "Nuk u nis riindeksimi",
            err instanceof ApiError ? err.message : undefined);
    }
  };

  const setStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: "active" | "inactive" }) =>
      documentsApi.setStatus(id, status),
    onSuccess: (doc) => {
      invalidate();
      toast("success", doc.status === "active" ? "Dokumenti u aktivizua" : "Dokumenti u çaktivizua",
            doc.title || doc.filename);
    },
    onError: (err) => toast("error", "Veprimi dështoi",
                            err instanceof ApiError ? err.message : undefined),
  });

  const reindexOne = useMutation({
    mutationFn: (id: number) => documentsApi.reindex(id),
    onMutate: (id) => setReindexingId(id),
    onSettled: () => setReindexingId(null),
    onSuccess: (r) => {
      invalidate();
      toast("success", "U riindeksua", `${r.chunks} copëza.`);
    },
    onError: (err) => toast("error", "Riindeksimi dështoi",
                            err instanceof ApiError ? err.message : undefined),
  });

  const remove = useMutation({
    mutationFn: (id: number) => documentsApi.delete(id),
    onSuccess: () => {
      invalidate();
      toast("success", "Dokumenti u fshi");
      setDeleting(null);
    },
    onError: (err) => {
      toast("error", "Fshirja dështoi", err instanceof ApiError ? err.message : undefined);
      setDeleting(null);
    },
  });

  const download = async (doc: DocumentRow) => {
    try {
      await documentsApi.download(doc.id);
    } catch (err) {
      toast("error", "Shkarkimi dështoi", err instanceof ApiError ? err.message : undefined);
    }
  };

  return (
    <>
      <PageHeader title="Menaxhimi i Dokumenteve"
                  subtitle="Ngarko, indekso dhe administro korpusin e dokumenteve institucionale."
                  actions={
                    <>
                      <Button variant="outline" onClick={startReindexAll}
                              disabled={reindexAll.running}>
                        <RefreshCw className="h-4 w-4" aria-hidden />
                        Riindekso korpusin
                      </Button>
                      <Button onClick={() => setUploadOpen(true)}>
                        <FilePlus2 className="h-4 w-4" aria-hidden />
                        Ngarko dokument
                      </Button>
                    </>
                  } />

      {reindexAll.task && reindexAll.running && (
        <Card className="mb-4 p-4">
          <ProgressBar value={reindexAll.task.progress}
                       label={reindexAll.task.message || "Duke riindeksuar korpusin…"} />
        </Card>
      )}

      <div className="mb-4 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden />
          <Input aria-label="Kërko sipas titullit" placeholder="Kërko sipas titullit…"
                 className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <Select aria-label="Filtro sipas tipit" value={fType} onChange={(e) => setFType(e.target.value)}>
          <option value="">Të gjitha tipet</option>
          {(meta.data?.document_types ?? []).map((t) => <option key={t}>{t}</option>)}
        </Select>
        <Select aria-label="Filtro sipas institucionit" value={fInst} onChange={(e) => setFInst(e.target.value)}>
          <option value="">Të gjitha institucionet</option>
          {(filters.data?.institutions ?? []).map((i) => <option key={i}>{i}</option>)}
        </Select>
        <Select aria-label="Filtro sipas vitit" value={fYear} onChange={(e) => setFYear(e.target.value)}>
          <option value="">Të gjithë vitet</option>
          {(filters.data?.years ?? []).map((y) => <option key={y}>{y}</option>)}
        </Select>
      </div>

      <Card>
        {docs.isPending ? (
          <div className="space-y-3 p-5">
            {[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-9 w-full" />)}
          </div>
        ) : !docs.data || docs.data.length === 0 ? (
          <EmptyState title="Asnjë dokument"
                      description="Ngarko dokumentin e parë PDF ose DOCX për të ndërtuar korpusin."
                      action={<Button onClick={() => setUploadOpen(true)}>Ngarko dokument</Button>} />
        ) : (
          <TableShell ariaLabel="Dokumentet e korpusit">
            <thead>
              <tr>
                <Th>Dokumenti</Th>
                <Th>Tipi</Th>
                <Th className="hidden md:table-cell">Institucioni</Th>
                <Th className="hidden sm:table-cell">Viti</Th>
                <Th className="hidden lg:table-cell">Copëza · Faqe</Th>
                <Th>Statusi</Th>
                <Th><span className="sr-only">Veprime</span></Th>
              </tr>
            </thead>
            <tbody>
              {docs.data.map((d) => (
                <Tr key={d.id}>
                  <Td className="max-w-[16rem]">
                    <p className="truncate font-medium text-slate-800 dark:text-slate-100"
                       title={d.title || d.filename}>
                      {d.title || d.filename}
                    </p>
                    <p className="truncate text-xs text-slate-400">{d.filename}</p>
                  </Td>
                  <Td><Badge variant="brand">{d.document_type || "—"}</Badge></Td>
                  <Td className="hidden max-w-[12rem] truncate md:table-cell">{d.institution || "—"}</Td>
                  <Td className="hidden tabular-nums sm:table-cell">{d.year ?? "—"}</Td>
                  <Td className="hidden tabular-nums lg:table-cell">
                    {d.total_chunks} · {d.num_pages}
                  </Td>
                  <Td>
                    <Badge variant={d.status === "active" ? "success" : "neutral"}>
                      {d.status === "active" ? "Aktiv" : "Joaktiv"}
                    </Badge>
                  </Td>
                  <Td>
                    <div className="flex items-center justify-end gap-0.5">
                      <IconButton title={d.status === "active" ? "Çaktivizo" : "Aktivizo"}
                                  onClick={() => setStatus.mutate({
                                    id: d.id,
                                    status: d.status === "active" ? "inactive" : "active",
                                  })}
                                  disabled={setStatus.isPending}>
                        <Power className="h-4 w-4" aria-hidden />
                      </IconButton>
                      <IconButton title="Riindekso"
                                  onClick={() => reindexOne.mutate(d.id)}
                                  disabled={reindexingId !== null || reindexAll.running}
                                  spinning={reindexingId === d.id}>
                        <RefreshCw className="h-4 w-4" aria-hidden />
                      </IconButton>
                      <IconButton title="Ndrysho metadata" onClick={() => setEditing(d)}>
                        <Pencil className="h-4 w-4" aria-hidden />
                      </IconButton>
                      <IconButton title="Parapamje" onClick={() => setPreviewing(d)}>
                        <Eye className="h-4 w-4" aria-hidden />
                      </IconButton>
                      <IconButton title="Shkarko" onClick={() => download(d)}>
                        <Download className="h-4 w-4" aria-hidden />
                      </IconButton>
                      <IconButton title="Fshi" danger onClick={() => setDeleting(d)}>
                        <Trash2 className="h-4 w-4" aria-hidden />
                      </IconButton>
                    </div>
                  </Td>
                </Tr>
              ))}
            </tbody>
          </TableShell>
        )}
      </Card>

      <p className="mt-3 text-xs text-slate-400 dark:text-slate-500">
        {docs.data ? `${docs.data.length} dokumente · Ngarkuar së fundmi: ${docs.data[0] ? formatDate(docs.data[0].created_at) : "—"}` : ""}
      </p>

      <UploadModal open={uploadOpen} onClose={() => setUploadOpen(false)} meta={meta.data} />
      {editing && (
        <EditMetadataModal key={editing.id} doc={editing}
                           onClose={() => setEditing(null)} meta={meta.data} />
      )}
      <PreviewModal doc={previewing} onClose={() => setPreviewing(null)} />
      <ConfirmDialog open={deleting !== null} danger
                     title="Fshi dokumentin?"
                     message={
                       <>
                         Dokumenti <strong>{deleting?.title || deleting?.filename}</strong> do
                         të hiqet nga korpusi bashkë me skedarin dhe të gjitha copëzat e
                         indeksuara. Ky veprim nuk kthehet.
                       </>
                     }
                     confirmLabel="Fshi përfundimisht"
                     loading={remove.isPending}
                     onConfirm={() => deleting && remove.mutate(deleting.id)}
                     onCancel={() => setDeleting(null)} />
    </>
  );
}

function IconButton({ title, onClick, disabled, danger, spinning, children }: {
  title: string;
  onClick: () => void;
  disabled?: boolean;
  danger?: boolean;
  spinning?: boolean;
  children: ReactNode;
}) {
  return (
    <button onClick={onClick} disabled={disabled} title={title} aria-label={title}
            className={`rounded-lg p-1.5 transition-colors disabled:opacity-40 ${
              danger
                ? "text-slate-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950"
                : "text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
            } ${spinning ? "animate-spin" : ""}`}>
      {children}
    </button>
  );
}
