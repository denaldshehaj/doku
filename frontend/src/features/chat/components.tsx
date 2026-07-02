/* Chat building blocks: message bubbles, citation cards, the sources side
 * panel. The refusal state is styled distinctly — it is the visible face of
 * the refusal gate, not an error. */
import { useState } from "react";
import { Bot, Check, Copy, Download, FileText, ShieldAlert, User as UserIcon } from "lucide-react";
import type { Answer, Source } from "@/api/types";
import { Badge } from "@/components/ui/Badge";
import { cx, formatSeconds } from "@/lib/format";

export interface ChatMessage {
  id: number;
  kind: "question" | "answer";
  text: string;
  answer?: Answer;
  /** true while tokens are still arriving over the SSE stream */
  streaming?: boolean;
  at: Date;
}

function timeLabel(d: Date): string {
  return d.toLocaleTimeString("sq-AL", { hour: "2-digit", minute: "2-digit" });
}

export function QuestionBubble({ message }: { message: ChatMessage }) {
  return (
    <div className="flex justify-end">
      <div className="flex max-w-[85%] items-start gap-2.5">
        <div className="rounded-2xl rounded-tr-sm bg-brand-700 px-4 py-2.5 text-sm text-white shadow-card">
          <p className="whitespace-pre-wrap break-words">{message.text}</p>
          <p className="mt-1 text-right text-[10px] text-brand-200">{timeLabel(message.at)}</p>
        </div>
        <span className="mt-1 rounded-full bg-brand-100 p-1.5 text-brand-700 dark:bg-brand-900 dark:text-brand-200"
              aria-hidden>
          <UserIcon className="h-4 w-4" />
        </span>
      </div>
    </div>
  );
}

export function RefusalBubble({ message }: { message: ChatMessage }) {
  const a = message.answer;
  return (
    <div className="flex justify-start">
      <div className="flex max-w-[85%] items-start gap-2.5">
        <span className="mt-1 rounded-full bg-red-100 p-1.5 text-red-600 dark:bg-red-950 dark:text-red-400"
              aria-hidden>
          <ShieldAlert className="h-4 w-4" />
        </span>
        <div className="rounded-2xl rounded-tl-sm border border-red-200 bg-red-50 px-4 py-2.5 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/60 dark:text-red-200">
          <p>{message.text}</p>
          {a && (
            <p className="mt-1.5 text-xs text-red-500 dark:text-red-400">
              Ngjashmëria më e lartë: {a.top_score.toFixed(3)} (nën pragun {a.min_similarity}).
              Sistemi refuzon në vend që të shpikë përgjigje.
            </p>
          )}
          <p className="mt-1 text-right text-[10px] opacity-60">{timeLabel(message.at)}</p>
        </div>
      </div>
    </div>
  );
}

