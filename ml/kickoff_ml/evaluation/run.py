"""Chronological evaluation pipeline.

Protocol (documented in docs/methodology.md):
- Features are built in a single forward pass (state accumulates from 1872).
- Model fitting window:      1980-01-01 .. 2018-12-31   ("train")
- Validation (selection +
  calibration + Elo tuning): 2019-01-01 .. 2022-12-31   ("validation")
- Untouched test:            2023-01-01 .. data cutoff  ("test")
- The champion is chosen on validation log loss BEFORE test is evaluated.
- The serving artifact is byte-identical to the evaluated pipeline; only
  rating/form state advances to the data cutoff.

Outputs -> ml/artifacts/: metrics.json, model_comparison.json,
calibration.json, test_predictions.parquet, elo_tuning.json, model_card.json,
prediction_bundle.joblib, elo_history.parquet, current_ratings.json
"""

from __future__ import annotations

import json
import subprocess
from datetime import UTC, datetime

import joblib
import numpy as np
import polars as pl
import structlog

from kickoff_ml.config import ARTIFACTS_DIR, MANIFEST_DIR, PROCESSED_DIR, TRAIN_END, VALIDATION_END
from kickoff_ml.evaluation import metrics as M
from kickoff_ml.features.builder import FeatureBuilder, build_feature_table
from kickoff_ml.models.goals import PoissonGoalModel
from kickoff_ml.models.outcome import (
    EloLogisticModel,
    FrequencyBaseline,
    GeometricMeanEnsemble,
    GradientBoostedModel,
)
from kickoff_ml.ratings.elo import EloConfig

log = structlog.get_logger()

FIT_START = "1980-01-01"
MODEL_VERSION = f"{datetime.now(UTC):%Y.%m.%d}-1"


