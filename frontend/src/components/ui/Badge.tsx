import type { HTMLAttributes } from "react";
import { cx } from "@/lib/format";

type Variant = "neutral" | "brand" | "success" | "warning" | "danger";

const VARIANTS: Record<Variant, string> = {
  neutral: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  brand: "bg-brand-50 text-brand-800 dark:bg-brand-950 dark:text-brand-200",
  success: "bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300",
  warning: "bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  danger: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
};

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: Variant;
}

export function Badge({ variant = "neutral", className, ...rest }: BadgeProps) {
  return (
    <span className={cx(
      "inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-xs font-medium",
      VARIANTS[variant], className)} {...rest} />
  );
}
