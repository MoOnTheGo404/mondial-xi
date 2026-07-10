import Link from "next/link";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Methodology & Data" };

function H2({ id, children }: { id: string; children: React.ReactNode }) {
  return (
    <h2
      id={id}
      className="mt-10 scroll-mt-24 font-display text-xl font-black uppercase tracking-wide text-ink-50"
    >
      {children}
    </h2>
  );
}

export default function MethodologyPage() {
  return (
    <article className="prose-invert mx-auto max-w-3xl">
      <h1 className="font-display text-3xl font-black uppercase tracking-tight">
        Methodology &amp; Data
      </h1>
      <p className="mt-2 text-ink-300">
        Mondial XI is built on a simple contract: every number is traceable to open
        data, a documented model, and a written-down protocol. This page summarizes the
        full documentation in the repository&apos;s <code>docs/</code> directory.
      </p>

      <H2 id="sources">Sources &amp; licensing</H2>
      <ul className="mt-3 list-inside list-disc space-y-2 text-ink-200">
        <li>
          <strong>Match results, goalscorers, shootouts</strong>:{" "}
          <code>martj42/international_results</code> (GitHub) — CC0 1.0 public domain.
          ~49,500 senior men&apos;s internationals, 1872 → the data cutoff shown in the
          header. Downloads are checksummed and recorded in provenance manifests.
        </li>
        <li>
          <strong>Fresh-results overlay</strong>: Wikipedia (CC BY-SA 4.0). The CC0
          core is volunteer-maintained and can lag a day or two behind a final whistle,
          so the current tournament&apos;s Wikipedia page is parsed for <em>completed</em>{" "}
          scorelines (facts only) to fill matches the core hasn&apos;t published yet.
          Never overwrites a recorded result; skips any tie without a numeric score, so
          nothing is invented. Falls back to the core alone if unavailable.
        </li>
        <li>
          <strong>Flags</strong>: <code>flag-icons</code> (MIT). Historical/dissolved
          teams without a licensed flag render a neutral monogram.
        </li>
        <li>
          <strong>Weather</strong>: Open-Meteo.com (CC BY 4.0, non-commercial tier) —
          display and scenario context only, never a model feature (no feasible
          historical backfill within fair use).
        </li>
        <li>
          <strong>Rejected</strong>: scraping eloratings.net (no license), TheSportsDB
          images (trademark ambiguity), API-Football free tier (no publication rights).
          Full comparison in <code>docs/data-source-evaluation.md</code>.
        </li>
      </ul>

      <H2 id="entities">Entity resolution</H2>
      <p className="mt-3 text-ink-200">
        Teams get stable kebab-case IDs keyed to their <em>current</em> identity; era
        names (Zaïre, Soviet Union) map forward via the dataset&apos;s former-names table
        while match pages preserve the historical name. Deliberately-distinct dissolved
        teams (Czechoslovakia, East Germany, Yugoslavia) are never merged into
        successors. Players are identified as <code>team/player-slug</code> from
        goalscorer records — accent-folded, deduplicated per team.
      </p>

      <H2 id="ratings">Ratings &amp; features</H2>
      <p className="mt-3 text-ink-200">
        A tuned Elo engine (home advantage and K-scale grid-searched on the validation
        window; margin-of-victory multiplier; tournament-importance K) runs a single
        chronological pass from 1872. For every match the feature vector is emitted{" "}
        <em>before</em> the engine sees the result — leakage is structurally impossible
        and additionally covered by dedicated tests (truncation invariance, future-result
        tampering, own-result tampering).
      </p>

      <H2 id="models">Models</H2>
      <ul className="mt-3 list-inside list-disc space-y-2 text-ink-200">
        <li>Frequency baseline (constant H/D/A rates).</li>
        <li>Elo-only multinomial logistic — the honest baseline.</li>
        <li>Independent Poisson GLMs for each side&apos;s goals.</li>
        <li>
          Dixon–Coles: the same GLMs plus the low-score dependence correction, ρ fitted
          by maximum likelihood.
        </li>
        <li>
          Gradient-boosted trees over the full feature set with per-class isotonic
          calibration fitted only on the validation window.
        </li>
      </ul>
      <p className="mt-3 text-ink-200">
        Fit 1980–2018, select and calibrate 2019–2022, report once on 2023→cutoff. The
        serving artifact is byte-identical to the evaluated pipeline; only rating state
        advances to the data cutoff.
      </p>

      <H2 id="players">Player layer (and its limits)</H2>
      <p className="mt-3 text-ink-200">
        The only legally usable player-level signal in the open data is{" "}
        <em>who scored</em>. We build attack-side impact estimates: a player&apos;s
        goals per team-match over their active window, shrunk toward zero with a
        25-match empirical-Bayes prior and capped. These power the Match Lab&apos;s
        what-if adjustments — expected-goals deltas that tilt the champion&apos;s
        probabilities through the Dixon–Coles score matrix (the tilt is multiplicative
        and shown next to the unadjusted team-only forecast).
      </p>
      <p className="mt-3 text-ink-200" id="availability">
        <strong>Availability:</strong> no free provider grants publication rights for
        injury/lineup feeds, so every player&apos;s status is honestly{" "}
        <em>unknown</em>. Scenario changes are labeled user assumptions; doubtful players
        are marginalized over their availability probability rather than assumed in or
        out. Because no historical availability data exists, we make no claim that the
        player layer improves historical accuracy — the team-level model remains the
        evaluated champion.
      </p>

      <H2 id="simulation">Tournament simulation</H2>
      <p className="mt-3 text-ink-200">
        A vectorized Monte Carlo engine samples scorelines from each pairing&apos;s
        Dixon–Coles matrix. Group ranking implements the 2026 tiebreaker order (points →
        head-to-head among tied teams → overall GD/GF → ranking; conduct scores are not
        in the data, so the final criterion is proxied by Elo — documented
        approximation). Real results are pinned; extra time uses ⅓-scaled goal rates;
        shootouts are 50/50. The WC-2026 format (12 groups, 8 best thirds, round of 32)
        was verified against FIFA/Wikipedia sources cited in the versioned config.
        Full-tournament what-ifs allocate qualified thirds by constraint satisfaction
        (FIFA&apos;s Annex C table isn&apos;t public — documented approximation).
      </p>

      <H2 id="track-record">Track record integrity</H2>
      <p className="mt-3 text-ink-200">
        Prospective forecasts are stored as immutable, SHA-256-hashed snapshots before
        kickoff and scored after. Backtests are computed under the chronological
        protocol and always labeled as backtests. There is no mechanism to backdate a
        &quot;published&quot; forecast.
      </p>

      <H2 id="reproduce">Reproducibility</H2>
      <pre className="mt-3 overflow-x-auto rounded border border-ink-700 bg-ink-900 p-4 font-mono text-xs text-ink-200">
        {`make bootstrap   # toolchain + dependencies
make data        # download (CC0) + validate + build parquet
make train       # tune Elo, fit models, evaluate, write artifacts
make dev         # API :8000 + web :3000`}
      </pre>

      <p className="mt-8 border-t border-ink-800 pt-4 font-mono text-xs text-ink-500">
        Deeper reading in the repository: docs/methodology.md · docs/model-card.md ·
        docs/data-card.md · docs/player-model.md · docs/tournament-rules.md ·
        docs/data-source-evaluation.md.{" "}
        <Link href="/performance" className="text-brand hover:underline">
          See measured performance →
        </Link>
      </p>
    </article>
  );
}
