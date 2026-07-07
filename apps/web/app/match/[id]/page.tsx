"use client";

import Link from "next/link";
import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet, fmtDate, fmtPct } from "@kickoff/shared";
import type { MatchRow, Prediction, Team } from "@kickoff/shared";
import { Badge, Card, EmptyState, Flag, SectionTitle, Stat } from "@kickoff/ui";
import { ErrorBox, FixtureCard } from "@/components/fixtures";
import { PredictionPanel } from "@/components/prediction";

interface H2H {
  total: number;
  wins_a: number;
  wins_b: number;
  draws: number;
  recent: MatchRow[];
}
interface GoalEvent {
  team_id: string;
  player_id: string;
  scorer: string;
  minute: number | null;
  own_goal: boolean;
  penalty: boolean;
}
interface Detail extends MatchRow {
  head_to_head: H2H;
  home_recent: MatchRow[];
  away_recent: MatchRow[];
  venue: { city: string | null; country: string | null; neutral: boolean; altitude_m: number | null };
  prediction?: Prediction;
  weather?: {
    temp_max_c: number;
    temp_min_c: number;
    precipitation_prob_pct: number;
    wind_max_kmh: number;
    retrieved_at: string;
    attribution: string;
  } | null;
  weather_note?: string | null;
  goals?: GoalEvent[];
  retrospective?: {
    kind: string;
    label: string;
    p_home: number;
    p_draw: number;
    p_away: number;
    outcome: string;
  } | null;
}

function FormStrip({ matches, teamId }: { matches: MatchRow[]; teamId: string }) {
  return (
    <ol className="flex gap-1" aria-label="Recent results, most recent first">
      {matches.slice(0, 8).map((m) => {
        const isHome = m.home.team_id === teamId;
        const gf = isHome ? m.home_score! : m.away_score!;
        const ga = isHome ? m.away_score! : m.home_score!;
        const r = gf > ga ? "W" : gf === ga ? "D" : "L";
        const cls =
          r === "W" ? "bg-home text-ink-950" : r === "D" ? "bg-ink-600 text-ink-100" : "bg-red-500/80 text-ink-50";
        return (
          <li key={m.match_id}>
            <Link
              href={`/match/${m.match_id}`}
              title={`${m.home.name} ${m.home_score}–${m.away_score} ${m.away.name} (${fmtDate(m.date)})`}
              className={`flex h-6 w-6 items-center justify-center rounded font-mono text-xs font-bold ${cls}`}
            >
              {r}
            </Link>
          </li>
        );
      })}
    </ol>
  );
}

