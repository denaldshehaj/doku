import type { HTMLAttributes, ReactNode } from "react";
import { cx } from "@/lib/format";

export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cx(
      "rounded-2xl border border-slate-200 bg-white shadow-card",
      "dark:border-slate-800 dark:bg-slate-900", className)} {...rest} />
  );
}

export function CardHeader({ title, subtitle, actions }: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 p-4 sm:p-5 dark:border-slate-800">
      <div className="min-w-0">
        <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
      </div>
      {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
    </div>
  );
}

export function CardBody({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cx("p-4 sm:p-5", className)} {...rest} />;
}
