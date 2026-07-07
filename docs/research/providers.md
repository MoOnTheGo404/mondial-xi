# Football Data Provider Research

Research for the international football forecasting portfolio project.
All facts verified against live sources on **2026-07-06** unless marked "unverified".
Quotes are verbatim from the cited pages. Licenses can change — re-verify before shipping.

## Comparison table

| Provider | Cost (entry) | License / redistribution | Intl. / World Cup coverage | Players / injuries / lineups | Quota (free) | Best use here |
|---|---|---|---|---|---|---|
| `martj42/international_results` (GitHub) | Free | **CC0-1.0** (public domain) — redistribution allowed | Excellent: all men's full internationals 1872–present, incl. 2026 WC (updated same-day) | Goalscorers only (no injuries/lineups) | n/a (CSV download) | **Primary training dataset** |
| football-data.org | Free tier (email signup) | Proprietary; attribution required; no referencing data after cancellation | WC + Euro in free tier (12 competitions) | Lineups/squads only on paid tiers (from €29/mo) | 10 calls/min | Free WC fixtures/results API |
| TheSportsDB | Free (test key `123`) / $9/mo | Proprietary; attribution required; no resale; app-store publishing needs paid tier | Broad but crowd-sourced; quality varies | Player pages + photos/badges (usable with attribution; trademarked logos "as is") | ~30–100 req/min (sources differ) | Badges/photos for UI |
| API-Football (api-sports.io) | Free 100 req/day | Proprietary; **no publication license granted** — user must clear rights; no resale | 1,100+ leagues incl. WC (season limits on free) | Yes: lineups, injuries, sidelined endpoints (incl. free tier) | 100 req/day, 10 req/min | Injuries/lineups if licensing accepted |
| Sportmonks | Free plan (2 leagues) / €29+/mo | Proprietary (commercial terms) | WC only on paid plans / WC widget product | Yes on paid plans | 3,000 calls/entity/hour (rate), 2 free leagues | Not useful free; paid WC option |
| FiveThirtyEight SPI archive | Free | **CC-BY-4.0** (attribution) — redistribution allowed | Intl. + club SPI ratings & forecasts | No | n/a (CSV) | Historical benchmark ratings (≤2023) |
| openfootball (`openfootball/worldcup`) | Free | **CC0-1.0** | World Cups 1930–2026 incl. qualifiers | Squads in some repos; no injuries | n/a (text/CSV) | Cross-check WC fixtures |
| eloratings.net | Free (website) | **No published license/terms found** — treat as all-rights-reserved; scraping unauthorized | Elo ratings for all national teams | No | n/a | Reference only; compute own Elo from CC0 data instead |

---

## 1. GitHub dataset: `martj42/international_results`

- Repo: https://github.com/martj42/international_results
- License API record: https://api.github.com/repos/martj42/international_results

**License.** Verified via both the repo README and the GitHub API: `CC0-1.0` ("Creative Commons Zero v1.0 Universal", SPDX `CC0-1.0`). Public domain dedication — **redistribution, modification, and commercial use are all allowed, no attribution legally required** (attribution is still good practice).

**Files and row counts** (downloaded raw CSVs from `master`, 2026-07-06; counts exclude header row):

| File | Rows | Contents |
|---|---|---|
| `results.csv` | 49,503 | date, home/away team, scores, tournament, city, country, neutral flag |
| `goalscorers.csv` | 47,875 | per-goal records (scorer, minute, own-goal, penalty) |
| `shootouts.csv` | 680 | penalty shootout winners |
| `former_names.csv` | 36 | historical team-name mappings |

**Date coverage.** First row: `1872-11-30, Scotland, England, 0, 0, Friendly, Glasgow`. Last rows include **2026 FIFA World Cup matches**: 98 rows tagged `FIFA World Cup` with 2026 dates, of which **92 already have final scores** (played through 2026-07-05, e.g. `2026-07-05, Mexico, England, 2, 3`) and 6 are upcoming fixtures. **The full 2026 World Cup group stage is included with results.**

**Update recency.** GitHub API `pushed_at`: `2026-07-06T15:23:44Z` — updated the same day this research was done; the maintainer is keeping pace with the ongoing World Cup.

**Caveats.**
- README (quoted): "The matches are strictly men's full internationals and the data does not include Olympic Games or matches where at least one of the teams was the nation's B-team, U-23 or a league select team."
- Team naming: current names are used for the team columns (an 1882 "Ireland" match is labeled "Northern Ireland"), while `country`/`city` reflect names in use at the time — use `former_names.csv` to reconcile.
- **Upcoming fixtures appear with `NA` scores** — filter `home_score != "NA"` before training.
- README's stated count ("49,459 results") lags the actual file slightly; README notes results may not always be updated immediately.
- `goalscorers.csv` does not cover every match in `results.csv` (47,875 goal rows vs 49,503 matches); scorer coverage is incomplete for older/minor fixtures (extent unverified).
- No player metadata, injuries, or lineups.

## 2. football-data.org

- Pricing: https://www.football-data.org/pricing
- Coverage: https://www.football-data.org/coverage
- Terms (T&C, linked from About): https://www.football-data.org/about
- Docs: https://docs.football-data.org/general/v4/index.html

