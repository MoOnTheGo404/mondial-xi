import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@kickoff/shared", "@kickoff/ui"],
  async rewrites() {
    // Proxy API calls to the FastAPI server. In production the browser only
    // ever talks to this Next server (same origin); the proxy reaches the API
    // server-side, so no CORS is involved. API_INTERNAL_URL may be a bare host
    // (e.g. Render's fromService) — normalize to an absolute https URL.
    const raw = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
    const api = /^https?:\/\//.test(raw) ? raw : `https://${raw}`;
    return [{ source: "/api/v1/:path*", destination: `${api}/api/v1/:path*` }];
  },
};

export default nextConfig;
