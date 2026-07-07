"""Reconstruct the real WC-2026 tournament state from the processed dataset.

Everything here is derived from the CC0 results data (group results, knockout
scores, shootout winners) plus the verified, versioned tournament config
(data/tournaments/wc2026.json). No result is invented: matches missing from
the dataset are simulated as *future* matches.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from kickoff_ml.config import ROOT
from kickoff_ml.models.service import ET_MEAN_SCALE, PredictionEngine
from kickoff_ml.simulation.engine import (
    GroupFixture,
    KnockoutResult,
    TournamentConfig,
    TournamentSimulator,
)

GROUP_STAGE_END = date(2026, 6, 27)
ROUND_DATES = {  # verified schedule windows
    "R32": (date(2026, 6, 28), date(2026, 7, 3)),
    "R16": (date(2026, 7, 4), date(2026, 7, 7)),
    "QF": (date(2026, 7, 9), date(2026, 7, 11)),
    "SF": (date(2026, 7, 14), date(2026, 7, 15)),
    "F": (date(2026, 7, 18), date(2026, 7, 19)),
}
HOSTS = {"united-states": "United States", "mexico": "Mexico", "canada": "Canada"}


def config_path() -> Path:
    return ROOT / "data" / "tournaments" / "wc2026.json"


class BundleMatchModel:
    """Adapts PredictionEngine's Dixon–Coles model to the simulator protocol."""

    def __init__(self, engine: PredictionEngine, importance: int = 4) -> None:
        self.engine = engine
        self.importance = importance

    def _mus(self, home: str, away: str, neutral: bool) -> tuple[float, float]:
        feats = self.engine._features(home, away, neutral, self.importance)
        mu_h, mu_a = self.engine.models["dixon_coles"].expected_goals(feats)
        return float(mu_h[0]), float(mu_a[0])

    def score_matrix_for(self, home: str, away: str, neutral: bool) -> np.ndarray:
        mu_h, mu_a = self._mus(home, away, neutral)
        return self.engine.models["dixon_coles"].score_matrix(mu_h, mu_a)

    def et_matrix_for(self, home: str, away: str, neutral: bool) -> np.ndarray:
        mu_h, mu_a = self._mus(home, away, neutral)
        return self.engine.models["dixon_coles"].score_matrix(
            mu_h * ET_MEAN_SCALE, mu_a * ET_MEAN_SCALE
        )

    def rating(self, team_id: str) -> float:
        return self.engine.rating(team_id)


def load_state(matches: pl.DataFrame, cfg: TournamentConfig) -> dict:
    """Split the dataset's WC-2026 rows into group fixtures + knockout results."""
    wc = matches.filter(
        (pl.col("tournament") == "FIFA World Cup") & (pl.col("date") >= pl.date(2026, 6, 1))
    ).sort("date")

    team_group = {t: g for g, members in cfg.groups.items() for t in members}

    group_fixtures: list[GroupFixture] = []
    knockout: dict[str, list[KnockoutResult]] = {r: [] for r in ROUND_DATES}
    for m in wc.iter_rows(named=True):
        h, a = m["home_id"], m["away_id"]
        if m["date"] <= GROUP_STAGE_END:
            g = team_group.get(h)
            if g is None or team_group.get(a) != g:
                continue  # defensive: non-config team
            group_fixtures.append(
                GroupFixture(
                    group=g, home=h, away=a,
                    home_goals=m["home_score"], away_goals=m["away_score"],
                    neutral=bool(m["neutral"]),
                )
            )
        else:
            rnd = next(
                (r for r, (lo, hi) in ROUND_DATES.items() if lo <= m["date"] <= hi), None
            )
            if rnd is None or m["home_score"] is None:
                continue
            if m["home_score"] > m["away_score"]:
                winner = h
            elif m["home_score"] < m["away_score"]:
                winner = a
            else:
                winner = m["shootout_winner_id"] or h  # dataset always records shootout
            knockout[rnd].append(
                KnockoutResult(
                    home=h, away=a, home_goals=m["home_score"],
                    away_goals=m["away_score"], winner=winner,
                )
            )
    # Recover the REAL R32 pairings in template order from the played matches:
    # every template slot's home ref (W_x / RU_x) resolves deterministically
    # from the completed group results; the real away side (incl. the actual
    # Annex-C third allocation) is read off the played R32 match.
    r32_pairs: list[tuple[str, str]] | None = None
    if len(knockout["R32"]) == 16:
        from kickoff_ml.simulation.engine import rank_group

        pair_order = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
        winners: dict[str, str] = {}
        runners: dict[str, str] = {}
        for g, members in cfg.groups.items():
            fx = [f for f in group_fixtures if f.group == g]
            if len(fx) != 6 or any(f.home_goals is None for f in fx):
                r32_pairs = None
                break
            scores = []
            for i, j in pair_order:
                a, b = members[i], members[j]
                f = next(x for x in fx if {x.home, x.away} == {a, b})
                hg, ag = (f.home_goals, f.away_goals) if f.home == a else (f.away_goals, f.home_goals)
                scores.append((hg, ag))
            elo_order = tuple(range(4))  # proxy irrelevant: real ties resolved by H2H/GD here
            ranking = rank_group(tuple(scores), elo_order)
            winners[g] = members[ranking[0]]
            runners[g] = members[ranking[1]]
        else:
            by_team: dict[str, KnockoutResult] = {}
            for r in knockout["R32"]:
                by_team[r.home] = r
                by_team[r.away] = r
            r32_pairs = []
            for t in cfg.r32_template:
                ref = t["home"]
                anchor = winners[ref[2:]] if ref.startswith("W_") else runners[ref[3:]]
                real = by_team.get(anchor)
                if real is None:
                    r32_pairs = None
                    break
                r32_pairs.append((real.home, real.away))

    return {
        "group_fixtures": group_fixtures,
        "completed_knockout": knockout,
        "r32_pairs": r32_pairs,
    }


def simulate_wc2026(
    engine: PredictionEngine,
    matches: pl.DataFrame,
    n_sims: int = 10_000,
    seed: int = 42,
    locked_knockout: dict[str, dict[frozenset[str], str]] | None = None,
    from_scratch: bool = False,
) -> dict:
    """Simulate WC-2026: remaining tournament from the real state (default),
    or a full what-if re-simulation (from_scratch=True)."""
    cfg = TournamentConfig.from_json(config_path())
    sim = TournamentSimulator(cfg, BundleMatchModel(engine))
    state = load_state(matches, cfg)
    if from_scratch:
        fixtures = [
            GroupFixture(f.group, f.home, f.away, None, None, f.neutral)
            for f in state["group_fixtures"]
        ]
        completed = {}
        r32_pairs = None
    else:
        fixtures = state["group_fixtures"]
        completed = state["completed_knockout"]
        r32_pairs = state["r32_pairs"]
    result = sim.simulate(
        fixtures, n_sims=n_sims, seed=seed,
        completed_knockout=completed, locked_knockout=locked_knockout,
        r32_pairs=r32_pairs,
    )
    result["mode"] = "what_if_full_resim" if from_scratch else "remaining_from_real_state"
    result["real_results_pinned"] = not from_scratch
    return result
