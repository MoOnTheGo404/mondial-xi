import React from "react";

/* An original, hand-drawn classic football (truncated-icosahedron pattern):
   a shaded white sphere with a central black pentagon, five rim pentagons and
   the seams joining them. Layered gradients fake real 3-D volume — a specular
   hotspot, edge ambient-occlusion and panel shading. Pure geometry, no
   external asset, no licensed mark. */

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
  const spokes = [-90, -18, 54, 126, 198];
  const gaps = [-54, 18, 90, 162, 234];
  const uid = React.useId().replace(/:/g, "");

  return (
    <svg
      viewBox="0 0 100 100"
      width={size}
      height={size}
      role="img"
      aria-label={title}
      className={className}
    >
      <defs>
        <radialGradient id={`sphere-${uid}`} cx="37%" cy="30%" r="80%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="45%" stopColor="#eef1f4" />
          <stop offset="82%" stopColor="#c3cbd4" />
          <stop offset="100%" stopColor="#9aa4b1" />
        </radialGradient>
        {/* edge ambient occlusion — transparent centre, dark rim */}
        <radialGradient id={`ao-${uid}`} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#000000" stopOpacity="0" />
          <stop offset="72%" stopColor="#000000" stopOpacity="0" />
          <stop offset="100%" stopColor="#0a0a18" stopOpacity="0.5" />
        </radialGradient>
        {/* subtle panel shading (lit top, shadowed bottom) */}
        <linearGradient id={`panel-${uid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1c2233" />
          <stop offset="100%" stopColor="#070b14" />
        </linearGradient>
        <clipPath id={`clip-${uid}`}>
          <circle cx={cx} cy={cy} r={R} />
        </clipPath>
      </defs>

      <g className={spin ? "animate-spin-slow" : ""} style={{ transformOrigin: "50px 50px" }}>
        <circle cx={cx} cy={cy} r={R} fill={`url(#sphere-${uid})`} />

        <g clipPath={`url(#clip-${uid})`}>
          <g fill={`url(#panel-${uid})`}>
            <polygon points={polygon(cx, cy, 15, -90)} />
            {gaps.map((g, i) => {
              const [ox, oy] = point(cx, cy, 40, g);
              return <polygon key={i} points={polygon(ox, oy, 10, g)} />;
            })}
          </g>
          <g stroke="#0b1018" strokeWidth={1.4} strokeLinecap="round" fill="none">
            {spokes.map((s, i) => {
              const [x1, y1] = point(cx, cy, 15, s);
              const [x2, y2] = point(cx, cy, R, s);
              return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} />;
            })}
          </g>
        </g>
      </g>

      {/* volume + gloss (do not spin — light stays fixed) */}
      <circle cx={cx} cy={cy} r={R} fill={`url(#ao-${uid})`} clipPath={`url(#clip-${uid})`} />
      <ellipse cx="35" cy="28" rx="15" ry="9" fill="#ffffff" opacity="0.4" clipPath={`url(#clip-${uid})`} />
      <ellipse cx="31" cy="24" rx="5" ry="3" fill="#ffffff" opacity="0.7" clipPath={`url(#clip-${uid})`} />
      <circle cx={cx} cy={cy} r={R} fill="none" stroke="rgba(0,0,0,0.25)" strokeWidth={1} />
    </svg>
  );
}
