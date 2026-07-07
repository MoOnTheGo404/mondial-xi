"use client";

import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost, fmtPct } from "@kickoff/shared";
import type { BracketMatch, GroupRow, SimulationResult } from "@kickoff/shared";
import { Badge, Card, Flag, SectionTitle } from "@kickoff/ui";
import { ErrorBox } from "@/components/fixtures";

interface TournamentDetail {
  tournament_id: string;
  name: string;
  config_version: string;
  sources: string[];
  format: { teams: number; groups: number; best_thirds: number };
  tiebreaker_notes: string;
  groups: Record<string, GroupRow[]>;
  bracket: { round: string; window: string[]; matches: BracketMatch[] }[];
  data_cutoff: string;
}

interface Lock {
  round: string;
  team_a: string;
  team_b: string;
  winner: string;
}

const ROUND_LABEL: Record<string, string> = {
  R32: "Round of 32",
  R16: "Round of 16",
  QF: "Quarter-finals",
  SF: "Semi-finals",
  F: "Final",
};

/** CSV cell sanitizer: quotes + neutralizes leading =+-@ (formula injection). */
function csvCell(v: string | number): string {
  let s = String(v);
  if (/^[=+\-@]/.test(s)) s = `'${s}`;
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function downloadCsv(sim: SimulationResult) {
  const rounds = ["R32", "R16", "QF", "SF", "F", "champion"];
  const header = ["team", "team_id", ...rounds, "n_sims", "seed", "mode", "model_version"];
  const lines = [header.join(",")];
  for (const t of sim.teams) {
    lines.push(
      [
        csvCell(t.team.name),
        csvCell(t.team_id),
        ...rounds.map((r) => csvCell(t.reach[r] ?? 0)),
        sim.n_sims,
        sim.seed,
        csvCell(sim.mode),
        csvCell(sim.model_version),
      ].join(","),
    );
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `kickoff-atlas-sim-${sim.seed}-${sim.n_sims}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

export default function SimulatorPage() {
  const [nSims, setNSims] = useState(10_000);
  const [seed, setSeed] = useState(42);
  const [fromScratch, setFromScratch] = useState(false);
  const [locks, setLocks] = useState<Lock[]>([]);
  const [runKey, setRunKey] = useState(0);

  const detail = useQuery({
    queryKey: ["wc2026"],
    queryFn: () => apiGet<TournamentDetail>("/tournaments/wc2026"),
    staleTime: Infinity,
  });

  const simBody = useMemo(
    () => ({ n_sims: nSims, seed, from_scratch: fromScratch, locked: locks }),
    [nSims, seed, fromScratch, locks],
  );
  const sim = useQuery({
    queryKey: ["simulate", simBody, runKey],
    queryFn: () => apiPost<SimulationResult>("/simulations/tournament", simBody),
    placeholderData: (prev) => prev,
  });

  const toggleLock = (round: string, a: string, b: string, winner: string) => {
    setLocks((prev) => {
      const without = prev.filter(
        (l) => !(l.round === round && new Set([l.team_a, l.team_b]).has(a)),
      );
      const existing = prev.find(
        (l) => l.round === round && new Set([l.team_a, l.team_b]).has(a) && l.winner === winner,
      );
      return existing ? without : [...without, { round, team_a: a, team_b: b, winner }];
    });
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-black uppercase tracking-tight">
          World Cup 2026 Simulator
        </h1>
        {detail.data && (
          <p className="mt-1 font-mono text-xs text-ink-400">
            config v{detail.data.config_version} (rules verified from cited sources) · real
            results pinned up to data cutoff {detail.data.data_cutoff}
          </p>
        )}
      </div>

      {/* controls */}
      <Card className="flex flex-wrap items-end gap-4 p-4">
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[11px] uppercase tracking-wide text-ink-400">
            Simulations
          </span>
          <select
            value={nSims}
            onChange={(e) => setNSims(Number(e.target.value))}
            className="rounded border border-ink-700 bg-ink-900 px-2 py-2 text-sm"
          >
            {[2000, 5000, 10000, 20000].map((n) => (
              <option key={n} value={n}>
                {n.toLocaleString()}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[11px] uppercase tracking-wide text-ink-400">Seed</span>
          <input
            type="number"
            value={seed}
            min={0}
            onChange={(e) => setSeed(Math.max(0, Number(e.target.value)))}
            className="w-24 rounded border border-ink-700 bg-ink-900 px-2 py-2 text-sm tabular-nums"
          />
        </label>
        <label className="flex items-center gap-2 pb-2" title="Ignore real results and replay the whole tournament from the group stage">
          <input
            type="checkbox"
            checked={fromScratch}
            onChange={(e) => setFromScratch(e.target.checked)}
            className="h-4 w-4 accent-home"
          />
          <span className="text-sm">What-if: replay from group stage</span>
        </label>
        <button
          type="button"
          onClick={() => setRunKey((k) => k + 1)}
          className="rounded bg-home px-4 py-2 font-display text-sm font-bold uppercase text-ink-950"
        >
          Re-run
        </button>
        {locks.length > 0 && (
          <button
            type="button"
            onClick={() => setLocks([])}
            className="rounded border border-amber-500/50 px-3 py-2 font-mono text-xs uppercase text-amber-300"
          >
            Clear {locks.length} lock{locks.length > 1 ? "s" : ""}
          </button>
        )}
        {sim.data && (
          <button
            type="button"
            onClick={() => downloadCsv(sim.data)}
            className="rounded border border-ink-600 px-3 py-2 font-mono text-xs uppercase text-ink-200 hover:border-home"
          >
            Export CSV
          </button>
        )}
        <span className="ml-auto font-mono text-xs text-ink-400" role="status">
          {sim.isFetching
            ? "simulating…"
            : sim.data
              ? `${sim.data.n_sims.toLocaleString()} sims in ${sim.data.elapsed_ms} ms · seed ${sim.data.seed} · ${sim.data.mode}`
              : ""}
        </span>
      </Card>

      {sim.isError && <ErrorBox message={(sim.error as Error).message} />}

      {/* probabilities table */}
      {sim.data && (
        <Card className="overflow-x-auto p-5">
          <SectionTitle sub="probability of reaching each round">
            Advancement probabilities
          </SectionTitle>
          <table className="w-full min-w-[640px] text-sm">
            <thead>
              <tr className="border-b border-ink-700 font-mono text-[11px] uppercase text-ink-400">
                <th className="py-2 pr-2 text-left">Team</th>
                {["R32", "R16", "QF", "SF", "F", "champion"].map((r) => (
                  <th key={r} className="px-2 py-2 text-right">
                    {r === "champion" ? "🏆 Champion" : r}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sim.data.teams
                .filter((t) => t.reach.R32 > 0 || fromScratch)
                .slice(0, 24)
                .map((t) => (
                  <tr key={t.team_id} className="border-b border-ink-800/60">
                    <td className="py-1.5 pr-2">
                      <span className="flex items-center gap-2">
                        <Flag team={t.team} size={18} />
                        <span className="truncate">{t.team.name}</span>
                      </span>
                    </td>
                    {(["R32", "R16", "QF", "SF", "F", "champion"] as const).map((r) => {
                      const v = t.reach[r] ?? 0;
                      return (
                        <td
                          key={r}
                          className="px-2 py-1.5 text-right font-mono tabular-nums"
                          style={{
                            color:
                              v === 0
                                ? "#55685c"
                                : v === 1
                                  ? "#a3e635"
                                  : `rgba(228, 234, 230, ${0.45 + 0.55 * v})`,
                          }}
                        >
                          {v === 0 ? "—" : v === 1 ? "✓" : fmtPct(v, 1)}
                        </td>
                      );
                    })}
                  </tr>
                ))}
            </tbody>
          </table>
        </Card>
      )}

      {/* bracket with lock controls */}
      {detail.data && (
        <section>
          <SectionTitle sub="lock a winner for any unplayed pairing, then re-run">
            Knockout bracket
          </SectionTitle>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
            {detail.data.bracket.map((rnd) => (
              <Card key={rnd.round} className="p-3">
                <h3 className="mb-2 font-display text-sm font-bold uppercase text-ink-200">
                  {ROUND_LABEL[rnd.round]}
                </h3>
                <div className="space-y-2">
                  {rnd.matches.length === 0 && (
                    <p className="font-mono text-[11px] text-ink-500">
                      Pairings not yet decided at data cutoff — simulated each run.
                    </p>
                  )}
                  {rnd.matches.map((mm, i) => (
                    <div key={i} className="rounded border border-ink-800 bg-ink-900/60 p-2">
                      {(["home", "away"] as const).map((side) => {
                        const team = mm[side];
                        const goals = side === "home" ? mm.home_goals : mm.away_goals;
                        const won = mm.winner_id === team.team_id;
                        const locked = locks.find(
                          (l) =>
                            l.round === rnd.round &&
                            new Set([l.team_a, l.team_b]).has(team.team_id) &&
                            l.winner === team.team_id,
                        );
                        return (
                          <div
                            key={side}
                            className="flex items-center justify-between gap-2 py-0.5"
                          >
                            <span className="flex min-w-0 items-center gap-1.5 text-sm">
                              <Flag team={team} size={16} />
                              <span
                                className={`truncate ${won ? "font-bold text-ink-50" : ""}`}
                              >
                                {team.name}
                              </span>
                            </span>
                            {mm.status === "finished" ? (
                              <span className="font-mono text-sm tabular-nums">
                                {goals}
                                {mm.shootout && won ? "·p" : ""}
                              </span>
                            ) : (
                              <button
                                type="button"
                                aria-pressed={Boolean(locked)}
                                aria-label={`Lock ${team.name} to win this ${ROUND_LABEL[rnd.round]} tie`}
                                title={`Lock ${team.name} to win this ${ROUND_LABEL[rnd.round]} tie`}
                                onClick={() =>
                                  toggleLock(
                                    rnd.round,
                                    mm.home.team_id,
                                    mm.away.team_id,
                                    team.team_id,
                                  )
                                }
                                className={`rounded px-1.5 py-0.5 font-mono text-[10px] uppercase ${
                                  locked
                                    ? "bg-amber-400 font-bold text-ink-950"
                                    : "border border-ink-700 text-ink-400 hover:border-amber-400 hover:text-amber-300"
                                }`}
                              >
                                {locked ? "locked" : "lock win"}
                              </button>
                            )}
                          </div>
                        );
                      })}
                      {mm.status === "finished" && (
                        <p className="mt-0.5 font-mono text-[10px] text-ink-500">
                          final{mm.shootout ? " · penalties" : ""}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </Card>
            ))}
          </div>
        </section>
      )}

      {/* group tables */}
      {detail.data && (
        <section>
          <SectionTitle
            sub={detail.data.tiebreaker_notes}
          >
            Group stage (final tables)
          </SectionTitle>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {Object.entries(detail.data.groups).map(([g, rows]) => (
              <Card key={g} className="p-3">
                <h3 className="mb-2 font-display text-sm font-bold uppercase">
                  Group {g}
                </h3>
                <table className="w-full text-sm">
                  <thead className="sr-only">
                    <tr>
                      <th>Team</th>
                      <th>Points</th>
                      <th>Goal difference</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((r) => (
                      <tr
                        key={r.team_id}
                        className={r.rank <= 2 ? "text-ink-50" : "text-ink-400"}
                      >
                        <td className="flex items-center gap-1.5 py-1">
                          <span className="w-3 font-mono text-[10px]">{r.rank}</span>
                          <Flag team={r.team} size={16} />
                          <span className="truncate">{r.team.name}</span>
                        </td>
                        <td className="text-right font-mono tabular-nums">{r.points}</td>
                        <td className="w-10 text-right font-mono tabular-nums">
                          {r.gd > 0 ? `+${r.gd}` : r.gd}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            ))}
          </div>
          <p className="mt-3 font-mono text-[11px] text-ink-500">
            Top two (bright) advance directly; eight best thirds also advanced.{" "}
            <Badge>real results from dataset</Badge>
          </p>
        </section>
      )}
    </div>
  );
}
