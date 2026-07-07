// Typed API client. In the browser we hit the Next.js rewrite (/api/v1/...);
// on the server (RSC) we hit the API directly.

const base = () =>
  typeof window === "undefined"
    ? (process.env.API_INTERNAL_URL ?? "http://localhost:8000")
    : "";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${base()}/api/v1${path}`, {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      msg = body?.error?.message ?? msg;
    } catch {
      /* keep default */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${base()}/api/v1${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const b = await res.json();
      msg = b?.error?.message ?? msg;
    } catch {
      /* keep default */
    }
    throw new ApiError(res.status, msg);
  }
  return res.json() as Promise<T>;
}

export const fmtPct = (p: number, digits = 0): string =>
  `${(100 * p).toFixed(digits)}%`;

export const fmtPP = (pp: number, digits = 1): string =>
  `${pp >= 0 ? "+" : ""}${pp.toFixed(digits)} pp`;

export const fmtDate = (iso: string): string =>
  new Date(iso + (iso.length === 10 ? "T12:00:00Z" : "")).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