**Free tier.** Free credential obtainable with only "a valid e-mail address" (T&C Art. 1.2); "a free and several paid subscription tiers" (Art. 4.1). Free tier: **12 competitions**, "Scores delayed", "Fixtures", "Schedules delayed", "League Tables", **10 calls/minute**.

**Is the World Cup included?** Yes. The coverage page lists the free tier as including: World Cup, European Championship, Champions League, Premier League, Championship, La Liga, Serie A (Italy), Bundesliga, Ligue 1, Eredivisie, Primeira Liga, Serie A (Brazil).

**Lineups/squads.** Not in the free tier. "Line-ups & Subs" and "Squads" appear starting at the €29/mo tiers; Standard €49/mo (30 competitions, 60 calls/min), Advanced €99/mo, Pro €199/mo (100 competitions, 120 calls/min).

**Key terms (quoted from T&C).**
- Attribution (Art. 7.1): "include the following attribution to Football-Data in your app or website: 'Football data provided by the Football-Data.org API'".
- Post-cancellation redistribution ban (Art. 9.1): "After cancellation of the subscription to the Service, the Customer is not permitted to reference the football data (incl. match fixtures, results, league tables, player/squad data, top scorers) obtained through the Football-Data API on their own site or service."
- "Developer credentials may not be stored in code repositories of open source projects." — do not commit the API token to this repo.
- No explicit commercial/non-commercial distinction found in the T&C.
- General redistribution of raw data as a dataset: not expressly permitted anywhere — assume **not allowed**.

## 3. TheSportsDB

- Site: https://www.thesportsdb.com/
- Terms: https://www.thesportsdb.com/docs_terms_of_use.php
- Pricing: https://www.thesportsdb.com/pricing
- Docs: https://www.thesportsdb.com/documentation

**Tiers.** Free $0/mo: shared test API key, "30 requests per minute" per the pricing page ("Most queries limited"; a forum/docs source says 100 req/min for free — figures conflict, exact free rate limit **unverified**). Premium "Single Developer" $9/mo: dedicated key, V2 API, 2-min livescores, "100 requests per minute". "Small Business" $20/mo: private key, 120 req/min, no data limits.

**API key model.** V1 free/test key is `123` appended to the URL (`https://www.thesportsdb.com/api/v1/json/123/...`); premium users get a dedicated key from their profile. V2 API (`/api/v2/json`) is premium.

**Data & image licensing (quoted from Terms of Service).**
- "You may use our API to lookup data and artwork for your development projects."
- "You can use our custom artwork in your projects but must mention us as the source of the data."
- "Most of our artwork is custom and is created by our users, you must not pass it off as your own and should link back to our website where appropriate."
- "Any trademarked sports logos must be used 'As is' and should not be modifed in any way."
- "You can check the 'strCreativeCommons' tag on player artwork to make sure its CC licensed."
- "You cannot resell our API in any way without specific permission."
- "You cannot publish apps to an appstore unless you are a paid subscriber."
- "We comply with any DMCA requests within 24hrs for any copywrite claims."

**Can images be displayed legally?** Custom fan-made artwork: yes, with attribution/link-back; check `strCreativeCommons` per image. **Caution:** team badges/club crests are trademarks — TheSportsDB permits "as is" display, but trademark rights belong to clubs/FIFA; for a non-commercial portfolio project displaying unmodified badges with attribution, risk is low but not zero (nominative fair use — not legal advice, and TheSportsDB itself cannot license third-party trademarks). Player photos flagged CC are safest.

## 4. API-Football (api-sports.io)

- Pricing: https://www.api-football.com/pricing (Cloudflare-gated; details below cross-verified via search results and https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide)
- Terms: https://www.api-football.com/terms and https://api-sports.io/terms
- Docs: https://www.api-football.com/documentation-v3

**Free tier.** 100 requests/day (resets 00:00 UTC, unused requests lost), rate limit 10 requests/minute. Free plan is auto-activated on dashboard registration and includes **all endpoints**: Fixtures, Lineups, Injuries, Sidelined, Players, Transfers, Standings, Odds, Predictions, etc. **Limitation: free plans are restricted in available seasons** (recent seasons only; exact season window unverified — historically ~3 seasons behind current). Paid: Pro $19/mo for 7,500 req/day, up to larger plans.

**International coverage.** 1,100+ leagues and cups including FIFA World Cup, WC qualifiers, continental championships and friendlies (coverage varies per league/season via per-league coverage flags: "events, lineups, fixture statistics, player statistics, standings, players, top scorers, ... injuries, predictions, odds").

**Injuries/lineups.** Yes — dedicated `injuries`, `sidelined`, and `fixtures/lineups` endpoints, available on the free tier (subject to season limits and per-league coverage flags).

