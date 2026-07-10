import React from "react";

/* An original, hand-drawn classic football (truncated-icosahedron pattern):
   a white sphere with a central black pentagon, five rim pentagons and the
   seams joining them. Pure geometry — no external asset, no licensed mark. */

const TAU = Math.PI * 2;

function polygon(cx: number, cy: number, r: number, rotDeg: number, n = 5): string {
  const rot = (rotDeg * Math.PI) / 180;
  const pts: string[] = [];
  for (let i = 0; i < n; i++) {
    const a = rot + (i * TAU) / n;
    pts.push(`${(cx + r * Math.cos(a)).toFixed(2)},${(cy + r * Math.sin(a)).toFixed(2)}`);
  }
  return pts.join(" ");
}

function point(cx: number, cy: number, r: number, deg: number): [number, number] {
  const a = (deg * Math.PI) / 180;
  return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
}

export function SoccerBall({
  size = 120,
  className = "",
  spin = false,
  title = "Football",
}: {
  size?: number;
  className?: string;
  spin?: boolean;
  title?: string;
}) {
  const cx = 50;
  const cy = 50;
  const R = 47;
  // vertices of the central pentagon (seams start here)
  const spokes = [-90, -18, 54, 126, 198];
  // the five gaps between spokes hold the rim pentagons
  const gaps = [-54, 18, 90, 162, 234];
  const panel = "#0c1413";

  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      role="img"
      aria-label={title}
      className={`${spin ? "animate-spin-slow" : ""} ${className}`.trim()}
    >
      <defs>
        <radialGradient id="ball-sphere" cx="38%" cy="32%" r="78%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="58%" stopColor="#e8edeb" />
          <stop offset="100%" stopColor="#aeb9b6" />
        </radialGradient>
        <clipPath id="ball-clip">
          <circle cx={cx} cy={cy} r={R} />
        </clipPath>
      </defs>

      <circle cx={cx} cy={cy} r={R} fill="url(#ball-sphere)" />

      <g clipPath="url(#ball-clip)">
        {/* black panels */}
        <g fill={panel}>
          <polygon points={polygon(cx, cy, 15, -90)} />
          {gaps.map((g, i) => {
            const [ox, oy] = point(cx, cy, 40, g);
            return <polygon key={i} points={polygon(ox, oy, 10, g)} />;
          })}
        </g>
        {/* seams from the central pentagon out to the rim */}
        <g stroke={panel} strokeWidth={1.4} strokeLinecap="round" fill="none">
          {spokes.map((s, i) => {
            const [x1, y1] = point(cx, cy, 15, s);
            const [x2, y2] = point(cx, cy, R, s);
            return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
          })}
        </g>
      </g>

      {/* glossy highlight + soft rim */}
      <ellipse cx="35" cy="29" rx="13" ry="8" fill="#ffffff" opacity="0.35" clipPath="url(#ball-clip)" />
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(0,0,0,0.22)" strokeWidth={1.2} />
    </svg>
  );
}
