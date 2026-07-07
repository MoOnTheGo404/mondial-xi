# Security

## Input handling
- All API inputs validated by Pydantic (types, ranges, max lengths, team-id
  slug pattern); simulation size capped server-side
  (`KICKOFF_MAX_SIMULATIONS`); scenario lists capped at 15 players.
- Consistent error envelope; unhandled exceptions return a sanitized 500 —
  no stack traces or internals leak.
- CORS restricted to the configured web origin(s), methods GET/POST only.

## Secrets
- None required. Optional key read from env only; `.gitignore` blocks
  `.env*`, keys, and credential files; `.env.example` documents everything.
- Git history contains no secrets (repo built clean from init).

## Data & assets
- CC0 core data; raw downloads checksummed (SHA-256) into committed
  manifests. Provider data is displayed within each provider's terms and
  never re-served in bulk. No unlicensed images.

## Model-artifact trust
`prediction_bundle.joblib` is deserialized with joblib/pickle — arbitrary
code execution by design of the format. **Trust boundary:** the API loads it
only from the repo-local `ml/artifacts/` path, produced by our own
`make train` (or CI). Never load artifacts from user uploads or remote URLs.
Docker images bake the artifact at build time from the same source.

## Injection surfaces
- No SQL string building (SQLAlchemy ORM only); no shelling out from
  request paths; no user-controlled file paths (fixture/team IDs are matched
  against loaded frames, not filesystem).
- CSV/spreadsheet export of simulation results is client-side JSON→CSV; if
  extended server-side, sanitize leading `= + - @` (formula injection) —
  helper documented here as the requirement for any future export endpoint.
  The current UI export (simulator aggregate download) escapes these.

## Dependencies
- Python pinned via `uv.lock`; JS via `pnpm-lock.yaml`; CI installs frozen.
- Playwright browsers only in dev/CI.

## Recommendations for public deployment
Reverse-proxy rate limits (docs/deployment.md), HTTPS-only, and platform
secret stores for the optional provider key.
