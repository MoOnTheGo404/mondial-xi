"use client";

import { useMemo } from "react";
import type { Team } from "@kickoff/shared";
import { Flag, Trophy } from "@kickoff/ui";

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

export interface Lock {
  round: string;
  team_a: string;
  team_b: string;
  winner: string;
}

const ROUND_LABEL: Record<string, string> = {
  R16: "Round of 16",
  QF: "Quarter-finals",
  SF: "Semi-finals",
  F: "Final",
};

// rounds we expand children for (leaves are Round of 16)
const EXPAND = new Set(["F", "SF", "QF"]);

// column geometry — must match MatchBox width (w-44) + Connector width (w-7)
const COL_W = "11rem"; // w-44
const CONN_W = "1.75rem"; // w-7

/** The winner of a node: the real result, or the user's pick for that tie. */
function pickedWinner(node: BracketNode, locks: Lock[]): { id: string; team: Team | null } | null {
  if (node.status === "finished" && node.winner_id) {
    return { id: node.winner_id, team: node.winner_id === node.home_id ? node.home : node.away };
  }
  if (node.home_id && node.away_id) {
    const lk = locks.find(
      (l) =>
        l.round === node.round &&
        ((l.team_a === node.home_id && l.team_b === node.away_id) ||
          (l.team_a === node.away_id && l.team_b === node.home_id)),
    );
    if (lk) return { id: lk.winner, team: lk.winner === node.home_id ? node.home : node.away };
  }
  return null;
}

/** Fill undecided (pending) rounds with the winners the user has picked in the
 * rounds below, so a pick advances and the next tie becomes pickable. */
function resolve(node: BracketNode, locks: Lock[]): BracketNode {
  const children = node.children?.map((c) => resolve(c, locks));
  let { home_id, away_id, home, away } = node;
  if (node.status === "pending" && children && children.length === 2) {
    const w0 = pickedWinner(children[0], locks);
    const w1 = pickedWinner(children[1], locks);
    home_id = w0?.id ?? null;
    home = w0?.team ?? null;
    away_id = w1?.id ?? null;
    away = w1?.team ?? null;
  }
  return { ...node, home_id, away_id, home, away, children };
}

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
          className={`shrink-0 rounded px-1.5 py-0.5 font-mono text-[9px] uppercase transition-colors ${
            locked
              ? "bg-gold font-bold text-ink-950"
              : "border border-ink-600 text-ink-400 hover:border-gold hover:text-gold"
          }`}
        >
          {locked ? "✓ won" : "pick"}
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
  const homeWon = node.winner_id === node.home_id;
  const awayWon = node.winner_id === node.away_id;
  // pickable once both teams are known and the tie hasn't actually been played
  const canPick = !finished && Boolean(node.home_id) && Boolean(node.away_id);
  const homeLocked = node.home_id ? isLocked(node.round, node.home_id) : false;
  const awayLocked = node.away_id ? isLocked(node.round, node.away_id) : false;
  const border = homeLocked || awayLocked
    ? "border-gold/60"
    : node.round === "F"
      ? "border-gold/40"
      : finished
        ? "border-ink-700"
        : canPick
          ? "border-away/40"
          : "border-ink-800";

  return (
    <div className={`w-44 rounded-md border bg-ink-900/70 ${border}`}>
      <TeamRow
        team={node.home}
        teamId={node.home_id}
        goals={finished ? node.home_goals : undefined}
        won={finished ? homeWon : homeLocked}
        faded={(finished && !homeWon) || (!finished && awayLocked)}
        locked={homeLocked}
        onLock={
          canPick
            ? () => onLock(node.round, node.home_id!, node.away_id!, node.home_id!)
            : undefined
        }
      />
      <div className="h-px bg-ink-800" />
      <TeamRow
        team={node.away}
        teamId={node.away_id}
        goals={finished ? node.away_goals : undefined}
        won={finished ? awayWon : awayLocked}
        faded={(finished && !awayWon) || (!finished && homeLocked)}
        locked={awayLocked}
        onLock={
          canPick
            ? () => onLock(node.round, node.home_id!, node.away_id!, node.away_id!)
            : undefined
        }
      />
      <div className="border-t border-ink-800 px-2 py-0.5 font-mono text-[9px] uppercase tracking-wide text-ink-500">
        {finished
          ? node.shootout
            ? "penalties"
            : "full time"
          : canPick
            ? "pick a winner →"
            : "awaiting teams"}
      </div>
    </div>
  );
}

/** Elbow connector joining two children (at 25% / 75% height) to the parent. */
function Connector() {
  return (
    <svg
      className="w-7 shrink-0 self-stretch text-ink-600"
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
  locks,
  champion,
  isLocked,
  onLock,
}: {
  tree: BracketNode;
  locks: Lock[];
  champion?: { team: Team; prob: number } | null;
  isLocked: (round: string, teamId: string) => boolean;
  onLock: (round: string, a: string, b: string, winner: string) => void;
}) {
  const resolved = useMemo(() => resolve(tree, locks), [tree, locks]);
  // if the user has picked the final, that team is *their* champion
  const pickedChamp = pickedWinner(resolved, locks);
  const cols = ["R16", "QF", "SF", "F"] as const;

  return (
    <div className="overflow-x-auto pb-2">
      <div className="min-w-[900px]">
        {/* column headers — fixed widths matching the bracket columns below */}
        <div className="mb-1 flex">
          {cols.map((c) => (
            <div key={c} className="flex shrink-0">
              <div
                className="text-center font-mono text-[10px] uppercase tracking-widest text-ink-500"
                style={{ width: COL_W }}
              >
                {ROUND_LABEL[c]}
              </div>
              <div className="shrink-0" style={{ width: CONN_W }} aria-hidden />
            </div>
          ))}
          <div
            className="text-center font-mono text-[10px] uppercase tracking-widest text-gold"
            style={{ width: "10rem" }}
          >
            Champion
          </div>
        </div>

        <div className="flex items-stretch">
          <Node node={resolved} isLocked={isLocked} onLock={onLock} />
          {/* champion cap */}
          <div className="flex items-center">
            <Connector />
            <div className="w-40 rounded-md border border-gold/50 bg-gold/[0.07] p-2 shadow-[0_0_24px_-8px_rgba(245,196,81,0.35)]">
              {pickedChamp?.team ? (
                <>
                  <div className="flex items-center gap-2">
                    <Trophy size={18} className="shrink-0" />
                    <Flag team={pickedChamp.team} size={18} />
                    <span className="truncate text-sm font-bold text-gold">
                      {pickedChamp.team.name}
                    </span>
                  </div>
                  <p className="mt-1 font-mono text-[10px] text-gold/80">your pick</p>
                </>
              ) : champion ? (
                <>
                  <div className="flex items-center gap-2">
                    <Trophy size={18} className="shrink-0" />
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
