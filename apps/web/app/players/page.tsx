"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiGet } from "@kickoff/shared";
import type { Player } from "@kickoff/shared";
import { Badge, Card, Flag } from "@kickoff/ui";
import { ErrorBox, LoadingGrid } from "@/components/fixtures";

export default function PlayersPage() {
  const [search, setSearch] = useState("");
  const [recentOnly, setRecentOnly] = useState(true);
  const q = useQuery({
    queryKey: ["players", search, recentOnly],
    queryFn: () =>
      apiGet<{ total: number; players: Player[] }>(
        `/players?limit=48&recent_only=${recentOnly}${
          search ? `&search=${encodeURIComponent(search)}` : ""
        }`,
      ),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-black uppercase tracking-tight">
          Player Explorer
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-300">
          Profiles reconstructed from international <em>goalscorer records</em> (CC0).
          Impact scores are attack-side estimates with heavy shrinkage —{" "}
          <strong>not overall player quality</strong>. Caps, positions and defensive
          players require a licensed provider and are shown as unavailable.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search players…"
          aria-label="Search players"
          className="w-64 rounded border border-ink-700 bg-ink-900 px-3 py-2 text-sm placeholder:text-ink-500"
        />
        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={recentOnly}
            onChange={(e) => setRecentOnly(e.target.checked)}
            className="h-4 w-4 accent-home"
          />
          Recently active only
        </label>
        {q.data && (
          <span className="font-mono text-xs text-ink-400">
            {q.data.total.toLocaleString()} players
          </span>
        )}
      </div>

      {q.isLoading && <LoadingGrid n={12} />}
      {q.isError && <ErrorBox message={(q.error as Error).message} />}
      <ol className={`grid gap-3 sm:grid-cols-2 lg:grid-cols-3 ${q.isPlaceholderData ? "opacity-60" : ""}`}>
        {q.data?.players.map((p) => (
          <li key={p.player_id}>
            <Link href={`/player/${p.player_id}`}>
              <Card className="flex items-center gap-3 p-3 hover:border-ink-500">
                <span
                  aria-hidden
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-ink-800 font-display text-sm font-black text-ink-200"
                >
                  {p.name
                    .split(" ")
                    .map((w) => w[0])
                    .slice(0, 2)
                    .join("")}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{p.name}</span>
                  <span className="flex items-center gap-1.5 font-mono text-[11px] text-ink-400">
                    {p.team && <Flag team={p.team} size={14} />}
                    {p.team?.name ?? p.team_id}
                  </span>
                </span>
                <span className="text-right">
                  <span className="block font-display text-lg font-bold tabular-nums text-home">
                    {p.goals}
                  </span>
                  <span className="font-mono text-[10px] uppercase text-ink-500">
                    recorded
                  </span>
                </span>
              </Card>
            </Link>
          </li>
        ))}
      </ol>
      {q.data?.players.length === 0 && (
        <Card className="p-6 text-center text-ink-300">
          No players found — the registry only contains players who scored in recorded
          matches. <Badge>coverage note</Badge>
        </Card>
      )}
    </div>
  );
}
