/* Admin document dialogs: upload (with drag & drop), edit metadata, preview. */
import { useRef, useState, type DragEvent, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { FileUp, UploadCloud } from "lucide-react";
import { ApiError } from "@/api/client";
import { documentsApi } from "@/api/endpoints";
import type { DocumentRow, Meta } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Input, Select, Textarea } from "@/components/ui/fields";
import { Modal } from "@/components/ui/Modal";
import { useToast } from "@/providers/ToastProvider";
import { cx } from "@/lib/format";

const CURRENT_YEAR = new Date().getFullYear();

export function UploadModal({ open, onClose, meta }: {
  open: boolean;
  onClose: () => void;
  meta: Meta | undefined;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [title, setTitle] = useState("");
  const [institution, setInstitution] = useState("");
  const [docType, setDocType] = useState("Tjetër");
  const [year, setYear] = useState(String(CURRENT_YEAR));
  const [description, setDescription] = useState("");

  const upload = useMutation({
    mutationFn: (form: FormData) => documentsApi.upload(form),
    onSuccess: (doc) => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["doc-filters"] });
      toast("success", "Dokumenti u indeksua",
            `"${doc.title || doc.filename}" me ${doc.total_chunks} copëza.`);
      reset();
      onClose();
    },
    onError: (err) => {
      toast("error", "Ngarkimi dështoi",
            err instanceof ApiError ? err.message : "Provo përsëri.");
    },
  });

  const reset = () => {
    setFile(null); setTitle(""); setInstitution(""); setDocType("Tjetër");
    setYear(String(CURRENT_YEAR)); setDescription("");
  };

  const acceptFile = (f: File | undefined) => {
    if (!f) return;
    const ext = f.name.toLowerCase().split(".").pop();
    if (ext !== "pdf" && ext !== "docx") {
      toast("error", "Format i palejuar", "Lejohen vetëm skedarë PDF ose DOCX.");
      return;
    }
    setFile(f);
    if (!title) setTitle(f.name.replace(/\.(pdf|docx)$/i, ""));
  };

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    acceptFile(e.dataTransfer.files[0]);
  };

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!file) return;
    const form = new FormData();
    form.set("file", file);
    form.set("title", title.trim());
    form.set("institution", institution);
    form.set("document_type", docType);
    if (year) form.set("year", year);
    form.set("description", description.trim());
    upload.mutate(form);
  };

  return (
    <Modal open={open} onClose={upload.isPending ? () => {} : onClose}
           title="Ngarko dokument të ri" width="max-w-2xl"
           footer={
             <>
               <Button variant="outline" onClick={onClose} disabled={upload.isPending}>Anulo</Button>
               <Button type="submit" form="upload-form" loading={upload.isPending} disabled={!file}>
                 <FileUp className="h-4 w-4" aria-hidden />
                 Ngarko dhe indekso
               </Button>
             </>
           }>
      <form id="upload-form" onSubmit={submit} className="space-y-4">
        <div role="button" tabIndex={0}
             onClick={() => fileInput.current?.click()}
             onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && fileInput.current?.click()}
             onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
             onDragLeave={() => setDragging(false)}
             onDrop={onDrop}
             className={cx(
               "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed p-6 text-center transition-colors",
               dragging ? "border-brand-500 bg-brand-50 dark:bg-brand-950"
                        : "border-slate-300 hover:border-brand-400 dark:border-slate-700")}>
          <UploadCloud className="h-8 w-8 text-brand-500" aria-hidden />
          {file ? (
            <p className="text-sm font-medium text-slate-700 dark:text-slate-200">{file.name}</p>
          ) : (
            <>
              <p className="text-sm font-medium text-slate-700 dark:text-slate-200">
                Tërhiq skedarin këtu ose kliko për ta zgjedhur
              </p>
              <p className="text-xs text-slate-400">PDF ose DOCX me tekst të lexueshëm (jo skanime)</p>
            </>
          )}
          <input ref={fileInput} type="file" accept=".pdf,.docx" className="sr-only"
                 aria-label="Zgjidh skedarin"
                 onChange={(e) => acceptFile(e.target.files?.[0])} />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Titulli" value={title} onChange={(e) => setTitle(e.target.value)}
                 placeholder="p.sh. Ligji nr. 44/2015" />
          <Select label="Institucioni burimor" value={institution}
                  onChange={(e) => setInstitution(e.target.value)}>
            <option value="">— Zgjidh —</option>
            {(meta?.institutions ?? []).map((i) => <option key={i}>{i}</option>)}
          </Select>
          <Select label="Tipi i dokumentit" value={docType}
                  onChange={(e) => setDocType(e.target.value)}>
            {(meta?.document_types ?? ["Tjetër"]).map((t) => <option key={t}>{t}</option>)}
          </Select>
          <Input label="Viti" type="number" min={1990} max={2100} value={year}
                 onChange={(e) => setYear(e.target.value)} />
        </div>
        <Textarea label="Përshkrim i shkurtër" rows={2} value={description}
                  onChange={(e) => setDescription(e.target.value)} />
        {upload.isPending && (
          <p className="text-center text-xs text-slate-400" role="status">
            Teksti po nxirret dhe indeksohet me embeddings lokale — mund të zgjasë
            deri në një minutë për dokumente të mëdha.
          </p>
        )}
      </form>
    </Modal>
  );
}

