# Assets & Stack Licensing / Version Research

Researched: 2026-07-06. All versions verified against the npm registry (`registry.npmjs.org`) and PyPI JSON API (`pypi.org/pypi/<pkg>/json`) on this date; licensing verified against official project pages. No claims below are from memory alone.

---

## 1. `flag-icons` (lipis/flag-icons)

| Item | Finding |
|---|---|
| License | **MIT** — [LICENSE](https://github.com/lipis/flag-icons/blob/main/LICENSE), confirmed in npm registry metadata |
| Latest version | **7.5.0**, published 2025-05-29 (npm registry; note: no release in ~13 months as of July 2026) |
| npm | <https://www.npmjs.com/package/flag-icons> |
| Repo | <https://github.com/lipis/flag-icons> |

**GB subdivision flags: YES.** Verified directly against the repo — all four return HTTP 200 at
`https://raw.githubusercontent.com/lipis/flag-icons/main/flags/4x3/{code}.svg`:

- `gb-eng` (England), `gb-sct` (Scotland), `gb-wls` (Wales), `gb-nir` (Northern Ireland)

**Addressing flags** (two ways):

1. **CSS classes**: import `flag-icons/css/flag-icons.min.css`, then `<span class="fi fi-gb-eng"></span>` (base class `fi` + `fi-{code}`; add `fis` for 1:1 squared). Codes are ISO 3166-1 alpha-2 plus subdivision codes like `gb-eng`.
2. **Direct SVG paths**: `flag-icons/flags/4x3/gb-eng.svg` and `flag-icons/flags/1x1/gb-eng.svg` — usable as static assets or imported into Next.js `Image`/inline SVG without the CSS bundle.

**Attribution**: None required. MIT only requires retaining the copyright/license notice in copies of the software (i.e., keep the LICENSE text in your dependency tree — automatic with npm). No UI credit needed. Neither the README nor the npm page states any extra attribution requirement.

## 2. Alternative: `circle-flags` (HatScripts)

| Item | Finding |
|---|---|
| License | **MIT** — [LICENSE.md](https://github.com/HatScripts/circle-flags/blob/gh-pages/LICENSE.md); GitHub API reports SPDX `MIT` |
| Repo | <https://github.com/HatScripts/circle-flags> (last push 2026-02-03 — actively maintained) |
| npm | [`circle-flags`](https://www.npmjs.com/package/circle-flags) **2.8.3**, published 2026-04-19, MIT |
| Coverage | 400+ minimal **circular** SVG country, state, and language flags — [gallery](https://hatscripts.github.io/circle-flags/) |

**GB subdivisions: YES** — `gb-eng`, `gb-sct`, `gb-wls`, `gb-nir` all verified present (HTTP 200) at `https://raw.githubusercontent.com/HatScripts/circle-flags/gh-pages/flags/{code}.svg`. Flags are plain SVG files addressed by ISO code (`flags/{code}.svg`); no CSS class system. React wrapper `react-circle-flags` exists. Notably, Open-Meteo's own geocoding docs credit circle-flags for their country flags.

**Verdict**: both are MIT with full GB-subdivision coverage; choose on aesthetics (rectangular `flag-icons` vs circular `circle-flags`). `circle-flags` is the more recently maintained of the two.

## 3. Open-Meteo API

Sources: [Terms](https://open-meteo.com/en/terms) · [Licence](https://open-meteo.com/en/licence) · [Forecast docs](https://open-meteo.com/en/docs) · [Historical docs](https://open-meteo.com/en/docs/historical-weather-api) · [Geocoding docs](https://open-meteo.com/en/docs/geocoding-api)

- **Free tier is non-commercial only.** Terms state: "You may only use the free API services for non-commercial purposes." Commercial use requires a paid subscription (API-key-based, e.g. `customer-api.open-meteo.com`).
- **Attribution required: yes, CC-BY 4.0.** Weather data is licensed under Attribution 4.0 International. Recommended credit, shown wherever the data appears:
  ```html
  <a href="https://open-meteo.com/">Weather data by Open-Meteo.com</a>
  ```
  Open-Meteo's server source code is separately AGPLv3 (irrelevant unless self-hosting/modifying their server).
- **API key: not required** for the free/non-commercial tier. The `apikey` parameter is "only required for commercial use to access reserved API resources."
- **Endpoints**:
  - Forecast: `https://api.open-meteo.com/v1/forecast`
  - Historical archive: `https://archive-api.open-meteo.com/v1/archive` (data back to **1940**; ERA5 has ~5-day delay, ECMWF IFS no delay)
  - Geocoding: `https://geocoding-api.open-meteo.com/v1/search` (data based on GeoNames)
- **Rate limits (free tier)**: **600 calls/min, 5,000/hour, 10,000/day.** Open-Meteo reserves the right to block abusive IPs without notice.

## 4. Current stable versions (verified 2026-07-06)

### JavaScript (npm registry, `dist-tags.latest`)

| Package | Version | Published | License | Source |
|---|---|---|---|---|
| Next.js | **16.2** (16.2.10) | 2026-07-01 | MIT | <https://www.npmjs.com/package/next> |
| React | **19.2** (19.2.7) | 2026-06-01 | MIT | <https://www.npmjs.com/package/react> |
| Tailwind CSS | **4.3** (4.3.2) | 2026-06-29 | MIT | <https://www.npmjs.com/package/tailwindcss> |
| TanStack Query | **5.101** (@tanstack/react-query 5.101.2) | 2026-06-27 | MIT | <https://www.npmjs.com/package/@tanstack/react-query> |
| Playwright | **1.61** (1.61.1) | 2026-06-23 | Apache-2.0 | <https://www.npmjs.com/package/playwright> |
| Vitest | **4.1** (4.1.10) | 2026-07-06 | MIT | <https://www.npmjs.com/package/vitest> |
| Recharts | **3.9** (3.9.2) | 2026-07-04 | MIT | <https://www.npmjs.com/package/recharts> |

Note: Next.js is on the **16.x** line now, not 15.x.

### Python (PyPI JSON API, `info.version`)

| Package | Version | License | Source |
|---|---|---|---|
| FastAPI | **0.139** (0.139.0) | MIT | <https://pypi.org/project/fastapi/> |
| Pydantic | **2.13** (2.13.4) | MIT | <https://pypi.org/project/pydantic/> |
| SQLAlchemy | **2.0** (2.0.51) | MIT | <https://pypi.org/project/SQLAlchemy/> |
| Polars | **1.42** (1.42.1) | MIT | <https://pypi.org/project/polars/> |
| scikit-learn | **1.9** (1.9.0) | BSD-3-Clause | <https://pypi.org/project/scikit-learn/> |
| XGBoost | **3.3** (3.3.0) | Apache-2.0 | <https://pypi.org/project/xgboost/> |
| LightGBM | **4.6** (4.6.0) | MIT | <https://pypi.org/project/lightgbm/> |
| Playwright (Python) | **1.61** (1.61.0) | Apache-2.0 | <https://pypi.org/project/playwright/> |

## 5. Charting: Recharts vs visx vs d3

- **Recharts** — [repo](https://github.com/recharts/recharts), **MIT**, actively maintained: latest release **v3.9.2 on 2026-07-04** (two days before this research), verified via the GitHub Releases API. The 3.x line rewrote internal state management to fix long-standing bugs. Multi-million weekly npm downloads; declarative React components (`<LineChart>`, `<BarChart>`), SSR-friendly for Next.js, no D3 knowledge needed. The default choice for standard analytics dashboards (line/bar/area/pie).
- **visx** (Airbnb) — MIT, low-level D3-based primitives for React. Maximum control, markedly steeper learning curve; best when you need fully custom visualizations beyond a standard library. ~10x smaller download base than Recharts.
- **d3** — ISC-licensed, imperative, framework-agnostic. Fights React's DOM ownership unless carefully scoped (e.g. d3 for math/scales, React for rendering). Overkill for a standard analytics UI.

**Recommendation** for this app: **Recharts 3.x** — MIT, actively released, React/Next-native, covers forecast-probability and analytics chart needs; drop to visx only if a bespoke visualization proves impossible in Recharts.

Comparison sources: [PkgPulse 2026 React charting guide](https://www.pkgpulse.com/guides/recharts-vs-chartjs-vs-nivo-vs-visx-react-charting-2026) · [Querio: top React chart libraries 2026](https://querio.ai/articles/top-react-chart-libraries-data-visualization) · [Recharts 3.0 migration guide](https://github.com/recharts/recharts/wiki/3.0-migration-guide)