export function AnswerBubble({ message, onExport, exporting }: {
  message: ChatMessage;
  onExport: (rowId: number) => void;
  exporting: boolean;
}) {
  const a = message.answer;
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(a?.text ?? message.text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard blocked — non-critical */
    }
  };

  return (
    <div className="flex justify-start">
      <div className="flex w-full max-w-[92%] items-start gap-2.5 sm:max-w-[85%]">
        <span className="mt-1 shrink-0 rounded-full bg-brand-50 p-1.5 text-brand-700 dark:bg-brand-950 dark:text-brand-300"
              aria-hidden>
          <Bot className="h-4 w-4" />
        </span>
        <div className="min-w-0 flex-1 rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 shadow-card dark:border-slate-800 dark:bg-slate-900">
          <p className="whitespace-pre-wrap break-words text-sm text-slate-800 dark:text-slate-200"
             aria-live={message.streaming ? "polite" : undefined}>
            {a?.text ?? message.text}
            {message.streaming && (
              <span className="ml-0.5 inline-block h-3.5 w-[2px] animate-doku-pulse bg-brand-500 align-middle"
                    aria-hidden />
            )}
          </p>

          {a && a.sources.length > 0 && (
            <div className="mt-3 space-y-1.5 border-t border-slate-100 pt-2.5 dark:border-slate-800">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400">Burimet:</p>
              {a.sources.map((s) => <SourceLine key={s.n} source={s} />)}
            </div>
          )}

          {a && (
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-2.5 dark:border-slate-800">
              <Badge variant="brand">RAG</Badge>
              {a.sources.length > 0 && <Badge variant="success">Me burime</Badge>}
              <span className="text-xs text-slate-400 dark:text-slate-500">
                ⏱ {formatSeconds(a.response_time)} · ngjashmëria {a.top_score.toFixed(2)}
              </span>
              <span className="ml-auto flex items-center gap-1">
                <button onClick={copy} title="Kopjo përgjigjen" aria-label="Kopjo përgjigjen"
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800">
                  {copied ? <Check className="h-4 w-4 text-emerald-500" aria-hidden />
                          : <Copy className="h-4 w-4" aria-hidden />}
                </button>
                <button onClick={() => onExport(a.row_id)} disabled={exporting}
                        title="Shkarko në Word (.docx)" aria-label="Shkarko në Word"
                        className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 disabled:opacity-50 dark:hover:bg-slate-800">
                  <Download className="h-4 w-4" aria-hidden />
                </button>
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SourceLine({ source }: { source: Source }) {
  return (
    <p className="text-xs text-slate-500 dark:text-slate-400">
      <span className="font-semibold text-slate-600 dark:text-slate-300">[{source.n}]</span>{" "}
      {source.title || source.filename} · {source.document_type}
      {source.institution ? ` · ${source.institution}` : ""} · faqe {source.page}
      <span className="ml-1 text-emerald-600 dark:text-emerald-400">({source.score.toFixed(2)})</span>
    </p>
  );
}

/** Right-hand panel: the cited chunks of the latest grounded answer. */
export function SourcesPanel({ answer }: { answer: Answer | null }) {
  return (
    <div className="space-y-3">
      <h2 className="flex items-center justify-between text-sm font-semibold text-slate-700 dark:text-slate-200">
        Burimet e përgjigjes së fundit
        {answer && answer.sources.length > 0 && (
          <Badge variant="brand">{answer.sources.length}</Badge>
        )}
      </h2>
      {!answer || answer.sources.length === 0 ? (
        <p className="rounded-xl border border-dashed border-slate-300 p-4 text-xs text-slate-400 dark:border-slate-700 dark:text-slate-500">
          Pas një përgjigjeje të bazuar, këtu shfaqen fragmentet e cituara me
          ngjashmërinë e tyre.
        </p>
      ) : (
        answer.sources.map((s) => (
          <div key={s.n}
               className="rounded-xl border border-slate-200 bg-white p-3 shadow-card dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-start justify-between gap-2">
              <div className="flex min-w-0 items-start gap-2">
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-brand-600 dark:text-brand-300" aria-hidden />
                <p className="min-w-0 break-words text-xs font-semibold text-slate-700 dark:text-slate-200">
                  {s.title || s.filename}
                </p>
              </div>
              <span className={cx(
                "shrink-0 rounded-md px-1.5 py-0.5 text-[11px] font-bold tabular-nums",
                s.score >= 0.6
                  ? "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300"
                  : "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300")}>
                {s.score.toFixed(2)}
              </span>
            </div>
            <p className="mt-1 text-[11px] text-slate-400 dark:text-slate-500">
              {s.document_type}{s.institution ? ` · ${s.institution}` : ""} · faqe {s.page}
            </p>
            <p className="mt-2 border-l-2 border-brand-200 pl-2 text-xs italic text-slate-500 dark:border-brand-800 dark:text-slate-400">
              “{s.fragment}”
            </p>
          </div>
        ))
      )}
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex items-center gap-2.5" role="status" aria-label="Duke analizuar">
      <span className="rounded-full bg-brand-50 p-1.5 text-brand-700 dark:bg-brand-950 dark:text-brand-300" aria-hidden>
        <Bot className="h-4 w-4" />
      </span>
      <div className="flex items-center gap-1.5 rounded-2xl border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
        {[0, 150, 300].map((delay) => (
          <span key={delay}
                className="h-1.5 w-1.5 animate-bounce rounded-full bg-brand-400"
                style={{ animationDelay: `${delay}ms` }} aria-hidden />
        ))}
        <span className="ml-1 text-xs text-slate-400">Duke kërkuar dhe analizuar…</span>
      </div>
    </div>
  );
}