**Terms re caching/storage/redistribution (from terms of service, via indexed excerpts — direct page is Cloudflare-blocked; treat wording as near-verbatim, re-verify from a browser).**
- Resale prohibited: data "obtained from partners" and it is "prohibited to resell this data to third parties or to use the services provided for illegal purposes."
- **No publication license granted**: the terms state that no license is provided for the use and publication of the data on the user's applications/websites/products, and "any license or permission to publish the data must be requested by the user from the competent authorities."
- Third-party rights: some data "may be subject to intellectual property rights or commercial restrictions imposed by third parties, including leagues, federations, or event organisers", and it is "the responsibility of the user to verify and obtain any necessary authorizations."
- Explicit caching/local-storage clause: **unverified** (not found in accessible excerpts).

This is the weakest legal footing of the APIs surveyed: convenient technically, but they push all publication-rights risk onto you.

## 5. Sportmonks

- Pricing: https://www.sportmonks.com/football-api/plans-pricing/
- Free plan: https://www.sportmonks.com/football-api/free-plan/
- Rate limits: https://docs.sportmonks.com/v3/api/rate-limit

**Free plan.** A "forever-free" plan exists (no credit card) but includes **only two leagues: Danish Superliga (id 271) and Scottish Premiership (id 501)** — fixtures, livescores, events, standings, stats, topscorers, venues for those leagues only. **No international/World Cup data on the free plan.** Rate limit: 3,000 API calls per entity per hour (API 3.0, all plans). A one-time 14-day trial unlocks the full 2,300+ leagues including the World Cup.

**Paid plans (verified 2026-07-06).** Starter €29/mo ("Pick any 5 leagues worldwide"), Growth €99/mo (30 leagues), Pro €249/mo (120 leagues), Enterprise custom (all 2,300+ leagues); extra leagues "Starting at €4/month". Yearly billing discounts apply (e.g. Starter €24/mo).

**Cost of World Cup data.** The World Cup is available via the league-selection model on paid plans (cheapest realistic path: Starter €29/mo with the World Cup as one of your 5 picks — whether the WC is selectable at Starter level is **unverified**). Sportmonks also sells a dedicated **World Cup 2026 widget product at €78–€169/month**. Lineups/injury-style data (sidelined players) available on paid plans per coverage matrix (per-plan detail unverified).

**Terms.** Standard commercial API terms; redistribution/resale of raw data not permitted (full T&C text not reviewed — unverified detail).

## 6. Other open / legally usable sources

### FiveThirtyEight SPI archive (discontinued)
- Repo: https://github.com/fivethirtyeight/data (contains `soccer-spi/` — existence verified via GitHub API, HTTP 200)
- License (quoted README): "Unless otherwise noted, our data sets are available under the Creative Commons Attribution 4.0 International License, and the code is available under the MIT License." GitHub API confirms `CC-BY-4.0`.
- Status: **discontinued** — sports prediction updates ceased June 13, 2023 (FiveThirtyEight's sports operation shut down). Repo is *not* archived (last push 2025-02-25), but SPI data ends mid-2023.
- Contents: `spi_matches.csv` etc. — historical SPI ratings and match forecasts for club and international football, incl. past World Cups. Redistribution allowed **with attribution** to FiveThirtyEight.
- Use here: benchmark/feature for historical seasons only; useless for 2026 WC itself.

### openfootball
- Org: https://github.com/openfootball ; World Cup repo: https://github.com/openfootball/worldcup
- License: **CC0-1.0** (verified via GitHub API on `openfootball/worldcup`); the project brands itself "free open public domain football data".
- Coverage: World Cups 1930 through **2026 (Canada/USA/Mexico)** including qualifiers; last push `2026-07-07` — actively maintained through the current tournament. Plain-text fixture format plus converters; some repos include squads.
- Caveats: community-maintained text files; parse effort required; data quality/completeness varies by tournament; no injuries.

### eloratings.net (World Football Elo Ratings)
- Site: https://www.eloratings.net/ ; about: http://www.eloratings.net/about
- Terms/license: **none found** — the site publishes no terms of use, copyright license, or scraping policy on its pages (checked 2026-07-06; site is a JS-rendered app). Default position: content is all-rights-reserved; **scraping/republishing is not authorized** and its database could enjoy protection in some jurisdictions.
- Recommendation: do not scrape/redistribute. Since `martj42/international_results` is CC0 and complete back to 1872, **compute your own Elo ratings from it** — reproducible, license-clean, and a better portfolio artifact anyway. (Kaggle mirrors of eloratings data exist but inherit the same unlicensed status.)

---

## Recommended stack for this project

1. **Core results/training data:** `martj42/international_results` (CC0, includes 2026 WC group stage + knockouts to date, updated daily). Vendor the CSVs freely.
2. **Ratings feature:** self-computed Elo from the CC0 data; optionally FiveThirtyEight SPI (CC-BY-4.0, ≤2023) as a historical benchmark with attribution.
3. **Live fixtures/results API (if needed):** football-data.org free tier (WC included, 10 calls/min, attribution string required, don't commit the token, don't redistribute raw API data).
4. **Cross-check WC schedule:** openfootball/worldcup (CC0).
5. **Injuries/lineups:** only API-Football offers them free (100 req/day), but its terms grant **no publication license** — display in a public portfolio is at your own legal risk. For badges/player photos, TheSportsDB with attribution (prefer CC-flagged artwork) is the pragmatic option.
