"""Outcome (H/D/A) probability models.

- EloLogisticModel: multinomial logistic regression on the effective Elo
  difference only — the honest "Elo baseline".
- GradientBoostedModel: HistGradientBoostingClassifier over the full
  pre-match feature set, with per-class isotonic calibration fitted on the
  validation window (never on training or test data).
- FrequencyBaseline: constant historical H/D/A frequencies.

Class order everywhere: ["H", "D", "A"].
"""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

CLASSES = ["H", "D", "A"]

FULL_FEATURES = [
    "elo_diff_eff", "home_elo", "away_elo",
    "home_form", "away_form",
    "home_gf", "home_ga", "away_gf", "away_ga",
    "home_rest", "away_rest",
    "home_matches_365", "away_matches_365",
    "home_experience", "away_experience",
    "neutral", "importance",
]

ELO_FEATURES = ["elo_diff_eff"]


def _y(df: pl.DataFrame) -> np.ndarray:
    return df["outcome"].to_numpy()


def _order_proba(model, proba: np.ndarray) -> np.ndarray:
    """Reorder sklearn's alphabetical classes to [H, D, A]."""
    cols = {c: i for i, c in enumerate(model.classes_)}
    return proba[:, [cols["H"], cols["D"], cols["A"]]]


class FrequencyBaseline:
    def fit(self, df: pl.DataFrame) -> FrequencyBaseline:
        y = _y(df)
        n = len(y)
        self.p = np.array([(y == c).sum() / n for c in CLASSES])
        return self

    def predict_proba(self, df: pl.DataFrame) -> np.ndarray:
        return np.tile(self.p, (df.height, 1))


class EloLogisticModel:
    def __init__(self) -> None:
        self.clf = LogisticRegression(max_iter=1000)

    def fit(self, df: pl.DataFrame) -> EloLogisticModel:
        self.clf.fit(df.select(ELO_FEATURES).to_numpy(), _y(df))
        return self

    def predict_proba(self, df: pl.DataFrame) -> np.ndarray:
        return _order_proba(self.clf, self.clf.predict_proba(df.select(ELO_FEATURES).to_numpy()))


class GradientBoostedModel:
    def __init__(self, **kw) -> None:
        params = {
            "max_depth": 4, "learning_rate": 0.06, "max_iter": 400,
            "l2_regularization": 1.0, "min_samples_leaf": 60,
            "random_state": 7, "early_stopping": False,
        }
        params.update(kw)
        self.clf = HistGradientBoostingClassifier(**params)
        self.calibrators: list[IsotonicRegression] | None = None

    def fit(self, df: pl.DataFrame) -> GradientBoostedModel:
        self.clf.fit(df.select(FULL_FEATURES).to_numpy(), _y(df))
        return self

    def _raw_proba(self, df: pl.DataFrame) -> np.ndarray:
        return _order_proba(self.clf, self.clf.predict_proba(df.select(FULL_FEATURES).to_numpy()))

    def calibrate(self, df_val: pl.DataFrame) -> GradientBoostedModel:
        """Per-class isotonic calibration on held-out validation data."""
        raw = self._raw_proba(df_val)
        y = _y(df_val)
        self.calibrators = []
        for k, c in enumerate(CLASSES):
            iso = IsotonicRegression(out_of_bounds="clip", y_min=1e-4, y_max=1 - 1e-4)
            iso.fit(raw[:, k], (y == c).astype(float))
            self.calibrators.append(iso)
        return self

    def predict_proba(self, df: pl.DataFrame) -> np.ndarray:
        raw = self._raw_proba(df)
        if self.calibrators is None:
            return raw
        cal = np.column_stack([iso.predict(raw[:, k]) for k, iso in enumerate(self.calibrators)])
        return cal / cal.sum(axis=1, keepdims=True)
