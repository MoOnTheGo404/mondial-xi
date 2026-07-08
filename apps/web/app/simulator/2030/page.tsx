"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiPost, fmtPct } from "@kickoff/shared";
import type { Team } from "@kickoff/shared";
import { Badge, Card, Flag, SectionTitle } from "@kickoff/ui";
import { ErrorBox } from "@/components/fixtures";

interface OutlookTeam {
  team_id: string;
  team: Team;
  is_host: boolean;
  confederation: string;
  p_qualify: number;
  reach: Record<string, number>;
}

interface Outlook {
  tournament_id: string;
  kind: string;
  name: string;
  config_version: string;
  n_sims: number;
  qualification_realizations: number;
  seed: number;
  elapsed_ms: number;
  model_version: string;
  data_cutoff: string;
  assumptions: string[];
  quotas_after_hosts: Record<string, number>;
  teams: OutlookTeam[];
}

const CONF_ORDER = ["UEFA", "CONMEBOL", "CAF", "AFC", "CONCACAF", "OFC"];

export default function Outlook2030Page() {
  const [nSims, setNSims] = useState(4000);
  const [seed, setSeed] = useState(42);
  const [runKey, setRunKey] = useState(0);

  const body = useMemo(
    () => ({ tournament_id: "wc2030", n_sims: nSims, seed, blocks: 16 }),
    [nSims, seed],
  );
  const q = useQuery({
    queryKey: ["outlook-2030", body, runKey],
    queryFn: () => apiPost<Outlook>("/simulations/tournament", body),
    placeholderData: (prev) => prev,
    staleTime: 600_000,
  });

  const d = q.data;

  return (
    <div className="space-y-8">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="font-display text-3xl font-black uppercase tracking-tight">
            World Cup 2030 Outlook
          </h1>
          <Badge tone="warn">outlook — assumptions apply</Badge>
          <Link
            href="/simulator"
            className="font-mono text-xs uppercase tracking-wide text-home hover:underline"
          >
            ← 2026 simulator (real state)
          </Link>
        </div>
        <p className="mt-2 max-w-3xl text-sm text-ink-300">
          Qualification, final draw and tournament simulated end-to-end from{" "}
          <strong>today&apos;s ratings</strong>. Verified: Morocco, Portugal, Spain plus
          centenary hosts Argentina, Uruguay and Paraguay all qualify automatically. Almost
          everything else about 2030 is not yet announced by FIFA — every assumption used
          here is listed below and echoed by the API.
        </p>
      </div>

      <Card className="flex flex-wrap items-end gap-4 p-4">
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[11px] uppercase tracking-wide text-ink-400">
            Finals simulations
          </span>
          <select
            value={nSims}
            onChange={(e) => setNSims(Number(e.target.value))}
            className="rounded border border-ink-700 bg-ink-900 px-2 py-2 text-sm"
          >
            {[2000, 4000, 8000].map((n) => (
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
        <button
          type="button"
          onClick={() => setRunKey((k) => k + 1)}
          className="rounded bg-home px-4 py-2 font-display text-sm font-bold uppercase text-ink-950"
        >
          Re-run
        </button>
        <span className="ml-auto font-mono text-xs text-ink-400" role="status">
          {q.isFetching
            ? "simulating qualification + draws + finals… (~10 s)"
            : d
              ? `${d.n_sims.toLocaleString()} finals sims over ${d.qualification_realizations} qualification realizations · ${(d.elapsed_ms / 1000).toFixed(1)} s · model ${d.model_version} · ratings as of ${d.data_cutoff}`
              : ""}
        </span>
      </Card>

      {q.isError && <ErrorBox message={(q.error as Error).message} />}
      {q.isLoading && <div className="h-96 animate-pulse rounded-lg bg-ink-900" />}

      {d && (
        <div className={q.isPlaceholderData ? "opacity-60" : ""}>
          {/* title odds */}
          <Card className="p-5">
            <SectionTitle sub="unconditional: includes the risk of not qualifying">
              Championship probabilities (2030 outlook)
            </SectionTitle>
            <ol className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
              {d.teams
                .filter((t) => t.reach.champion >= 0.005)
                .slice(0, 16)
                .map((t) => (
                  <li key={t.team_id} className="flex items-center gap-3">
                    <Flag team={t.team} size={20} />
                    <Link
                      href={`/team/${t.team_id}`}
                      className="w-36 truncate font-medium hover:text-home"
                    >
                      {t.team.name}
                    </Link>
                    {t.is_host && <Badge tone="info">host</Badge>}
                    <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-ink-800">
                      <div
                        className="h-full rounded-full bg-home"
                        style={{
                          width: `${(100 * t.reach.champion) / d.teams[0].reach.champion}%`,
                        }}
                      />
                    </div>
                    <span className="w-14 text-right font-mono text-sm tabular-nums">
                      {fmtPct(t.reach.champion, 1)}
                    </span>
                  </li>
                ))}
            </ol>
          </Card>

          {/* qualification odds by confederation */}
          <section className="mt-8">
            <SectionTitle sub="hosts qualify automatically; quotas assume the 2026 baseline minus host berths">
              Qualification probabilities
            </SectionTitle>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {CONF_ORDER.map((conf) => {
                const rows = d.teams
                  .filter((t) => t.confederation === conf && (t.p_qualify > 0.02 || t.is_host))
                  .slice(0, 12);
                if (rows.length === 0) return null;
                return (
                  <Card key={conf} className="p-4">
                    <h3 className="mb-2 flex items-baseline justify-between font-display text-sm font-bold uppercase">
                      {conf}
                      <span className="font-mono text-[10px] font-normal text-ink-400">
                        {d.quotas_after_hosts[conf]} slots + hosts
                      </span>
                    </h3>
                    <ul className="space-y-1">
                      {rows.map((t) => (
                        <li key={t.team_id} className="flex items-center gap-2 text-sm">
                          <Flag team={t.team} size={16} />
                          <span className="min-w-0 flex-1 truncate">{t.team.name}</span>
                          {t.is_host ? (
                            <Badge tone="info">auto</Badge>
                          ) : (
                            <>
                              <div className="h-1.5 w-20 overflow-hidden rounded-full bg-ink-800">
                                <div
                                  className="h-full bg-away"
                                  style={{ width: `${100 * t.p_qualify}%` }}
                                />
                              </div>
                              <span className="w-10 text-right font-mono text-xs tabular-nums text-ink-300">
                                {fmtPct(t.p_qualify)}
                              </span>
                            </>
                          )}
                        </li>
                      ))}
                    </ul>
                  </Card>
                );
              })}
            </div>
          </section>

          {/* assumptions */}
          <Card className="mt-8 border-amber-500/30 p-5">
            <SectionTitle sub="every unverified choice, in the open">
              Assumptions behind this outlook
            </SectionTitle>
            <ul className="list-inside list-disc space-y-1.5 text-sm text-ink-300">
              {d.assumptions.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
            <p className="mt-3 font-mono text-[11px] text-ink-500">
              Sources & verification: docs/research/wc2030.md · config v{d.config_version}
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}
