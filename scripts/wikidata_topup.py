"""Surgical Wikidata top-up: rows with caps > 225 (record-holders that the
old sanity bound wrongly dropped). Merges into the saved raw file instead of
re-fetching everything — kinder to WDQS rate limits."""

import json
import re
import time

import httpx

from kickoff_ml.config import RAW_DIR
from kickoff_ml.entities.teams import slugify
from kickoff_ml.ingestion.wikidata_players import _sparql, plausible

raw_path = RAW_DIR / "wikidata_players.json"
data = json.loads(raw_path.read_text())
qids = data["team_qids"]
qid_to_team = {v: k for k, v in qids.items()}
existing = {(r["qid"], r["team_id"]) for r in data["players"]}

added = 0
items = list(qids.values())
with httpx.Client(timeout=90) as client:
    for i in range(0, len(items), 50):
        chunk = items[i : i + 50]
        values = " ".join(f"wd:{q}" for q in chunk)
        rows = _sparql(
            client,
            f"""SELECT ?team ?player ?playerLabel ?caps ?goals ?dob WHERE {{
                 VALUES ?team {{ {values} }}
                 ?player p:P54 ?st .
                 ?st ps:P54 ?team ; pq:P1350 ?caps .
                 FILTER(?caps > 225)
                 OPTIONAL {{ ?st pq:P1351 ?goals . }}
                 OPTIONAL {{ ?player wdt:P569 ?dob . }}
                 SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
               }}""",
        )
        for b in rows:
            label = b.get("playerLabel", {}).get("value", "")
            if not label or re.fullmatch(r"Q\d+", label):
                continue
            try:
                caps = int(float(b["caps"]["value"]))
                goals = int(float(b["goals"]["value"])) if "goals" in b else None
            except (ValueError, KeyError):
                continue
            if not plausible(caps, goals):
                continue
            team_id = qid_to_team[b["team"]["value"].split("/")[-1]]
            pqid = b["player"]["value"].split("/")[-1]
            if (pqid, team_id) in existing:
                continue
            dob = b.get("dob", {}).get("value", "")[:10]
            data["players"].append(
                {
                    "team_id": team_id,
                    "name": label,
                    "player_slug": slugify(label),
                    "caps": caps,
                    "goals": goals,
                    "dob": dob if re.fullmatch(r"\d{4}-\d{2}-\d{2}", dob) else None,
                    "qid": pqid,
                }
            )
            added += 1
            print("added:", label, team_id, caps, goals)
        time.sleep(3)

raw_path.write_text(json.dumps(data))
print(f"top-up complete: {added} rows added, total {len(data['players'])}")
