/* Thin, typed table primitives — semantic <table> markup (screen-reader
 * friendly) with the visual language of the reference design. */
import type { HTMLAttributes, ReactNode, ThHTMLAttributes, TdHTMLAttributes } from "react";
import { cx } from "@/lib/format";

export function TableShell({ children, ariaLabel }: { children: ReactNode; ariaLabel?: string }) {
  return (
    <div className="overflow-x-auto">
      <table aria-label={ariaLabel} className="w-full border-collapse text-left text-sm">
        {children}
      </table>
    </div>
  );
}

export function Th({ className, ...rest }: ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th scope="col"
        className={cx(
          "whitespace-nowrap border-b border-slate-200 px-3 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500",
          "first:pl-4 last:pr-4 sm:first:pl-5 sm:last:pr-5 dark:border-slate-700 dark:text-slate-400",
          className)}
        {...rest} />
  );
}

export function Td({ className, ...rest }: TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td className={cx(
      "border-b border-slate-100 px-3 py-2.5 align-middle text-slate-700",
      "first:pl-4 last:pr-4 sm:first:pl-5 sm:last:pr-5 dark:border-slate-800 dark:text-slate-300",
      className)}
        {...rest} />
  );
}

export function Tr({ className, ...rest }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr className={cx("transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/50", className)}
        {...rest} />
  );
}
