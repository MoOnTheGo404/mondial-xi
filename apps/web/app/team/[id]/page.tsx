"use client";

import Link from "next/link";
import { use, useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiGet, fmtDate } from "@kickoff/shared";
import type { MatchRow, Player, Team } from "@kickoff/shared";
import { Badge, Card, EmptyState, Flag, SectionTitle, Stat } from "@kickoff/ui";
import { ErrorBox, FixtureCard } from "@/components/fixtures";
import { EloChart } from "@/components/elo-chart";

interface TeamDetail extends Team {
  form_last10: number;
  rolling_goals_for: number;
  rolling_goals_against: number;
  record: Record<"home" | "away" | "neutral", { played: number; wins: number; draws: number; losses: number }>;
  recent_matches: MatchRow[];
  upcoming_fixtures: MatchRow[];
  known_attacking_contributors: Player[];
  squad_note: string;
  world_cup_editions: number[];
  data_density_warning: string | null;
}

export default function TeamPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const q = useQuery({
    queryKey: ["team", id],
    queryFn: () => apiGet<TeamDetail>(`/teams/${id}`),
  });
  const [comp, setComp] = useState<"all" | "competitive" | "friendly">("all");
  const [venue, setVenue] = useState<"all" | "home" | "away" | "neutral">("all");
  const matches = useQuery({
    queryKey: ["team-matches", id, comp, venue],
    queryFn: () =>
      apiGet<{ total: number; matches: MatchRow[] }>(
        `/teams/${id}/matches?competitions=${comp}&venue=${venue}&limit=20`,
      ),
    placeholderData: keepPreviousData,
  });

  if (q.isLoading) return <div className="h-96 animate-pulse rounded-lg bg-ink-900" />;
  if (q.isError) return <ErrorBox message={(q.error as Error).message} />;
  const t = q.data!;

  return (
    <div className="space-y-8">
      <section className="flex flex-wrap items-center gap-5 border-b border-ink-800 pb-6">
        <Flag team={t} size={64} />
        <div className="min-w-0 flex-1">
          <h1 className="font-display text-4xl font-black uppercase tracking-tight">
            {t.name}
          </h1>
          <p className="mt-1 flex flex-wrap items-center gap-2 font-mono text-xs text-ink-400">
            <span>{t.confederation}</span>
            {t.is_historical && <Badge>historical identity</Badge>}
            {t.world_cup_editions.length > 0 && (
              <span>
                World Cups: {t.world_cup_editions.length} (
                {t.world_cup_editions.slice(-3).join(", ")}
                {t.world_cup_editions.length > 3 ? "…" : ""})
              </span>
            )}
          </p>
          {t.data_density_warning && (
            <p className="mt-2 font-mono text-xs text-amber-400">
              ⚠ {t.data_density_warning}
            </p>
          )}
        </div>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4">
          <Stat label="Elo" value={t.elo ? Math.round(t.elo) : "—"} />
          <Stat label="form (pts/match)" value={t.form_last10.toFixed(2)} hint="Exponentially weighted, last 10" />
          <Stat label="goals for (r10)" value={t.rolling_goals_for.toFixed(2)} />
          <Stat label="goals against (r10)" value={t.rolling_goals_against.toFixed(2)} />
        </dl>
      </section>

      <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-8">
          <Card className="p-5">
            <SectionTitle sub="pre-match rating before each game since 1960">
              Elo history
            </SectionTitle>
            <EloChart teamId={id} teamName={t.name} />
          </Card>

          <section>
            <SectionTitle sub={matches.data ? `${matches.data.total.toLocaleString()} matches` : ""}>
              Match history
            </SectionTitle>
            <div className="mb-3 flex flex-wrap gap-2">
              <div role="group" aria-label="Competition filter" className="flex overflow-hidden rounded border border-ink-700">
                {(["all", "competitive", "friendly"] as const).map((c) => (
                  <button
                    key={c}
                    type="button"
                    aria-pressed={comp === c}
                    onClick={() => setComp(c)}
                    className={`px-2.5 py-1 text-xs capitalize ${comp === c ? "bg-home font-bold text-ink-950" : "text-ink-300 hover:bg-ink-800"}`}
                  >
                    {c}
                  </button>
                ))}
              </div>
              <div role="group" aria-label="Venue filter" className="flex overflow-hidden rounded border border-ink-700">
                {(["all", "home", "away", "neutral"] as const).map((v) => (
                  <button
                    key={v}
                    type="button"
                    aria-pressed={venue === v}
                    onClick={() => setVenue(v)}
                    className={`px-2.5 py-1 text-xs capitalize ${venue === v ? "bg-home font-bold text-ink-950" : "text-ink-300 hover:bg-ink-800"}`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>
            <div className={`grid gap-3 sm:grid-cols-2 ${matches.isPlaceholderData ? "opacity-60" : ""}`}>
              {matches.data?.matches.map((m) => (
                <FixtureCard key={m.match_id} m={m} href={`/match/${m.match_id}`} />
              ))}
            </div>
            {matches.data?.matches.length === 0 && (
              <EmptyState title="No matches under these filters" />
            )}
          </section>
        </div>

        <aside className="space-y-6">
          <Card className="p-5">
            <SectionTitle>Record by venue</SectionTitle>
            <table className="w-full text-sm">
              <thead>
                <tr className="font-mono text-[11px] uppercase text-ink-400">
                  <th className="py-1 text-left">Venue</th>
                  <th className="text-right">P</th>
                  <th className="text-right">W</th>
                  <th className="text-right">D</th>
                  <th className="text-right">L</th>
                </tr>
              </thead>
              <tbody className="font-mono tabular-nums">
                {(["home", "away", "neutral"] as const).map((k) => (
                  <tr key={k} className="border-t border-ink-800">
                    <td className="py-1.5 capitalize">{k}</td>
                    <td className="text-right">{t.record[k].played}</td>
                    <td className="text-right text-home">{t.record[k].wins}</td>
                    <td className="text-right text-ink-300">{t.record[k].draws}</td>
                    <td className="text-right text-red-400">{t.record[k].losses}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          {t.upcoming_fixtures.length > 0 && (
            <Card className="p-5">
              <SectionTitle>Upcoming</SectionTitle>
              <ul className="space-y-2">
                {t.upcoming_fixtures.map((m) => (
                  <li key={m.match_id}>
                    <Link
                      href={`/match/${m.match_id}`}
                      className="flex items-center justify-between rounded border border-ink-800 px-3 py-2 text-sm hover:border-ink-600"
                    >
                      <span className="flex items-center gap-2">
                        <Flag team={m.home} size={16} />
                        {m.home.name} v {m.away.name}
                        <Flag team={m.away} size={16} />
                      </span>
                      <span className="font-mono text-xs text-ink-400">{fmtDate(m.date)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            </Card>
          )}

          <Card className="p-5">
            <SectionTitle sub="from goalscorer records">Attack contributors</SectionTitle>
            {t.known_attacking_contributors.length === 0 && (
              <p className="text-sm text-ink-400">No recently active scorers on record.</p>
            )}
            <ul className="space-y-1.5">
              {t.known_attacking_contributors.slice(0, 10).map((p) => (
                <li key={p.player_id}>
                  <Link
                    href={`/player/${p.player_id}`}
                    className="flex items-center justify-between rounded px-2 py-1 text-sm hover:bg-ink-800"
                  >
                    <span>{p.name}</span>
                    <span className="font-mono text-xs text-ink-400">
                      {p.goals}g rec. · {(100 * p.goal_share_recent).toFixed(0)}% share
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
            <p className="mt-3 font-mono text-[10px] leading-snug text-ink-500">{t.squad_note}</p>
          </Card>

          <Card className="p-5">
            <SectionTitle>Forecast shortcuts</SectionTitle>
            <div className="flex flex-col gap-2">
              <Link
                href={`/lab?home=${id}`}
                className="rounded bg-home px-3 py-2 text-center font-display text-sm font-bold uppercase text-ink-950"
              >
                Forecast a {t.name} match
              </Link>
              <Link
                href="/simulator"
                className="rounded border border-ink-600 px-3 py-2 text-center font-display text-sm font-bold uppercase hover:border-home"
              >
                Tournament odds
              </Link>
            </div>
          </Card>
        </aside>
      </div>
    </div>
  );
}
