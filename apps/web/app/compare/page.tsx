"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost, fmtPct, fmtPP } from "@kickoff/shared";
import type { Prediction, Team } from "@kickoff/shared";
import { Badge, Card, EmptyState, ProbBar, SectionTitle, Stat } from "@kickoff/ui";
import { ErrorBox } from "@/components/fixtures";
import {
  decodeScenario,
  encodeScenario,
  scenarioToParams,
  SquadPanel,
  TeamSelect,
  type ScenarioMap,
} from "@/components/scenario-controls";

interface CompareResult {
  teams: { home: Team; away: Team };
  scenario_a: Prediction;
  scenario_b: Prediction;
  delta: {
    probabilities_pp: { home: number; draw: number; away: number };
    expected_goals: { home: number; away: number };
    advance_pp: number;
    uncertainty: number;
    what_changed: string[];
  };
  label: string;
}

function ScenarioColumn({
  title,
  p,
  home,
  away,
}: {
  title: string;
  p: Prediction;
  home: Team;
  away: Team;
}) {
  return (
    <Card className="p-5">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-display text-lg font-bold uppercase">{title}</h3>
        {p.scenario_adjusted ? (
          <Badge tone="warn">adjusted</Badge>
        ) : (
          <Badge>baseline</Badge>
        )}
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        <Stat label={home.name} value={fmtPct(p.probabilities.home, 1)} />
        <Stat label="draw" value={fmtPct(p.probabilities.draw, 1)} />
        <Stat label={away.name} value={fmtPct(p.probabilities.away, 1)} />
      </div>
      <div className="mt-3">
        <ProbBar probs={p.probabilities} homeName={home.name} awayName={away.name} />
      </div>
      <dl className="mt-4 grid grid-cols-2 gap-3">
        <Stat label="xG home" value={p.expected_goals.home.toFixed(2)} />
        <Stat label="xG away" value={p.expected_goals.away.toFixed(2)} />
        <Stat label="advance (KO)" value={fmtPct(p.knockout.advance_home, 1)} />
        <Stat label="uncertainty" value={p.uncertainty.normalized_entropy.toFixed(3)} />
      </dl>
      {(p.player_assumptions.home.length > 0 || p.player_assumptions.away.length > 0) && (
        <div className="mt-4 space-y-1">
          {[...p.player_assumptions.home, ...p.player_assumptions.away].map((a, i) => (
            <p key={i} className="font-mono text-xs text-amber-300">
              {a.name ?? a.player_id}: {a.status}
              {a.share_effect ? ` (${(100 * a.share_effect).toFixed(0)}% of goals)` : ""}
            </p>
          ))}
        </div>
      )}
    </Card>
  );
}

