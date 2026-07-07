"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiGet, fmtPct } from "@kickoff/shared";
import type { Snapshot } from "@kickoff/shared";
import { Badge, Card, Flag, ProbBar, SectionTitle, Stat } from "@kickoff/ui";
import { ErrorBox } from "@/components/fixtures";

interface Archive {
  prospective: {
    label: string;
    snapshots: Snapshot[];
    cumulative: {
      n_scored: number;
      mean_rps: number;
      mean_brier: number;
      mean_log_loss: number;
      top_pick_accuracy: number;
    } | null;
  };
  backtest_summary: {
    label: string;
    window: string[];
    metrics: { log_loss: number; rps: number; brier: number; accuracy: number; ece: number; n: number };
  } | null;
}

export default function ArchivePage() {
  const q = useQuery({
    queryKey: ["archive"],
    queryFn: () => apiGet<Archive>("/predictions/archive?limit=200"),
  });

  if (q.isLoading) return <div className="h-96 animate-pulse rounded-lg bg-ink-900" />;
  if (q.isError) return <ErrorBox message={(q.error as Error).message} />;
  const d = q.data!;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-black uppercase tracking-tight">
          Prediction Archive
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-300">
          Every genuine prospective forecast is stored as an immutable, content-hashed
          snapshot before kickoff, then scored against the real result. Backtests live in
          a separate, clearly-labeled section — they are never presented as published
          forecasts.
        </p>
      </div>

      <section>
        <SectionTitle sub={d.prospective.label}>
          Prospective forecasts
        </SectionTitle>
        {d.prospective.cumulative && (
          <Card className="mb-4 p-5">
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-5">
              <Stat label="scored" value={d.prospective.cumulative.n_scored} />
              <Stat label="top-pick acc." value={fmtPct(d.prospective.cumulative.top_pick_accuracy)} />
              <Stat label="mean RPS" value={d.prospective.cumulative.mean_rps.toFixed(4)} />
              <Stat label="mean Brier" value={d.prospective.cumulative.mean_brier.toFixed(4)} />
              <Stat label="mean log loss" value={d.prospective.cumulative.mean_log_loss.toFixed(4)} />
            </dl>
          </Card>
        )}
        <div className="space-y-3">
          {d.prospective.snapshots.map((s) => (
            <Card key={s.id} className="p-4">
              <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                <span className="font-mono text-xs text-ink-400">{s.kickoff_date}</span>
                <Link
                  href={`/match/${s.fixture_id}`}
                  className="flex items-center gap-2 font-medium hover:text-home"
                >
                  {s.home && <Flag team={s.home} size={18} />}
                  {s.home?.name ?? s.home_id}
                  <span className="text-ink-500">v</span>
                  {s.away?.name ?? s.away_id}
                  {s.away && <Flag team={s.away} size={18} />}
                </Link>
                <Badge>{s.version_label}</Badge>
                <span className="font-mono text-[10px] text-ink-500">
                  model {s.model_version} · cutoff {s.data_cutoff} · generated{" "}
                  {s.generated_at.slice(0, 16).replace("T", " ")} · hash{" "}
                  {s.content_hash.slice(0, 10)}…
                </span>
                {s.result ? (
                  <span className="ml-auto flex items-center gap-3">
                    <span className="font-display font-black tabular-nums">
                      {s.result.home}–{s.result.away}
                    </span>
                    <Badge tone={s.scores?.top_pick_correct ? "signal" : "danger"}>
                      {s.scores?.top_pick_correct ? "top pick ✓" : "top pick ✗"}
                    </Badge>
                    <span className="font-mono text-xs text-ink-400">
                      RPS {s.scores?.rps.toFixed(3)}
                    </span>
                  </span>
                ) : (
                  <Badge tone="info">awaiting result</Badge>
                )}
              </div>
              <div className="mt-3 max-w-xl">
                <ProbBar
                  probs={s.probabilities}
                  homeName={s.home?.name}
                  awayName={s.away?.name}
                  showLabels
                />
              </div>
            </Card>
          ))}
          {d.prospective.snapshots.length === 0 && (
            <Card className="p-6 text-ink-300">No snapshots yet.</Card>
          )}
        </div>
      </section>

      {d.backtest_summary && (
        <section>
          <SectionTitle sub={d.backtest_summary.label}>
            Historical backtest (separate)
          </SectionTitle>
          <Card className="p-5">
            <p className="mb-3 font-mono text-xs text-ink-400">
              Chronological test window {d.backtest_summary.window[0]} →{" "}
              {d.backtest_summary.window[1]} · untouched during model selection
            </p>
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-6">
              <Stat label="matches" value={d.backtest_summary.metrics.n.toLocaleString()} />
              <Stat label="log loss" value={d.backtest_summary.metrics.log_loss.toFixed(4)} />
              <Stat label="RPS" value={d.backtest_summary.metrics.rps.toFixed(4)} />
              <Stat label="Brier" value={d.backtest_summary.metrics.brier.toFixed(4)} />
              <Stat label="accuracy" value={fmtPct(d.backtest_summary.metrics.accuracy)} />
              <Stat label="ECE" value={d.backtest_summary.metrics.ece.toFixed(4)} />
            </dl>
            <Link
              href="/performance"
              className="mt-4 inline-block font-mono text-xs uppercase tracking-wide text-home hover:underline"
            >
              Full model performance →
            </Link>
          </Card>
        </section>
      )}
    </div>
  );
}
