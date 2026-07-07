import React from "react";
import type { Probabilities } from "@kickoff/shared";

/**
 * Horizontal stacked H/D/A probability bar with consistent color semantics:
 * home = signal (lime), draw = neutral slate, away = azure.
 * Includes a text alternative for screen readers.
 */
export function ProbBar({
  probs,
  homeName = "Home",
  awayName = "Away",
  height = 10,
  showLabels = false,
}: {
  probs: Probabilities;
  homeName?: string;
  awayName?: string;
  height?: number;
  showLabels?: boolean;
}) {
  const pct = (x: number) => `${(100 * x).toFixed(1)}%`;
  const summary = `${homeName} win ${pct(probs.home)}, draw ${pct(probs.draw)}, ${awayName} win ${pct(probs.away)}`;
  return (
    <div>
      {showLabels && (
        <div className="mb-1 flex justify-between font-mono text-xs text-ink-300">
          <span className="text-home">{pct(probs.home)}</span>
          <span>{pct(probs.draw)}</span>
          <span className="text-away">{pct(probs.away)}</span>
        </div>
      )}
      <div
        role="img"
        aria-label={summary}
        className="flex w-full overflow-hidden rounded-full bg-ink-800"
        style={{ height }}
      >
        <div className="bg-home" style={{ width: pct(probs.home) }} />
        <div className="bg-ink-500" style={{ width: pct(probs.draw) }} />
        <div className="bg-away" style={{ width: pct(probs.away) }} />
      </div>
    </div>
  );
}
