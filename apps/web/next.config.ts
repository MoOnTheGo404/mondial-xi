import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  // Self-contained server bundle — runs with `node server.js`, no pnpm/install
  // at container start. Keeps the runtime tiny so it fits a 512 MB instance
  // (the pnpm-at-runtime CMD used to OOM on Render's free tier).
  output: "standalone",
  // Trace from the monorepo root so the pnpm workspace deps (@kickoff/shared,
  // @kickoff/ui) get bundled into the standalone output.
  outputFileTracingRoot: path.join(__dirname, "../.."),
  transpilePackages: ["@kickoff/shared", "@kickoff/ui"],
  // API calls are proxied by the runtime route handler at app/api/v1/[...path]
  // (reads API_INTERNAL_URL at request time — works with runtime-injected env).
};

export default nextConfig;
