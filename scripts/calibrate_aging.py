"""Measure the 2030-outlook aging parameters from our own data. Writes
ml/artifacts/aging_calibration.json (loaded by kickoff_ml.simulation.aging).

Everything here is measured, never invented:
- scoring-survival curve S(age->age+4): fraction of players who scored near
  age a and were still scoring 4 years later, from goalscorer events joined
  to Wikidata birthdates (observable cohorts only);
- 4-year team-Elo dynamics: OLS of Elo(t+4) on Elo(t) around the mean ->
  persistence beta and residual std (the irreducible 4-year uncertainty that
  stands in for unknowable future breakouts/declines).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import numpy as np
import polars as pl

from kickoff_ml.config import ARTIFACTS_DIR, PROCESSED_DIR

HORIZON = 4  # years to the 2030 finals from the data cutoff era


def elo_dynamics() -> dict:
    eh = pl.read_parquet(ARTIFACTS_DIR / "elo_history.parquet")
    long = pl.concat(
        [
            eh.select(pl.col("date").dt.year().alias("year"),
                      pl.col("home_id").alias("team"), pl.col("home_elo").alias("elo")),
            eh.select(pl.col("date").dt.year().alias("year"),
                      pl.col("away_id").alias("team"), pl.col("away_elo").alias("elo")),
        ]
    )
    yearly = long.group_by(["team", "year"]).agg(pl.col("elo").mean()).filter(pl.col("year") >= 1960)
    now = yearly.rename({"elo": "e0"})
    fut = yearly.rename({"elo": "eH", "year": "yearH"}).with_columns(
        (pl.col("yearH") - HORIZON).alias("year")
    )
    pairs = now.join(fut, on=["team", "year"])
    x, y = pairs["e0"].to_numpy(), pairs["eH"].to_numpy()
    m = float(x.mean())
    beta = float(np.sum((x - m) * (y - m)) / np.sum((x - m) ** 2))
    resid = (y - m) - beta * (x - m)
    return {
        "mean_elo": round(m, 1),
        "persistence_beta": round(beta, 4),
        "residual_std": round(float(resid.std()), 1),
        "n_pairs": len(x),
    }


def survival_curve() -> dict:
    p = pl.read_parquet(PROCESSED_DIR / "players.parquet").filter(pl.col("dob").is_not_null())
    gs = pl.read_parquet(PROCESSED_DIR / "goalscorers.parquet")
    cutoff_year = int(str(pl.read_parquet(PROCESSED_DIR / "matches.parquet")["date"].max())[:4])
    gp = gs.join(p.select(["player_id", "dob"]), on="player_id", how="inner").with_columns(
        ((pl.col("date") - pl.col("dob").str.to_date()).dt.total_days() / 365.25).alias("age")
    )
    ages = gp.group_by("player_id").agg(
        pl.col("age").min().alias("a_min"),
        pl.col("age").max().alias("a_max"),
        pl.col("dob").first(),
    )
    knots: dict[str, float] = {}
    for a in range(18, 40):
        obs = ages.filter(
            (pl.col("a_min") <= a)
            & (pl.col("a_max") >= a - 1)
            & (pl.col("dob").str.to_date().dt.year() <= cutoff_year - (a + HORIZON) - 1)
        )
        if obs.height < 40:
            continue
        still = obs.filter(pl.col("a_max") >= a + HORIZON)
        knots[str(a)] = round(still.height / obs.height, 4)
    return knots


def run() -> dict:
    calib = {
        "generated_at": datetime.now(UTC).isoformat(),
        "horizon_years": HORIZON,
        "elo_dynamics": elo_dynamics(),
        "scoring_survival": survival_curve(),
        "notes": (
            "beta~1 => team Elo is a 4-year random walk (no mean reversion); "
            "residual_std is the measured 4-year uncertainty used as per-team "
            "noise (stands in for unknowable future breakouts/declines). "
            "Survival is P(still scoring at age+4 | scoring at age) from our "
            "goalscorer log + Wikidata DOBs; it is a floor (partial coverage)."
        ),
    }
    (ARTIFACTS_DIR / "aging_calibration.json").write_text(json.dumps(calib, indent=2))
    return calib


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
