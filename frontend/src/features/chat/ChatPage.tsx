/* Biseda — RAG Q&A over the active corpus. The conversation lives in component
 * state for the session (every exchange is persisted server-side in history).
 * Answers stream in token-by-token over SSE; the refusal gate still answers
 * instantly. Layout: chat column + sources panel (xl+), filters by composer. */
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useQuery } from "@tanstack/react-query";
import { SendHorizonal, SlidersHorizontal } from "lucide-react";
import { ApiError } from "@/api/client";
import { chatApi, documentsApi, metaApi } from "@/api/endpoints";
import type { Answer } from "@/api/types";
import { Button } from "@/components/ui/Button";
import { Input, Select, Textarea } from "@/components/ui/fields";
import { Alert, EmptyState } from "@/components/ui/misc";
import { PageHeader } from "@/components/shared/PageHeader";
import { useToast } from "@/providers/ToastProvider";
import {
  AnswerBubble, QuestionBubble, RefusalBubble, SourcesPanel, TypingIndicator,
  type ChatMessage,
} from "./components";

interface Filters {
  docType: string;
  institution: string;
  year: string;
  keyword: string;
  documentId: string; // "" = whole filtered corpus
}

const NO_FILTER: Filters = { docType: "", institution: "", year: "", keyword: "", documentId: "" };

