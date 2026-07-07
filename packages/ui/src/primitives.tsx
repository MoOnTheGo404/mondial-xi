import React from "react";

export function Card({
  children,
  className = "",
  ...rest
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={`rounded-lg border border-ink-700 bg-ink-900/70 ${className}`}
      {...rest}
    >
      {children}
    </div>
  );
}

export function SectionTitle({
  children,
  sub,
}: {
  children: React.ReactNode;
  sub?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="font-display text-lg font-bold uppercase tracking-wider text-ink-50">
        {children}
      </h2>
      {sub && <span className="font-mono text-xs text-ink-400">{sub}</span>}
    </div>
  );
}

export function Badge({
  tone = "neutral",
  children,
  title,
}: {
  tone?: "neutral" | "signal" | "warn" | "info" | "danger";
  children: React.ReactNode;
  title?: string;
}) {
  const tones: Record<string, string> = {
    neutral: "border-ink-600 text-ink-300",
    signal: "border-home/50 text-home",
    warn: "border-amber-500/50 text-amber-400",
    info: "border-away/50 text-away",
    danger: "border-red-500/50 text-red-400",
  };
  return (
    <span
      title={title}
      className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 font-mono text-[10px] uppercase tracking-wide ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

export function Stat({
  label,
  value,
  hint,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
}) {
  return (
    <div title={hint}>
      <div className="font-mono text-[11px] uppercase tracking-wider text-ink-400">
        {label}
      </div>
      <div className="font-display text-xl font-bold tabular-nums text-ink-50">
        {value}
      </div>
    </div>
  );
}

export function EmptyState({
  title,
  detail,
}: {
  title: string;
  detail?: string;
}) {
  return (
    <div className="rounded-lg border border-dashed border-ink-600 p-6 text-center">
      <p className="font-display font-semibold text-ink-200">{title}</p>
      {detail && <p className="mt-1 text-sm text-ink-400">{detail}</p>}
    </div>
  );
}
