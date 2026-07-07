import numpy as np

from kickoff_ml.evaluation import metrics as M


def test_log_loss_perfect_and_uniform():
    y = np.array(["H", "D", "A"])
    perfect = np.eye(3)
    assert M.log_loss(y, perfect) < 1e-9
    uniform = np.full((3, 3), 1 / 3)
    assert abs(M.log_loss(y, uniform) - np.log(3)) < 1e-9


def test_brier_bounds():
    y = np.array(["H", "H"])
    worst = np.array([[0, 0, 1.0], [0, 0, 1.0]])
    assert abs(M.brier_multiclass(y, worst) - 2.0) < 1e-9


def test_rps_orders_outcomes():
    """RPS must punish a 'far' miss (H predicted, A happened) more than a
    'near' miss (H predicted, D happened)."""
    p = np.array([[0.8, 0.1, 0.1]])
    near = M.rps(np.array(["D"]), p)
    far = M.rps(np.array(["A"]), p)
    assert far > near


def test_accuracy():
    y = np.array(["H", "A"])
    p = np.array([[0.6, 0.3, 0.1], [0.5, 0.3, 0.2]])
    assert M.accuracy(y, p) == 0.5


def test_reliability_bins_have_counts():
    rng = np.random.default_rng(0)
    p = rng.dirichlet([2, 1, 2], size=500)
    y = np.array(["HDA"[i] for i in rng.integers(0, 3, 500)])
    bins = M.reliability_bins(y, p)
    assert all(b["count"] >= 10 for b in bins)
