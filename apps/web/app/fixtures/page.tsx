"use client";

import { useState } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiGet } from "@kickoff/shared";
import type { MatchRow } from "@kickoff/shared";
import { EmptyState } from "@kickoff/ui";
import { ErrorBox, FixtureCard, LoadingGrid } from "@/components/fixtures";

interface FixtureList {
  total: number;
  fixtures: MatchRow[];
  data_cutoff: string;
  fixture_source_note: string;
}

const PAGE = 24;

export default function FixturesPage() {
  const [status, setStatus] = useState<"upcoming" | "recent">("upcoming");
  const [tournament, setTournament] = useState("");
  const [search, setSearch] = useState("");
  const [offset, setOffset] = useState(0);

  const params = new URLSearchParams({
    status,
    limit: String(PAGE),
    offset: String(offset),
  });
  if (tournament) params.set("tournament", tournament);
  if (search) params.set("search", search);

  const q = useQuery({
    queryKey: ["fixtures", status, tournament, search, offset],
    queryFn: () => apiGet<FixtureList>(`/fixtures?${params}`),
    placeholderData: keepPreviousData,
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl font-black uppercase tracking-tight">
          Fixtures &amp; Predictions
        </h1>
        {q.data && (
          <p className="mt-1 font-mono text-xs text-ink-400">
            {q.data.fixture_source_note}
          </p>
        )}
      </div>

      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => e.preventDefault()}
        aria-label="Fixture filters"
      >
        <div role="group" aria-label="Status" className="flex overflow-hidden rounded border border-ink-700">
          {(["upcoming", "recent"] as const).map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => {
                setStatus(s);
                setOffset(0);
              }}
              aria-pressed={status === s}
              className={`px-3 py-1.5 text-sm capitalize ${
                status === s ? "bg-brand font-bold text-white" : "text-ink-300 hover:bg-ink-800"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[11px] uppercase tracking-wide text-ink-400">
            Competition
          </span>
          <select
            value={tournament}
            onChange={(e) => {
              setTournament(e.target.value);
              setOffset(0);
            }}
            className="rounded border border-ink-700 bg-ink-900 px-2 py-1.5 text-sm"
          >
            <option value="">All</option>
            <option value="FIFA World Cup">FIFA World Cup</option>
            <option value="qualification">Qualifiers</option>
            <option value="Friendly">Friendlies</option>
            <option value="Nations League">Nations League</option>
          </select>
        </label>
        <label className="flex flex-col gap-1">
          <span className="font-mono text-[11px] uppercase tracking-wide text-ink-400">
            Team search
          </span>
          <input
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setOffset(0);
            }}
            placeholder="e.g. Morocco"
            className="w-44 rounded border border-ink-700 bg-ink-900 px-2 py-1.5 text-sm placeholder:text-ink-500"
          />
        </label>
        {q.data && (
          <span className="ml-auto font-mono text-xs text-ink-400">
            {q.data.total.toLocaleString()} fixtures
          </span>
        )}
      </form>

      {q.isLoading && <LoadingGrid n={9} />}
      {q.isError && <ErrorBox message={(q.error as Error).message} />}
      {q.data && q.data.fixtures.length === 0 && (
        <EmptyState
          title="No fixtures match these filters"
          detail={
            status === "upcoming"
              ? "The dataset snapshot only lists confirmed upcoming pairings. Try Recent, or use Match Lab for any custom matchup."
              : "Try broadening the filters."
          }
        />
      )}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {q.data?.fixtures.map((m) => (
          <FixtureCard
            key={m.match_id}
            m={m}
            probs={m.forecast?.probabilities}
            href={`/match/${m.match_id}`}
          />
        ))}
      </div>

      {q.data && q.data.total > PAGE && (
        <nav className="flex items-center justify-center gap-3" aria-label="Pagination">
          <button
            type="button"
            disabled={offset === 0}
            onClick={() => setOffset((o) => Math.max(0, o - PAGE))}
            className="rounded border border-ink-700 px-3 py-1.5 text-sm disabled:opacity-40"
          >
            ← Newer
          </button>
          <span className="font-mono text-xs text-ink-400">
            {offset + 1}–{Math.min(offset + PAGE, q.data.total)} of {q.data.total.toLocaleString()}
          </span>
          <button
            type="button"
            disabled={offset + PAGE >= q.data.total}
            onClick={() => setOffset((o) => o + PAGE)}
            className="rounded border border-ink-700 px-3 py-1.5 text-sm disabled:opacity-40"
          >
            Older →
          </button>
        </nav>
      )}
    </div>
  );
}
