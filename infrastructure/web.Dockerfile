# Mondial XI — web image (Next.js).
# Build context = repository root:
#   docker build -f infrastructure/web.Dockerfile -t mondial-xi-web .
FROM node:22-slim AS builder
RUN corepack enable && corepack prepare pnpm@11.10.0 --activate
WORKDIR /app
COPY package.json pnpm-workspace.yaml pnpm-lock.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/shared/package.json packages/shared/package.json
COPY packages/ui/package.json packages/ui/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web apps/web
COPY packages packages
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @kickoff/web build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0
# Next.js standalone output: a self-contained server with only the traced
# dependencies. No pnpm and no install at container start, so the runtime
# footprint is tiny — the old `pnpm exec next start` re-fetched platform
# binaries on boot and OOM'd Render's 512 MB free instance.
COPY --from=builder /app/apps/web/.next/standalone ./
COPY --from=builder /app/apps/web/.next/static ./apps/web/.next/static
EXPOSE 3000
# The standalone server proxies /api/v1/* to API_INTERNAL_URL (runtime env) and
# binds $HOSTNAME:$PORT (Render injects $PORT; HOSTNAME=0.0.0.0 so it's routable).
CMD ["sh", "-c", "PORT=${PORT:-3000} node apps/web/server.js"]