export default function MatchPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const q = useQuery({
    queryKey: ["fixture", id],
    queryFn: () => apiGet<Detail>(`/fixtures/${id}`),
  });

  if (q.isLoading)
    return <div className="h-96 animate-pulse rounded-lg bg-ink-900" aria-label="Loading" />;
  if (q.isError) return <ErrorBox message={(q.error as Error).message} />;
  const m = q.data!;
  const finished = m.status === "finished";

  return (
    <div className="space-y-8">
      {/* header */}
      <section className="border-b border-ink-800 pb-6">
        <div className="mb-3 flex flex-wrap items-center gap-2 font-mono text-xs text-ink-400">
          <span>{fmtDate(m.date)}</span>
          <span aria-hidden>·</span>
          <span>{m.tournament}</span>
          {m.venue.city && (
            <>
              <span aria-hidden>·</span>
              <span>
                {m.venue.city}
                {m.venue.country ? `, ${m.venue.country}` : ""}
              </span>
            </>
          )}
          {m.neutral ? <Badge>neutral venue</Badge> : <Badge tone="info">home venue</Badge>}
          {m.venue.altitude_m && (
            <Badge tone="warn" title="High-altitude venue">
              {m.venue.altitude_m} m altitude
            </Badge>
          )}
        </div>
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-4">
          <TeamHeader team={m.home} recent={m.home_recent} />
          <div className="text-center">
            {finished ? (
              <div>
                <div className="font-display text-5xl font-black tabular-nums">
                  {m.home_score}–{m.away_score}
                </div>
                {m.shootout_winner_id && (
                  <div className="mt-1 font-mono text-xs text-amber-400">
                    {m.shootout_winner_id === m.home.team_id ? m.home.name : m.away.name} won on
                    penalties
                  </div>
                )}
              </div>
            ) : (
              <div className="font-display text-3xl font-black uppercase text-ink-500">vs</div>
            )}
          </div>
          <TeamHeader team={m.away} recent={m.away_recent} right />
        </div>
      </section>

      <div className="grid gap-8 lg:grid-cols-[2fr_1fr]">
        <div className="space-y-8">
          {/* prediction or result */}
          {!finished && m.prediction && (
            <PredictionPanel p={m.prediction} home={m.home} away={m.away} />
          )}
          {finished && (
            <Card className="p-5">
              <SectionTitle>Match report</SectionTitle>
              {m.goals && m.goals.length > 0 ? (
                <ol className="space-y-1.5">
                  {m.goals.map((g, i) => (
                    <li key={i} className="flex items-center gap-3 text-sm">
                      <span className="w-10 shrink-0 font-mono text-xs tabular-nums text-ink-400">
                        {g.minute ? `${Math.round(g.minute)}'` : "—"}
                      </span>
                      <Flag
                        team={g.team_id === m.home.team_id ? m.home : m.away}
                        size={16}
                      />
                      <Link
                        href={`/player/${g.player_id}`}
                        className="hover:text-home"
                      >
                        {g.scorer}
                      </Link>
                      {g.penalty && <Badge>pen</Badge>}
                      {g.own_goal && <Badge tone="danger">o.g.</Badge>}
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="text-sm text-ink-400">
                  No goal-scorer detail in the open dataset for this match.
                </p>
              )}
              {m.retrospective && (
                <div className="mt-5 rounded border border-ink-700 bg-ink-900 p-4">
                  <Badge tone="warn">{m.retrospective.kind}</Badge>
                  <p className="mt-2 text-sm text-ink-300">{m.retrospective.label}</p>
                  <p className="mt-2 font-mono text-sm tabular-nums">
                    H {fmtPct(m.retrospective.p_home, 1)} · D {fmtPct(m.retrospective.p_draw, 1)} · A{" "}
                    {fmtPct(m.retrospective.p_away, 1)} — outcome:{" "}
                    <span className="font-bold text-ink-100">{m.retrospective.outcome}</span>
                  </p>
                </div>
              )}
            </Card>
          )}

          {/* head to head */}
          <Card className="p-5">
            <SectionTitle sub={`${m.head_to_head.total} meetings on record`}>
              Head to head
            </SectionTitle>
            {m.head_to_head.total === 0 ? (
              <EmptyState title="First recorded meeting" />
            ) : (
              <>
                <div className="mb-4 grid grid-cols-3 gap-3 text-center">
                  <Stat label={`${m.home.name} wins`} value={m.head_to_head.wins_a} />
                  <Stat label="draws" value={m.head_to_head.draws} />
                  <Stat label={`${m.away.name} wins`} value={m.head_to_head.wins_b} />
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {m.head_to_head.recent.slice(0, 6).map((h) => (
                    <FixtureCard key={h.match_id} m={h} href={`/match/${h.match_id}`} />
                  ))}
                </div>
              </>
            )}
          </Card>
        </div>

        {/* sidebar */}
        <aside className="space-y-6">
          {!finished && (
            <Card className="p-5">
              <SectionTitle>Scenario tools</SectionTitle>
              <p className="text-sm text-ink-300">
                Explore how availability assumptions change this forecast.
              </p>
              <div className="mt-3 flex flex-col gap-2">
                <Link
                  href={`/lab?home=${m.home.team_id}&away=${m.away.team_id}&neutral=${m.neutral}`}
                  className="rounded bg-home px-3 py-2 text-center font-display text-sm font-bold uppercase text-ink-950"
                >
                  Open in Match Lab
                </Link>
                <Link
                  href={`/compare?home=${m.home.team_id}&away=${m.away.team_id}&neutral=${m.neutral}`}
                  className="rounded border border-ink-600 px-3 py-2 text-center font-display text-sm font-bold uppercase text-ink-100 hover:border-home"
                >
                  Compare scenarios
                </Link>
              </div>
            </Card>
          )}

          {!finished && (
            <Card className="p-5">
              <SectionTitle sub="Open-Meteo.com · CC BY 4.0">Match-day weather</SectionTitle>
              {m.weather ? (
                <dl className="grid grid-cols-2 gap-3">
                  <Stat
                    label="temp range"
                    value={`${Math.round(m.weather.temp_min_c)}–${Math.round(m.weather.temp_max_c)}°C`}
                  />
                  <Stat label="rain chance" value={`${m.weather.precipitation_prob_pct}%`} />
                  <Stat label="max wind" value={`${Math.round(m.weather.wind_max_kmh)} km/h`} />
                  <div className="col-span-2 font-mono text-[10px] text-ink-500">
                    retrieved {m.weather.retrieved_at} · display only — weather is not a model
                    input
                  </div>
                </dl>
              ) : (
                <p className="text-sm text-ink-400">{m.weather_note ?? "Unavailable."}</p>
              )}
            </Card>
          )}

          <Card className="p-5">
            <SectionTitle>Lineups &amp; availability</SectionTitle>
            <p className="text-sm text-ink-400">
              Confirmed lineups and injury feeds require a licensed provider and are not
              configured. Player availability defaults to <em>unknown</em>; the Match Lab
              lets you set your own labeled assumptions.
            </p>
            <Link
              href="/methodology#availability"
              className="mt-2 inline-block font-mono text-xs text-home hover:underline"
            >
              Why? →
            </Link>
          </Card>
        </aside>
      </div>
    </div>
  );
}

function TeamHeader({
  team,
  recent,
  right = false,
}: {
  team: Team;
  recent: MatchRow[];
  right?: boolean;
}) {
  return (
    <div className={right ? "justify-items-end text-right" : ""}>
      <Link
        href={`/team/${team.team_id}`}
        className={`flex items-center gap-3 hover:text-home ${right ? "flex-row-reverse" : ""}`}
      >
        <Flag team={team} size={40} />
        <span>
          <span className="block font-display text-2xl font-black leading-none">
            {team.name}
          </span>
          <span className="mt-1 block font-mono text-xs text-ink-400">
            Elo {team.elo?.toFixed(0) ?? "—"} · {team.matches_played} matches
          </span>
        </span>
      </Link>
      <div className={`mt-2 ${right ? "flex justify-end" : ""}`}>
        <FormStrip matches={recent} teamId={team.team_id} />
      </div>
    </div>
  );
}
