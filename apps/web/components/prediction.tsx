"use client";

import type { Prediction, Team } from "@kickoff/shared";
import { fmtPct } from "@kickoff/shared";
import { Badge, Card, ProbBar, SectionTitle, Stat } from "@kickoff/ui";

export function QualityBadge({ grade }: { grade: string }) {
  const tone = grade === "A" ? "signal" : grade === "B" ? "info" : "warn";
  return (
    <Badge tone={tone} title="Data-quality grade based on both teams' match history depth">
      data quality {grade}
    </Badge>
  );
}

export function ModelStamp({ p }: { p: Prediction }) {
  return (
    <div className="flex flex-wrap items-center gap-2 font-mono text-[11px] text-ink-400">
      <span>model {p.model_version}</span>
      <span aria-hidden>·</span>
      <span>champion: {p.champion_model}</span>
      <span aria-hidden>·</span>
      <span>data cutoff {p.data_cutoff}</span>
      <QualityBadge grade={p.data_quality.grade} />
      {p.scenario_adjusted && <Badge tone="warn">user scenario</Badge>}
    </div>
  );
}

export function ScoreMatrix({
  matrix,
  homeName,
  awayName,
  max = 5,
}: {
  matrix: number[][];
  homeName: string;
  awayName: string;
  max?: number;
}) {
  const peak = Math.max(...matrix.flat());
  return (
    <div className="overflow-x-auto">
      <table className="border-separate border-spacing-0.5 font-mono text-[11px]">
        <caption className="sr-only">
          Scoreline probability matrix: rows are {homeName} goals, columns are {awayName} goals.
        </caption>
        <thead>
          <tr>
            <th className="p-1 text-ink-400" scope="col">
              <span aria-hidden>↓</span> {homeName.slice(0, 3).toUpperCase()} /{" "}
              {awayName.slice(0, 3).toUpperCase()} <span aria-hidden>→</span>
            </th>
            {Array.from({ length: max + 1 }).map((_, j) => (
              <th key={j} scope="col" className="p-1 text-ink-400">
                {j}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {matrix.slice(0, max + 1).map((row, i) => (
            <tr key={i}>
              <th scope="row" className="p-1 text-ink-400">
                {i}
              </th>
              {row.slice(0, max + 1).map((p, j) => {
                const alpha = peak > 0 ? p / peak : 0;
                return (
                  <td
                    key={j}
                    className="rounded-sm p-1 text-center tabular-nums"
                    style={{
                      background: `rgba(163, 230, 53, ${(0.85 * alpha).toFixed(3)})`,
                      color: alpha > 0.55 ? "#0d1410" : "#a6b5ac",
                      minWidth: 38,
                    }}
                    title={`${homeName} ${i}–${j} ${awayName}: ${fmtPct(p, 1)}`}
                  >
                    {(100 * p).toFixed(1)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function PredictionPanel({
  p,
  home,
  away,
}: {
  p: Prediction;
  home: Team;
  away: Team;
}) {
  return (
    <div className="space-y-6">
      <Card className="p-5">
        <SectionTitle sub={<ModelStamp p={p} />}>Forecast</SectionTitle>
        <div className="grid grid-cols-3 gap-3 text-center">
          <Stat label={`${home.name} win`} value={fmtPct(p.probabilities.home, 1)} />
          <Stat label="Draw" value={fmtPct(p.probabilities.draw, 1)} />
          <Stat label={`${away.name} win`} value={fmtPct(p.probabilities.away, 1)} />
        </div>
        <div className="mt-4">
          <ProbBar probs={p.probabilities} homeName={home.name} awayName={away.name} height={14} />
        </div>
        {p.scenario_adjusted && (
          <div className="mt-4 rounded border border-amber-500/30 bg-amber-950/20 p-3 text-xs text-amber-200">
            <p className="font-bold uppercase tracking-wide">Scenario-adjusted forecast</p>
            <p className="mt-1">
              Team-only baseline: {fmtPct(p.team_only_probabilities.home, 1)} /{" "}
              {fmtPct(p.team_only_probabilities.draw, 1)} /{" "}
              {fmtPct(p.team_only_probabilities.away, 1)} — differences come from your
              player-availability assumptions below.
            </p>
          </div>
        )}
        <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="xG home" value={p.expected_goals.home.toFixed(2)} />
          <Stat label="xG away" value={p.expected_goals.away.toFixed(2)} />
          <Stat label="BTTS" value={fmtPct(p.btts)} hint="Both teams to score" />
          <Stat label="Over 2.5" value={fmtPct(p.over_2_5)} />
        </dl>
      </Card>

      <Card className="p-5">
        <SectionTitle sub="from the Dixon–Coles goal model">Scorelines</SectionTitle>
        <div className="grid gap-6 lg:grid-cols-[auto_1fr]">
          <ScoreMatrix matrix={p.score_matrix} homeName={home.name} awayName={away.name} />
          <div>
            <h3 className="mb-2 font-mono text-xs uppercase tracking-wider text-ink-400">
              Most likely scorelines
            </h3>
            <ol className="space-y-1.5">
              {p.top_scorelines.map((s, i) => (
                <li key={i} className="flex items-center gap-3 font-mono text-sm">
                  <span className="w-12 tabular-nums text-ink-100">
                    {s.home}–{s.away}
                  </span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-ink-800">
                    <div
                      className="h-full bg-home/70"
                      style={{ width: fmtPct(s.prob / p.top_scorelines[0].prob, 1) }}
                    />
                  </div>
                  <span className="w-14 text-right tabular-nums text-ink-300">
                    {fmtPct(s.prob, 1)}
                  </span>
                </li>
              ))}
            </ol>
            <dl className="mt-4 grid grid-cols-2 gap-3">
              <Stat label={`${home.name} clean sheet`} value={fmtPct(p.clean_sheet_home)} />
              <Stat label={`${away.name} clean sheet`} value={fmtPct(p.clean_sheet_away)} />
            </dl>
          </div>
        </div>
      </Card>

      <Card className="p-5">
        <SectionTitle sub={p.knockout.shootout_model}>If knockout</SectionTitle>
        <dl className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Extra time" value={fmtPct(p.knockout.p_extra_time, 1)} />
          <Stat label="Shootout" value={fmtPct(p.knockout.p_shootout, 1)} />
          <Stat label={`${home.name} advance`} value={fmtPct(p.knockout.advance_home, 1)} />
          <Stat label={`${away.name} advance`} value={fmtPct(p.knockout.advance_away, 1)} />
        </dl>
      </Card>

      <Card className="p-5">
        <SectionTitle sub="generated from actual model components">
          Why the model thinks this
        </SectionTitle>
        <ul className="space-y-2">
          {p.explanations.map((e, i) => (
            <li key={i} className="flex gap-2 text-sm text-ink-200">
              <span
                aria-hidden
                className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${
                  e.direction === "home"
                    ? "bg-home"
                    : e.direction === "away"
                      ? "bg-away"
                      : "bg-ink-500"
                }`}
              />
              {e.text}
            </li>
          ))}
        </ul>
        {p.warnings.length > 0 && (
          <div className="mt-4 space-y-1">
            {p.warnings.map((w, i) => (
              <p key={i} className="font-mono text-xs text-amber-400">
                ⚠ {w}
              </p>
            ))}
          </div>
        )}
        <details className="mt-4">
          <summary className="cursor-pointer font-mono text-xs uppercase tracking-wide text-ink-400">
            Data-quality reasons
          </summary>
          <ul className="mt-2 space-y-1 font-mono text-xs text-ink-400">
            {p.data_quality.reasons.map((r, i) => (
              <li key={i}>· {r}</li>
            ))}
          </ul>
        </details>
      </Card>
    </div>
  );
}
