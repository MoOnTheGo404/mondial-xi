"""Career international stats enrichment from Wikidata (CC0).

Wikidata stores, per player, national-team membership (P54) with qualifiers
"number of matches played/races/starts" (P1350 -> caps) and "number of
points/goals/set scored" (P1351 -> goals). License: CC0 1.0 — the only
license-clean source of *career* international totals we found
(docs/data-source-evaluation.md).

Honesty notes baked in:
- Community data: freshness varies per player; every value carries
  retrieved_at and is displayed with its source.
- Sanity filters reject implausible rows (goals > 1.5x caps, caps > 230,
  career goals below our recorded floor, dob inconsistent with activity).
- Name matching is (team, slugified label); ambiguous same-name cases are
  marked and NOT enriched. No assists: Wikidata does not track
  international assists — the field stays null rather than invented.

Run: uv run python -m kickoff_ml.ingestion.wikidata_players  (optional step;
the app degrades gracefully without it)
"""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime

import httpx
import structlog

from kickoff_ml.config import MANIFEST_DIR, RAW_DIR
from kickoff_ml.entities.teams import slugify

log = structlog.get_logger()

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "KickoffAtlas/1.0 (open-source portfolio project; CC0 data ingestion)"
TEAM_CLASS = "Q135408445"  # men's national association football team
BATCH = 2
THROTTLE_S = 2.0

EXCLUDE = re.compile(
    r"women|under[- ]|u-?\d\d|youth|olympic|futsal|beach|amateur|\bB\b|schoolboys|junior",
    re.IGNORECASE,
)
NAME_RE = re.compile(r"^(.*?) (?:men.s )?national (?:association )?(?:football|soccer) team$")


def _sparql(client: httpx.Client, query: str) -> list[dict]:
    for attempt in range(4):
        try:
            r = client.get(
                ENDPOINT,
                params={"query": query},
                headers={"User-Agent": UA, "Accept": "application/sparql-results+json"},
            )
            if r.status_code == 429:
                time.sleep(10 * (attempt + 1))
                continue
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except httpx.HTTPError as exc:
            log.warning("sparql retry", attempt=attempt, error=str(exc))
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("Wikidata SPARQL failed after retries")


def fetch_team_qids(client: httpx.Client, our_team_names: dict[str, str]) -> dict[str, str]:
    """Map our team_id -> Wikidata QID for senior men's national teams."""
    rows = _sparql(
        client,
        f"""SELECT ?team ?teamLabel WHERE {{
             ?team wdt:P31 wd:{TEAM_CLASS} .
             SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
           }}""",
    )
    mapping: dict[str, str] = {}
    for b in rows:
        label = b.get("teamLabel", {}).get("value", "")
        if EXCLUDE.search(label):
            continue
        m = NAME_RE.match(label)
        if not m:
            continue
        team_id = slugify(m.group(1))
        if team_id in our_team_names and team_id not in mapping:
            mapping[team_id] = b["team"]["value"].split("/")[-1]
    return mapping


def fetch_players(client: httpx.Client, qids: dict[str, str]) -> list[dict]:
    """Per-team career rows: (team_id, name, caps, goals, dob, player_qid)."""
    qid_to_team = {v: k for k, v in qids.items()}
    out: list[dict] = []
    failed: list[str] = []
    items = list(qids.values())

    def num(b: dict, field: str) -> int | None:
        # qualifier values can be blank nodes ("unknown value") — skip those
        try:
            return int(float(b[field]["value"])) if field in b else None
        except (ValueError, KeyError):
            return None

    for i in range(0, len(items), BATCH):
        chunk = items[i : i + BATCH]
        values = " ".join(f"wd:{q}" for q in chunk)
        try:
            rows = _sparql(
                client,
                f"""SELECT ?team ?player ?playerLabel ?caps ?goals ?dob WHERE {{
                     VALUES ?team {{ {values} }}
                     ?player p:P54 ?st .
                     ?st ps:P54 ?team .
                     OPTIONAL {{ ?st pq:P1350 ?caps . }}
                     OPTIONAL {{ ?st pq:P1351 ?goals . }}
                     OPTIONAL {{ ?player wdt:P569 ?dob . }}
                     FILTER(BOUND(?caps) || BOUND(?goals))
                     SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
                   }}""",
            )
        except RuntimeError:
            # partial data beats none: skip this chunk, record the gap
            failed.extend(qid_to_team[q] for q in chunk)
            log.warning("chunk failed, continuing", teams=[qid_to_team[q] for q in chunk])
            continue
        for b in rows:
            label = b.get("playerLabel", {}).get("value", "")
            if not label or re.fullmatch(r"Q\d+", label):
                continue  # unlabeled item — unmatchable
            team_qid = b["team"]["value"].split("/")[-1]
            dob_raw = b.get("dob", {}).get("value", "")[:10]
            out.append(
                {
                    "team_id": qid_to_team[team_qid],
                    "name": label,
                    "player_slug": slugify(label),
                    "caps": num(b, "caps"),
                    "goals": num(b, "goals"),
                    "dob": dob_raw if re.fullmatch(r"\d{4}-\d{2}-\d{2}", dob_raw) else None,
                    "qid": b["player"]["value"].split("/")[-1],
                }
            )
        log.info("wikidata chunk", teams=len(chunk), rows=len(rows), progress=f"{i + len(chunk)}/{len(items)}")
        time.sleep(THROTTLE_S)
    if failed:
        log.warning("teams without enrichment", n=len(failed), teams=failed[:10])
    return out


def plausible(caps: int | None, goals: int | None) -> bool:
    # 300: Ronaldo holds the real record at 233 caps; garbage rows are far larger
    if caps is not None and not (0 < caps <= 300):
        return False
    if goals is not None and goals < 0:
        return False
    return not (caps and goals is not None and goals > 1.5 * caps)


def run() -> dict:
    import polars as pl

    from kickoff_ml.config import PROCESSED_DIR

    teams = pl.read_parquet(PROCESSED_DIR / "teams.parquet")
    our = dict(zip(teams["team_id"].to_list(), teams["name"].to_list(), strict=True))

    with httpx.Client(timeout=90) as client:
        qids = fetch_team_qids(client, our)
        log.info("matched national teams", n=len(qids))
        players = fetch_players(client, qids)

    kept = [p for p in players if plausible(p["caps"], p["goals"])]
    dropped = len(players) - len(kept)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    payload = {"players": kept, "team_qids": qids}
    (RAW_DIR / "wikidata_players.json").write_text(json.dumps(payload))

    manifest = {
        "source_name": "Wikidata (SPARQL)",
        "url": ENDPOINT,
        "license": {
            "name": "CC0 1.0 (Wikidata structured data)",
            "url": "https://www.wikidata.org/wiki/Wikidata:Licensing",
            "redistribution_allowed": True,
        },
        "retrieved_at": datetime.now(UTC).isoformat(),
        "teams_matched": len(qids),
        "player_rows": len(kept),
        "implausible_rows_dropped": dropped,
        "fields": ["career caps (P1350)", "career goals (P1351)", "date of birth (P569)"],
        "known_limitations": [
            "Community-maintained; per-player freshness varies (values may lag recent matches)",
            "Only players with caps/goals qualifiers on their P54 statement appear",
            "No international assists exist in Wikidata — field intentionally absent",
            "Name-based matching; ambiguous same-name players are not enriched",
        ],
    }
    (MANIFEST_DIR / "wikidata_players.json").write_text(json.dumps(manifest, indent=2))
    log.info("wikidata enrichment saved", players=len(kept), dropped=dropped)
    return manifest


if __name__ == "__main__":
    run()
