"""Dataset-backed providers: fixtures, teams, matches from the CC0 core.

`last_sync` is the retrieval timestamp recorded in the download manifest —
never fabricated.
"""

from __future__ import annotations

import json

import polars as pl

from kickoff_ml.config import MANIFEST_DIR, PROCESSED_DIR
from kickoff_ml.providers.base import Fixture, ProviderStatus


class LocalDatasetProvider:
    """Serves upcoming fixtures & results from the processed open dataset."""

    name = "open-data-core"

    def __init__(self) -> None:
        self._upcoming = pl.read_parquet(PROCESSED_DIR / "upcoming.parquet")
        manifest_path = MANIFEST_DIR / "results.json"
        self._manifest = (
            json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        )

    def upcoming_fixtures(self) -> list[Fixture]:
        retrieved = self._manifest.get("retrieved_at")
        return [
            Fixture(
                fixture_id=m["match_id"],
                date=str(m["date"]),
                home_id=m["home_id"],
                away_id=m["away_id"],
                tournament=m["tournament"],
                city=m["city"],
                country=m["country"],
                neutral=bool(m["neutral"]),
                status="scheduled",
                source="martj42/international_results (CC0)",
                retrieved_at=retrieved,
            )
            for m in self._upcoming.sort("date").iter_rows(named=True)
        ]

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            kind="dataset",
            available=True,
            capabilities=[
                "historical_matches", "upcoming_fixtures_snapshot",
                "goalscorers", "shootouts", "team_registry",
            ],
            license_note="CC0 1.0 (public domain) — redistribution allowed",
            last_sync=self._manifest.get("retrieved_at"),
            detail=(
                f"snapshot includes scheduled fixtures to {self._manifest.get('date_max', 'unknown')}; "
                "completed-results cutoff is reported by the model as data_cutoff"
            ),
        )
