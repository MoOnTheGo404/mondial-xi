from kickoff_ml.ratings.elo import EloConfig, EloEngine


def test_zero_sum_update():
    e = EloEngine()
    e.update("a", "b", 2, 0, neutral=True, tier="friendly")
    assert abs((e.rating("a") - 1500) + (e.rating("b") - 1500)) < 1e-9


def test_winner_gains_loser_drops():
    e = EloEngine()
    e.update("a", "b", 3, 1, neutral=True, tier="world_cup")
    assert e.rating("a") > 1500 > e.rating("b")


def test_home_advantage_raises_expectation():
    e = EloEngine(EloConfig(home_advantage=100))
    assert e.expected_home("a", "b", neutral=False) > e.expected_home("a", "b", neutral=True)
    assert abs(e.expected_home("a", "b", neutral=True) - 0.5) < 1e-12


def test_margin_multiplier_monotone():
    m = EloEngine._margin_multiplier
    assert m(0) == m(1) == 1.0
    assert m(2) == 1.5
    assert m(3) < m(5) < m(9)


def test_tier_weighting():
    friendly, wc = EloEngine(), EloEngine()
    friendly.update("a", "b", 1, 0, True, "friendly")
    wc.update("a", "b", 1, 0, True, "world_cup")
    assert wc.rating("a") > friendly.rating("a")


def test_upset_moves_more_than_expected_win():
    e = EloEngine()
    e.ratings = {"strong": 1900.0, "weak": 1400.0}
    before = e.rating("weak")
    e.update("weak", "strong", 1, 0, neutral=True, tier="friendly")
    upset_gain = e.rating("weak") - before

    e2 = EloEngine()
    e2.ratings = {"strong": 1900.0, "weak": 1400.0}
    e2.update("strong", "weak", 1, 0, neutral=True, tier="friendly")
    expected_gain = e2.rating("strong") - 1900.0
    assert upset_gain > expected_gain > 0


def test_deterministic():
    a, b = EloEngine(), EloEngine()
    for eng in (a, b):
        eng.update("x", "y", 2, 2, False, "qualifier")
        eng.update("y", "z", 0, 1, True, "continental")
    assert a.ratings == b.ratings
