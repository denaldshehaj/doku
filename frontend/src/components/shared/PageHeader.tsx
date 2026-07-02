import type { ReactNode } from "react";

/** Page title with the institutional red underline accent from the references. */
export function PageHeader({ title, subtitle, actions }: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-xl font-bold text-slate-900 sm:text-2xl dark:text-slate-50">{title}</h1>
        <div className="mt-1.5 h-0.5 w-10 rounded bg-accent-600" aria-hidden />
        {subtitle && (
          <p className="mt-2 max-w-2xl text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}
