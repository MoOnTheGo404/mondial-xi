import React from "react";

/* An original, generic two-handled champion's cup — deliberately NOT a replica
   of any real tournament trophy (those are trademarked/copyrighted). A plain
   gold cup reads as "the winner's prize" to every fan, with no licensing risk. */

export function Trophy({
  size = 96,
  className = "",
  shine = false,
  title = "Champion's trophy",
}: {
  size?: number;
  className?: string;
  shine?: boolean;
  title?: string;
}) {
  return (
    <svg
      viewBox="0 0 100 120"
      width={size}
      height={(size * 120) / 100}
      role="img"
      aria-label={title}
      className={className}
    >
      <defs>
        <linearGradient id="trophy-gold" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#ffe9a8" />
          <stop offset="34%" stopColor="#f5c451" />
          <stop offset="72%" stopColor="#d69a2b" />
          <stop offset="100%" stopColor="#b57e1e" />
        </linearGradient>
        <linearGradient id="trophy-rim" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#b57e1e" />
          <stop offset="50%" stopColor="#ffe9a8" />
          <stop offset="100%" stopColor="#b57e1e" />
        </linearGradient>
      </defs>

      {/* handles */}
      <path
        d="M27,29 C9,29 9,57 30,53"
        fill="none"
        stroke="url(#trophy-gold)"
        strokeWidth="5"
        strokeLinecap="round"
      />
      <path
        d="M73,29 C91,29 91,57 70,53"
        fill="none"
        stroke="url(#trophy-gold)"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* bowl */}
      <path
        d="M26,25 L74,25 C74,53 62,65 50,65 C38,65 26,53 26,25 Z"
        fill="url(#trophy-gold)"
        stroke="#8a5e15"
        strokeWidth="0.8"
      />
      {/* rim / lip */}
      <rect x="22" y="18" width="56" height="9" rx="4.5" fill="url(#trophy-rim)" stroke="#8a5e15" strokeWidth="0.6" />
      {/* bowl highlight */}
      <path d="M33,28 C34,44 40,54 47,58" fill="none" stroke="#fff6da" strokeWidth="2.4" strokeLinecap="round" opacity="0.55" />

      {/* stem + foot + plinth */}
      <rect x="46" y="64" width="8" height="14" fill="url(#trophy-gold)" />
      <path d="M38,78 L62,78 L66,88 L34,88 Z" fill="url(#trophy-gold)" stroke="#8a5e15" strokeWidth="0.6" />
      <rect x="30" y="88" width="40" height="11" rx="2" fill="url(#trophy-gold)" stroke="#8a5e15" strokeWidth="0.6" />
      <rect x="26" y="99" width="48" height="8" rx="2.5" fill="#a06d18" />

      {/* star emblem on the cup */}
      <polygon
        points="50,33 52.4,40 59.8,40 53.8,44.4 56.1,51.4 50,47.1 43.9,51.4 46.2,44.4 40.2,40 47.6,40"
        fill="#fff6da"
        opacity="0.9"
      />

      {/* twinkling glints */}
      {shine && (
        <g fill="#ffffff">
          <polygon className="animate-twinkle" style={{ animationDelay: "-0.4s" }} points="30,20 31.2,23 34.2,24.2 31.2,25.4 30,28.4 28.8,25.4 25.8,24.2 28.8,23" />
          <polygon className="animate-twinkle" style={{ animationDelay: "-1.6s" }} points="70,44 70.9,46.2 73.1,47.1 70.9,48 70,50.2 69.1,48 66.9,47.1 69.1,46.2" />
        </g>
      )}
    </svg>
  );
}
