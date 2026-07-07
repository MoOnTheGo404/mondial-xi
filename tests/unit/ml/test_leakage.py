"""Temporal-integrity tests: nothing from a match's own result, or from any
later match, may influence its pre-match feature vector."""

import polars as pl

from kickoff_ml.features.builder import build_feature_table

META_COLS = {"match_id", "home_score", "away_score", "outcome"}


def _feature_row(feats: pl.DataFrame, match_id: str) -> dict:
    row = feats.filter(pl.col("match_id") == match_id).to_dicts()[0]
    return {k: v for k, v in row.items() if k not in META_COLS}


def test_future_result_change_cannot_alter_earlier_features(core8: pl.DataFrame):
    df = core8.sort("date")
    mid_idx = df.height // 2
    earlier_id = df["match_id"][mid_idx - 1]
    base = build_feature_table(df)

    # Flip the result of a match played AFTER the earlier match.
    tampered = df.with_columns(
        pl.when(pl.arange(0, df.height) == df.height - 5)
        .then(pl.col("home_score") + 5)
        .otherwise(pl.col("home_score"))
        .alias("home_score")
    )
    tampered_feats = build_feature_table(tampered)
    assert _feature_row(base, earlier_id) == _feature_row(tampered_feats, earlier_id)


def test_own_result_change_cannot_alter_own_features(core8: pl.DataFrame):
    """The predicted match's own score must not appear in its features."""
    df = core8.sort("date")
    target_idx = df.height - 10
    target_id = df["match_id"][target_idx]
    base = build_feature_table(df)

    tampered = df.with_columns(
        pl.when(pl.arange(0, df.height) == target_idx)
        .then(pl.col("away_score") + 7)
        .otherwise(pl.col("away_score"))
        .alias("away_score")
    )
    tampered_feats = build_feature_table(tampered)
    assert _feature_row(base, target_id) == _feature_row(tampered_feats, target_id)


def test_features_depend_only_on_strict_past(core8: pl.DataFrame):
    """Truncating the dataset after match k leaves match k's features intact."""
    df = core8.sort("date")
    k = df.height - 3
    target_id = df["match_id"][k]
    full = build_feature_table(df)
    truncated = build_feature_table(df.head(k + 1))
    assert _feature_row(full, target_id) == _feature_row(truncated, target_id)


def test_all_probabilities_normalized(core8: pl.DataFrame):
    from kickoff_ml.models.outcome import EloLogisticModel

    feats = build_feature_table(core8)
    model = EloLogisticModel().fit(feats)
    p = model.predict_proba(feats)
    assert ((p.sum(axis=1) - 1.0) ** 2 < 1e-12).all()
    assert (p >= 0).all() and (p <= 1).all()
