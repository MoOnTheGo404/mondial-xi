"""PredictionEngine: serve forecasts from the trained artifact bundle.

- Loads ml/artifacts/prediction_bundle.joblib (created by `make evaluate`).
  Never trains at load time.
- Outcome probabilities come from the champion model; the scoreline matrix
  comes from the Dixon–Coles goal model. When a scenario adjusts expected
  goals (player absences, venue changes), the champion probabilities are
  tilted multiplicatively by the DC probability ratio — a transparent,
  documented mechanism (docs/methodology.md#scenario-adjustments).
- Every response carries model_version, data_cutoff, data-quality grade,
  warnings and explanation components derived from actual model inputs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from functools import lru_cache
from typing import Any

import joblib
import numpy as np
import polars as pl

from kickoff_ml.config import ARTIFACTS_DIR, PROCESSED_DIR
from kickoff_ml.models.goals import matrix_summaries

ET_MEAN_SCALE = 1.0 / 3.0  # 30' extra time vs 90' regulation


@dataclass
class Scenario:
    """User-controlled assumptions. Everything here is clearly labeled as a
    user assumption in the response."""
    home_absences: list[str] = field(default_factory=list)
    away_absences: list[str] = field(default_factory=list)
    # doubtful players: (player_id, availability_probability)
    home_doubtful: list[tuple[str, float]] = field(default_factory=list)
    away_doubtful: list[tuple[str, float]] = field(default_factory=list)
    neutral: bool | None = None
    importance: int | None = None


class PredictionEngine:
    def __init__(self, bundle_path: str | None = None) -> None:
        path = bundle_path or str(ARTIFACTS_DIR / "prediction_bundle.joblib")
        self.bundle = joblib.load(path)
        self.builder = self.bundle["builder"]
        self.models = self.bundle["models"]
        self.champion_name: str = self.bundle["champion"]
        self.model_version: str = self.bundle["model_version"]
        self.data_cutoff: str = self.bundle["data_cutoff"]
        self._players: pl.DataFrame | None = None

    # -- data access -------------------------------------------------------

    @property
    def players(self) -> pl.DataFrame:
        if self._players is None:
            p = PROCESSED_DIR / "players.parquet"
            self._players = pl.read_parquet(p) if p.exists() else pl.DataFrame()
        return self._players

    def team_known(self, team_id: str) -> bool:
        return self.builder.elo.matches_played(team_id) > 0

    def rating(self, team_id: str) -> float:
        return self.builder.elo.rating(team_id)

    # -- feature assembly ---------------------------------------------------

    def _features(self, home_id: str, away_id: str, neutral: bool, importance: int) -> pl.DataFrame:
        snap = self.builder.snapshot(home_id, away_id, neutral, date.fromisoformat(self.data_cutoff))
        return pl.DataFrame([{**snap, "importance": importance}])

    def _champion_probs(self, feats: pl.DataFrame) -> np.ndarray:
        model = self.models[self.champion_name] if self.champion_name in self.models else self.models["gbm_calibrated"]
        return model.predict_proba(feats)[0]

    # -- scenario mechanics --------------------------------------------------

    MAX_SHARE_LOSS = 0.9  # even a fully-gutted attack retains residual scoring

    def _attack_share_loss(
        self, absences: list[str], doubtful: list[tuple[str, float]]
    ) -> tuple[float, list[dict]]:
        """Fraction of the team's recent recorded attacking output removed.

        Each player's `goal_share_recent` (coverage-robust, EB-shrunk share of
        the team's recorded goals over the trailing window) is summed; doubtful
        players contribute (1 - p_available) x share (marginalization).
        Assumption, stated in every explanation: lost output is NOT replaced
        like-for-like — this is the transparent no-replacement bound.
        """
        if self.players.is_empty():
            return 0.0, []
        details: list[dict] = []
        total = 0.0

        def share_of(pid: str) -> tuple[float, str]:
            row = self.players.filter(pl.col("player_id") == pid)
            if row.is_empty():
                return 0.0, pid
            return float(row["goal_share_recent"][0]), str(row["name"][0])

        for pid in absences:
            share, name = share_of(pid)
            total += share
            details.append({"player_id": pid, "name": name, "status": "unavailable",
                            "share_effect": -round(share, 4)})
        for pid, p_avail in doubtful:
            share, name = share_of(pid)
            eff = (1.0 - p_avail) * share
            total += eff
            details.append({"player_id": pid, "name": name, "status": "doubtful",
                            "availability_prob": p_avail, "share_effect": -round(eff, 4)})
        return min(total, self.MAX_SHARE_LOSS), details

    # -- main API -------------------------------------------------------------

    def predict(
        self,
        home_id: str,
        away_id: str,
        neutral: bool = True,
        importance: int = 4,
        scenario: Scenario | None = None,
    ) -> dict[str, Any]:
        scenario = scenario or Scenario()
        if scenario.neutral is not None:
            neutral = scenario.neutral
        if scenario.importance is not None:
            importance = scenario.importance

        warnings: list[str] = []
        for tid in (home_id, away_id):
            n = self.builder.elo.matches_played(tid)
            if n == 0:
                warnings.append(f"'{tid}' has no match history — rating is the global prior")
            elif n < 30:
                warnings.append(f"'{tid}' has only {n} recorded matches — high rating uncertainty")

        feats = self._features(home_id, away_id, neutral, importance)
        base_probs = self._champion_probs(feats)
        dc = self.models["dixon_coles"]
        mu_h, mu_a = dc.expected_goals(feats)
        mu_h, mu_a = float(mu_h[0]), float(mu_a[0])

        # scenario adjustments: proportional attack-share reduction
        fh, home_detail = self._attack_share_loss(scenario.home_absences, scenario.home_doubtful)
        fa, away_detail = self._attack_share_loss(scenario.away_absences, scenario.away_doubtful)
        adj_mu_h = max(mu_h * (1.0 - fh), 0.15)
        adj_mu_a = max(mu_a * (1.0 - fa), 0.15)
        dh, da = fh, fa  # nonzero when a scenario applies

        base_matrix = dc.score_matrix(mu_h, mu_a)
        matrix = dc.score_matrix(adj_mu_h, adj_mu_a)

        def probs_from_matrix(m: np.ndarray) -> np.ndarray:
            return np.array([np.tril(m, -1).sum(), np.trace(m), np.triu(m, 1).sum()])

        if dh > 0 or da > 0:
            q0, q1 = probs_from_matrix(base_matrix), probs_from_matrix(matrix)
            tilted = base_probs * (q1 / np.clip(q0, 1e-9, None))
            probs = tilted / tilted.sum()
            adjusted = True
        else:
            probs, adjusted = base_probs, False

        # knockout extras: ET / shootout / advancement
        p_draw_90 = float(probs[1])
        et_matrix = dc.score_matrix(adj_mu_h * ET_MEAN_SCALE, adj_mu_a * ET_MEAN_SCALE)
        p_et_draw = float(np.trace(et_matrix))
        p_home_et = float(np.tril(et_matrix, -1).sum())
        p_away_et = float(np.triu(et_matrix, 1).sum())
        # shootout: no defensible skill signal in the open data -> 50/50, documented
        adv_home = float(probs[0]) + p_draw_90 * (p_home_et + p_et_draw * 0.5)
        adv_away = float(probs[2]) + p_draw_90 * (p_away_et + p_et_draw * 0.5)

        snap = feats.to_dicts()[0]
        explanations = self._explanations(snap, neutral, home_detail, away_detail, home_id, away_id)
        grade, grade_reasons = self._quality_grade(home_id, away_id)

        entropy = float(-(probs * np.log(probs + 1e-12)).sum() / np.log(3))

        return {
            "model_version": self.model_version,
            "champion_model": self.champion_name,
            "data_cutoff": self.data_cutoff,
            "teams": {"home": home_id, "away": away_id},
            "context": {"neutral": neutral, "importance": importance},
            "probabilities": {
                "home": round(float(probs[0]), 4),
                "draw": round(float(probs[1]), 4),
                "away": round(float(probs[2]), 4),
            },
            "team_only_probabilities": {
                "home": round(float(base_probs[0]), 4),
                "draw": round(float(base_probs[1]), 4),
                "away": round(float(base_probs[2]), 4),
            },
            "scenario_adjusted": adjusted,
            "expected_goals": {"home": round(adj_mu_h, 3), "away": round(adj_mu_a, 3)},
            "base_expected_goals": {"home": round(mu_h, 3), "away": round(mu_a, 3)},
            "score_matrix": np.round(matrix, 5).tolist(),
            **matrix_summaries(matrix),
            "knockout": {
                "p_extra_time": round(p_draw_90, 4),
                "p_shootout": round(p_draw_90 * p_et_draw, 4),
                "advance_home": round(adv_home, 4),
                "advance_away": round(adv_away, 4),
                "shootout_model": "50/50 (no licensed shootout-skill data; documented)",
            },
            "player_assumptions": {"home": home_detail, "away": away_detail},
            "elo": {
                "home": round(snap["home_elo"], 1),
                "away": round(snap["away_elo"], 1),
                "diff_effective": round(snap["elo_diff_eff"], 1),
            },
            "uncertainty": {"normalized_entropy": round(entropy, 4)},
            "data_quality": {"grade": grade, "reasons": grade_reasons},
            "warnings": warnings,
            "explanations": explanations,
        }

    # -- explanation & grading -------------------------------------------------

    def _explanations(
        self, snap: dict, neutral: bool,
        home_detail: list[dict], away_detail: list[dict],
        home_id: str, away_id: str,
    ) -> list[dict]:
        out = []
        diff = snap["elo_diff"]
        if abs(diff) > 15:
            stronger = home_id if diff > 0 else away_id
            out.append({
                "factor": "rating_gap",
                "text": f"The pre-match Elo gap of {abs(diff):.0f} points favors {stronger}.",
                "direction": "home" if diff > 0 else "away",
                "magnitude": round(abs(diff), 1),
            })
        if not neutral:
            out.append({
                "factor": "home_advantage",
                "text": "Playing at home adds the model's tuned home advantage "
                        f"({self.builder.elo.config.home_advantage:.0f} Elo points).",
                "direction": "home", "magnitude": self.builder.elo.config.home_advantage,
            })
        else:
            out.append({
                "factor": "neutral_venue",
                "text": "The neutral venue removes the model's home adjustment.",
                "direction": "none", "magnitude": 0,
            })
        form_gap = snap["home_form"] - snap["away_form"]
        if abs(form_gap) > 0.35:
            better = home_id if form_gap > 0 else away_id
            out.append({
                "factor": "recent_form",
                "text": f"Time-decayed recent form favors {better} "
                        f"({snap['home_form']:.2f} vs {snap['away_form']:.2f} points/match).",
                "direction": "home" if form_gap > 0 else "away",
                "magnitude": round(abs(form_gap), 2),
            })
        for side, details in (("home", home_detail), ("away", away_detail)):
            for d in details:
                if d.get("share_effect", 0) != 0:
                    out.append({
                        "factor": "player_absence",
                        "text": f"{d['name']} marked {d['status']} (user scenario): removes "
                                f"~{abs(100 * d['share_effect']):.0f}% of the team's recent "
                                "recorded attacking output (shrunk share; assumes no "
                                "like-for-like replacement).",
                        "direction": "away" if side == "home" else "home",
                        "magnitude": abs(d["share_effect"]),
                    })
        return out

    def _quality_grade(self, home_id: str, away_id: str) -> tuple[str, list[str]]:
        reasons = []
        score = 0
        for tid in (home_id, away_id):
            n = self.builder.elo.matches_played(tid)
            if n >= 300:
                score += 2
            elif n >= 100:
                score += 1
                reasons.append(f"{tid}: moderate history ({n} matches)")
            else:
                reasons.append(f"{tid}: thin history ({n} matches)")
        grade = {4: "A", 3: "B", 2: "C", 1: "D", 0: "D"}[score]
        if not reasons:
            reasons.append("both teams have deep match history")
        reasons.append("player availability feeds are not configured — team-level forecast")
        return grade, reasons


@lru_cache(maxsize=1)
def get_engine() -> PredictionEngine:
    return PredictionEngine()
