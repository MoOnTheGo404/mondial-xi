"""Application state: read-only data + trained artifacts loaded once.

The API never trains anything; it loads the evaluated bundle and processed
datasets from disk. Missing artifacts produce a clear 503, not a crash.
"""

from __future__ import annotations

import json
from functools import cached_property

import polars as pl
import structlog

from kickoff_api.settings import settings
from kickoff_ml.config import ARTIFACTS_DIR, MANIFEST_DIR, PROCESSED_DIR, ROOT
from kickoff_ml.models.service import PredictionEngine
from kickoff_ml.providers.football_data import FootballDataProvider
from kickoff_ml.providers.local import LocalDatasetProvider
from kickoff_ml.providers.weather import OpenMeteoProvider

log = structlog.get_logger()


class AppState:
    def __init__(self) -> None:
        self.ready = False
        self.load_error: str | None = None

    def load(self) -> None:
        try:
            self.engine = PredictionEngine()
            self.matches = pl.read_parquet(PROCESSED_DIR / "matches.parquet")
            self.upcoming = pl.read_parquet(PROCESSED_DIR / "upcoming.parquet")
            self.teams = pl.read_parquet(PROCESSED_DIR / "teams.parquet")
            players_path = PROCESSED_DIR / "players.parquet"
            self.players = pl.read_parquet(players_path) if players_path.exists() else pl.DataFrame()
            self.elo_history = pl.read_parquet(ARTIFACTS_DIR / "elo_history.parquet")
            self.metrics = json.loads((ARTIFACTS_DIR / "metrics.json").read_text())
            self.model_comparison = json.loads((ARTIFACTS_DIR / "model_comparison.json").read_text())
            self.calibration = json.loads((ARTIFACTS_DIR / "calibration.json").read_text())
            self.model_card = json.loads((ARTIFACTS_DIR / "model_card.json").read_text())
            self.elo_tuning = json.loads((ARTIFACTS_DIR / "elo_tuning.json").read_text())
            self.data_quality = json.loads((MANIFEST_DIR / "data_quality.json").read_text())
            tp = ARTIFACTS_DIR / "test_predictions.parquet"
            self.test_predictions = pl.read_parquet(tp) if tp.exists() else pl.DataFrame()
            self.local_provider = LocalDatasetProvider()
            self.football_data = FootballDataProvider()
            self.weather = OpenMeteoProvider(enabled=settings.weather_enabled)
            self.tournament_config = json.loads(
                (ROOT / "data" / "tournaments" / "wc2026.json").read_text()
            )
            self.ready = True
            log.info(
                "state loaded",
                matches=self.matches.height,
                model_version=self.engine.model_version,
                cutoff=self.engine.data_cutoff,
            )
        except FileNotFoundError as exc:
            self.load_error = (
                f"Missing artifact or dataset: {exc}. Run `make data && make train`."
            )
            log.error("state load failed", error=self.load_error)

    @cached_property
    def team_index(self) -> dict[str, dict]:
        return {r["team_id"]: r for r in self.teams.iter_rows(named=True)}


STATE = AppState()
