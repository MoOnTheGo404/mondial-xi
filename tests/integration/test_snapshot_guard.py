"""The track-record guarantee: no snapshot may be created on/after its
fixture's kickoff date (found by independent review; regression-locked)."""

import os
import tempfile
import uuid
from datetime import UTC, datetime, timedelta

os.environ.setdefault(
    "KICKOFF_DATABASE_URL",
    f"sqlite:///{tempfile.gettempdir()}/kickoff_guard_test.db",
)

from kickoff_ml.providers.base import Fixture


class StubEngine:
    model_version = "test-0"
    data_cutoff = "2026-01-01"

    def predict(self, home, away, neutral=True, importance=4):
        return {
            "model_version": self.model_version,
            "data_cutoff": self.data_cutoff,
            "probabilities": {"home": 0.5, "draw": 0.3, "away": 0.2},
            "expected_goals": {"home": 1.2, "away": 0.9},
        }


class StubProvider:
    def __init__(self, fixtures):
        self._fx = fixtures

    def upcoming_fixtures(self):
        return self._fx


class StubState:
    def __init__(self, fixtures):
        self.engine = StubEngine()
        self.local_provider = StubProvider(fixtures)


def _fx(fid: str, date: str) -> Fixture:
    return Fixture(
        fixture_id=fid, date=date, home_id="a", away_id="b",
        tournament="Test Cup", neutral=True,
    )


def test_same_day_and_past_fixtures_are_never_snapshotted():
    from kickoff_api.db import PredictionSnapshot, get_session, init_db
    from kickoff_api.snapshots import snapshot_upcoming

    init_db()
    today = datetime.now(UTC).date()
    past = (today - timedelta(days=1)).isoformat()
    same_day = today.isoformat()
    future = (today + timedelta(days=2)).isoformat()

    # unique per run: the shared test DB may persist across sessions
    run = uuid.uuid4().hex[:8]
    label = f"guard_{run}"
    state = StubState([
        _fx(f"guard-past-{run}", past),
        _fx(f"guard-today-{run}", same_day),
        _fx(f"guard-future-{run}", future),
    ])
    created = snapshot_upcoming(state, version_label=label)
    assert created == 1  # only the strictly-future fixture

    with get_session() as session:
        rows = session.query(PredictionSnapshot).filter(
            PredictionSnapshot.version_label == label
        ).all()
        assert [r.fixture_id for r in rows] == [f"guard-future-{run}"]
        # invariant: generated strictly before kickoff date
        for r in rows:
            assert r.generated_at.date().isoformat() < r.kickoff_date
