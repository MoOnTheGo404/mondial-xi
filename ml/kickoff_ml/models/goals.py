"""Goal-scoring models: independent Poisson and Dixon–Coles correction.

Both are Poisson GLMs over pre-match features predicting each side's goals;
Dixon–Coles adds the low-score dependence correction tau(x,y;rho) with rho
estimated by maximum likelihood on the training window.
"""

from __future__ import annotations

import math

import numpy as np
import polars as pl
from scipy.optimize import minimize_scalar
from sklearn.linear_model import PoissonRegressor
from sklearn.preprocessing import StandardScaler

MAX_GOALS = 10  # score matrix support 0..10 per team

GOAL_FEATURES_HOME = ["elo_diff_eff", "home_gf", "away_ga", "home_form", "importance"]
GOAL_FEATURES_AWAY = ["elo_diff_eff", "away_gf", "home_ga", "away_form", "importance"]


class PoissonGoalModel:
    """Two Poisson GLMs (home goals, away goals) on pre-match features."""

    def __init__(self, alpha: float = 1e-4) -> None:
        self.home = PoissonRegressor(alpha=alpha, max_iter=1000)
        self.away = PoissonRegressor(alpha=alpha, max_iter=1000)
        self.scaler_h = StandardScaler()
        self.scaler_a = StandardScaler()
        self.rho: float = 0.0  # Dixon–Coles correction; 0 = independent

    def _xh(self, df: pl.DataFrame) -> np.ndarray:
        return df.select(GOAL_FEATURES_HOME).to_numpy().astype(float)

    def _xa(self, df: pl.DataFrame) -> np.ndarray:
        x = df.select(GOAL_FEATURES_AWAY).to_numpy().astype(float)
        x[:, 0] = -x[:, 0]  # away perspective of elo difference
        return x

    def fit(self, df: pl.DataFrame) -> PoissonGoalModel:
        self.home.fit(self.scaler_h.fit_transform(self._xh(df)), df["home_score"].to_numpy())
        self.away.fit(self.scaler_a.fit_transform(self._xa(df)), df["away_score"].to_numpy())
        return self

    def expected_goals(self, df: pl.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        mu_h = self.home.predict(self.scaler_h.transform(self._xh(df)))
        mu_a = self.away.predict(self.scaler_a.transform(self._xa(df)))
        return np.clip(mu_h, 0.05, 6.0), np.clip(mu_a, 0.05, 6.0)

    # ---- Dixon–Coles ----------------------------------------------------

    @staticmethod
    def _tau(x: np.ndarray, y: np.ndarray, mu: np.ndarray, nu: np.ndarray, rho: float) -> np.ndarray:
        t = np.ones_like(mu)
        t = np.where((x == 0) & (y == 0), 1 - mu * nu * rho, t)
        t = np.where((x == 0) & (y == 1), 1 + mu * rho, t)
        t = np.where((x == 1) & (y == 0), 1 + nu * rho, t)
        t = np.where((x == 1) & (y == 1), 1 - rho, t)
        return np.clip(t, 1e-10, None)

    def fit_rho(self, df: pl.DataFrame) -> float:
        """MLE for the DC dependence parameter on the fitted means."""
        mu, nu = self.expected_goals(df)
        x = df["home_score"].to_numpy().astype(float)
        y = df["away_score"].to_numpy().astype(float)

        def nll(rho: float) -> float:
            return -np.log(self._tau(x, y, mu, nu, rho)).sum()

        res = minimize_scalar(nll, bounds=(-0.2, 0.2), method="bounded")
        self.rho = float(res.x)
        return self.rho

    # ---- score matrix & outcome probabilities ---------------------------

    def score_matrix(self, mu_h: float, mu_a: float) -> np.ndarray:
        """P(home=i, away=j) grid with DC correction, normalized."""
        i = np.arange(MAX_GOALS + 1)
        fact = np.array([math.factorial(k) for k in i], dtype=float)
        ph = np.exp(-mu_h) * mu_h**i / fact
        pa = np.exp(-mu_a) * mu_a**i / fact
        m = np.outer(ph, pa)
        if self.rho != 0.0:
            for x in (0, 1):
                for y in (0, 1):
                    m[x, y] *= float(
                        self._tau(
                            np.array([x], float), np.array([y], float),
                            np.array([mu_h]), np.array([mu_a]), self.rho,
                        )[0]
                    )
        return m / m.sum()

    def outcome_probs(self, df: pl.DataFrame) -> np.ndarray:
        """(n,3) array of [P(H), P(D), P(A)] from score matrices."""
        mu_h, mu_a = self.expected_goals(df)
        out = np.empty((len(mu_h), 3))
        for k in range(len(mu_h)):
            m = self.score_matrix(mu_h[k], mu_a[k])
            out[k, 0] = np.tril(m, -1).sum()  # home > away
            out[k, 1] = np.trace(m)
            out[k, 2] = np.triu(m, 1).sum()
        return out

    # alias so ensembles can treat this like any outcome model
    def predict_proba(self, df: pl.DataFrame) -> np.ndarray:
        return self.outcome_probs(df)


def matrix_summaries(m: np.ndarray) -> dict:
    """Derived quantities from a normalized score matrix."""
    idx = np.dstack(np.unravel_index(np.argsort(m, axis=None)[::-1], m.shape))[0]
    top = [
        {"home": int(i), "away": int(j), "prob": float(m[i, j])}
        for i, j in idx[:6]
    ]
    goals = np.add.outer(np.arange(m.shape[0]), np.arange(m.shape[1]))
    return {
        "top_scorelines": top,
        "clean_sheet_home": float(m[:, 0].sum()),
        "clean_sheet_away": float(m[0, :].sum()),
        "btts": float(m[1:, 1:].sum()),
        "over_2_5": float(m[goals > 2.5].sum()),
        "under_2_5": float(m[goals < 2.5].sum()),
    }
