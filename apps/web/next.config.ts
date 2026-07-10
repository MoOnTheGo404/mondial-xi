import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@kickoff/shared", "@kickoff/ui"],
  // API calls are proxied by the runtime route handler at app/api/v1/[...path]
  // (reads API_INTERNAL_URL at request time — works with runtime-injected env).
};

export default nextConfig;
