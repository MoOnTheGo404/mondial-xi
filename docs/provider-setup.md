# Provider setup

The app is fully functional with **zero credentials**. Providers add
capabilities; each reports its own availability, license constraints and last
sync at `/api/v1/providers`, and the UI surfaces unavailable capabilities
honestly (no fake data, no dead controls).

## Built-in (no setup)

| Provider | Capabilities | Notes |
|---|---|---|
| `open-data-core` | historical matches, dataset-snapshot fixtures, goalscorers, shootouts, registry | CC0; retrieval timestamp in manifest |
| `kickoff-atlas-models` | Elo, forecasts, score matrices, simulation, player attack impact | computed in-repo |
| `open-meteo` | matchday weather panels | keyless; CC BY 4.0 attribution shown; disable with `KICKOFF_WEATHER_ENABLED=false` |

## Optional: football-data.org (free credential)

1. Register (email only): https://www.football-data.org/client/register
2. `FOOTBALL_DATA_API_KEY=...` in `.env`.
3. Restart the API — `/api/v1/providers` flips the adapter to available.

Adds: live World Cup fixture list + standings sync. The adapter throttles to
the free tier's 10 req/min, retries 429s with the advertised reset, caches
for 10 min, and displays the required attribution. **Their terms prohibit
bulk redistribution and use after cancellation** — data is displayed, never
re-served in bulk. Lineups/squads are a paid tier we do not claim.

## Deliberately unsupported

- **API-Football free tier** — includes injuries/lineups but its terms grant
  no publication rights → legally unsuitable for a public site.
- **eloratings.net scraping** — no published license.
- **TheSportsDB imagery** — trademark/per-image licensing ambiguity.

Full evaluation: docs/data-source-evaluation.md.
