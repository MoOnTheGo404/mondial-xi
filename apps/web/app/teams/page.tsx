"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@kickoff/shared";
import type { Team } from "@kickoff/shared";
import { Badge, Card, Flag } from "@kickoff/ui";
import { ErrorBox, LoadingGrid } from "@/components/fixtures";

const CONFEDS = ["", "UEFA", "CONMEBOL", "CONCACAF", "CAF", "AFC", "OFC"];

export default function TeamsPage() {
  const [search, setSearch] = useState("");
  const [confed, setConfed] = useState("");
  const q = useQuery({
    queryKey: ["teams", search, confed],
    queryFn: () =>
      apiGet<{ teams: Team[]; total: number }>(
        `/teams?limit=400${search ? `&search=${encodeURIComponent(search)}` : ""}${
          confed ? `&confederation=${confed}` : ""
        }`,
      ),
  });

  return (
    <div className="space-y-6">
      <h1 className="font-display text-3xl font-black uppercase tracking-tight">
        Team Explorer
      </h1>
      <div className="flex flex-wrap gap-3">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search teams…"
          aria-label="Search teams"
          className="w-56 rounded border border-ink-700 bg-ink-900 px-3 py-2 text-sm placeholder:text-ink-500"
        />
        <select
          value={confed}
          onChange={(e) => setConfed(e.target.value)}
          aria-label="Filter by confederation"
          className="rounded border border-ink-700 bg-ink-900 px-2 py-2 text-sm"
        >
          {CONFEDS.map((c) => (
            <option key={c} value={c}>
              {c || "All confederations"}
            </option>
          ))}
        </select>
        {q.data && (
          <span className="self-center font-mono text-xs text-ink-400">
            {q.data.total} teams · ranked by current Elo
          </span>
        )}
      </div>

      {q.isLoading && <LoadingGrid n={12} />}
      {q.isError && <ErrorBox message={(q.error as Error).message} />}
      <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {q.data?.teams.map((t, i) => (
          <li key={t.team_id}>
            <Link href={`/team/${t.team_id}`}>
              <Card className="flex items-center gap-3 p-3 transition-colors hover:border-ink-500">
                <span className="w-8 text-right font-mono text-sm text-ink-500">
                  {i + 1}
                </span>
                <Flag team={t} size={26} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate font-medium">{t.name}</span>
                  <span className="font-mono text-[11px] text-ink-400">
                    {t.confederation} · {t.matches_played} matches
                  </span>
                </span>
                {t.is_historical && <Badge>historical</Badge>}
                <span className="font-display text-lg font-bold tabular-nums text-home">
                  {t.elo ? Math.round(t.elo) : "—"}
                </span>
              </Card>
            </Link>
          </li>
        ))}
      </ol>
    </div>
  );
}
