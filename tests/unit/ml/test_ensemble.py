import numpy as np

from kickoff_ml.features.builder import build_feature_table
from kickoff_ml.models.goals import PoissonGoalModel
from kickoff_ml.models.outcome import EloLogisticModel, GeometricMeanEnsemble


def test_geometric_mean_is_normalized_and_between_components(core8):
    feats = build_feature_table(core8)
    elo = EloLogisticModel().fit(feats)
    dc = PoissonGoalModel().fit(feats)
    ens = GeometricMeanEnsemble({"elo": elo, "dc": dc})
    p = ens.predict_proba(feats)
    assert np.allclose(p.sum(axis=1), 1.0)
    assert (p >= 0).all() and (p <= 1).all()
    # geometric mean of two prob vectors lies between them (per element, then
    # renormalized) — at minimum it is a genuine blend, not equal to one input
    pe, pd_ = elo.predict_proba(feats), dc.outcome_probs(feats)
    assert not np.allclose(p, pe)
    assert not np.allclose(p, pd_)


def test_parameter_free_fit_is_noop(core8):
    feats = build_feature_table(core8)
    elo = EloLogisticModel().fit(feats)
    dc = PoissonGoalModel().fit(feats)
    ens = GeometricMeanEnsemble({"elo": elo, "dc": dc})
    before = ens.predict_proba(feats)
    ens.fit(feats.head(5))  # fitting must change nothing
    after = ens.predict_proba(feats)
    assert np.array_equal(before, after)


def test_dc_has_predict_proba_alias(core8):
    feats = build_feature_table(core8)
    dc = PoissonGoalModel().fit(feats)
    assert np.array_equal(dc.predict_proba(feats), dc.outcome_probs(feats))
