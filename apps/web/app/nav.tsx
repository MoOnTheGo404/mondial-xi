"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@kickoff/shared";
import { useState } from "react";

const LINKS = [
  { href: "/fixtures", label: "Fixtures" },
  { href: "/simulator", label: "Simulator" },
  { href: "/lab", label: "Match Lab" },
  { href: "/compare", label: "Compare" },
  { href: "/teams", label: "Teams" },
  { href: "/players", label: "Players" },
  { href: "/archive", label: "Archive" },
  { href: "/performance", label: "Performance" },
  { href: "/methodology", label: "Methodology" },
];

interface Status {
  ready: boolean;
  model_version?: string;
  data_cutoff?: string;
}

export function Nav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const { data } = useQuery({
    queryKey: ["system-status"],
    queryFn: () => apiGet<Status>("/system/status"),
    staleTime: 300_000,
  });

  return (
    <header className="sticky top-0 z-40 border-b border-ink-800 bg-ink-950/90 backdrop-blur">
      <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-3 sm:px-6">
        <Link
          href="/"
          className="flex items-baseline gap-1.5 whitespace-nowrap"
          aria-label="Kickoff Atlas home"
        >
          <span className="font-display text-lg font-black uppercase tracking-tight text-ink-50">
            Kickoff
          </span>
          <span className="font-display text-lg font-black uppercase tracking-tight text-home">
            Atlas
          </span>
        </Link>

        <nav className="hidden flex-1 lg:block" aria-label="Primary">
          <ul className="flex items-center gap-1">
            {LINKS.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  aria-current={pathname === l.href ? "page" : undefined}
                  className={`rounded px-2.5 py-1.5 text-sm font-medium transition-colors ${
                    pathname?.startsWith(l.href)
                      ? "bg-ink-800 text-home"
                      : "text-ink-300 hover:bg-ink-900 hover:text-ink-100"
                  }`}
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        <div className="ml-auto hidden items-center gap-2 font-mono text-[11px] text-ink-400 md:flex">
          {data?.ready ? (
            <span title={`Model ${data.model_version}`}>
              data cutoff <span className="text-ink-200">{data.data_cutoff}</span>
            </span>
          ) : (
            <span className="text-amber-400">API offline</span>
          )}
        </div>

        <button
          type="button"
          className="rounded border border-ink-700 px-2.5 py-1.5 text-sm text-ink-200 lg:hidden"
          aria-expanded={open}
          aria-controls="mobile-nav"
          onClick={() => setOpen((v) => !v)}
        >
          Menu
        </button>
      </div>

      {open && (
        <nav id="mobile-nav" aria-label="Primary mobile" className="border-t border-ink-800 lg:hidden">
          <ul className="mx-auto grid max-w-7xl grid-cols-2 gap-1 px-4 py-3 sm:px-6">
            {LINKS.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  onClick={() => setOpen(false)}
                  className="block rounded px-3 py-2 text-sm text-ink-200 hover:bg-ink-900"
                >
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      )}
    </header>
  );
}
