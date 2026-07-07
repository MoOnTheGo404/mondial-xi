"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@kickoff/shared";
import type { Player, Team } from "@kickoff/shared";
import { Badge, Flag } from "@kickoff/ui";

export interface PlayerState {
  status: "available" | "unavailable" | "doubtful";
  prob: number; // availability probability when doubtful
}

export type ScenarioMap = Record<string, PlayerState>;

export function TeamSelect({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (id: string) => void;
}) {
  const { data } = useQuery({
    queryKey: ["teams-all"],
    queryFn: () => apiGet<{ teams: Team[] }>("/teams?limit=400"),
    staleTime: Infinity,
  });
  return (
    <label className="flex flex-col gap-1">
      <span className="font-mono text-[11px] uppercase tracking-wide text-ink-400">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-w-44 rounded border border-ink-700 bg-ink-900 px-2 py-2 text-sm"
      >
        <option value="">Select team…</option>
        {data?.teams.map((t) => (
          <option key={t.team_id} value={t.team_id}>
            {t.name} {t.elo ? `(${Math.round(t.elo)})` : ""}
          </option>
        ))}
      </select>
    </label>
  );
}

export function SquadPanel({
  team,
  scenario,
  onChange,
}: {
  team: Team;
  scenario: ScenarioMap;
  onChange: (next: ScenarioMap) => void;
}) {
  const { data, isLoading } = useQuery({
    queryKey: ["squad", team.team_id],
    queryFn: () =>
      apiGet<{ players: (Player & { availability: string })[]; coverage_note: string }>(
        `/teams/${team.team_id}/squad`,
      ),
  });

  const set = (pid: string, st: PlayerState | null) => {
    const next = { ...scenario };
    if (st === null) delete next[pid];
    else next[pid] = st;
    onChange(next);
  };

  if (isLoading) return <div className="h-40 animate-pulse rounded bg-ink-900" />;
  const players = (data?.players ?? []).filter((p) => p.recently_active).slice(0, 12);

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <Flag team={team} size={18} />
        <span className="font-display font-bold">{team.name}</span>
        <Badge>attack contributors</Badge>
      </div>
      {players.length === 0 && (
        <p className="text-sm text-ink-400">
          No recently active scorers on record for this team.
        </p>
      )}
      <ul className="space-y-1.5">
        {players.map((p) => {
          const st = scenario[p.player_id];
          return (
            <li
              key={p.player_id}
              className="flex flex-wrap items-center gap-2 rounded border border-ink-800 bg-ink-900/60 px-2.5 py-1.5"
            >
              <span className="min-w-0 flex-1 truncate text-sm">{p.name}</span>
              <span
                className="font-mono text-[10px] text-ink-400"
                title="Shrunken attacking impact (xG/match) from scoring records"
              >
                {p.attack_impact_recent.toFixed(2)} xG/m
              </span>
              <div
                role="group"
                aria-label={`${p.name} availability assumption`}
                className="flex overflow-hidden rounded border border-ink-700"
              >
                {(
                  [
                    ["available", "In"],
                    ["doubtful", "50/50"],
                    ["unavailable", "Out"],
                  ] as const
                ).map(([key, label]) => {
                  const active = key === "available" ? !st : st?.status === key;
                  return (
                    <button
                      key={key}
                      type="button"
                      aria-pressed={active}
                      onClick={() =>
                        set(
                          p.player_id,
                          key === "available" ? null : { status: key, prob: 0.5 },
                        )
                      }
                      className={`px-2 py-1 font-mono text-[10px] uppercase ${
                        active
                          ? key === "unavailable"
                            ? "bg-red-500/80 font-bold text-ink-950"
                            : key === "doubtful"
                              ? "bg-amber-400 font-bold text-ink-950"
                              : "bg-home font-bold text-ink-950"
                          : "text-ink-300 hover:bg-ink-800"
                      }`}
                    >
                      {label}
                    </button>
                  );
                })}
              </div>
            </li>
          );
        })}
      </ul>
      <p className="mt-2 font-mono text-[10px] leading-snug text-ink-500">
        Default status is “unknown” (treated as available). Changes here are labeled
        user assumptions — no injury feed is configured.
      </p>
    </div>
  );
}

export function scenarioToParams(s: ScenarioMap): { absences: string[]; doubtful: [string, number][] } {
  const absences: string[] = [];
  const doubtful: [string, number][] = [];
  for (const [pid, st] of Object.entries(s)) {
    if (st.status === "unavailable") absences.push(pid);
    else if (st.status === "doubtful") doubtful.push([pid, st.prob]);
  }
  return { absences, doubtful };
}

export function encodeScenario(s: ScenarioMap): string {
  return Object.entries(s)
    .map(([pid, st]) => `${pid}:${st.status === "unavailable" ? "out" : `d${st.prob}`}`)
    .join(",");
}

export function decodeScenario(raw: string | null): ScenarioMap {
  const out: ScenarioMap = {};
  if (!raw) return out;
  for (const part of raw.split(",")) {
    const idx = part.lastIndexOf(":");
    if (idx < 0) continue;
    const pid = part.slice(0, idx);
    const code = part.slice(idx + 1);
    if (code === "out") out[pid] = { status: "unavailable", prob: 0 };
    else if (code.startsWith("d")) {
      const prob = Number(code.slice(1));
      if (!Number.isNaN(prob)) out[pid] = { status: "doubtful", prob };
    }
  }
  return out;
}
