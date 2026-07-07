import React from "react";
import type { Team } from "@kickoff/shared";

/**
 * Country flag via the MIT-licensed `flag-icons` CSS sprite package.
 * Teams without a licensed flag (historical states, CONIFA sides) get a
 * neutral monogram tile. Always paired with an accessible label.
 */
export function Flag({
  team,
  size = 20,
  className = "",
}: {
  team: Pick<Team, "flag_code" | "name">;
  size?: number;
  className?: string;
}) {
  const h = Math.round(size * 0.75);
  if (!team.flag_code) {
    return (
      <span
        role="img"
        aria-label={`${team.name} (no flag available)`}
        className={`inline-flex items-center justify-center rounded-[2px] bg-ink-700 font-mono uppercase text-ink-200 ${className}`}
        style={{ width: size, height: h, fontSize: h * 0.55, lineHeight: 1 }}
      >
        {team.name.slice(0, 1)}
      </span>
    );
  }
  return (
    <span
      role="img"
      aria-label={`Flag of ${team.name}`}
      className={`fi fi-${team.flag_code} inline-block rounded-[2px] ${className}`}
      style={{ width: size, height: h, backgroundSize: "cover" }}
    />
  );
}
