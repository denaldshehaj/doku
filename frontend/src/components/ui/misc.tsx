/* Small presentational helpers: Spinner, Skeleton, EmptyState, Alert,
 * ProgressBar — shared loading/empty/feedback states. */
import type { HTMLAttributes, ReactNode } from "react";
import { AlertTriangle, Inbox, Loader2 } from "lucide-react";
import { cx } from "@/lib/format";

export function Spinner({ label = "Duke ngarkuar…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 p-8 text-sm text-slate-500 dark:text-slate-400"
         role="status">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden />
      {label}
    </div>
  );
}

export function Skeleton({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cx("animate-doku-pulse rounded-lg bg-slate-200 dark:bg-slate-800", className)}
         aria-hidden {...rest} />
  );
}

export function EmptyState({ icon, title, description, action }: {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 p-10 text-center">
      <div className="rounded-2xl bg-slate-100 p-3 text-slate-400 dark:bg-slate-800 dark:text-slate-500">
        {icon ?? <Inbox className="h-7 w-7" aria-hidden />}
      </div>
      <p className="text-sm font-semibold text-slate-700 dark:text-slate-200">{title}</p>
      {description && (
        <p className="max-w-sm text-sm text-slate-500 dark:text-slate-400">{description}</p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}

export function Alert({ variant = "warning", title, children }: {
  variant?: "warning" | "danger" | "info";
  title?: string;
  children: ReactNode;
}) {
  const styles = {
    warning: "border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-100",
    danger: "border-red-300 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-100",
    info: "border-brand-200 bg-brand-50 text-brand-900 dark:border-brand-800 dark:bg-brand-950 dark:text-brand-100",
  }[variant];
  return (
    <div role="alert" className={cx("flex gap-3 rounded-xl border p-3.5 text-sm", styles)}>
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        <div className={title ? "mt-0.5" : undefined}>{children}</div>
      </div>
    </div>
  );
}

export function ProgressBar({ value, label }: { value: number; label?: string }) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className="space-y-1.5">
      {label && (
        <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
          <span className="min-w-0 truncate">{label}</span>
          <span className="ml-2 shrink-0 tabular-nums">{pct}%</span>
        </div>
      )}
      <div className="h-2 overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800"
           role="progressbar" aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100}>
        <div className="h-full rounded-full bg-brand-600 transition-[width] duration-500"
             style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}
