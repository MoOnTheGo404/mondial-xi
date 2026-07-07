"""Elo rating engine for international football.

Follows the well-established World Football Elo conventions
(eloratings.net-style): tournament-importance K, goal-margin multiplier,
home advantage. Parameters are tuned on the validation window (see
evaluation.tune), not folklore-fixed.

The engine is strictly sequential: `pre_match()` reads state, `update()`
mutates it. The feature builder always calls pre_match before update, which
is what makes leakage structurally impossible (see tests/unit/ml/test_leakage).
"""

from __future__ import annotations

from dataclasses import dataclass, field

K_BY_TIER = {
    "world_cup": 60.0,
    "continental": 50.0,
    "qualifier": 40.0,
    "other": 30.0,
    "friendly": 20.0,
}

DEFAULT_RATING = 1500.0


@dataclass
class EloConfig:
    home_advantage: float = 80.0     # rating points added to non-neutral home side
    k_scale: float = 1.0             # global multiplier on tier K
    margin_scaling: bool = True      # goal-difference multiplier
    new_team_rating: float = DEFAULT_RATING


@dataclass
class EloEngine:
    config: EloConfig = field(default_factory=EloConfig)
    ratings: dict[str, float] = field(default_factory=dict)
    match_counts: dict[str, int] = field(default_factory=dict)

    def rating(self, team_id: str) -> float:
        return self.ratings.get(team_id, self.config.new_team_rating)

    def matches_played(self, team_id: str) -> int:
        return self.match_counts.get(team_id, 0)

    def expected_home(self, home_id: str, away_id: str, neutral: bool) -> float:
        """Expected score (win=1, draw=0.5) for the home side."""
        diff = self.rating(home_id) - self.rating(away_id)
        if not neutral:
            diff += self.config.home_advantage
        return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))

    def pre_match(self, home_id: str, away_id: str, neutral: bool) -> dict[str, float]:
        diff = self.rating(home_id) - self.rating(away_id)
        eff = diff + (0.0 if neutral else self.config.home_advantage)
        return {
            "home_elo": self.rating(home_id),
            "away_elo": self.rating(away_id),
            "elo_diff": diff,
            "elo_diff_eff": eff,
            "elo_expected_home": 1.0 / (1.0 + 10.0 ** (-eff / 400.0)),
        }

    @staticmethod
    def _margin_multiplier(goal_diff: int) -> float:
        g = abs(goal_diff)
        if g <= 1:
            return 1.0
        if g == 2:
            return 1.5
        return (11.0 + g) / 8.0

    def update(
        self,
        home_id: str,
        away_id: str,
        home_score: int,
        away_score: int,
        neutral: bool,
        tier: str,
    ) -> None:
        exp_home = self.expected_home(home_id, away_id, neutral)
        if home_score > away_score:
            actual = 1.0
        elif home_score < away_score:
            actual = 0.0
        else:
            actual = 0.5
        k = K_BY_TIER.get(tier, 30.0) * self.config.k_scale
        if self.config.margin_scaling:
            k *= self._margin_multiplier(home_score - away_score)
        delta = k * (actual - exp_home)
        self.ratings[home_id] = self.rating(home_id) + delta
        self.ratings[away_id] = self.rating(away_id) - delta
        self.match_counts[home_id] = self.matches_played(home_id) + 1
        self.match_counts[away_id] = self.matches_played(away_id) + 1
