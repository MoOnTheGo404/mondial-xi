import type { NextRequest } from "next/server";

// Runtime proxy: the browser calls same-origin /api/v1/* and this handler
// forwards to the FastAPI backend. Unlike next.config rewrites (whose
// destination can be frozen at build time), a route handler reads
// API_INTERNAL_URL at REQUEST time, so it works with hosts (e.g. Render) that
// inject the backend URL as a runtime env var. Server-to-server, so no CORS.
export const dynamic = "force-dynamic";

function apiBase(): string {
  const raw = process.env.API_INTERNAL_URL ?? "http://localhost:8000";
  return /^https?:\/\//.test(raw) ? raw : `https://${raw}`;
}

async function proxy(req: NextRequest, path: string[]): Promise<Response> {
  const target = `${apiBase()}/api/v1/${path.join("/")}${req.nextUrl.search}`;
  const method = req.method;
  const init: RequestInit = {
    method,
    headers: {
      "content-type": req.headers.get("content-type") ?? "application/json",
      accept: "application/json",
    },
    body: method === "GET" || method === "HEAD" ? undefined : await req.text(),
    cache: "no-store",
  };
  try {
    const res = await fetch(target, init);
    const body = await res.text();
    return new Response(body, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return new Response(
      JSON.stringify({ error: { code: "upstream_unreachable", message: "API is unreachable" } }),
      { status: 502, headers: { "content-type": "application/json" } },
    );
  }
}

type Ctx = { params: Promise<{ path: string[] }> };

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, (await ctx.params).path);
}
