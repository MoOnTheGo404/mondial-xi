"""Chronological feature builder.

Single forward pass over matches sorted by date. For every match the
pre-match feature vector is EMITTED FIRST, then team state is updated with
the match outcome. Nothing about the current match (or any later match) can
therefore enter its own features — enforced further by tests.

Rolling state per team:
- Elo (via EloEngine)
- last-N results (exponentially weighted form score)
- rolling goals scored / conceded (last N)
- days since previous match, matches in last 365 days
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import date

import polars as pl

from kickoff_ml.ratings.elo import EloConfig, EloEngine

FORM_N = 10
FORM_HALF_LIFE = 4.0  # matches


@dataclass
class TeamState:
    recent: deque = field(default_factory=lambda: deque(maxlen=FORM_N))  # (points, gf, ga)
    last_date: date | None = None
    dates_365: deque = field(default_factory=deque)

    def form_score(self) -> float:
        """Exponentially weighted mean points (0..3), most recent heaviest."""
        if not self.recent:
            return 1.0  # league-average prior ~1.0 pt/match
        num = den = 0.0
        n = len(self.recent)
        for i, (pts, _, _) in enumerate(self.recent):
            w = 0.5 ** ((n - 1 - i) / FORM_HALF_LIFE)
            num += w * pts
            den += w
        return num / den

    def rolling_goals(self) -> tuple[float, float]:
        if not self.recent:
            return (1.2, 1.2)  # global mean prior
        gf = sum(g for _, g, _ in self.recent) / len(self.recent)
        ga = sum(g for _, _, g in self.recent) / len(self.recent)
        return gf, ga


class FeatureBuilder:
    def __init__(self, elo_config: EloConfig | None = None) -> None:
        self.elo = EloEngine(elo_config or EloConfig())
        self.states: dict[str, TeamState] = {}

    def _state(self, team_id: str) -> TeamState:
        if team_id not in self.states:
            self.states[team_id] = TeamState()
        return self.states[team_id]

    def snapshot(self, home_id: str, away_id: str, neutral: bool, d: date) -> dict:
        """Pre-match feature vector using only past information."""
        hs, as_ = self._state(home_id), self._state(away_id)
        elo = self.elo.pre_match(home_id, away_id, neutral)
        h_gf, h_ga = hs.rolling_goals()
        a_gf, a_ga = as_.rolling_goals()

        def rest(s: TeamState) -> float:
            if s.last_date is None:
                return 30.0
            return float(min((d - s.last_date).days, 60))

        def congestion(s: TeamState) -> int:
            while s.dates_365 and (d - s.dates_365[0]).days > 365:
                s.dates_365.popleft()
            return len(s.dates_365)

        return {
            **elo,
            "home_form": hs.form_score(),
            "away_form": as_.form_score(),
            "home_gf": h_gf, "home_ga": h_ga,
            "away_gf": a_gf, "away_ga": a_ga,
            "home_rest": rest(hs), "away_rest": rest(as_),
            "home_matches_365": congestion(hs), "away_matches_365": congestion(as_),
            "home_experience": self.elo.matches_played(home_id),
            "away_experience": self.elo.matches_played(away_id),
            "neutral": int(neutral),
        }

    def update(
        self, home_id: str, away_id: str, home_score: int, away_score: int,
        neutral: bool, tier: str, d: date,
    ) -> None:
        self.elo.update(home_id, away_id, home_score, away_score, neutral, tier)
        h_pts = 3 if home_score > away_score else (1 if home_score == away_score else 0)
        a_pts = 3 if away_score > home_score else (1 if home_score == away_score else 0)
        hs, as_ = self._state(home_id), self._state(away_id)
        hs.recent.append((h_pts, home_score, away_score))
        as_.recent.append((a_pts, away_score, home_score))
        hs.last_date = as_.last_date = d
        hs.dates_365.append(d)
        as_.dates_365.append(d)


TIER_IMPORTANCE = {"world_cup": 4, "continental": 3, "qualifier": 2, "other": 1, "friendly": 0}


def build_feature_table(matches: pl.DataFrame, elo_config: EloConfig | None = None) -> pl.DataFrame:
    """Walk matches chronologically, emit features + label per match."""
    fb = FeatureBuilder(elo_config)
    rows: list[dict] = []
    for m in matches.sort("date").iter_rows(named=True):
        feats = fb.snapshot(m["home_id"], m["away_id"], m["neutral"], m["date"])
        outcome = (
            "H" if m["home_score"] > m["away_score"]
            else ("A" if m["home_score"] < m["away_score"] else "D")
        )
        rows.append(
            {
                "match_id": m["match_id"], "date": m["date"],
                "home_id": m["home_id"], "away_id": m["away_id"],
                "tier": m["tier"],
                "importance": TIER_IMPORTANCE.get(m["tier"], 1),
                **feats,
                "home_score": m["home_score"], "away_score": m["away_score"],
                "outcome": outcome,
            }
        )
        fb.update(
            m["home_id"], m["away_id"], m["home_score"], m["away_score"],
            m["neutral"], m["tier"], m["date"],
        )
    return pl.DataFrame(rows)


def final_state(matches: pl.DataFrame, elo_config: EloConfig | None = None) -> FeatureBuilder:
    """Builder state after consuming all completed matches (for serving)."""
    fb = FeatureBuilder(elo_config)
    for m in matches.sort("date").iter_rows(named=True):
        fb.update(
            m["home_id"], m["away_id"], m["home_score"], m["away_score"],
            m["neutral"], m["tier"], m["date"],
        )
    return fb
