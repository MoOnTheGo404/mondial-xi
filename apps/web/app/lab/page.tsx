"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiGet, apiPost, parsePrediction } from "@kickoff/shared";
import type { Prediction, Team } from "@kickoff/shared";
import { Badge, Card, EmptyState, SectionTitle } from "@kickoff/ui";
import { ErrorBox } from "@/components/fixtures";
import { PredictionPanel } from "@/components/prediction";
import { FORMATIONS, PitchFormation } from "@/components/pitch";
import {
  decodeScenario,
  encodeScenario,
  scenarioToParams,
  SquadPanel,
  TeamSelect,
  type ScenarioMap,
} from "@/components/scenario-controls";

function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

function LabInner() {
  const router = useRouter();
  const sp = useSearchParams();

  const [home, setHome] = useState(sp.get("home") ?? "");
  const [away, setAway] = useState(sp.get("away") ?? "");
  const [neutral, setNeutral] = useState(sp.get("neutral") !== "false");
  const [importance, setImportance] = useState(Number(sp.get("importance") ?? 4));
  const [formation, setFormation] = useState(sp.get("formation") ?? "4-3-3");
  const [homeScenario, setHomeScenario] = useState<ScenarioMap>(
    decodeScenario(sp.get("hs")),
  );
  const [awayScenario, setAwayScenario] = useState<ScenarioMap>(
    decodeScenario(sp.get("as")),
  );

  // URL persistence — the URL is the shareable scenario definition
  useEffect(() => {
    const p = new URLSearchParams();
    if (home) p.set("home", home);
    if (away) p.set("away", away);
    p.set("neutral", String(neutral));
    if (importance !== 4) p.set("importance", String(importance));
    if (formation !== "4-3-3") p.set("formation", formation);
    const hs = encodeScenario(homeScenario);
    const as = encodeScenario(awayScenario);
    if (hs) p.set("hs", hs);
    if (as) p.set("as", as);
    router.replace(`/lab?${p.toString()}`, { scroll: false });
  }, [home, away, neutral, importance, formation, homeScenario, awayScenario, router]);

  const teams = useQuery({
    queryKey: ["teams-all"],
    queryFn: () => apiGet<{ teams: Team[] }>("/teams?limit=400"),
    staleTime: Infinity,
  });
  const homeTeam = teams.data?.teams.find((t) => t.team_id === home);
  const awayTeam = teams.data?.teams.find((t) => t.team_id === away);

  const body = useMemo(() => {
    if (!home || !away || home === away) return null;
    const h = scenarioToParams(homeScenario);
    const a = scenarioToParams(awayScenario);
    return {
      home_id: home,
      away_id: away,
      neutral,
      importance,
      scenario: {
        home_absences: h.absences,
        away_absences: a.absences,
        home_doubtful: h.doubtful.map(([player_id, availability_prob]) => ({
          player_id,
          availability_prob,
        })),
        away_doubtful: a.doubtful.map(([player_id, availability_prob]) => ({
          player_id,
          availability_prob,
        })),
      },
    };
  }, [home, away, neutral, importance, homeScenario, awayScenario]);

  const debouncedBody = useDebounced(body, 350);
  const pred = useQuery({
    queryKey: ["lab-prediction", debouncedBody],
    queryFn: async () =>
      parsePrediction(await apiPost<Prediction>("/predictions/match", debouncedBody)),
    enabled: Boolean(debouncedBody),
    placeholderData: (prev) => prev,
  });

  const reset = () => {
    setHomeScenario({});
    setAwayScenario({});
    setNeutral(true);
    setImportance(4);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="font-display text-3xl font-black uppercase tracking-tight">
            Match Lab
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-ink-300">
            Build any matchup, set availability assumptions and venue context, and watch
            the forecast respond. Everything you change is a{" "}
            <strong className="text-amber-300">labeled user assumption</strong> — the URL
            captures the whole scenario for sharing.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => navigator.clipboard?.writeText(window.location.href)}
            className="rounded border border-ink-600 px-3 py-2 font-mono text-xs uppercase text-ink-200 hover:border-home"
          >
            Copy share URL
          </button>
          <button
            type="button"
            onClick={reset}
            className="rounded border border-ink-600 px-3 py-2 font-mono text-xs uppercase text-ink-200 hover:border-home"
          >
            Reset assumptions
          </button>
        </div>
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
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[11px] uppercase tracking-wide text-ink-400">
            Competition importance
          </span>
          <select
            value={importance}
            onChange={(e) => setImportance(Number(e.target.value))}
            className="rounded border border-ink-700 bg-ink-900 px-2 py-2 text-sm"
          >
            <option value={4}>World Cup</option>
            <option value={3}>Continental</option>
            <option value={2}>Qualifier</option>
            <option value={0}>Friendly</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[11px] uppercase tracking-wide text-ink-400">
            Formation (illustrative)
          </span>
          <select
            value={formation}
            onChange={(e) => setFormation(e.target.value)}
            className="rounded border border-ink-700 bg-ink-900 px-2 py-2 text-sm"
          >
            {Object.keys(FORMATIONS).map((f) => (
              <option key={f}>{f}</option>
            ))}
          </select>
        </label>
      </Card>

      {home && away && home === away && (
        <ErrorBox message="Pick two different teams." />
      )}

      {(!home || !away) && (
        <EmptyState
          title="Pick two teams to start"
          detail="Try Norway vs England, or load a fixture from the Fixtures page."
        />
      )}

      {homeTeam && awayTeam && home !== away && (
        <div className="grid gap-6 lg:grid-cols-[1fr_1.6fr]">
          <div className="space-y-6">
            <Card className="p-4">
              <SectionTitle sub="user assumptions">Availability</SectionTitle>
              <div className="space-y-5">
                <SquadPanel team={homeTeam} scenario={homeScenario} onChange={setHomeScenario} />
                <SquadPanel team={awayTeam} scenario={awayScenario} onChange={setAwayScenario} />
              </div>
            </Card>
            <Card className="p-4">
              <SectionTitle>Formation shape</SectionTitle>
              <PitchFormation
                formation={formation}
                teamName={homeTeam.name}
                attackerNames={[]}
              />
            </Card>
          </div>

          <div>
            {pred.isLoading && (
              <div className="h-96 animate-pulse rounded-lg bg-ink-900" aria-label="Computing" />
            )}
            {pred.isError && <ErrorBox message={(pred.error as Error).message} />}
            {pred.data && (
              <div className={pred.isPlaceholderData ? "opacity-60 transition-opacity" : ""}>
                <div className="mb-3">
                  <Badge tone="warn">{pred.data.label ?? "custom scenario"}</Badge>
                </div>
                <PredictionPanel p={pred.data} home={homeTeam} away={awayTeam} />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default function LabPage() {
  return (
    <Suspense fallback={<div className="h-96 animate-pulse rounded-lg bg-ink-900" />}>
      <LabInner />
    </Suspense>
  );
}
