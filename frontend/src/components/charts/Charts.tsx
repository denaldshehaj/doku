/* Lightweight, dependency-free SVG charts for the reports module.
 * Hand-rolled instead of a chart library on purpose: zero external runtime,
 * ~3KB total instead of ~500KB, full control over the institutional palette,
 * and everything renders in print. Each chart carries an aria-label and the
 * data is also reachable through <title> tooltips. */
import { useId, useState } from "react";
import { cx } from "@/lib/format";

const PALETTE = [
  "var(--color-brand-600)", "var(--color-brand-400)", "#0e9f6e", "#d97706",
  "#7c3aed", "#db2777", "#0891b2", "#64748b",
];

// --- Line / area chart --------------------------------------------------------

export interface LineSeries {
  name: string;
  color?: string;
  values: number[];
  /** render a soft area under this line */
  area?: boolean;
}

export function LineChart({ labels, series, height = 180, ariaLabel }: {
  labels: string[];
  series: LineSeries[];
  height?: number;
  ariaLabel: string;
}) {
  const gradId = useId();
  const [hover, setHover] = useState<number | null>(null);
  const W = 640;
  const H = height;
  const PAD = { top: 12, right: 8, bottom: 22, left: 34 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;

  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const n = Math.max(labels.length, 2);
  const x = (i: number) => PAD.left + (i / (n - 1)) * innerW;
  const y = (v: number) => PAD.top + innerH - (v / max) * innerH;

  const path = (values: number[]) =>
    values.map((v, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");

  // At most ~6 x labels so long ranges stay readable.
  const step = Math.max(1, Math.ceil(n / 6));
  const yTicks = [0, 0.5, 1].map((f) => Math.round(max * f));

  return (
    <figure aria-label={ariaLabel} className="m-0">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel}
           className="w-full"
           onMouseLeave={() => setHover(null)}>
        {yTicks.map((t) => (
          <g key={t}>
            <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)}
                  className="stroke-slate-200 dark:stroke-slate-700" strokeDasharray="3 3" />
            <text x={PAD.left - 6} y={y(t) + 3} textAnchor="end"
                  className="fill-slate-400 text-[10px] tabular-nums">{t}</text>
          </g>
        ))}
        {series.map((s, si) => {
          const color = s.color ?? PALETTE[si % PALETTE.length];
          return (
            <g key={s.name}>
              {s.area && (
                <>
                  <defs>
                    <linearGradient id={`${gradId}-${si}`} x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={color} stopOpacity="0.25" />
                      <stop offset="100%" stopColor={color} stopOpacity="0.02" />
                    </linearGradient>
                  </defs>
                  <path d={`${path(s.values)} L${x(s.values.length - 1)},${y(0)} L${x(0)},${y(0)} Z`}
                        fill={`url(#${gradId}-${si})`} stroke="none" />
                </>
              )}
              <path d={path(s.values)} fill="none" stroke={color} strokeWidth="2"
                    strokeLinejoin="round" strokeLinecap="round" />
            </g>
          );
        })}
        {/* Hover hit areas + markers */}
        {labels.map((label, i) => (
          <g key={label}>
            <rect x={x(i) - innerW / n / 2} y={PAD.top} width={innerW / n} height={innerH}
                  fill="transparent" onMouseEnter={() => setHover(i)}>
              <title>{`${label}: ${series.map((s) => `${s.name} ${s.values[i] ?? 0}`).join(" · ")}`}</title>
            </rect>
            {hover === i && series.map((s, si) => (
              <circle key={s.name} cx={x(i)} cy={y(s.values[i] ?? 0)} r="3.5"
                      fill={s.color ?? PALETTE[si % PALETTE.length]} />
            ))}
            {i % step === 0 && (
              <text x={x(i)} y={H - 6} textAnchor="middle"
                    className="fill-slate-400 text-[10px]">{label.slice(5)}</text>
            )}
          </g>
        ))}
      </svg>
      <figcaption className="mt-1 flex flex-wrap gap-4">
        {series.map((s, si) => (
          <span key={s.name} className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400">
            <span className="h-2 w-2 rounded-full"
                  style={{ background: s.color ?? PALETTE[si % PALETTE.length] }} aria-hidden />
            {s.name}
            {hover !== null && (
              <span className="font-semibold tabular-nums">{s.values[hover] ?? 0}</span>
            )}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}

// --- Donut chart ----------------------------------------------------------------

export function DonutChart({ data, ariaLabel, size = 168 }: {
  data: { label: string; count: number }[];
  ariaLabel: string;
  size?: number;
}) {
  const total = data.reduce((s, d) => s + d.count, 0);
  const R = 60;
  const C = 2 * Math.PI * R;
  let acc = 0;

  return (
    <figure aria-label={ariaLabel} className="m-0 flex flex-wrap items-center gap-5">
      <svg viewBox="0 0 160 160" width={size} height={size} role="img" aria-label={ariaLabel}>
        <circle cx="80" cy="80" r={R} fill="none" strokeWidth="24"
                className="stroke-slate-100 dark:stroke-slate-800" />
        {total > 0 && data.map((d, i) => {
          const frac = d.count / total;
          const dash = `${(frac * C).toFixed(2)} ${(C - frac * C).toFixed(2)}`;
          const offset = (-acc * C + C / 4).toFixed(2);
          acc += frac;
          return (
            <circle key={d.label} cx="80" cy="80" r={R} fill="none" strokeWidth="24"
                    stroke={PALETTE[i % PALETTE.length]} strokeDasharray={dash}
                    strokeDashoffset={offset}>
              <title>{`${d.label}: ${d.count} (${(frac * 100).toFixed(1)}%)`}</title>
            </circle>
          );
        })}
        <text x="80" y="76" textAnchor="middle"
              className="fill-slate-900 text-xl font-bold tabular-nums dark:fill-slate-100">
          {total.toLocaleString("sq-AL")}
        </text>
        <text x="80" y="92" textAnchor="middle" className="fill-slate-400 text-[10px]">
          gjithsej
        </text>
      </svg>
      <ul className="min-w-0 flex-1 space-y-1.5">
        {data.map((d, i) => (
          <li key={d.label} className="flex items-center gap-2 text-xs">
            <span className="h-2.5 w-2.5 shrink-0 rounded-sm"
                  style={{ background: PALETTE[i % PALETTE.length] }} aria-hidden />
            <span className="min-w-0 flex-1 truncate text-slate-600 dark:text-slate-300"
                  title={d.label}>{d.label}</span>
            <span className="tabular-nums font-medium text-slate-700 dark:text-slate-200">
              {total ? `${((d.count / total) * 100).toFixed(1)}%` : "—"}
            </span>
          </li>
        ))}
      </ul>
    </figure>
  );
}

// --- Horizontal bars ---------------------------------------------------------------

export function HBarChart({ data, ariaLabel, valueLabel = "" }: {
  data: { label: string; count: number }[];
  ariaLabel: string;
  valueLabel?: string;
}) {
  const max = Math.max(1, ...data.map((d) => d.count));
  return (
    <div role="img" aria-label={ariaLabel} className="space-y-2.5">
      {data.map((d, i) => (
        <div key={d.label}>
          <div className="mb-0.5 flex items-baseline justify-between gap-3 text-xs">
            <span className="min-w-0 truncate text-slate-600 dark:text-slate-300" title={d.label}>
              {d.label}
            </span>
            <span className="shrink-0 tabular-nums font-semibold text-slate-700 dark:text-slate-200">
              {d.count.toLocaleString("sq-AL")}{valueLabel && ` ${valueLabel}`}
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
            <div className={cx("h-full rounded-full transition-[width] duration-500")}
                 style={{ width: `${(d.count / max) * 100}%`,
                          background: i === 0 ? "var(--color-brand-700)" : "var(--color-brand-400)" }} />
          </div>
        </div>
      ))}
    </div>
  );
}
