"""The track-record guarantee: no snapshot may be created on/after its
fixture's kickoff date (found by independent review; regression-locked)."""

import os
import tempfile
from datetime import UTC, datetime, timedelta

os.environ.setdefault(
    "KICKOFF_DATABASE_URL",
    f"sqlite:///{tempfile.gettempdir()}/kickoff_guard_test.db",
)

from kickoff_ml.providers.base import Fixture  # noqa: E402


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

    state = StubState([
        _fx("guard-past", past),
        _fx("guard-today", same_day),
        _fx("guard-future", future),
    ])
    created = snapshot_upcoming(state, version_label="guard_test")
    assert created == 1  # only the strictly-future fixture

    with get_session() as session:
        rows = session.query(PredictionSnapshot).filter(
            PredictionSnapshot.version_label == "guard_test"
        ).all()
        assert [r.fixture_id for r in rows] == ["guard-future"]
        # invariant: generated strictly before kickoff date
        for r in rows:
            assert r.generated_at.date().isoformat() < r.kickoff_date