def _split(feats: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
    train = feats.filter(
        (pl.col("date") >= pl.lit(FIT_START).str.to_date())
        & (pl.col("date") <= pl.lit(TRAIN_END).str.to_date())
    )
    val = feats.filter(
        (pl.col("date") > pl.lit(TRAIN_END).str.to_date())
        & (pl.col("date") <= pl.lit(VALIDATION_END).str.to_date())
    )
    test = feats.filter(pl.col("date") > pl.lit(VALIDATION_END).str.to_date())
    return train, val, test


def tune_elo(matches: pl.DataFrame) -> tuple[EloConfig, list[dict]]:
    """Grid-search Elo params by validation log loss of the Elo-only model."""
    results = []
    best: tuple[float, EloConfig] | None = None
    for home_adv in (60.0, 80.0, 100.0):
        for k_scale in (0.75, 1.0, 1.25):
            cfg = EloConfig(home_advantage=home_adv, k_scale=k_scale)
            feats = build_feature_table(matches, cfg)
            train, val, _ = _split(feats)
            model = EloLogisticModel().fit(train)
            ll = M.log_loss(val["outcome"].to_numpy(), model.predict_proba(val))
            results.append({"home_advantage": home_adv, "k_scale": k_scale, "val_log_loss": round(ll, 5)})
            log.info("elo grid point", home_adv=home_adv, k_scale=k_scale, val_ll=round(ll, 5))
            if best is None or ll < best[0]:
                best = (ll, cfg)
    assert best is not None
    return best[1], results


def evaluate() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    matches = pl.read_parquet(PROCESSED_DIR / "matches.parquet")
    cutoff = str(matches["date"].max())
    log.info("loaded matches", n=matches.height, cutoff=cutoff)

    elo_cfg, elo_grid = tune_elo(matches)
    (ARTIFACTS_DIR / "elo_tuning.json").write_text(json.dumps(
        {"grid": elo_grid, "selected": {"home_advantage": elo_cfg.home_advantage, "k_scale": elo_cfg.k_scale}},
        indent=2,
    ))

    feats = build_feature_table(matches, elo_cfg)
    train, val, test = _split(feats)
    log.info("split", train=train.height, val=val.height, test=test.height)

    # ---- fit candidates on train ----------------------------------------
    freq = FrequencyBaseline().fit(train)
    elo_model = EloLogisticModel().fit(train)
    poisson = PoissonGoalModel().fit(train)
    dc = PoissonGoalModel().fit(train)
    dc.fit_rho(train)
    gbm_raw = GradientBoostedModel().fit(train)  # uncalibrated reference

    # Champion is selected on the FULL validation window. Every candidate is
    # scored there strictly out-of-sample: the base models (elo/poisson/DC/
    # GBM) train only on `train`, and the geometric ensemble is parameter-free.
    # The one model that would otherwise touch validation — the GBM's isotonic
    # calibration — is made honest with 2-fold out-of-fold calibration, so no
    # candidate gets an in-sample edge. Test stays sealed until after selection.
    val_s = val.sort("date")
    half = val_s.height // 2
    va, vb = val_s.head(half), val_s.tail(val_s.height - half)

    gbm = GradientBoostedModel().fit(train)  # serving: calibrated on full val
    gbm.calibrate(val)

    # out-of-fold GBM calibration for a bias-free validation comparison
    g_a = GradientBoostedModel().fit(train)
    g_a.calibrate(va)
    g_b = GradientBoostedModel().fit(train)
    g_b.calibrate(vb)
    gbm_oof_val = np.vstack([g_b.predict_proba(va), g_a.predict_proba(vb)])

    ensemble = GeometricMeanEnsemble(
        {"elo_logistic": elo_model, "dixon_coles": dc}
    )

    candidates = {
        "frequency_baseline": lambda df: freq.predict_proba(df),
        "elo_logistic": lambda df: elo_model.predict_proba(df),
        "poisson": lambda df: poisson.outcome_probs(df),
        "dixon_coles": lambda df: dc.outcome_probs(df),
        "gbm_uncalibrated": lambda df: gbm_raw.predict_proba(df),
        "gbm_calibrated": lambda df: gbm.predict_proba(df),
        "geometric_ensemble": lambda df: ensemble.predict_proba(df),
    }

    # ---- validation comparison & champion selection (full validation) -----
    comparison: dict[str, dict] = {}
    y_val = val_s["outcome"].to_numpy()
    for name, fn in candidates.items():
        # gbm_calibrated uses its OOF validation probs so it isn't in-sample
        p_val = gbm_oof_val if name == "gbm_calibrated" else fn(val_s)
        comparison[name] = {"validation": M.all_metrics(y_val, p_val)}
    champion = min(
        (n for n in candidates if n != "frequency_baseline"),
        key=lambda n: comparison[n]["validation"]["log_loss"],
    )
    log.info("champion selected on full validation", champion=champion)

    # ---- single test evaluation ------------------------------------------
    y_test = test["outcome"].to_numpy()
    for name, fn in candidates.items():
        comparison[name]["test"] = M.all_metrics(y_test, fn(test))

    champ_fn = candidates[champion]
    p_test = champ_fn(test)

    # slices: by year / tier / confederation, favorites vs close
    teams = pl.read_parquet(PROCESSED_DIR / "teams.parquet")
    conf_map = dict(zip(teams["team_id"].to_list(), teams["confederation"].to_list(), strict=True))
    test_meta = test.with_columns(
        pl.col("date").dt.year().alias("year"),
        pl.col("home_id").replace_strict(conf_map, default="OTHER").alias("home_conf"),
    )
    by_year = []
    for yr in sorted(test_meta["year"].unique().to_list()):
        mask = (test_meta["year"] == yr).to_numpy()
        by_year.append({"year": int(yr), **M.all_metrics(y_test[mask], p_test[mask])})
    by_tier = []
    for tier in test_meta["tier"].unique().to_list():
        mask = (test_meta["tier"] == tier).to_numpy()
        if mask.sum() >= 30:
            by_tier.append({"tier": tier, **M.all_metrics(y_test[mask], p_test[mask])})
    by_conf = []
    for conf in sorted(set(conf_map.values())):
        mask = (test_meta["home_conf"] == conf).to_numpy()
        if mask.sum() >= 50:
            by_conf.append({"confederation": conf, **M.all_metrics(y_test[mask], p_test[mask])})
    conf_gap = p_test.max(axis=1)
    fav_mask = conf_gap >= np.median(conf_gap)
    favorites_vs_close = [
        {"segment": "clear_favorite", **M.all_metrics(y_test[fav_mask], p_test[fav_mask])},
        {"segment": "close_match", **M.all_metrics(y_test[~fav_mask], p_test[~fav_mask])},
    ]

    metrics_doc = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model_version": MODEL_VERSION,
        "data_cutoff": cutoff,
        "protocol": {
            "fit_window": [FIT_START, TRAIN_END],
            "validation_window": ["2019-01-01", VALIDATION_END],
            "test_window": ["2023-01-01", cutoff],
            "split_type": "chronological",
            "champion_selected_on": (
                "log loss on the full validation window, every candidate scored "
                "strictly out-of-sample (base models train on 1980–2018; the "
                "geometric ensemble is parameter-free; GBM calibration is made "
                "honest with 2-fold out-of-fold isotonic)"
            ),
        },
        "champion": champion,
        "champion_test": M.all_metrics(y_test, p_test),
        "champion_validation": comparison[champion]["validation"],
        "confidence_buckets": M.confidence_buckets(y_test, p_test),
        "by_year": by_year,
        "by_tier": by_tier,
        "by_confederation": by_conf,
        "favorites_vs_close": favorites_vs_close,
        "counts": {"train": train.height, "validation": val_s.height, "test": test.height},
    }
    (ARTIFACTS_DIR / "metrics.json").write_text(json.dumps(metrics_doc, indent=2))
    (ARTIFACTS_DIR / "model_comparison.json").write_text(json.dumps(comparison, indent=2))
    (ARTIFACTS_DIR / "calibration.json").write_text(json.dumps(
        {
            "champion": champion,
            "test_reliability": M.reliability_bins(y_test, p_test),
            "uncalibrated_gbm_test_reliability": M.reliability_bins(y_test, candidates["gbm_uncalibrated"](test)),
        },
        indent=2,
    ))

    # test predictions for the archive's "backtest" section
    test.select(
        ["match_id", "date", "home_id", "away_id", "tier", "outcome", "home_score", "away_score"]
    ).with_columns(
        pl.Series("p_home", p_test[:, 0]),
        pl.Series("p_draw", p_test[:, 1]),
        pl.Series("p_away", p_test[:, 2]),
    ).write_parquet(ARTIFACTS_DIR / "test_predictions.parquet")

    # ---- Elo history (for team pages) ------------------------------------
    feats.select(["match_id", "date", "home_id", "away_id", "home_elo", "away_elo"]).write_parquet(
        ARTIFACTS_DIR / "elo_history.parquet"
    )

    # ---- serving bundle ---------------------------------------------------
    final_builder = FeatureBuilder(elo_cfg)
    for m in matches.sort("date").iter_rows(named=True):
        final_builder.update(
            m["home_id"], m["away_id"], m["home_score"], m["away_score"],
            m["neutral"], m["tier"], m["date"],
        )
    ratings_now = {
        t: {
            "elo": round(final_builder.elo.rating(t), 1),
            "matches": final_builder.elo.matches_played(t),
        }
        for t in final_builder.elo.ratings
    }
    (ARTIFACTS_DIR / "current_ratings.json").write_text(json.dumps(
        {"as_of": cutoff, "elo_config": {"home_advantage": elo_cfg.home_advantage, "k_scale": elo_cfg.k_scale}, "ratings": ratings_now},
        indent=2,
    ))

    bundle = {
        "model_version": MODEL_VERSION,
        "data_cutoff": cutoff,
        "champion": champion,
        "elo_config": elo_cfg,
        "builder": final_builder,
        "models": {
            "elo_logistic": elo_model, "poisson": poisson, "dixon_coles": dc,
            "gbm_calibrated": gbm, "geometric_ensemble": ensemble,
        },
        "created_at": datetime.now(UTC).isoformat(),
    }
    joblib.dump(bundle, ARTIFACTS_DIR / "prediction_bundle.joblib", compress=3)

    # ---- model card --------------------------------------------------------
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=False
        ).stdout.strip()
    except OSError:
        commit = "unknown"
    quality = json.loads((MANIFEST_DIR / "data_quality.json").read_text())
    card = {
        "model_version": MODEL_VERSION,
        "git_commit": commit,
        "champion": champion,
        "candidates": list(candidates.keys()),
        "data": {
            "source": "martj42/international_results (CC0)",
            "completed_matches": quality["completed_matches"],
            "date_range": [quality["date_min"], quality["date_max"]],
        },
        "features": "pre-match only; single forward pass; leakage tests in tests/unit/ml",
        "calibration": "per-class isotonic fitted on validation window only",
        "intended_use": "editorial forecasting & simulation; not betting advice",
        "limitations": [
            "team-level model; no lineup/injury inputs (no licensed historical source)",
            "friendlies carry lower Elo weight but add label noise",
            "small-sample teams rely on rating priors",
        ],
    }
    (ARTIFACTS_DIR / "model_card.json").write_text(json.dumps(card, indent=2))
    log.info("evaluation complete", champion=champion, **metrics_doc["champion_test"])


if __name__ == "__main__":
    evaluate()
