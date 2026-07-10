"use client";

import Link from "next/link";
import type { MatchRow, Probabilities } from "@kickoff/shared";
import { fmtDate } from "@kickoff/shared";
import { Flag, ProbBar, Badge, Card } from "@kickoff/ui";

export function TeamCell({
  team,
  right = false,
  nameThen,
}: {
  team: MatchRow["home"];
  right?: boolean;
  nameThen?: string | null;
}) {
  const renamed = nameThen && nameThen !== team.name;
  return (
    <Link
      href={`/team/${team.team_id}`}
      className={`flex items-center gap-2 hover:text-brand ${right ? "flex-row-reverse text-right" : ""}`}
    >
      <Flag team={team} size={22} />
      <span className="font-medium leading-tight">
        {team.name}
        {renamed && (
          <span className="block font-mono text-[10px] text-ink-400">
            then “{nameThen}”
          </span>
        )}
      </span>
    </Link>
  );
}

export function FixtureCard({
  m,
  probs,
  href,
}: {
  m: MatchRow;
  probs?: Probabilities;
  href?: string;
}) {
  const finished = m.home_score !== null && m.home_score !== undefined;
  return (
    <Card className={`p-4 ${href ? "card-hover" : ""}`}>
      <div className="mb-2 flex items-center justify-between gap-2 font-mono text-[11px] text-ink-400">
        <span>{fmtDate(m.date)}</span>
        <span className="truncate">{m.tournament}</span>
        {m.neutral ? <Badge>neutral</Badge> : <Badge tone="info">home venue</Badge>}
      </div>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <TeamCell team={m.home} nameThen={m.home_team_name_then} />
        <div className="px-1 text-center">
          {finished ? (
            <span className="font-display text-xl font-black tabular-nums">
              {m.home_score}–{m.away_score}
            </span>
          ) : (
            <span className="font-mono text-xs uppercase text-ink-400">vs</span>
          )}
          {m.shootout_winner_id && (
            <div className="font-mono text-[10px] text-amber-400">pens</div>
          )}
        </div>
        <TeamCell team={m.away} right nameThen={m.away_team_name_then} />
      </div>
      {probs && (
        <div className="mt-3">
          <ProbBar probs={probs} homeName={m.home.name} awayName={m.away.name} showLabels />
        </div>
      )}
      {(m.city || m.country) && (
        <div className="mt-2 font-mono text-[11px] text-ink-500">
          {[m.city, m.country].filter(Boolean).join(", ")}
        </div>
      )}
      {href && (
        <Link
          href={href}
          className="mt-3 inline-block font-mono text-xs uppercase tracking-wide text-brand hover:underline"
        >
          Match center →
        </Link>
      )}
    </Card>
  );
}

export function LoadingGrid({ n = 6 }: { n?: number }) {
  return (
    <div
      className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
      role="status"
      aria-label="Loading"
    >
      {Array.from({ length: n }).map((_, i) => (
        <div key={i} className="h-36 animate-pulse rounded-lg bg-ink-900" />
      ))}
    </div>
  );
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-red-500/40 bg-red-950/30 p-4 text-sm text-red-200"
    >
      <p className="font-bold">Something went wrong</p>
      <p className="mt-1 font-mono text-xs">{message}</p>
      <p className="mt-2 text-xs text-red-300">
        Is the API running? Start it with <code className="font-mono">make dev</code>.
      </p>
    </div>
  );
}
