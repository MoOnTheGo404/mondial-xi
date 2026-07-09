"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet, fmtPct } from "@kickoff/shared";
import { Badge, Card, SectionTitle, Stat } from "@kickoff/ui";
import { ErrorBox } from "@/components/fixtures";
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Slice {
  n: number;
  log_loss: number;
  rps: number;
  brier: number;
  accuracy: number;
  ece: number;
}

interface Metrics {
  metrics: {
    model_version: string;
    data_cutoff: string;
    protocol: {
      fit_window: string[];
      validation_window: string[];
      test_window: string[];
      champion_selected_on: string;
    };
    champion: string;
    champion_test: Record<string, number>;
    champion_validation: Record<string, number>;
    confidence_buckets: {
      bucket: string;
      count: number;
      mean_confidence: number;
      top_pick_accuracy: number;
    }[];
    by_year: (Slice & { year: number })[];
    by_tier: (Slice & { tier: string })[];
    by_confederation: (Slice & { confederation: string })[];
    favorites_vs_close: (Slice & { segment: string })[];
    counts: { train: number; validation: number; test: number };
  };
  comparison: Record<string, { validation: Record<string, number>; test: Record<string, number> }>;
  calibration: {
    champion: string;
    test_reliability: { class: string; forecast_mean: number; observed_freq: number; count: number }[];
  };
}

const chartTheme = {
  contentStyle: {
    background: "#0d1410",
    border: "1px solid #253229",
    borderRadius: 6,
    fontFamily: "monospace",
    fontSize: 12,
  },
};

