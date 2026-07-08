import numpy as np

from kickoff_ml.simulation.qualifiers import (
    _snake_groups,
    playoff,
    simulate_confederation,
)


class FakeModel:
    """Strength = alphabetical: 'a…' strongest. Heavy favorite matrix."""

    def __init__(self, ratings: dict[str, float]):
        self._r = ratings

    def score_matrix_for(self, home, away, neutral):
        m = np.zeros((11, 11))
        if self._r[home] >= self._r[away]:
            m[2, 0], m[1, 1], m[0, 1] = 0.7, 0.15, 0.15
        else:
            m[0, 2], m[1, 1], m[1, 0] = 0.7, 0.15, 0.15
        return m

    def rating(self, t):
        return self._r[t]


def _model(teams):
    return FakeModel({t: 2000 - 50 * i for i, t in enumerate(teams)})


def test_snake_groups_seeded():
    groups = _snake_groups(["t1", "t2", "t3", "t4", "t5", "t6"], 2)
    # snake: pot1 -> g1,g2 ; pot2 reversed -> g2,g1 ; pot3 -> g1,g2
    assert groups[0] == ["t1", "t4", "t5"]
    assert groups[1] == ["t2", "t3", "t6"]
    # strongest teams never share a group
    assert not ({"t1", "t2"} <= set(groups[0]))


def test_league_mode_quota_and_favorites():
    teams = [f"t{i}" for i in range(8)]
    model = _model(teams)
    rng = np.random.default_rng(3)
    qualified, candidates = simulate_confederation(model, teams, 3, rng, 200, {})
    assert all(len(q) == 3 for q in qualified)
    # the clear favorite qualifies almost always under a 70% win matrix
    rate = sum("t0" in q for q in qualified) / 200
    assert rate > 0.8
    assert all(len(c) <= 2 for c in candidates)


def test_group_mode_quota_exact():
    teams = [f"t{i:02d}" for i in range(30)]
    model = _model(teams)
    rng = np.random.default_rng(1)
    qualified, candidates = simulate_confederation(model, teams, 6, rng, 50, {})
    assert all(len(q) == 6 for q in qualified)
    assert all(len(set(q)) == 6 for q in qualified)  # no duplicates
    assert all(set(c).isdisjoint(q) for q, c in zip(qualified, candidates, strict=True))


def test_playoff_returns_two_and_prefers_seeds():
    teams = [f"p{i}" for i in range(6)]
    model = _model(teams)
    wins = {t: 0 for t in teams}
    for s in range(150):
        for w in playoff(model, teams, np.random.default_rng(s), {}):
            wins[w] += 1
    assert all(
        len(playoff(model, teams, np.random.default_rng(s), {})) == 2 for s in range(5)
    )
    assert wins["p0"] > wins["p5"]  # top seed advances far more often


def test_pot_draw_constraints():
    from kickoff_ml.simulation.wc2030 import _pot_draw

    confeds = ["UEFA"] * 16 + ["CAF"] * 9 + ["AFC"] * 8 + ["CONMEBOL"] * 6 \
        + ["CONCACAF"] * 6 + ["OFC"] * 3
    teams = [f"n{i:02d}" for i in range(48)]
    confed = dict(zip(teams, confeds, strict=True))

    class M:
        def rating(self, t):
            return 2200 - int(t[1:]) * 10

    # patch config hosts to teams present in this synthetic field
    import kickoff_ml.simulation.wc2030 as w

    orig = w.config_2030
    try:
        w.config_2030 = lambda: {
            **orig(),
            "verified_facts": {"hosts_auto_qualified": ["n00", "n16", "n25"]},
        }
        groups = _pot_draw(teams, confed, M(), np.random.default_rng(0))
    finally:
        w.config_2030 = orig
    assert groups is not None
    assert sum(len(g) for g in groups.values()) == 48
    for members in groups.values():
        assert len(members) == 4
        per_conf: dict[str, int] = {}
        for t in members:
            per_conf[confed[t]] = per_conf.get(confed[t], 0) + 1
        for c, n in per_conf.items():
            assert n <= (2 if c == "UEFA" else 1), (c, members)
