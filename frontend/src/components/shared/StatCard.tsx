import type { LucideIcon } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/misc";

export function StatCard({ label, value, icon: Icon, loading = false, hint }: {
  label: string;
  value: string | number | null | undefined;
  icon: LucideIcon;
  loading?: boolean;
  hint?: string;
}) {
  return (
    <Card className="p-4 sm:p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm text-slate-500 dark:text-slate-400">{label}</p>
          {loading ? (
            <Skeleton className="mt-2 h-8 w-20" />
          ) : (
            <p className="mt-1 text-2xl font-bold tabular-nums text-slate-900 dark:text-slate-50">
              {value ?? "—"}
            </p>
          )}
          {hint && <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">{hint}</p>}
        </div>
        <div className="rounded-xl bg-brand-50 p-2.5 text-brand-700 dark:bg-brand-950 dark:text-brand-300">
          <Icon className="h-5 w-5" aria-hidden />
        </div>
      </div>
    </Card>
  );
}
