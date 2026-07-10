"use client";

import type { Team } from "@kickoff/shared";
import { Flag } from "@kickoff/ui";

export interface BracketNode {
  round: string;
  home_id: string | null;
  away_id: string | null;
  home: Team | null;
  away: Team | null;
  home_goals?: number;
  away_goals?: number;
  winner_id?: string | null;
  status: "finished" | "scheduled" | "pending";
  shootout?: boolean;
  children?: BracketNode[];
}

const ROUND_LABEL: Record<string, string> = {
  R16: "Round of 16",
  QF: "Quarter-finals",
  SF: "Semi-finals",
  F: "Final",
};

// rounds we expand children for (leaves are Round of 16)
const EXPAND = new Set(["F", "SF", "QF"]);

function TeamRow({
  team,
  teamId,
  goals,
  won,
  faded,
  onLock,
  locked,
}: {
  team: Team | null;
  teamId: string | null;
  goals?: number;
  won: boolean;
  faded: boolean;
  onLock?: () => void;
  locked?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-2 px-2 py-1">
      <span className="flex min-w-0 items-center gap-1.5">
        {team ? (
          <Flag team={team} size={15} />
        ) : (
          <span className="inline-block h-[11px] w-[15px] rounded-[2px] bg-ink-700" aria-hidden />
        )}
        <span
          className={`truncate text-[13px] ${
            won ? "font-bold text-ink-50" : faded ? "text-ink-500" : "text-ink-200"
          }`}
        >
          {team ? team.name : "TBD"}
        </span>
      </span>
      {goals !== undefined ? (
        <span className={`font-mono text-[13px] tabular-nums ${won ? "text-home" : "text-ink-400"}`}>
          {goals}
        </span>
      ) : onLock && teamId ? (
        <button
          type="button"
          aria-pressed={locked}
          aria-label={`Lock ${team?.name ?? "team"} to win`}
          onClick={onLock}
          className={`rounded px-1.5 py-0.5 font-mono text-[9px] uppercase transition-colors ${
            locked
              ? "bg-amber-400 font-bold text-ink-950"
              : "border border-ink-700 text-ink-500 hover:border-amber-400 hover:text-amber-300"
          }`}
        >
          {locked ? "✓" : "pick"}
        </button>
      ) : null}
    </div>
  );
}

function MatchBox({
  node,
  isLocked,
  onLock,
}: {
  node: BracketNode;
  isLocked: (round: string, teamId: string) => boolean;
  onLock: (round: string, a: string, b: string, winner: string) => void;
}) {
  const finished = node.status === "finished";
  const scheduled = node.status === "scheduled";
  const homeWon = node.winner_id === node.home_id;
  const awayWon = node.winner_id === node.away_id;
  const canLock = scheduled && node.home_id && node.away_id;
  const border =
    node.round === "F"
      ? "border-gold/50"
      : finished
        ? "border-ink-700"
        : scheduled
          ? "border-away/40"
          : "border-ink-800";

  return (
    <div className={`w-44 rounded-md border bg-ink-900/70 ${border}`}>
      <TeamRow
        team={node.home}
        teamId={node.home_id}
        goals={finished ? node.home_goals : undefined}
        won={homeWon}
        faded={finished && !homeWon}
        locked={node.home_id ? isLocked(node.round, node.home_id) : false}
        onLock={
          canLock
            ? () => onLock(node.round, node.home_id!, node.away_id!, node.home_id!)
            : undefined
        }
      />
      <div className="h-px bg-ink-800" />
      <TeamRow
        team={node.away}
        teamId={node.away_id}
        goals={finished ? node.away_goals : undefined}
        won={awayWon}
        faded={finished && !awayWon}
        locked={node.away_id ? isLocked(node.round, node.away_id) : false}
        onLock={
          canLock
            ? () => onLock(node.round, node.home_id!, node.away_id!, node.away_id!)
            : undefined
        }
      />
      {(finished || scheduled) && (
        <div className="border-t border-ink-800 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide text-ink-500">
          {finished ? (node.shootout ? "penalties" : "full time") : "quarter-final"}
        </div>
      )}
    </div>
  );
}

/** Elbow connector joining two children (at 25% / 75% height) to the parent. */
function Connector() {
  return (
    <svg
      className="w-7 shrink-0 self-stretch text-ink-700"
      preserveAspectRatio="none"
      viewBox="0 0 28 100"
      aria-hidden
    >
      <path
        d="M0,25 H14 V75 H0 M14,50 H28"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function Node({
  node,
  isLocked,
  onLock,
}: {
  node: BracketNode;
  isLocked: (round: string, teamId: string) => boolean;
  onLock: (round: string, a: string, b: string, winner: string) => void;
}) {
  const expand = EXPAND.has(node.round) && node.children?.length === 2;
  return (
    <div className="flex items-stretch">
      {expand && (
        <>
          <div className="flex flex-col justify-around">
            <Node node={node.children![0]} isLocked={isLocked} onLock={onLock} />
            <Node node={node.children![1]} isLocked={isLocked} onLock={onLock} />
          </div>
          <Connector />
        </>
      )}
      <div className="flex items-center py-3">
        <MatchBox node={node} isLocked={isLocked} onLock={onLock} />
      </div>
    </div>
  );
}

export function KnockoutBracket({
  tree,
  champion,
  isLocked,
  onLock,
}: {
  tree: BracketNode;
  champion?: { team: Team; prob: number } | null;
  isLocked: (round: string, teamId: string) => boolean;
  onLock: (round: string, a: string, b: string, winner: string) => void;
}) {
  // column headers, left→right (R16 … Final)
  const cols = ["R16", "QF", "SF", "F"];
  return (
    <div className="overflow-x-auto pb-2">
      <div className="min-w-[900px]">
        <div className="mb-2 flex items-stretch">
          {cols.map((c, i) => (
            <div key={c} className="flex items-center" style={{ flex: i === cols.length - 1 ? "0 0 auto" : 1 }}>
              <span className="font-mono text-[10px] uppercase tracking-widest text-ink-500">
                {ROUND_LABEL[c]}
              </span>
            </div>
          ))}
          <div className="ml-7 flex items-center">
            <span className="font-mono text-[10px] uppercase tracking-widest text-home">Champion</span>
          </div>
        </div>
        <div className="flex items-stretch">
          <Node node={tree} isLocked={isLocked} onLock={onLock} />
          {/* champion cap */}
          <div className="flex items-center">
            <Connector />
            <div className="w-40 rounded-md border border-gold/50 bg-gold/[0.07] p-2 shadow-[0_0_24px_-8px_rgba(245,196,81,0.35)]">
              {champion ? (
                <>
                  <div className="flex items-center gap-2">
                    <span aria-hidden className="text-xs">🏆</span>
                    <Flag team={champion.team} size={18} />
                    <span className="truncate text-sm font-bold text-gold">
                      {champion.team.name}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[10px] text-gold/80">
                    {(100 * champion.prob).toFixed(1)}% title (sim)
                  </p>
                </>
              ) : (
                <p className="font-mono text-[10px] text-ink-500">most likely champion</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
