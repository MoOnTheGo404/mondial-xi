"use client";

/**
 * Football pitch formation diagram (pure SVG, no external assets).
 * Honesty note baked into the UI: the open dataset has no lineups or player
 * positions, so this renders the SHAPE of a user-chosen formation. Known
 * attacking contributors (from scoring records) can be attached by the user
 * to forward slots; all other slots are explicitly unnamed.
 */

export const FORMATIONS: Record<string, number[]> = {
  "4-3-3": [4, 3, 3],
  "4-4-2": [4, 4, 2],
  "4-2-3-1": [4, 2, 3, 1],
  "3-5-2": [3, 5, 2],
  "5-3-2": [5, 3, 2],
};

export function PitchFormation({
  formation,
  attackerNames = [],
  teamName,
}: {
  formation: string;
  attackerNames?: string[];
  teamName: string;
}) {
  const rows = FORMATIONS[formation] ?? FORMATIONS["4-3-3"];
  const W = 300;
  const H = 400;
  // slot positions: GK + rows from defense (bottom) to attack (top)
  const slots: { x: number; y: number; label: string }[] = [
    { x: W / 2, y: H - 34, label: "GK" },
  ];
  const bandNames = ["DF", "MF", "MF", "FW"];
  rows.forEach((count, ri) => {
    const y = H - 100 - ri * ((H - 160) / Math.max(rows.length - 1, 1));
    for (let i = 0; i < count; i++) {
      const x = ((i + 1) * W) / (count + 1);
      const isTopRow = ri === rows.length - 1;
      slots.push({ x, y, label: isTopRow ? "FW" : (bandNames[ri] ?? "MF") });
    }
  });
  // attach known attacker names to the most advanced slots
  const fwSlots = slots.filter((s) => s.label === "FW");
  const named = new Map<number, string>();
  attackerNames.slice(0, fwSlots.length).forEach((n, i) => {
    named.set(slots.indexOf(fwSlots[i]), n);
  });

  return (
    <figure>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Illustrative ${formation} formation shape for ${teamName}`}
        className="w-full max-w-xs rounded-lg border border-ink-700"
      >
        <rect width={W} height={H} fill="#0e1a12" />
        {/* pitch markings */}
        <g stroke="#2c4232" strokeWidth="1.5" fill="none">
          <rect x="8" y="8" width={W - 16} height={H - 16} rx="2" />
          <line x1="8" y1={H / 2} x2={W - 8} y2={H / 2} />
          <circle cx={W / 2} cy={H / 2} r="34" />
          <rect x={W / 2 - 66} y={H - 60} width="132" height="52" />
          <rect x={W / 2 - 66} y="8" width="132" height="52" />
          <rect x={W / 2 - 30} y={H - 30} width="60" height="22" />
          <rect x={W / 2 - 30} y="8" width="60" height="22" />
        </g>
        {slots.map((s, i) => {
          const name = named.get(i);
          return (
            <g key={i}>
              <circle
                cx={s.x}
                cy={s.y}
                r="13"
                fill={name ? "#34e57e" : "#131b1e"}
                stroke={name ? "#34e57e" : "#52625f"}
                strokeWidth="1.5"
              />
              <text
                x={s.x}
                y={s.y + 3.5}
                textAnchor="middle"
                fontSize="9"
                fontFamily="monospace"
                fill={name ? "#0a1012" : "#7d8d8a"}
              >
                {s.label}
              </text>
              {name && (
                <text
                  x={s.x}
                  y={s.y + 26}
                  textAnchor="middle"
                  fontSize="9"
                  fill="#c8d2cf"
                >
                  {name.split(" ").slice(-1)[0]}
                </text>
              )}
            </g>
          );
        })}
      </svg>
      <figcaption className="mt-1 font-mono text-[10px] leading-snug text-ink-500">
        Illustrative formation shape — the open dataset contains no lineups or
        positions. Named markers are user-assigned attacking contributors.
      </figcaption>
    </figure>
  );
}
