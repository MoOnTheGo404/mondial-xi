"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiGet, fmtPct } from "@kickoff/shared";
import type { MatchRow, SimulationResult, Snapshot } from "@kickoff/shared";
import { Badge, Card, Flag, SectionTitle, Stat } from "@kickoff/ui";
import { ErrorBox, FixtureCard, LoadingGrid } from "@/components/fixtures";

interface FixtureList {
  total: number;
  fixtures: MatchRow[];
  data_cutoff: string;
}
interface Status {
  ready: boolean;
  model_version: string;
  data_cutoff: string;
  completed_matches: number;
  teams: number;
  players: number;
}
interface Archive {
  prospective: { snapshots: Snapshot[]; cumulative: null | Record<string, number> };
  backtest_summary: { metrics: { log_loss: number; accuracy: number; ece: number; n: number } };
}

export default function HomePage() {
  const status = useQuery({
    queryKey: ["system-status"],
    queryFn: () => apiGet<Status>("/system/status"),
  });
  const upcoming = useQuery({
    queryKey: ["fixtures-upcoming"],
    queryFn: () => apiGet<FixtureList>("/fixtures?status=upcoming&limit=6"),
  });
  const simPost = useQuery({
    queryKey: ["sim-champions"],
    queryFn: async () => {
      const res = await fetch("/api/v1/simulations/tournament", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n_sims: 10000, seed: 42 }),
      });
      if (!res.ok) throw new Error("simulation failed");
      return (await res.json()) as SimulationResult;
    },
    staleTime: 600_000,
  });
  const archive = useQuery({
    queryKey: ["archive-home"],
    queryFn: () => apiGet<Archive>("/predictions/archive?limit=30"),
  });
  const recent = useQuery({
    queryKey: ["fixtures-recent-home"],
    queryFn: () => apiGet<FixtureList>("/fixtures?status=recent&limit=6&tournament=FIFA World Cup"),
  });

  return (
    <div className="space-y-10">
      {/* hero */}
      <section className="grid items-end gap-6 border-b border-ink-800 pb-8 lg:grid-cols-[1.4fr_1fr]">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-home">
            The international football forecast
          </p>
          <h1 className="mt-3 max-w-2xl font-display text-4xl font-black uppercase leading-[0.95] tracking-tight text-ink-50 sm:text-5xl">
            What&apos;s likely to happen —{" "}
            <span className="text-home">and why</span> the model believes it
          </h1>
          <p className="mt-4 max-w-xl text-ink-300">
            Calibrated match forecasts, player-scenario experiments and a tournament
            engine that plays the World Cup out tens of thousands of times, built on
            150 years of open international results. Every number carries its model
            version, data cutoff and data-quality grade.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href="/simulator"
              className="btn-glow rounded bg-home px-4 py-2 font-display text-sm font-bold uppercase tracking-wide text-ink-950"
            >
              Simulate the World Cup
            </Link>
            <Link
              href="/lab"
              className="rounded border border-ink-600 px-4 py-2 font-display text-sm font-bold uppercase tracking-wide text-ink-100 transition-colors hover:border-home hover:text-home"
            >
              Open Match Lab
            </Link>
          </div>
        </div>
        <Card className="p-5">
          <SectionTitle sub="live from evaluation artifacts">System</SectionTitle>
          {status.isLoading && <div className="h-24 animate-pulse rounded bg-ink-900" />}
          {status.isError && <ErrorBox message={(status.error as Error).message} />}
          {status.data && (
            <dl className="grid grid-cols-2 gap-4">
              <Stat label="matches ingested" value={status.data.completed_matches.toLocaleString()} />
              <Stat label="data cutoff" value={status.data.data_cutoff} />
              <Stat label="model" value={status.data.model_version} />
              <Stat
                label="backtest log loss"
                value={archive.data?.backtest_summary?.metrics.log_loss.toFixed(3) ?? "—"}
                hint="Untouched chronological test window"
              />
            </dl>
          )}
        </Card>
      </section>

      {/* featured prediction */}
      <section>
        <SectionTitle
          sub={
            upcoming.data
              ? `fixtures from dataset snapshot · cutoff ${upcoming.data.data_cutoff}`
              : undefined
          }
        >
          Next fixtures
        </SectionTitle>
        {upcoming.isLoading && <LoadingGrid />}
        {upcoming.isError && <ErrorBox message={(upcoming.error as Error).message} />}
        {upcoming.data && upcoming.data.fixtures.length === 0 && (
          <Card className="p-6 text-ink-300">
            No scheduled fixtures in the current dataset snapshot.
          </Card>
        )}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {upcoming.data?.fixtures.map((m) => (
            <FixtureCard
              key={m.match_id}
              m={m}
              probs={m.forecast?.probabilities}
              href={`/match/${m.match_id}`}
            />
          ))}
        </div>
      </section>

      {/* championship probabilities */}
      <section>
        <SectionTitle
          sub={
            simPost.data
              ? `${simPost.data.n_sims.toLocaleString()} simulations · seed ${simPost.data.seed} · ${simPost.data.elapsed_ms} ms · remaining tournament from real state`
              : "simulated tournaments"
          }
        >
          World Cup 2026 — championship probabilities
        </SectionTitle>
        {simPost.isLoading && <div className="h-48 animate-pulse rounded-lg bg-ink-900" />}
        {simPost.isError && <ErrorBox message={(simPost.error as Error).message} />}
        {simPost.data && (
          <Card className="p-5">
            <ol className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
              {simPost.data.teams
                .filter((t) => t.reach.champion > 0)
                .slice(0, 12)
                .map((t) => (
                  <li key={t.team_id} className="flex items-center gap-3">
                    <Flag team={t.team} size={22} />
                    <Link
                      href={`/team/${t.team_id}`}
                      className="w-32 truncate font-medium hover:text-home"
                    >
                      {t.team.name}
                    </Link>
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-ink-800">
                      <div
                        className="h-full rounded-full bg-home"
                        style={{
                          width: `${(100 * t.reach.champion) / simPost.data.teams[0].reach.champion}%`,
                        }}
                      />
                    </div>
                    <span className="w-14 text-right font-mono text-sm tabular-nums text-ink-200">
                      {fmtPct(t.reach.champion, 1)}
                    </span>
                  </li>
                ))}
            </ol>
            <p className="mt-4 font-mono text-[11px] text-ink-500">
              Group results and completed knockouts are pinned to real outcomes from the
              dataset; only unplayed matches are simulated.{" "}
              <Link className="text-home hover:underline" href="/simulator">
                Full simulator →
              </Link>
            </p>
          </Card>
        )}
      </section>

      {/* track record + recent results */}
      <section className="grid gap-6 lg:grid-cols-2">
        <div>
          <SectionTitle sub="immutable snapshots, scored after kickoff">
            Forecast track record
          </SectionTitle>
          {archive.isLoading && <div className="h-40 animate-pulse rounded-lg bg-ink-900" />}
          {archive.data && (
            <Card className="p-5">
              {archive.data.prospective.cumulative ? (
                <dl className="grid grid-cols-2 gap-4">
                  <Stat
                    label="scored forecasts"
                    value={archive.data.prospective.cumulative.n_scored}
                  />
                  <Stat
                    label="top-pick accuracy"
                    value={fmtPct(archive.data.prospective.cumulative.top_pick_accuracy, 0)}
                  />
                  <Stat
                    label="mean RPS"
                    value={archive.data.prospective.cumulative.mean_rps.toFixed(4)}
                  />
                  <Stat
                    label="mean log loss"
                    value={archive.data.prospective.cumulative.mean_log_loss.toFixed(4)}
                  />
                </dl>
              ) : (
                <div>
                  <p className="text-sm text-ink-300">
                    {archive.data.prospective.snapshots.length} prospective forecasts
                    recorded and awaiting results.{" "}
                  </p>
                  <p className="mt-2 font-mono text-xs text-ink-500">
                    Prospective forecasts are scored only after their real kickoff — no
                    retroactive “published” predictions, ever.
                  </p>
                </div>
              )}
              <Link
                href="/archive"
                className="mt-4 inline-block font-mono text-xs uppercase tracking-wide text-home hover:underline"
              >
                Full archive →
              </Link>
            </Card>
          )}
        </div>
        <div>
          <SectionTitle sub="World Cup 2026">Latest results</SectionTitle>
          {recent.isLoading && <div className="h-40 animate-pulse rounded-lg bg-ink-900" />}
          {recent.data && (
            <div className="space-y-2">
              {recent.data.fixtures.slice(0, 6).map((m) => (
                <Link
                  key={m.match_id}
                  href={`/match/${m.match_id}`}
                  className="flex items-center justify-between gap-3 rounded-lg border border-ink-800 bg-ink-900/50 px-4 py-2.5 hover:border-ink-600"
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <Flag team={m.home} size={18} />
                    <span className="truncate text-sm">{m.home.name}</span>
                  </span>
                  <span className="shrink-0 font-display font-black tabular-nums">
                    {m.home_score}–{m.away_score}
                    {m.shootout_winner_id ? <span className="text-amber-400"> p</span> : null}
                  </span>
                  <span className="flex min-w-0 items-center justify-end gap-2">
                    <span className="truncate text-right text-sm">{m.away.name}</span>
                    <Flag team={m.away} size={18} />
                  </span>
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="rounded-lg border border-ink-800 bg-ink-900/40 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="max-w-2xl text-sm text-ink-300">
            <Badge tone="signal">open method</Badge>{" "}
            <span className="ml-1">
              Chronological evaluation, isotonic calibration, leakage tests and every
              licensing decision are documented in the methodology.
            </span>
          </p>
          <Link
            href="/methodology"
            className="font-mono text-xs uppercase tracking-wide text-home hover:underline"
          >
            Read the methodology →
          </Link>
        </div>
      </section>
    </div>
  );
}
