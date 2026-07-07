import numpy as np

from kickoff_ml.features.builder import build_feature_table
from kickoff_ml.models.goals import PoissonGoalModel, matrix_summaries


def _fitted(core8):
    feats = build_feature_table(core8)
    return PoissonGoalModel().fit(feats), feats


def test_score_matrix_normalized(core8):
    model, _ = _fitted(core8)
    m = model.score_matrix(1.4, 1.1)
    assert abs(m.sum() - 1.0) < 1e-9
    assert (m >= 0).all()


def test_outcome_probs_sum_to_one(core8):
    model, feats = _fitted(core8)
    p = model.outcome_probs(feats.tail(20))
    assert np.allclose(p.sum(axis=1), 1.0)


def test_dixon_coles_rho_shifts_low_scores(core8):
    model, _feats = _fitted(core8)
    base = model.score_matrix(1.2, 1.0)
    model.rho = -0.08
    dc = model.score_matrix(1.2, 1.0)
    # negative rho raises P(0-0) and P(1-1), lowers P(1-0)/P(0-1)
    assert dc[0, 0] > base[0, 0]
    assert dc[1, 1] > base[1, 1]
    assert dc[1, 0] < base[1, 0]


def test_matrix_summaries_consistent(core8):
    model, _ = _fitted(core8)
    m = model.score_matrix(1.6, 0.9)
    s = matrix_summaries(m)
    assert abs(s["over_2_5"] + s["under_2_5"] - 1.0) < 1e-9
    assert 0 <= s["btts"] <= 1
    assert s["top_scorelines"][0]["prob"] >= s["top_scorelines"][1]["prob"]


def test_expected_goals_positive_and_bounded(core8):
    model, feats = _fitted(core8)
    mu_h, mu_a = model.expected_goals(feats)
    assert (mu_h > 0).all() and (mu_a > 0).all()
    assert mu_h.max() <= 6.0 and mu_a.max() <= 6.0
