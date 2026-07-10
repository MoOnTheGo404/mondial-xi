"use client";

import Link from "next/link";
import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet, fmtDate, fmtPct } from "@kickoff/shared";
import type { Player, Team } from "@kickoff/shared";
import { Badge, Card, Flag, SectionTitle, Stat } from "@kickoff/ui";
import { ErrorBox } from "@/components/fixtures";

interface PlayerDetail extends Player {
  team: Team;
  goal_log: {
    date: string;
    match_id: string;
    against: string;
    minute: number | null;
    penalty: boolean;
  }[];
  upcoming_fixture_impact?: {
    fixture_id: string;
    date: string;
    opponent: string;
    team_win_prob_with: number;
    team_win_prob_without: number;
    delta_pp: number;
  };
}

export default function PlayerPage({
  params,
}: {
  params: Promise<{ id: string[] }>;
}) {
  const { id } = use(params);
  const playerId = id.join("/");
  const q = useQuery({
    queryKey: ["player", playerId],
    queryFn: () => apiGet<PlayerDetail>(`/players/${playerId}`),
  });

  if (q.isLoading) return <div className="h-96 animate-pulse rounded-lg bg-ink-900" />;
  if (q.isError) return <ErrorBox message={(q.error as Error).message} />;
  const p = q.data!;

  return (
    <div className="space-y-8">
      <section className="flex flex-wrap items-center gap-5 border-b border-ink-800 pb-6">
        <span
          aria-hidden
          className="flex h-20 w-20 items-center justify-center rounded-full bg-ink-800 font-display text-2xl font-black text-ink-100"
        >
          {p.name
            .split(" ")
            .map((w) => w[0])
            .slice(0, 2)
            .join("")}
        </span>
        <div className="min-w-0 flex-1">
          <h1 className="font-display text-4xl font-black uppercase tracking-tight">
            {p.name}
          </h1>
          <Link
            href={`/team/${p.team.team_id}`}
            className="mt-1 inline-flex items-center gap-2 text-ink-300 hover:text-brand"
          >
            <Flag team={p.team} size={20} /> {p.team.name}
          </Link>
          <p className="mt-2 font-mono text-xs text-ink-500">
            No licensed player photo — initials avatar used. Career caps/goals and
            birth date come from Wikidata (CC0) where matched; position requires a
            licensed provider.
          </p>
          <p className="mt-1 font-mono text-xs text-amber-400/90">
            Scorer detail exists for {p.coverage_pct}% of {p.team.name}&apos;s matches in
            this player&apos;s span — recorded goals are a floor, not a career total.
          </p>
          {p.possible_name_collision && (
            <p className="mt-1 font-mono text-xs text-red-400">
              ⚠ Long gap between recorded goals — this ID may merge two same-named
              players (the source has no birthdates).
            </p>
          )}
        </div>
        <dl className="grid grid-cols-2 gap-x-8 gap-y-3 sm:grid-cols-4">
          <Stat
            label="career int'l goals"
            value={p.career_goals ?? "—"}
            hint={
              p.career_goals != null
                ? `Wikidata (CC0), retrieved ${p.career_retrieved ?? "n/a"} — community-maintained, may lag recent matches`
                : "No unambiguous Wikidata match for this player"
            }
          />
          <Stat
            label="career caps"
            value={p.career_caps ?? "—"}
            hint={p.career_caps != null ? "Wikidata (CC0)" : undefined}
          />
          <Stat
            label="recorded goals"
            value={p.goals}
            hint="Floor from the CC0 goalscorer log (partial coverage)"
          />
          <Stat
            label={p.dob ? "born" : "active span"}
            value={
              p.dob
                ? p.dob
                : `${p.first_goal.slice(0, 4)}–${p.last_goal.slice(0, 4)}`
            }
          />
        </dl>
      </section>

      <div className="grid gap-8 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-6">
          <Card className="p-5">
            <SectionTitle sub="attack-side, scoring-derived, shrunken">
              Estimated impact
            </SectionTitle>
            <dl className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              <Stat
                label="attack impact"
                value={`${p.attack_impact.toFixed(3)} xG/m`}
                hint="Shrunken goals contributed per team match while active"
              />
              <Stat
                label="recent impact"
                value={`${p.attack_impact_recent.toFixed(3)} xG/m`}
                hint="Attack impact decayed by time since last recorded goal"
              />
              <Stat
                label="shrinkage weight"
                value={p.shrinkage_weight.toFixed(2)}
                hint="1 = estimate dominated by data; 0 = dominated by the zero prior"
              />
              <Stat
                label="scenario weight"
                value={`${(100 * p.scenario_share).toFixed(0)}%`}
                hint={`Share of the team's recent goal involvements: ${p.recent_goals} of ${p.team_recent_goals} recorded recent goals, blended with the Wikidata career rate${p.career_goals_per_cap != null ? ` (${p.career_goals_per_cap.toFixed(2)} goals/cap)` : " (no career match)"} — the weight used by scenario tools`}
              />
              <Stat
                label="int'l assists"
                value="n/a"
                hint="No legally usable international-assist source exists; the contribution model includes them at weight 0.5 once a licensed provider is configured"
              />
              <Stat label="defensive impact" value="n/a" hint="No licensed defensive data" />
              <Stat
                label="availability"
                value={p.availability?.status ?? "unknown"}
                hint={p.availability?.note}
              />
            </dl>
            <p className="mt-4 rounded border border-ink-700 bg-ink-900 p-3 font-mono text-[11px] leading-relaxed text-ink-400">
              {p.impact_note} Estimates shrink toward zero with a 25-match prior
              {p.shrinkage_weight < 0.5
                ? " — this player's sample is small, so the estimate is strongly shrunk toward the positional average."
                : "."}
            </p>
          </Card>

          {p.upcoming_fixture_impact && (
            <Card className="p-5">
              <SectionTitle sub="user-scenario counterfactual">
                Impact on the next fixture
              </SectionTitle>
              <p className="text-sm text-ink-200">
                <Link
                  className="text-brand hover:underline"
                  href={`/match/${p.upcoming_fixture_impact.fixture_id}`}
                >
                  vs {p.upcoming_fixture_impact.opponent} ({fmtDate(p.upcoming_fixture_impact.date)})
                </Link>
                : {p.team.name} win probability{" "}
                <strong>{fmtPct(p.upcoming_fixture_impact.team_win_prob_with, 1)}</strong> with{" "}
                {p.name} vs{" "}
                <strong>{fmtPct(p.upcoming_fixture_impact.team_win_prob_without, 1)}</strong>{" "}
                if marked unavailable ({p.upcoming_fixture_impact.delta_pp} pp).
              </p>
              <p className="mt-2 font-mono text-[11px] text-amber-400/80">
                Hypothetical scenario — availability is actually unknown.
              </p>
            </Card>
          )}
        </div>

        <aside>
          <Card className="p-5">
            <SectionTitle sub="most recent first">Recorded goals</SectionTitle>
            {p.goal_log.length === 0 && (
              <p className="text-sm text-ink-400">No goal events on record.</p>
            )}
            <ul className="space-y-1.5">
              {p.goal_log.map((g, i) => (
                <li key={i}>
                  <Link
                    href={`/match/${g.match_id}`}
                    className="flex items-center justify-between rounded px-2 py-1 text-sm hover:bg-ink-800"
                  >
                    <span>
                      vs {g.against.replace(/-/g, " ")}
                      {g.penalty && <Badge tone="neutral">pen</Badge>}
                    </span>
                    <span className="font-mono text-xs text-ink-400">
                      {fmtDate(g.date)}
                      {g.minute ? ` · ${Math.round(g.minute)}'` : ""}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          </Card>
        </aside>
      </div>
    </div>
  );
}
