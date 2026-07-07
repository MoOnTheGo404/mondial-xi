import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@kickoff/shared", "@kickoff/ui"],
  async rewrites() {
    // dev convenience: proxy API calls to the FastAPI server
    const api = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
    return [{ source: "/api/v1/:path*", destination: `${api}/api/v1/:path*` }];
  },
};

export default nextConfig;
