import numpy as np
import pytest

from kickoff_ml.simulation.engine import (
    GroupFixture,
    TournamentConfig,
    TournamentSimulator,
    allocate_thirds,
    rank_group,
)

# match order for rank_group: [(0,1),(2,3),(0,2),(1,3),(0,3),(1,2)]


class TestRankGroup:
    def test_clear_order(self):
        # team0 wins all, team1 second, ...
        scores = ((2, 0), (1, 0), (2, 0), (1, 0), (2, 0), (1, 0))
        assert rank_group(scores, (0, 1, 2, 3)) == (0, 1, 2, 3)

    def test_h2h_before_overall_gd_2026_rule(self):
        """2026 rule: among tied teams, head-to-head result ranks BEFORE
        overall goal difference."""
        scores = (
            (1, 0),  # 0 v 1 -> t0 wins
            (0, 2),  # 2 v 3 -> t3 wins
            (1, 0),  # 0 v 2 -> t0 wins
            (5, 0),  # 1 v 3 -> t1 wins big
            (0, 1),  # 0 v 3 -> t3 wins
            (0, 5),  # 1 v 2 -> t2 wins big
        )
        # pts: t0=6, t3=6 (tied); t1=3, t2=3 (tied).
        # Overall GD: t0=+1, t3=-2 -> pre-2026 ordering would put t0 first.
        # But t3 WON the head-to-head -> 2026 rules rank t3 above t0.
        # Similarly t2 beat t1 head-to-head.
        ranking = rank_group(scores, (0, 1, 2, 3))
        assert ranking == (3, 0, 2, 1)

    def test_two_way_tie_resolved_by_h2h_win(self):
        scores = (
            (1, 0),  # 0 beats 1
            (1, 1),
            (3, 0),  # 0 beats 2
            (2, 0),  # 1 beats 3
            (0, 1),  # 0 loses to 3 -> t0: 6 pts
            (0, 4),  # 1 beats 2 big -> t1: 6 pts, better overall gd than t0?
        )
        # t0 gd: +1+3-1=+3 ; t1 gd: -1+2+4=+5. Overall GD favors t1,
        # but t0 won the head-to-head -> t0 first (2026 rule).
        ranking = rank_group(scores, (0, 1, 2, 3))
        assert ranking.index(0) < ranking.index(1)

    def test_full_tie_falls_to_ranking_proxy(self):
        scores = ((0, 0),) * 6
        assert rank_group(scores, (2, 0, 3, 1)) == (2, 0, 3, 1)


class TestThirdsAllocation:
    TEMPLATE = [
        {"match": 74, "home": "W_E", "away": "T3_ABCDF"},
        {"match": 77, "home": "W_I", "away": "T3_CDFGH"},
        {"match": 79, "home": "W_A", "away": "T3_CEFHI"},
        {"match": 80, "home": "W_L", "away": "T3_EHIJK"},
        {"match": 81, "home": "W_D", "away": "T3_BEFIJ"},
        {"match": 82, "home": "W_G", "away": "T3_AEHIJ"},
        {"match": 85, "home": "W_B", "away": "T3_EFGIJ"},
        {"match": 87, "home": "W_K", "away": "T3_DEIJL"},
    ]

    def test_real_2026_qualified_set_is_feasible(self):
        alloc = allocate_thirds(["B", "D", "E", "F", "I", "J", "K", "L"], self.TEMPLATE)
        assert alloc is not None
        assert sorted(alloc.values()) == ["B", "D", "E", "F", "I", "J", "K", "L"]
        for t in self.TEMPLATE:
            allowed = set(t["away"].removeprefix("T3_"))
            assert alloc[t["match"]] in allowed

    def test_infeasible_returns_none(self):
        template = [{"match": 1, "home": "W_A", "away": "T3_B"}]
        assert allocate_thirds(["C"], template) is None


class FakeModel:
    """Deterministic toy model: fixed score matrix favoring the
    alphabetically-first team; ratings by name."""

    def __init__(self, ratings: dict[str, float]):
        self._r = ratings

    def _m(self, home, away):
        m = np.zeros((11, 11))
        if self._r[home] >= self._r[away]:
            m[2, 0] = 0.6
            m[1, 1] = 0.2
            m[0, 2] = 0.2
        else:
            m[2, 0] = 0.2
            m[1, 1] = 0.2
            m[0, 2] = 0.6
        return m

    def score_matrix_for(self, home, away, neutral):
        return self._m(home, away)

    def et_matrix_for(self, home, away, neutral):
        return self._m(home, away)

    def rating(self, t):
        return self._r[t]