export default function ChatPage() {
  const { toast } = useToast();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [question, setQuestion] = useState("");
  const [filters, setFilters] = useState<Filters>(NO_FILTER);
  const [filtersOpen, setFiltersOpen] = useState(false);
  const [exportingRow, setExportingRow] = useState<number | null>(null);
  const nextId = useRef(1);
  const bottomRef = useRef<HTMLDivElement>(null);

  const meta = useQuery({ queryKey: ["meta"], queryFn: metaApi.meta });
  const availableFilters = useQuery({ queryKey: ["doc-filters"], queryFn: documentsApi.filters });
  const docs = useQuery({
    queryKey: ["documents", "active"],
    queryFn: () => documentsApi.list({ activeOnly: true }),
  });

  // Scope dropdown honours the metadata filters, exactly like the old page.
  const scopeDocs = useMemo(() => {
    if (!docs.data) return [];
    return docs.data.filter((d) =>
      (!filters.docType || d.document_type === filters.docType) &&
      (!filters.institution || d.institution === filters.institution) &&
      (!filters.year || String(d.year) === filters.year) &&
      (!filters.keyword || (d.title ?? "").toLowerCase().includes(filters.keyword.toLowerCase())));
  }, [docs.data, filters]);

  const [streaming, setStreaming] = useState(false);

  const patchMessage = (id: number, patch: Partial<ChatMessage> | ((m: ChatMessage) => Partial<ChatMessage>)) => {
    setMessages((list) => list.map((m) =>
      m.id === id ? { ...m, ...(typeof patch === "function" ? patch(m) : patch) } : m));
  };

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, streaming]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const q = question.trim();
    if (!q || streaming) return;
    // Ids are allocated outside the state updater: updaters must stay pure
    // (StrictMode double-invokes them in development).
    const questionId = nextId.current++;
    const answerId = nextId.current++;
    setMessages((list) => [
      ...list,
      { id: questionId, kind: "question", text: q, at: new Date() },
      { id: answerId, kind: "answer", text: "", streaming: true, at: new Date() },
    ]);
    setQuestion("");
    setStreaming(true);

    void chatApi.askStream({
      question: q,
      document_id: filters.documentId ? Number(filters.documentId) : null,
      doc_type: filters.docType || null,
      institution: filters.institution || null,
      year: filters.year ? Number(filters.year) : null,
      title_kw: filters.keyword || null,
    }, {
      onDelta: (t) => {
        patchMessage(answerId, (m) => ({ text: m.text + t }));
      },
      onRefusal: (answer: Answer) => {
        patchMessage(answerId, { text: answer.text, answer, streaming: false });
        setStreaming(false);
      },
      onDone: (answer: Answer) => {
        patchMessage(answerId, { text: answer.text, answer, streaming: false });
        setStreaming(false);
      },
      onError: (message, code) => {
        // Drop the empty placeholder; keep any partial text with a note.
        setMessages((list) => list
          .map((m) => m.id === answerId && m.text
            ? { ...m, streaming: false, text: m.text + "\n\n[Përgjigja u ndërpre]" }
            : m)
          .filter((m) => m.id !== answerId || m.text !== ""));
        setStreaming(false);
        toast("error",
              code === "ollama_unavailable" ? "Modeli lokal nuk është aktiv" : "Gabim gjatë përgjigjes",
              message);
      },
    });
  };

  const onExport = async (rowId: number) => {
    setExportingRow(rowId);
    try {
      await chatApi.exportAnswer(rowId);
      toast("success", "U shkarkua", "Përgjigjja u eksportua në Word (.docx).");
    } catch (err) {
      toast("error", "Eksporti dështoi",
            err instanceof ApiError ? err.message : "Provo përsëri.");
    } finally {
      setExportingRow(null);
    }
  };

  const lastAnswer = [...messages].reverse()
    .find((m) => m.kind === "answer" && !m.answer?.refused)?.answer ?? null;
  const noActiveDocs = docs.isSuccess && docs.data.length === 0;
  const activeFilterCount =
    Number(!!filters.docType) + Number(!!filters.institution) +
    Number(!!filters.year) + Number(!!filters.keyword) + Number(!!filters.documentId);

  return (
    <>
      <PageHeader title="Biseda me DOKU"
                  subtitle="Pyet mbi korpusin e dokumenteve — çdo përgjigje bazohet vetëm në fragmentet e gjetura dhe citon burimin." />

      {noActiveDocs && (
        <div className="mb-4">
          <Alert variant="warning" title="Nuk ka dokumente aktive">
            Kërkoji administratorit të ngarkojë dhe aktivizojë dokumente përpara se të bësh pyetje.
          </Alert>
        </div>
      )}

      <div className="grid gap-5 xl:grid-cols-[1fr_20rem]">
        {/* Chat column */}
        <div className="flex min-h-[60vh] flex-col rounded-2xl border border-slate-200 bg-slate-50/60 dark:border-slate-800 dark:bg-slate-900/40">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 sm:p-5">
            {messages.length === 0 ? (
              <EmptyState title="Fillo bisedën"
                          description='Shembull: "Sa ditë leje vjetore kam të drejtë sipas legjislacionit në fuqi?"' />
            ) : (
              messages.map((m) => {
                if (m.kind === "question") return <QuestionBubble key={m.id} message={m} />;
                if (m.answer?.refused) return <RefusalBubble key={m.id} message={m} />;
                // Placeholder pa asnjë token ende: indikatori "duke analizuar".
                if (m.streaming && m.text === "") return <TypingIndicator key={m.id} />;
                return <AnswerBubble key={m.id} message={m} onExport={onExport}
                                     exporting={exportingRow === m.answer?.row_id} />;
              })
            )}
            <div ref={bottomRef} />
          </div>

          {/* Filters */}
          <div className="border-t border-slate-200 px-4 pt-3 dark:border-slate-800">
            <button onClick={() => setFiltersOpen((v) => !v)}
                    aria-expanded={filtersOpen}
                    className="flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-slate-100">
              <SlidersHorizontal className="h-4 w-4" aria-hidden />
              Filtro fushën e kërkimit
              {activeFilterCount > 0 && (
                <span className="rounded-full bg-brand-100 px-2 py-0.5 text-xs font-semibold text-brand-800 dark:bg-brand-900 dark:text-brand-100">
                  {activeFilterCount}
                </span>
              )}
            </button>
            {filtersOpen && (
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                <Select label="Dokument specifik" value={filters.documentId}
                        onChange={(e) => setFilters((f) => ({ ...f, documentId: e.target.value }))}>
                  <option value="">Të gjithë dokumentet aktive</option>
                  {scopeDocs.map((d) => (
                    <option key={d.id} value={d.id}>{d.title || d.filename}</option>
                  ))}
                </Select>
                <Select label="Tipi" value={filters.docType} disabled={!!filters.documentId}
                        onChange={(e) => setFilters((f) => ({ ...f, docType: e.target.value }))}>
                  <option value="">Të gjitha</option>
                  {(meta.data?.document_types ?? []).map((t) => <option key={t}>{t}</option>)}
                </Select>
                <Select label="Institucioni" value={filters.institution} disabled={!!filters.documentId}
                        onChange={(e) => setFilters((f) => ({ ...f, institution: e.target.value }))}>
                  <option value="">Të gjitha</option>
                  {(availableFilters.data?.institutions ?? []).map((i) => <option key={i}>{i}</option>)}
                </Select>
                <Select label="Viti" value={filters.year} disabled={!!filters.documentId}
                        onChange={(e) => setFilters((f) => ({ ...f, year: e.target.value }))}>
                  <option value="">Të gjithë</option>
                  {(availableFilters.data?.years ?? []).map((y) => <option key={y}>{y}</option>)}
                </Select>
                <Input label="Fjalë kyçe në titull" value={filters.keyword}
                       disabled={!!filters.documentId} placeholder="p.sh. prokurim"
                       onChange={(e) => setFilters((f) => ({ ...f, keyword: e.target.value }))} />
                <div className="flex items-end">
                  <Button variant="ghost" size="sm" onClick={() => setFilters(NO_FILTER)}>
                    Pastro filtrat
                  </Button>
                </div>
              </div>
            )}
          </div>

          {/* Composer */}
          <form onSubmit={submit} className="flex items-end gap-2 p-4">
            <div className="flex-1">
              <Textarea aria-label="Pyetja jote" placeholder="Shkruaj pyetjen tënde në shqip…"
                        value={question} rows={2}
                        onChange={(e) => setQuestion(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter" && !e.shiftKey) {
                            e.preventDefault();
                            e.currentTarget.form?.requestSubmit();
                          }
                        }}
                        disabled={noActiveDocs} />
            </div>
            <Button type="submit" size="lg" loading={streaming}
                    disabled={!question.trim() || noActiveDocs}>
              <SendHorizonal className="h-4 w-4" aria-hidden />
              <span className="hidden sm:inline">Dërgo</span>
            </Button>
          </form>
        </div>

        {/* Sources panel */}
        <aside className="hidden xl:block">
          <div className="sticky top-4">
            <SourcesPanel answer={lastAnswer} />
          </div>
        </aside>
      </div>
    </>
  );
}