export function EditMetadataModal({ doc, onClose, meta }: {
  doc: DocumentRow | null;
  onClose: () => void;
  meta: Meta | undefined;
}) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState(doc?.title ?? "");
  const [institution, setInstitution] = useState(doc?.institution ?? "");
  const [docType, setDocType] = useState(doc?.document_type ?? "Tjetër");
  const [year, setYear] = useState(doc?.year ? String(doc.year) : "");
  const [description, setDescription] = useState(doc?.description ?? "");

  const save = useMutation({
    mutationFn: () => documentsApi.patch(doc!.id, {
      title: title.trim(), institution, document_type: docType,
      year: year ? Number(year) : undefined, description: description.trim(),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents"] });
      queryClient.invalidateQueries({ queryKey: ["doc-filters"] });
      toast("success", "Metadata u ruajt");
      onClose();
    },
    onError: (err) => {
      toast("error", "Ruajtja dështoi", err instanceof ApiError ? err.message : undefined);
    },
  });

  if (!doc) return null;
  const institutions = meta?.institutions ?? [];
  const instOptions = institution && !institutions.includes(institution)
    ? [institution, ...institutions] : institutions;

  return (
    <Modal open onClose={onClose} title={`Metadata — ${doc.filename}`} width="max-w-xl"
           footer={
             <>
               <Button variant="outline" onClick={onClose}>Anulo</Button>
               <Button onClick={() => save.mutate()} loading={save.isPending}>Ruaj</Button>
             </>
           }>
      <div className="space-y-4">
        <Input label="Titulli" value={title} onChange={(e) => setTitle(e.target.value)} />
        <div className="grid gap-4 sm:grid-cols-2">
          <Select label="Institucioni" value={institution}
                  onChange={(e) => setInstitution(e.target.value)}>
            <option value="">— Zgjidh —</option>
            {instOptions.map((i) => <option key={i}>{i}</option>)}
          </Select>
          <Select label="Tipi" value={docType} onChange={(e) => setDocType(e.target.value)}>
            {(meta?.document_types ?? [docType]).map((t) => <option key={t}>{t}</option>)}
          </Select>
        </div>
        <Input label="Viti" type="number" min={1990} max={2100} value={year}
               onChange={(e) => setYear(e.target.value)} />
        <Textarea label="Përshkrim" rows={3} value={description}
                  onChange={(e) => setDescription(e.target.value)} />
      </div>
    </Modal>
  );
}

export function PreviewModal({ doc, onClose }: {
  doc: DocumentRow | null;
  onClose: () => void;
}) {
  if (!doc) return null;
  const isPdf = doc.filename.toLowerCase().endsWith(".pdf");
  return (
    <Modal open onClose={onClose} title={`Parapamje — ${doc.title || doc.filename}`}
           width="max-w-4xl">
      {isPdf ? (
        <iframe src={documentsApi.inlineUrl(doc.id)} title={`Parapamje: ${doc.filename}`}
                className="h-[70vh] w-full rounded-lg border border-slate-200 dark:border-slate-700" />
      ) : (
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Parapamja në shfletues mbështetet vetëm për PDF. Shkarko skedarin Word
          me butonin e shkarkimit në tabelë.
        </p>
      )}
    </Modal>
  );
}
