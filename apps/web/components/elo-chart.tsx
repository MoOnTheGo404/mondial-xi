"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@kickoff/shared";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface EloPoint {
  date: string;
  elo: number;
}

export function EloChart({ teamId, teamName }: { teamId: string; teamName: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ["elo-history", teamId],
    queryFn: () =>
      apiGet<{ points: EloPoint[] }>(`/teams/${teamId}/elo-history?since=1960-01-01`),
  });
  if (isLoading) return <div className="h-56 animate-pulse rounded bg-ink-900" />;
  if (!data || data.points.length < 2)
    return <p className="text-sm text-ink-400">Not enough rating history to chart.</p>;

  const pts = data.points.map((p) => ({ ...p, year: p.date.slice(0, 4) }));
  const first = pts[0];
  const last = pts[pts.length - 1];

  return (
    <figure>
      <div className="h-56 w-full" aria-hidden>
        <ResponsiveContainer>
          <LineChart data={pts} margin={{ top: 6, right: 8, bottom: 0, left: -18 }}>
            <XAxis
              dataKey="year"
              stroke="#52625f"
              fontSize={11}
              tickLine={false}
              minTickGap={40}
              fontFamily="monospace"
            />
            <YAxis
              stroke="#52625f"
              fontSize={11}
              tickLine={false}
              domain={["auto", "auto"]}
              fontFamily="monospace"
            />
            <Tooltip
              contentStyle={{
                background: "#0a1012",
                border: "1px solid #202b2e",
                borderRadius: 6,
                fontFamily: "monospace",
                fontSize: 12,
              }}
              labelFormatter={(_, payload) =>
                payload?.[0]?.payload?.date ?? ""
              }
              formatter={(v) => [typeof v === "number" ? v.toFixed(0) : String(v ?? ""), "Elo"]}
            />
            <Line
              type="monotone"
              dataKey="elo"
              stroke="#34e57e"
              strokeWidth={1.75}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="sr-only">
        Elo rating history for {teamName}: from {first.elo.toFixed(0)} on {first.date} to{" "}
        {last.elo.toFixed(0)} on {last.date}, across {pts.length} sampled points.
      </figcaption>
    </figure>
  );
}
