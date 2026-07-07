"""Reproducible download of the open-data core with provenance manifests.

Source: github.com/martj42/international_results — CC0 1.0 (public domain).
Every download records URL, retrieval time, SHA-256, row count and date range
into data/manifests/<name>.json. Raw files are immutable inputs; all cleaning
happens in the build step.
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx
import structlog

from kickoff_ml.config import MANIFEST_DIR, RAW_DIR

log = structlog.get_logger()

BASE = "https://raw.githubusercontent.com/martj42/international_results/master"

SOURCES: dict[str, dict[str, str]] = {
    "results": {
        "url": f"{BASE}/results.csv",
        "description": "Senior men's international football results, 1872–present",
    },
    "shootouts": {
        "url": f"{BASE}/shootouts.csv",
        "description": "Penalty shootout outcomes for drawn matches",
    },
    "goalscorers": {
        "url": f"{BASE}/goalscorers.csv",
        "description": "Goalscorers with minute/own-goal/penalty flags",
    },
    "former_names": {
        "url": f"{BASE}/former_names.csv",
        "description": "Mapping of historical team names to current identities",
    },
}

LICENSE = {
    "name": "CC0 1.0 Universal (public domain)",
    "url": "https://github.com/martj42/international_results/blob/master/LICENSE",
    "redistribution_allowed": True,
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _csv_stats(path: Path) -> dict:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields = reader.fieldnames or []
        n = 0
        dmin = dmax = None
        for row in reader:
            n += 1
            d = row.get("date")
            if d:
                dmin = d if dmin is None or d < dmin else dmin
                dmax = d if dmax is None or d > dmax else dmax
    return {"row_count": n, "columns": fields, "date_min": dmin, "date_max": dmax}


def download_all(force: bool = False) -> dict[str, dict]:
    """Download all source files and write per-file provenance manifests."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifests: dict[str, dict] = {}
    with httpx.Client(timeout=60, follow_redirects=True) as client:
        for name, src in SOURCES.items():
            dest = RAW_DIR / f"{name}.csv"
            if dest.exists() and not force:
                log.info("raw file exists, skipping download", file=name)
            else:
                log.info("downloading", file=name, url=src["url"])
                resp = client.get(src["url"])
                resp.raise_for_status()
                dest.write_bytes(resp.content)
            manifest = {
                "source_name": "martj42/international_results",
                "dataset": name,
                "description": src["description"],
                "url": src["url"],
                "retrieved_at": datetime.now(UTC).isoformat(),
                "license": LICENSE,
                "sha256": _sha256(dest),
                **_csv_stats(dest),
                "known_limitations": [
                    "Community-maintained; occasional corrections upstream",
                    "Senior men's full internationals only (per upstream inclusion criteria)",
                    "No lineups, cards, or in-match statistics",
                    "Scores for knockout matches are after extra time; shootouts recorded separately",
                ],
            }
            (MANIFEST_DIR / f"{name}.json").write_text(json.dumps(manifest, indent=2))
            manifests[name] = manifest
    log.info("download complete", files=len(manifests))
    return manifests


if __name__ == "__main__":
    import sys

    download_all(force="--force" in sys.argv)
