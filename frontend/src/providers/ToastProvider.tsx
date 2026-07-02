/* Minimal toast system (no external dependency): success / error / info,
 * auto-dismiss, accessible via role="status" / role="alert". */
import { createContext, useCallback, useContext, useRef, useState,
  type ReactNode } from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";
import { cx } from "@/lib/format";

export type ToastVariant = "success" | "error" | "info";

interface ToastItem {
  id: number;
  variant: ToastVariant;
  title: string;
  description?: string;
}

interface ToastContextValue {
  toast: (variant: ToastVariant, title: string, description?: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const ICONS = {
  success: CheckCircle2,
  error: AlertCircle,
  info: Info,
} as const;

const STYLES: Record<ToastVariant, string> = {
  success: "border-emerald-300 bg-emerald-50 text-emerald-900 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-100",
  error: "border-red-300 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100",
  info: "border-brand-200 bg-brand-50 text-brand-900 dark:border-brand-800 dark:bg-brand-950 dark:text-brand-100",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const dismiss = useCallback((id: number) => {
    setItems((list) => list.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((variant: ToastVariant, title: string, description?: string) => {
    const id = nextId.current++;
    setItems((list) => [...list.slice(-4), { id, variant, title, description }]);
    window.setTimeout(() => dismiss(id), variant === "error" ? 8000 : 5000);
  }, [dismiss]);

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div aria-live="polite"
           className="pointer-events-none fixed right-4 top-4 z-[100] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2">
        {items.map((t) => {
          const Icon = ICONS[t.variant];
          return (
            <div key={t.id}
                 role={t.variant === "error" ? "alert" : "status"}
                 className={cx(
                   "pointer-events-auto flex items-start gap-3 rounded-xl border p-3 shadow-pop",
                   STYLES[t.variant])}>
              <Icon className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{t.title}</p>
                {t.description && (
                  <p className="mt-0.5 break-words text-sm opacity-90">{t.description}</p>
                )}
              </div>
              <button onClick={() => dismiss(t.id)} aria-label="Mbyll njoftimin"
                      className="rounded p-0.5 opacity-60 hover:opacity-100">
                <X className="h-4 w-4" aria-hidden />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast duhet përdorur brenda ToastProvider.");
  return ctx;
}
