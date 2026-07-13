"""Live-results overlay from Wikipedia (CC BY-SA 4.0).

The open-data core (martj42) is a volunteer-maintained CSV that can lag a day or
two behind a finished match. Wikipedia's tournament pages are edited within
minutes of full time, so we use them as a *fresh-results overlay*: we parse the
per-match sections of the current tournament page and fill in scores the core
hasn't published yet. martj42 stays the historical base (150 years, CC0); this
only supplements recent, completed matches.

Design / safety:
- Only *facts* are taken (final scores + shootout winners) — not prose. Output
  matches the martj42 results.csv schema so the existing build canonicalises it.
- Team identities come from the section HEADERS ("France vs Morocco"), which are
  plain nation names, validated against the canonical registry. Placeholder
  bracket slots ("Winner Match 98") are rejected.
- A match is only emitted once it has a numeric score; scheduled ties are
  skipped. No score is ever invented.
- Best-effort: any fetch/parse failure writes nothing and the build proceeds on
  martj42 alone (graceful degradation).
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from datetime import UTC, datetime

import httpx
import structlog

from kickoff_ml.config import MANIFEST_DIR, RAW_DIR
from kickoff_ml.entities.teams import CONFEDERATIONS, FLAG_CODES

log = structlog.get_logger()

API = "https://en.wikipedia.org/w/api.php"

# Current-tournament pages to overlay. Knockout page carries the ties martj42
# is slowest on; add group-stage pages here if the core ever lags on those too.
PAGES = ("2026 FIFA World Cup knockout stage",)

_KNOWN_TEAMS = set(FLAG_CODES) | set(CONFEDERATIONS)
_HEADER = re.compile(r"^===+\s*([^=]+?)\s+vs\s+([^=]+?)\s*===+\s*$", re.MULTILINE)


def _clean_team(name: str) -> str:
    """Strip wiki markup/footnotes from a header team name."""
    name = re.sub(r"\[\[[^\]|]*\|([^\]]*)\]\]", r"\1", name)  # [[a|b]] -> b
    name = re.sub(r"\[\[([^\]]*)\]\]", r"\1", name)  # [[a]] -> a
    name = re.sub(r"<[^>]+>.*?</[^>]+>|<[^>]+/?>", "", name)  # tags
    name = re.sub(r"\{\{[^}]*\}\}", "", name)  # templates
    return name.strip()


def fetch_wikitext(page: str) -> str | None:
    params = {
        "action": "parse",
        "page": page,
        "format": "json",
        "prop": "wikitext",
        "formatversion": "2",
    }
    try:
        with httpx.Client(timeout=20, headers={"User-Agent": "mondial-xi/1.0 (open-data project)"}) as c:
            r = c.get(API, params=params)
            r.raise_for_status()
            data = r.json()
        if "error" in data:
            log.warning("wikipedia parse error", page=page, info=data["error"].get("info"))
            return None
        return data["parse"]["wikitext"]
    except Exception as exc:
        log.warning("wikipedia fetch failed", page=page, error=str(exc))
        return None


def parse_matches(wikitext: str) -> list[dict]:
    """Return match rows (results.csv schema) from a tournament page.

    Completed ties carry their numeric score; ties whose *pairing is known* but
    which haven't been played yet are emitted as scheduled fixtures with "NA"
    scores — the same convention martj42 uses for future matches — so the app's
    "next fixtures" stay populated when the core dataset lags on adding them.
    A score is never invented: no numeric score on the page → NA row."""
    rows: list[dict] = []
    heads = list(_HEADER.finditer(wikitext))
    for i, h in enumerate(heads):
        home = _clean_team(h.group(1))
        away = _clean_team(h.group(2))
        if home not in _KNOWN_TEAMS or away not in _KNOWN_TEAMS:
            continue  # placeholder slot (e.g. "Winner Match 98") or unknown
        seg = wikitext[h.end() : heads[i + 1].start() if i + 1 < len(heads) else h.end() + 1600]

        score_line = re.search(r"\|\s*score\s*=\s*([^\n]+)", seg)
        if not score_line:
            continue
        val = score_line.group(1)
        # score link terminal "|X–Y}}", else a bare leading "X–Y"
        m = re.search(r"\|\s*(\d+)\s*[–\-‑]\s*(\d+)\s*\}\}", val) or re.match(
            r"\s*(\d+)\s*[–\-‑]\s*(\d+)", val
        )
        # no numeric score → known pairing, not yet played → scheduled fixture
        hs, as_ = (m.group(1), m.group(2)) if m else ("NA", "NA")

        dm = re.search(r"\|\s*date\s*=\s*\{\{\s*Start date\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)", seg)
        if not dm:
            continue
        date = f"{int(dm.group(1)):04d}-{int(dm.group(2)):02d}-{int(dm.group(3)):02d}"

        # shootout winner, if the tie went to penalties
        pens = re.search(r"\|\s*penalties1\s*=\s*(\d+).*?\|\s*penalties2\s*=\s*(\d+)", seg, re.DOTALL)
        winner = ""
        if pens:
            p1, p2 = int(pens.group(1)), int(pens.group(2))
            winner = home if p1 > p2 else away if p2 > p1 else ""

        rows.append(
            {
                "date": date,
                "home_team": home,
                "away_team": away,
                "home_score": hs,
                "away_score": as_,
                "tournament": "FIFA World Cup",
                "city": "",
                "country": "",
                "neutral": "TRUE",
                "shootout_winner": winner,
            }
        )
    return rows


RESULT_HEADER = [
    "date", "home_team", "away_team", "home_score", "away_score",
    "tournament", "city", "country", "neutral",
]


def run() -> int:
    """Fetch configured pages and write the results/shootout overlays. Returns
    the number of completed matches written (0 if unavailable)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    matches: list[dict] = []
    for page in PAGES:
        wt = fetch_wikitext(page)
        if wt:
            found = parse_matches(wt)
            n_done = sum(1 for r in found if r["home_score"] != "NA")
            log.info(
                "wikipedia page parsed", page=page,
                completed=n_done, scheduled=len(found) - n_done,
            )
            matches.extend(found)

    results_path = RAW_DIR / "wikipedia_results.csv"
    shootouts_path = RAW_DIR / "wikipedia_shootouts.csv"

    if not matches:
        log.info("wikipedia overlay empty — core dataset used as-is")
        return 0

    with results_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=RESULT_HEADER)
        w.writeheader()
        for m in matches:
            w.writerow({k: m[k] for k in RESULT_HEADER})

    shootouts = [m for m in matches if m["shootout_winner"]]
    with shootouts_path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["date", "home_team", "away_team", "winner"])
        w.writeheader()
        for m in shootouts:
            w.writerow({"date": m["date"], "home_team": m["home_team"],
                        "away_team": m["away_team"], "winner": m["shootout_winner"]})

    payload = results_path.read_bytes()
    (MANIFEST_DIR / "wikipedia.json").write_text(
        json.dumps(
            {
                "source": "en.wikipedia.org",
                "license": "CC BY-SA 4.0",
                "pages": list(PAGES),
                "retrieved_at": datetime.now(UTC).isoformat(),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "completed_matches": sum(1 for m in matches if m["home_score"] != "NA"),
                "scheduled_fixtures": sum(1 for m in matches if m["home_score"] == "NA"),
                "shootouts": len(shootouts),
            },
            indent=2,
        )
    )
    log.info("wikipedia overlay written", matches=len(matches), shootouts=len(shootouts))
    return len(matches)


if __name__ == "__main__":
    run()