function CompareInner() {
  const router = useRouter();
  const sp = useSearchParams();
  const [home, setHome] = useState(sp.get("home") ?? "");
  const [away, setAway] = useState(sp.get("away") ?? "");
  const [neutral, setNeutral] = useState(sp.get("neutral") !== "false");
  const [aHome, setAHome] = useState<ScenarioMap>(decodeScenario(sp.get("ah")));
  const [aAway, setAAway] = useState<ScenarioMap>(decodeScenario(sp.get("aa")));
  const [bHome, setBHome] = useState<ScenarioMap>(decodeScenario(sp.get("bh")));
  const [bAway, setBAway] = useState<ScenarioMap>(decodeScenario(sp.get("ba")));

  useEffect(() => {
    const p = new URLSearchParams();
    if (home) p.set("home", home);
    if (away) p.set("away", away);
    p.set("neutral", String(neutral));
    const enc: [string, ScenarioMap][] = [
      ["ah", aHome],
      ["aa", aAway],
      ["bh", bHome],
      ["ba", bAway],
    ];
    for (const [k, v] of enc) {
      const s = encodeScenario(v);
      if (s) p.set(k, s);
    }
    router.replace(`/compare?${p.toString()}`, { scroll: false });
  }, [home, away, neutral, aHome, aAway, bHome, bAway, router]);

  const teams = useQuery({
    queryKey: ["teams-all"],
    queryFn: () => apiGet<{ teams: Team[] }>("/teams?limit=400"),
    staleTime: Infinity,
  });
  const homeTeam = teams.data?.teams.find((t) => t.team_id === home);
  const awayTeam = teams.data?.teams.find((t) => t.team_id === away);

  const body = useMemo(() => {
    if (!home || !away || home === away) return null;
    const mk = (h: ScenarioMap, a: ScenarioMap) => {
      const hp = scenarioToParams(h);
      const ap = scenarioToParams(a);
      return {
        home_absences: hp.absences,
        away_absences: ap.absences,
        home_doubtful: hp.doubtful.map(([player_id, availability_prob]) => ({
          player_id,
          availability_prob,
        })),
        away_doubtful: ap.doubtful.map(([player_id, availability_prob]) => ({
          player_id,
          availability_prob,
        })),
      };
    };
    return {
      home_id: home,
      away_id: away,
      neutral,
      scenario_a: mk(aHome, aAway),
      scenario_b: mk(bHome, bAway),
    };
  }, [home, away, neutral, aHome, aAway, bHome, bAway]);

  const cmp = useQuery({
    queryKey: ["compare", body],
    queryFn: () => apiPost<CompareResult>("/predictions/compare", body),
    enabled: Boolean(body),
    placeholderData: (prev) => prev,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-black uppercase tracking-tight">
          Scenario Compare
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-300">
          Two labeled what-if scenarios, side by side — e.g. star striker available vs
          injured. Deltas are shown in percentage points against Scenario A.
        </p>
      </div>

      <Card className="flex flex-wrap items-end gap-4 p-4">
        <TeamSelect label="Team A (home slot)" value={home} onChange={setHome} />
        <TeamSelect label="Team B (away slot)" value={away} onChange={setAway} />
        <label className="flex items-center gap-2 pb-2">
          <input
            type="checkbox"
            checked={neutral}
            onChange={(e) => setNeutral(e.target.checked)}
            className="h-4 w-4 accent-home"
          />
          <span className="text-sm">Neutral venue</span>
        </label>
      </Card>

      {(!home || !away) && (
        <EmptyState
          title="Pick the matchup first"
          detail="Then set different availability assumptions in each scenario."
        />
      )}

      {homeTeam && awayTeam && home !== away && (
        <>
          <div className="grid gap-6 md:grid-cols-2">
            <Card className="p-4">
              <SectionTitle sub="assumptions for scenario A">Scenario A</SectionTitle>
              <div className="space-y-4">
                <SquadPanel team={homeTeam} scenario={aHome} onChange={setAHome} />
                <SquadPanel team={awayTeam} scenario={aAway} onChange={setAAway} />
              </div>
            </Card>
            <Card className="p-4">
              <SectionTitle sub="assumptions for scenario B">Scenario B</SectionTitle>
              <div className="space-y-4">
                <SquadPanel team={homeTeam} scenario={bHome} onChange={setBHome} />
                <SquadPanel team={awayTeam} scenario={bAway} onChange={setBAway} />
              </div>
            </Card>
          </div>

          {cmp.isLoading && <div className="h-72 animate-pulse rounded-lg bg-ink-900" />}
          {cmp.isError && <ErrorBox message={(cmp.error as Error).message} />}
          {cmp.data && (
            <div className={cmp.isPlaceholderData ? "opacity-60" : ""}>
              <div className="grid gap-6 md:grid-cols-2">
                <ScenarioColumn title="Scenario A" p={cmp.data.scenario_a} home={homeTeam} away={awayTeam} />
                <ScenarioColumn title="Scenario B" p={cmp.data.scenario_b} home={homeTeam} away={awayTeam} />
              </div>
              <Card className="mt-6 p-5">
                <SectionTitle sub="B minus A">What changed</SectionTitle>
                <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                  <Stat label={`${homeTeam.name} win`} value={fmtPP(cmp.data.delta.probabilities_pp.home)} />
                  <Stat label="draw" value={fmtPP(cmp.data.delta.probabilities_pp.draw)} />
                  <Stat label={`${awayTeam.name} win`} value={fmtPP(cmp.data.delta.probabilities_pp.away)} />
                  <Stat label="advance (KO)" value={fmtPP(cmp.data.delta.advance_pp)} />
                  <Stat label="xG home Δ" value={cmp.data.delta.expected_goals.home.toFixed(2)} />
                  <Stat label="xG away Δ" value={cmp.data.delta.expected_goals.away.toFixed(2)} />
                  <Stat label="uncertainty Δ" value={cmp.data.delta.uncertainty.toFixed(4)} />
                </dl>
                <ul className="mt-4 space-y-1">
                  {cmp.data.delta.what_changed.map((c, i) => (
                    <li key={i} className="font-mono text-xs text-ink-300">
                      · {c}
                    </li>
                  ))}
                </ul>
                <p className="mt-3 font-mono text-[11px] text-amber-400/80">
                  {cmp.data.label}
                </p>
              </Card>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={<div className="h-96 animate-pulse rounded-lg bg-ink-900" />}>
      <CompareInner />
    </Suspense>
  );
}