export default function PerformancePage() {
  const q = useQuery({
    queryKey: ["model-metrics"],
    queryFn: () => apiGet<Metrics>("/models/metrics"),
    staleTime: Infinity,
  });
  if (q.isLoading) return <div className="h-96 animate-pulse rounded-lg bg-ink-900" />;
  if (q.isError) return <ErrorBox message={(q.error as Error).message} />;
  const { metrics, comparison, calibration } = q.data!;

  const rel = calibration.test_reliability;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="font-display text-3xl font-black uppercase tracking-tight">
          Model Performance
        </h1>
        <p className="mt-1 font-mono text-xs text-ink-400">
          model {metrics.model_version} · data cutoff {metrics.data_cutoff} · every number
          on this page is loaded from evaluation artifacts, not typed by hand
        </p>
      </div>

      {/* protocol diagram */}
      <Card className="p-5">
        <SectionTitle sub={`champion selected on ${metrics.protocol.champion_selected_on}`}>
          Chronological protocol
        </SectionTitle>
        <div className="flex flex-col gap-1 sm:flex-row" role="img" aria-label={`Chronological split: fit ${metrics.protocol.fit_window.join(" to ")}, validation ${metrics.protocol.validation_window.join(" to ")}, test ${metrics.protocol.test_window.join(" to ")}`}>
          {(
            [
              ["FIT", metrics.protocol.fit_window, metrics.counts.train, "bg-ink-700", "text-ink-100", "text-ink-300"],
              ["VALIDATION", metrics.protocol.validation_window, metrics.counts.validation, "bg-away/60", "text-ink-950", "text-ink-950/80"],
              ["UNTOUCHED TEST", metrics.protocol.test_window, metrics.counts.test, "bg-home/70", "text-ink-950", "text-ink-950/80"],
            ] as const
          ).map(([label, window, n, cls, titleCls, subCls]) => (
            <div key={label} className={`flex-1 rounded p-3 ${cls}`}>
              <p className={`font-display text-xs font-bold uppercase tracking-wider sm:text-sm ${titleCls}`}>
                {label}
              </p>
              <p className={`font-mono text-[11px] ${subCls}`}>
                {window[0]} → {window[1]} · {n.toLocaleString()} matches
              </p>
            </div>
          ))}
        </div>
        <p className="mt-2 font-mono text-[11px] text-ink-500">
          Ratings/features accumulate from 1872; matches before 1980 warm up state only.
          Random splits are never used.
        </p>
      </Card>

      {/* headline metrics */}
      <Card className="p-5">
        <SectionTitle sub={`champion: ${metrics.champion}`}>
          Untouched-test results
        </SectionTitle>
        <dl className="grid grid-cols-2 gap-4 sm:grid-cols-6">
          <Stat label="matches" value={metrics.champion_test.n.toLocaleString()} />
          <Stat label="log loss" value={metrics.champion_test.log_loss.toFixed(4)} />
          <Stat label="RPS" value={metrics.champion_test.rps.toFixed(4)} />
          <Stat label="Brier" value={metrics.champion_test.brier.toFixed(4)} />
          <Stat label="top-pick acc." value={fmtPct(metrics.champion_test.accuracy)} />
          <Stat label="ECE" value={metrics.champion_test.ece.toFixed(4)} />
        </dl>
      </Card>

      {/* model comparison */}
      <Card className="overflow-x-auto p-5">
        <SectionTitle sub="lower log loss / RPS is better; champion chosen on validation before test was touched">
          Model comparison
        </SectionTitle>
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="border-b border-ink-700 font-mono text-[11px] uppercase text-ink-400">
              <th className="py-2 text-left">Model</th>
              <th className="px-2 text-right">Val log loss</th>
              <th className="px-2 text-right">Test log loss</th>
              <th className="px-2 text-right">Test RPS</th>
              <th className="px-2 text-right">Test acc.</th>
              <th className="px-2 text-right">Test ECE</th>
            </tr>
          </thead>
          <tbody className="font-mono tabular-nums">
            {Object.entries(comparison)
              .sort((a, b) => a[1].validation.log_loss - b[1].validation.log_loss)
              .map(([name, m]) => (
                <tr
                  key={name}
                  className={`border-b border-ink-800/60 ${name === metrics.champion ? "text-home" : ""}`}
                >
                  <td className="py-1.5 font-sans">
                    {name}
                    {name === metrics.champion && <Badge tone="signal">champion</Badge>}
                  </td>
                  <td className="px-2 text-right">{m.validation.log_loss.toFixed(4)}</td>
                  <td className="px-2 text-right">{m.test.log_loss.toFixed(4)}</td>
                  <td className="px-2 text-right">{m.test.rps.toFixed(4)}</td>
                  <td className="px-2 text-right">{fmtPct(m.test.accuracy, 1)}</td>
                  <td className="px-2 text-right">{m.test.ece.toFixed(4)}</td>
                </tr>
              ))}
          </tbody>
        </table>
        <p className="mt-3 max-w-3xl text-xs text-ink-400">
          Honest reading: the champion is a <strong>parameter-free geometric mean</strong>{" "}
          of the Elo-logistic and Dixon–Coles models — it wins both validation and the
          untouched test set because their errors are partly independent. Notably, a{" "}
          <em>learned</em> stack and the isotonic-calibrated GBM overfit this modest data
          and lose under rigorous out-of-sample selection: parsimony generalizes here.
        </p>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* calibration */}
        <Card className="p-5">
          <SectionTitle sub="test window · perfect calibration = diagonal">
            Calibration
          </SectionTitle>
          <div className="h-72" aria-hidden>
            <ResponsiveContainer>
              <ScatterChart margin={{ top: 8, right: 8, bottom: 4, left: -14 }}>
                <CartesianGrid stroke="#1c2921" />
                <XAxis
                  type="number"
                  dataKey="forecast_mean"
                  domain={[0, 1]}
                  stroke="#55685c"
                  fontSize={11}
                  fontFamily="monospace"
                  label={{ value: "forecast", position: "insideBottom", offset: -2, fill: "#7f9186", fontSize: 11 }}
                />
                <YAxis
                  type="number"
                  dataKey="observed_freq"
                  domain={[0, 1]}
                  stroke="#55685c"
                  fontSize={11}
                  fontFamily="monospace"
                  label={{ value: "observed", angle: -90, position: "insideLeft", offset: 24, fill: "#7f9186", fontSize: 11 }}
                />
                <ReferenceLine
                  segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
                  stroke="#55685c"
                  strokeDasharray="4 4"
                />
                <Tooltip
                  {...chartTheme}
                  formatter={(v) => (typeof v === "number" ? v.toFixed(3) : String(v ?? ""))}
                />
                {(["H", "D", "A"] as const).map((cls, i) => (
                  <Scatter
                    key={cls}
                    name={cls}
                    data={rel.filter((r) => r.class === cls)}
                    fill={["#a3e635", "#7f9186", "#38bdf8"][i]}
                  />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <p className="font-mono text-[11px] text-ink-500">
            <span className="text-home">● home</span> · <span>● draw</span> ·{" "}
            <span className="text-away">● away</span> — per-class reliability, bins with
            ≥10 matches. Text alternative: max deviation from diagonal is{" "}
            {Math.max(...rel.map((r) => Math.abs(r.forecast_mean - r.observed_freq))).toFixed(3)}.
          </p>
        </Card>

        {/* by year */}
        <Card className="p-5">
          <SectionTitle sub="champion log loss per test year">Through time</SectionTitle>
          <div className="h-72" aria-hidden>
            <ResponsiveContainer>
              <LineChart data={metrics.by_year} margin={{ top: 8, right: 8, bottom: 4, left: -14 }}>
                <CartesianGrid stroke="#1c2921" />
                <XAxis dataKey="year" stroke="#55685c" fontSize={11} fontFamily="monospace" />
                <YAxis stroke="#55685c" fontSize={11} fontFamily="monospace" domain={["auto", "auto"]} />
                <Tooltip {...chartTheme} />
                <Line type="monotone" dataKey="log_loss" stroke="#a3e635" strokeWidth={2} dot />
                <Line type="monotone" dataKey="accuracy" stroke="#38bdf8" strokeWidth={1.5} dot />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <p className="font-mono text-[11px] text-ink-500">
            <span className="text-home">— log loss</span> ·{" "}
            <span className="text-away">— top-pick accuracy</span>. Table alternative:{" "}
            {metrics.by_year.map((y) => `${y.year}: ${y.log_loss.toFixed(3)}`).join(" · ")}
          </p>
        </Card>
      </div>

      {/* confidence buckets & slices */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="p-5">
          <SectionTitle sub="does confidence mean accuracy?">Confidence buckets</SectionTitle>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-700 font-mono text-[11px] uppercase text-ink-400">
                <th className="py-2 text-left">Top-prob bucket</th>
                <th className="text-right">n</th>
                <th className="text-right">mean conf.</th>
                <th className="text-right">accuracy</th>
              </tr>
            </thead>
            <tbody className="font-mono tabular-nums">
              {metrics.confidence_buckets.map((b) => (
                <tr key={b.bucket} className="border-b border-ink-800/60">
                  <td className="py-1.5">{b.bucket}</td>
                  <td className="text-right">{b.count}</td>
                  <td className="text-right">{fmtPct(b.mean_confidence, 1)}</td>
                  <td className="text-right">{fmtPct(b.top_pick_accuracy, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card className="p-5">
          <SectionTitle sub="test-window slices">Segments</SectionTitle>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ink-700 font-mono text-[11px] uppercase text-ink-400">
                <th className="py-2 text-left">Segment</th>
                <th className="text-right">n</th>
                <th className="text-right">log loss</th>
                <th className="text-right">accuracy</th>
              </tr>
            </thead>
            <tbody className="font-mono tabular-nums">
              {[
                ...metrics.favorites_vs_close.map((s) => ({ name: s.segment, ...s })),
                ...metrics.by_tier.map((s) => ({ name: `tier: ${s.tier}`, ...s })),
                ...metrics.by_confederation.map((s) => ({ name: s.confederation, ...s })),
              ].map((s) => (
                <tr key={s.name} className="border-b border-ink-800/60">
                  <td className="py-1.5">{s.name}</td>
                  <td className="text-right">{s.n}</td>
                  <td className="text-right">{s.log_loss.toFixed(4)}</td>
                  <td className="text-right">{fmtPct(s.accuracy, 1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      </div>

      <Card className="p-5">
        <SectionTitle>Known limitations</SectionTitle>
        <ul className="list-inside list-disc space-y-1 text-sm text-ink-300">
          <li>
            Team-level model: no lineup or injury inputs exist in the open data, so the
            player-aware layer is a labeled scenario tool, not part of the evaluated
            champion.
          </li>
          <li>Draw probabilities are the hardest class — visible in per-class calibration.</li>
          <li>Small-history teams fall back to rating priors (grade C/D forecasts say so).</li>
          <li>
            Shootouts are modeled 50/50 — the open data offers no defensible shootout-skill
            signal.
          </li>
        </ul>
      </Card>
    </div>
  );
}