@pytest.fixture
def mini_cfg() -> TournamentConfig:
    """A 2-group / 4-team-per-group toy tournament: winners+runners -> SF."""
    return TournamentConfig(
        tournament_id="mini", name="Mini Cup",
        groups={"A": ["a1", "a2", "a3", "a4"], "B": ["b1", "b2", "b3", "b4"]},
        r32_template=[
            {"match": 1, "home": "W_A", "away": "RU_B"},
            {"match": 2, "home": "W_B", "away": "RU_A"},
        ],
        round_names=["SF", "F"],
        folds=[[[1, 2]]],  # winners of template matches 1 & 2 meet in the final
        best_thirds=0,
    )


def _fixtures(cfg):
    out = []
    for g, ms in cfg.groups.items():
        for i in range(4):
            for j in range(i + 1, 4):
                out.append(GroupFixture(group=g, home=ms[i], away=ms[j]))
    return out


class TestSimulator:
    def _model(self, cfg):
        ratings = {}
        for g, ms in cfg.groups.items():
            for k, t in enumerate(ms):
                ratings[t] = 2000 - 100 * k
        return FakeModel(ratings)

    def test_deterministic_seed(self, mini_cfg):
        sim = TournamentSimulator(mini_cfg, self._model(mini_cfg))
        r1 = sim.simulate(_fixtures(mini_cfg), n_sims=500, seed=9)
        r2 = sim.simulate(_fixtures(mini_cfg), n_sims=500, seed=9)
        assert r1["teams"] == r2["teams"]

    def test_probabilities_are_coherent(self, mini_cfg):
        sim = TournamentSimulator(mini_cfg, self._model(mini_cfg))
        res = sim.simulate(_fixtures(mini_cfg), n_sims=2000, seed=1)
        total_champ = sum(t["reach"]["champion"] for t in res["teams"])
        assert abs(total_champ - 1.0) < 1e-9
        for t in res["teams"]:
            r = t["reach"]
            assert r["SF"] >= r["F"] >= r["champion"]  # monotone progression

    def test_favorite_usually_wins(self, mini_cfg):
        sim = TournamentSimulator(mini_cfg, self._model(mini_cfg))
        res = sim.simulate(_fixtures(mini_cfg), n_sims=3000, seed=3)
        best = max(res["teams"], key=lambda t: t["reach"]["champion"])
        assert best["team_id"] in ("a1", "b1")
        assert best["reach"]["champion"] > 0.25

    def test_locked_result_forces_winner(self, mini_cfg):
        sim = TournamentSimulator(mini_cfg, self._model(mini_cfg))
        # lock the a1-vs-b2 semifinal: b2 always advances when they meet
        locked = {"SF": {frozenset({"a1", "b2"}): "b2"}}
        base = sim.simulate(_fixtures(mini_cfg), n_sims=1500, seed=5)
        res = sim.simulate(_fixtures(mini_cfg), n_sims=1500, seed=5, locked_knockout=locked)
        a1_base = next(t for t in base["teams"] if t["team_id"] == "a1")
        a1_lock = next(t for t in res["teams"] if t["team_id"] == "a1")
        b2_lock = next(t for t in res["teams"] if t["team_id"] == "b2")
        assert a1_lock["reach"]["F"] < a1_base["reach"]["F"]
        assert b2_lock["reach"]["F"] >= b2_lock["reach"]["SF"] * 0.99 or b2_lock["reach"]["F"] > 0

    def test_group_rank_distribution_sums_to_one(self, mini_cfg):
        sim = TournamentSimulator(mini_cfg, self._model(mini_cfg))
        res = sim.simulate(_fixtures(mini_cfg), n_sims=800, seed=2)
        for t in res["teams"]:
            assert abs(sum(t["group_rank_dist"]) - 1.0) < 1e-3  # rounded to 4dp

    def test_completed_results_pin_group_stage(self, mini_cfg):
        fixtures = _fixtures(mini_cfg)
        for f in fixtures:
            if f.group == "A":
                # a4 wins everything 1-0
                f.home_goals, f.away_goals = (0, 1) if f.away == "a4" else (1, 0)
                if f.home != "a4" and f.away != "a4":
                    f.home_goals, f.away_goals = 0, 0
        sim = TournamentSimulator(mini_cfg, self._model(mini_cfg))
        res = sim.simulate(fixtures, n_sims=400, seed=11)
        a4 = next(t for t in res["teams"] if t["team_id"] == "a4")
        assert a4["group_rank_dist"][0] == 1.0  # always wins pinned group
