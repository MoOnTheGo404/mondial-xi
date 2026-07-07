"""Integration tests against the real trained artifact bundle.

These require `make data && make evaluate` to have produced artifacts;
they are skipped (not failed) on a fresh checkout without artifacts.
"""

import numpy as np
import pytest

from kickoff_ml.config import ARTIFACTS_DIR

pytestmark = pytest.mark.skipif(
    not (ARTIFACTS_DIR / "prediction_bundle.joblib").exists(),
    reason="prediction bundle not built (run `make evaluate`)",
)


@pytest.fixture(scope="module")
def engine():
    from kickoff_ml.models.service import PredictionEngine

    return PredictionEngine()


def test_basic_prediction_shape(engine):
    r = engine.predict("brazil", "argentina", neutral=True)
    p = r["probabilities"]
    assert abs(p["home"] + p["draw"] + p["away"] - 1.0) < 1e-3
    assert r["model_version"] and r["data_cutoff"]
    assert r["data_quality"]["grade"] in "ABCD"
    assert len(r["score_matrix"]) == 11
    assert abs(sum(sum(row) for row in r["score_matrix"]) - 1.0) < 1e-3


def test_home_advantage_shifts_probability(engine):
    neutral = engine.predict("japan", "south-korea", neutral=True)
    home = engine.predict("japan", "south-korea", neutral=False)
    assert home["probabilities"]["home"] > neutral["probabilities"]["home"]


def test_stronger_team_favored(engine):
    r = engine.predict("france", "luxembourg", neutral=True)
    assert r["probabilities"]["home"] > 0.6
    assert r["expected_goals"]["home"] > r["expected_goals"]["away"]


def test_unknown_team_warns_not_crashes(engine):
    r = engine.predict("atlantis", "brazil", neutral=True)
    assert any("no match history" in w for w in r["warnings"])
    assert r["probabilities"]["away"] > 0.5


def test_scenario_absence_reduces_team_chance(engine):
    from kickoff_ml.models.service import Scenario

    base = engine.predict("argentina", "france", neutral=True)
    absent = engine.predict(
        "argentina", "france", neutral=True,
        scenario=Scenario(home_absences=["argentina/lionel-messi"]),
    )
    assert absent["scenario_adjusted"]
    assert absent["probabilities"]["home"] < base["probabilities"]["home"]
    assert absent["expected_goals"]["home"] < base["expected_goals"]["home"]
    assert any(e["factor"] == "player_absence" for e in absent["explanations"])
    # team-only forecast is preserved unchanged alongside
    assert absent["team_only_probabilities"] == base["team_only_probabilities"]


def test_doubtful_marginalization_between_bounds(engine):
    from kickoff_ml.models.service import Scenario

    base = engine.predict("argentina", "france", neutral=True)["probabilities"]["home"]
    out = engine.predict(
        "argentina", "france", neutral=True,
        scenario=Scenario(home_absences=["argentina/lionel-messi"]),
    )["probabilities"]["home"]
    doubt = engine.predict(
        "argentina", "france", neutral=True,
        scenario=Scenario(home_doubtful=[("argentina/lionel-messi", 0.5)]),
    )["probabilities"]["home"]
    assert out < doubt < base


def test_knockout_block_coherent(engine):
    r = engine.predict("spain", "portugal", neutral=True)
    k = r["knockout"]
    assert abs(k["advance_home"] + k["advance_away"] - 1.0) < 1e-3
    assert 0 <= k["p_shootout"] <= k["p_extra_time"] <= 1


def test_deterministic(engine):
    a = engine.predict("germany", "italy", neutral=True)
    b = engine.predict("germany", "italy", neutral=True)
    assert a["probabilities"] == b["probabilities"]
