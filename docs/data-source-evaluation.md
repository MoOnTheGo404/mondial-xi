# Data source evaluation

Full research notes with citations: [research/providers.md](research/providers.md),
[research/wc2026.md](research/wc2026.md), [research/assets-and-stack.md](research/assets-and-stack.md).
Evaluated 2026-07-06.

## Selected sources

| Source | Role | License / terms | Coverage | Cost | Redistribution |
|---|---|---|---|---|---|
| **martj42/international_results** (GitHub) | Core historical + current results | **CC0-1.0** (verified) | 49,503 senior men's internationals 1872 → 2026-07-05, incl. full WC-2026 to date; goalscorers (47,875), shootouts (680), former names | Free | ✅ Allowed |
| **Self-computed Elo** | Ratings | Our own derivative of CC0 data | All teams/dates | Free | ✅ |
| **flag-icons** (lipis) | Country flags | MIT (verified; incl. gb-eng/sct/wls/nir, xk) | All ISO + GB subdivisions | Free | ✅ |
| **Open-Meteo** | Match-day weather (display/scenario only) | Free non-commercial, **CC-BY 4.0 attribution required**, no key | Forecast + archive (1940→, ~5-day lag) | Free | Attribution |
| **football-data.org** (optional adapter) | Live fixtures/standings enrichment | Free tier w/ email credential; WC included; **attribution mandatory**; data unusable after cancellation; lineups/squads paid (€29/mo) | 12 comps free | Free tier | ⚠️ Display w/ attribution; no bulk redistribution |
| **openfootball/worldcup** | Cross-check of WC fixtures | CC0-1.0 | 1930–2026 | Free | ✅ |
| FiveThirtyEight SPI archive | Optional benchmark only | CC-BY 4.0, discontinued 2023 | to 2023 | Free | Attribution |

## Rejected sources

| Source | Why rejected |
|---|---|
| **API-Football** (api-sports.io) | Free tier has injuries/lineups, but ToS grant **no license to publish** the data — legally unsuitable for a public site. Documented; no adapter shipped. |
| **Sportmonks** | Free plan excludes international football; WC-2026 requires paid plans. |
| **eloratings.net** (scraping) | No published license/terms → treat as all-rights-reserved. We compute our own Elo from CC0 data instead. |
| **TheSportsDB images** (badges/photos) | Trademark and per-image license ambiguity; unnecessary risk. Initials avatars used instead. |
| Wikipedia squad/lineup scraping | CC-BY-SA text but reliability/effort and derived-data ambiguity; out of scope. |

## Product scope matrix

| Capability | No credentials (default) | Free credential (FOOTBALL_DATA_API_KEY) | Paid provider | Unavailable / legally unsuitable |
|---|---|---|---|---|
| Historical results 1872–present | ✅ CC0 dataset | — | — | — |
| WC-2026 real state (group stage + knockouts to data cutoff) | ✅ CC0 dataset | ✅ fresher sync | — | — |
| Upcoming fixtures | ✅ from dataset snapshot (6 known WC fixtures) | ✅ live fixture list w/ retrieval timestamps | — | — |
| Team ratings, form, forecasts, calibration | ✅ fully local | — | — | — |
| Tournament simulation (real WC-2026 state) | ✅ | ✅ | — | — |
| Goalscorer-derived player profiles & attack impact | ✅ CC0 goalscorers | — | — | — |
| Live standings sync | — | ✅ | — | — |
| Confirmed lineups, squads | — | ❌ (paid tier at football-data.org) | ⚠️ €29/mo | — |
| Injury feeds | — | — | ⚠️ providers with publication restrictions | ❌ no legally publishable free source |
| Player photos, federation badges | — | — | — | ❌ (licensing) — initials avatars used |
| Weather (display + scenarios) | ✅ Open-Meteo, attribution | — | — | not a trained feature (no historical backfill at fair-use scale) |

**Consequence for modeling:** injury/lineup historical data has no legally usable
source here → the player-aware layer is trained only on CC0 goalscorer data
(attack-side impact, shrunken), is clearly labeled, and the team-level model
remains the evaluated champion. Availability adjustments exist as scenario
tooling with honest provenance, not as claimed historical accuracy gains.
