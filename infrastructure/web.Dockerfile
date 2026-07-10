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
RUN corepack enable && corepack prepare pnpm@11.10.0 --activate
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=builder /app ./
EXPOSE 3000
# The Next server proxies /api/v1/* to API_INTERNAL_URL (set at runtime).
# Render injects $PORT; default to 3000 locally.
CMD ["sh", "-c", "pnpm --filter @kickoff/web exec next start -p ${PORT:-3000}"]
