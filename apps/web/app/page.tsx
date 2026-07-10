"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { apiGet, fmtPct } from "@kickoff/shared";
import type { MatchRow, SimulationResult, Snapshot } from "@kickoff/shared";
import { Badge, Card, Flag, SectionTitle, SoccerBall, Stat, Trophy } from "@kickoff/ui";
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
      {/* hero — "stadium at night" */}
      <section className="relative overflow-hidden rounded-2xl border border-ink-700 pitch-glow">
        {/* ambient floodlights + drifting pitch stripes */}
        <div aria-hidden className="pointer-events-none absolute inset-0">
          <div className="floodlight absolute -top-12 left-[12%] h-56 w-44 -rotate-12 animate-[beam-pulse_6s_ease-in-out_infinite]" />
          <div className="floodlight absolute -top-12 right-[16%] h-56 w-44 rotate-12 animate-[beam-pulse_7.5s_ease-in-out_infinite]" />
          <div className="pitch-stripes absolute inset-x-0 bottom-0 h-24 opacity-70" />
        </div>

        <div className="relative grid items-center gap-6 p-6 sm:p-10 lg:grid-cols-[1.55fr_1fr]">
          <div className="animate-fade-up">
            <p className="inline-flex items-center gap-2 rounded-full border border-gold/30 bg-gold/10 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.25em] text-gold">
              <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-gold" />
              Le Mondial · World Cup 2026
            </p>
            <h1 className="mt-4 max-w-2xl font-display text-4xl font-black uppercase leading-[0.9] tracking-tight text-ink-50 sm:text-6xl">
              Who lifts the <span className="text-gold">trophy</span>?
              <span className="mt-1 block text-home">The data has a hunch.</span>
            </h1>
            <p className="mt-4 max-w-xl text-ink-300">
              Calibrated match forecasts, player-scenario experiments and a tournament
              engine that plays the World Cup out tens of thousands of times — built on
              150 years of open international results. Every number carries its model
              version, data cutoff and data-quality grade.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link
                href="/simulator"
                className="btn-glow rounded bg-home px-5 py-2.5 font-display text-sm font-bold uppercase tracking-wide text-ink-950"
              >
                Simulate the World Cup
              </Link>
              <Link
                href="/lab"
                className="rounded border border-ink-600 px-5 py-2.5 font-display text-sm font-bold uppercase tracking-wide text-ink-100 transition-colors hover:border-gold hover:text-gold"
              >
                Open Match Lab
              </Link>
            </div>

            {status.data && (
              <dl className="mt-7 grid max-w-lg grid-cols-2 gap-x-6 gap-y-3 border-t border-ink-800/80 pt-5 sm:grid-cols-4">
                <Stat label="matches" value={status.data.completed_matches.toLocaleString()} />
                <Stat label="data cutoff" value={status.data.data_cutoff} />
                <Stat label="model" value={status.data.model_version} />
                <Stat
                  label="log loss"
                  value={archive.data?.backtest_summary?.metrics.log_loss.toFixed(3) ?? "—"}
                  hint="Untouched chronological test window"
                />
              </dl>
            )}
            {status.isError && (
              <div className="mt-5 max-w-lg">
                <ErrorBox message={(status.error as Error).message} />
              </div>
            )}
          </div>

          {/* animated crest: spinning ball with a gleaming trophy */}
          <div
            aria-hidden
            className="relative mx-auto hidden aspect-square w-full max-w-[19rem] items-center justify-center lg:flex"
          >
            <div className="absolute inset-8 rounded-full bg-home/10 blur-2xl" />
            <div className="absolute inset-12 rounded-full bg-gold/10 blur-2xl" />
            <div className="animate-float">
              <SoccerBall size={228} spin className="drop-shadow-[0_22px_44px_rgba(0,0,0,0.6)]" />
            </div>
            <div
              className="animate-float absolute -right-1 -top-1"
              style={{ animationDelay: "-2.2s" }}
            >
              <Trophy size={96} shine className="drop-shadow-[0_12px_26px_rgba(245,196,81,0.4)]" />
            </div>
          </div>
        </div>
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
                .map((t, i) => (
                  <li key={t.team_id} className="flex items-center gap-3">
                    {i === 0 ? (
                      <Trophy size={22} title="Current favourite" className="shrink-0" />
                    ) : (
                      <Flag team={t.team} size={22} />
                    )}
                    <Link
                      href={`/team/${t.team_id}`}
                      className={`w-32 truncate hover:text-home ${
                        i === 0 ? "font-bold text-gold" : "font-medium"
                      }`}
                    >
                      {t.team.name}
                    </Link>
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-ink-800">
                      <div
                        className={`bar-grow h-full rounded-full ${i === 0 ? "bg-gold" : "bg-home"}`}
                        style={{
                          width: `${(100 * t.reach.champion) / simPost.data.teams[0].reach.champion}%`,
                        }}
                      />
                    </div>
                    <span
                      className={`w-14 text-right font-mono text-sm tabular-nums ${
                        i === 0 ? "text-gold" : "text-ink-200"
                      }`}
                    >
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
