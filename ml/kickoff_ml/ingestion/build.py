"""Build processed, validated Parquet datasets from immutable raw CSVs.

Outputs (data/processed/):
- matches.parquet            completed matches, chronological, canonical IDs
- upcoming.parquet           scheduled fixtures (null scores) from the source
- goalscorers.parquet        goal events with canonical team & player IDs
- teams.parquet              canonical team registry observed in the data
Also writes data/manifests/data_quality.json (validation & coverage report).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime

import polars as pl
import structlog

from kickoff_ml.config import MANIFEST_DIR, PROCESSED_DIR, RAW_DIR
from kickoff_ml.entities.teams import build_team, slugify

log = structlog.get_logger()

RESULT_SCHEMA = {
    "date": pl.Utf8, "home_team": pl.Utf8, "away_team": pl.Utf8,
    "home_score": pl.Utf8, "away_score": pl.Utf8, "tournament": pl.Utf8,
    "city": pl.Utf8, "country": pl.Utf8, "neutral": pl.Utf8,
}

# Tournament importance tiers (feature + UI grouping).
TIER_WORLD = {"FIFA World Cup"}
TIER_CONTINENTAL = {
    "AFC Asian Cup", "African Cup of Nations", "Copa América", "Copa America",
    "UEFA Euro", "Gold Cup", "CONCACAF Championship", "Oceania Nations Cup",
    "Confederations Cup", "CONCACAF Nations League", "UEFA Nations League",
    "African Nations Championship",
}


def competition_tier(t: str) -> str:
    if t in TIER_WORLD:
        return "world_cup"
    if "qualification" in t.lower():
        return "qualifier"
    if t in TIER_CONTINENTAL or "Euro" in t or "Asian Cup" in t:
        return "continental"
    if t == "Friendly":
        return "friendly"
    return "other"


def _canonical_cols(df: pl.DataFrame) -> pl.DataFrame:
    teams = sorted(set(df["home_team"].to_list()) | set(df["away_team"].to_list()))
    registry = {name: build_team(name) for name in teams}
    id_map = {n: t.team_id for n, t in registry.items()}
    return df.with_columns(
        pl.col("home_team").replace_strict(id_map).alias("home_id"),
        pl.col("away_team").replace_strict(id_map).alias("away_id"),
        pl.col("tournament").map_elements(competition_tier, return_dtype=pl.Utf8).alias("tier"),
    )


def _overlay_wikipedia(raw: pl.DataFrame) -> pl.DataFrame:
    """Fill scores the core (martj42) hasn't published yet from the Wikipedia
    overlay (data/raw/wikipedia_results.csv). Only *missing* core scores are
    filled — recorded results are never overwritten — and matches absent from
    the core in either orientation are appended. No-op if the overlay is absent
    (graceful degradation)."""
    path = RAW_DIR / "wikipedia_results.csv"
    if not path.exists():
        return raw
    wiki = pl.read_csv(path, schema_overrides=RESULT_SCHEMA)
    if wiki.is_empty():
        return raw

    keys = ["date", "home_team", "away_team"]
    missing = pl.col("home_score").is_null() | pl.col("home_score").is_in(["NA", ""])
    w = wiki.select([*keys, "home_score", "away_score"]).rename(
        {"home_score": "_whs", "away_score": "_was"}
    )
    joined = raw.join(w, on=keys, how="left")
    filled = joined.filter(missing & pl.col("_whs").is_not_null()).height
    merged = joined.with_columns(
        pl.when(missing & pl.col("_whs").is_not_null())
        .then(pl.col("_whs"))
        .otherwise(pl.col("home_score"))
        .alias("home_score"),
        pl.when(missing & pl.col("_was").is_not_null())
        .then(pl.col("_was"))
        .otherwise(pl.col("away_score"))
        .alias("away_score"),
    ).drop(["_whs", "_was"])

    core_pairs = {
        (d, frozenset((h, a)))
        for d, h, a in zip(raw["date"], raw["home_team"], raw["away_team"], strict=True)
    }
    extra = [
        r
        for r in wiki.iter_rows(named=True)
        if (r["date"], frozenset((r["home_team"], r["away_team"]))) not in core_pairs
    ]
    if extra:
        merged = pl.concat(
            [merged, pl.DataFrame(extra, schema_overrides=RESULT_SCHEMA).select(merged.columns)],
            how="vertical",
        )
    log.info("wikipedia overlay applied", filled_scores=filled, appended=len(extra))
    return merged


def build_all() -> dict:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {"generated_at": datetime.now(UTC).isoformat(), "checks": []}

    raw = pl.read_csv(RAW_DIR / "results.csv", schema_overrides=RESULT_SCHEMA)
    raw = _overlay_wikipedia(raw)
    n_raw = raw.height

    # --- validation -------------------------------------------------------
    bad_date = raw.filter(~pl.col("date").str.contains(r"^\d{4}-\d{2}-\d{2}$"))
    raw = raw.filter(pl.col("date").str.contains(r"^\d{4}-\d{2}-\d{2}$"))

    dupes = raw.filter(raw.select(["date", "home_team", "away_team"]).is_duplicated())
    raw = raw.unique(subset=["date", "home_team", "away_team"], keep="first", maintain_order=True)

    raw = raw.with_columns(
        pl.col("home_score").cast(pl.Int32, strict=False),
        pl.col("away_score").cast(pl.Int32, strict=False),
        (pl.col("neutral").str.to_lowercase() == "true").alias("neutral"),
        pl.col("date").str.to_date(),
    )
    self_play = raw.filter(pl.col("home_team") == pl.col("away_team"))
    raw = raw.filter(pl.col("home_team") != pl.col("away_team"))
    neg = raw.filter((pl.col("home_score") < 0) | (pl.col("away_score") < 0))
    raw = raw.filter(
        ((pl.col("home_score") >= 0) & (pl.col("away_score") >= 0))
        | pl.col("home_score").is_null()
    )
    report["checks"] += [
        {"check": "bad_date_rows_dropped", "count": bad_date.height},
        {"check": "duplicate_rows_dropped", "count": dupes.height},
        {"check": "self_play_rows_dropped", "count": self_play.height},
        {"check": "negative_score_rows_dropped", "count": neg.height},
    ]

    raw = _canonical_cols(raw).sort(["date", "home_id", "away_id"])
    raw = raw.with_columns(
        (
            pl.col("date").dt.strftime("%Y%m%d")
            + "-" + pl.col("home_id") + "-" + pl.col("away_id")
        ).alias("match_id"),
        pl.col("home_team").alias("home_team_name"),
        pl.col("away_team").alias("away_team_name"),
    ).drop(["home_team", "away_team"])

    # --- shootouts --------------------------------------------------------
    so = pl.read_csv(RAW_DIR / "shootouts.csv", schema_overrides={"date": pl.Utf8})
    so = so.with_columns(pl.col("date").str.to_date())
    so = _so = so.rename({"winner": "shootout_winner_name"})
    so = so.with_columns(
        pl.col("home_team").map_elements(lambda n: build_team(n).team_id, return_dtype=pl.Utf8).alias("home_id"),
        pl.col("away_team").map_elements(lambda n: build_team(n).team_id, return_dtype=pl.Utf8).alias("away_id"),
        pl.col("shootout_winner_name").map_elements(lambda n: build_team(n).team_id, return_dtype=pl.Utf8).alias("shootout_winner_id"),
    ).select(["date", "home_id", "away_id", "shootout_winner_id"])
    raw = raw.join(so, on=["date", "home_id", "away_id"], how="left")

    completed = raw.filter(pl.col("home_score").is_not_null())
    upcoming = raw.filter(pl.col("home_score").is_null())

    completed.write_parquet(PROCESSED_DIR / "matches.parquet")
    upcoming.write_parquet(PROCESSED_DIR / "upcoming.parquet")

    # --- goalscorers ------------------------------------------------------
    gs = pl.read_csv(
        RAW_DIR / "goalscorers.csv",
        schema_overrides={
            "date": pl.Utf8, "minute": pl.Utf8,
            "own_goal": pl.Utf8, "penalty": pl.Utf8,
        },
    )
    n_gs_raw = gs.height
    gs = gs.filter(pl.col("scorer").is_not_null()).with_columns(
        pl.col("date").str.to_date(),
        pl.col("minute").cast(pl.Float64, strict=False).alias("minute"),
        (pl.col("own_goal").str.to_lowercase() == "true").alias("own_goal"),
        (pl.col("penalty").str.to_lowercase() == "true").alias("penalty"),
    )
    gs = gs.with_columns(
        pl.col("home_team").map_elements(lambda n: build_team(n).team_id, return_dtype=pl.Utf8).alias("home_id"),
        pl.col("away_team").map_elements(lambda n: build_team(n).team_id, return_dtype=pl.Utf8).alias("away_id"),
        pl.col("team").map_elements(lambda n: build_team(n).team_id, return_dtype=pl.Utf8).alias("team_id"),
        pl.col("scorer").map_elements(slugify, return_dtype=pl.Utf8).alias("player_slug"),
    )
    gs = gs.with_columns(
        (
            pl.col("date").dt.strftime("%Y%m%d")
            + "-" + pl.col("home_id") + "-" + pl.col("away_id")
        ).alias("match_id"),
        (pl.col("team_id") + "/" + pl.col("player_slug")).alias("player_id"),
    )
    gs.write_parquet(PROCESSED_DIR / "goalscorers.parquet")

    # --- team registry ----------------------------------------------------
    names = sorted(
        set(pl.concat([completed, upcoming])["home_team_name"].to_list())
        | set(pl.concat([completed, upcoming])["away_team_name"].to_list())
    )
    teams = {}
    for n in names:
        t = build_team(n)
        teams[t.team_id] = t
    teams_df = pl.DataFrame(
        [
            {
                "team_id": t.team_id, "name": t.name, "flag_code": t.flag_code,
                "confederation": t.confederation, "is_historical": t.is_historical,
            }
            for t in sorted(teams.values(), key=lambda x: x.team_id)
        ]
    )
    teams_df.write_parquet(PROCESSED_DIR / "teams.parquet")

    # --- quality / coverage report ---------------------------------------
    report.update(
        {
            "raw_rows": n_raw,
            "completed_matches": completed.height,
            "upcoming_fixtures": upcoming.height,
            "goal_events_raw": n_gs_raw,
            "goal_events_kept": gs.height,
            "teams": teams_df.height,
            "teams_with_flag": teams_df.filter(pl.col("flag_code").is_not_null()).height,
            "date_min": str(completed["date"].min()),
            "date_max": str(completed["date"].max()),
            "missingness": {
                "goalscorer_minute_null_pct": round(
                    100 * gs["minute"].null_count() / max(gs.height, 1), 2
                ),
                "matches_with_goal_detail_pct": round(
                    100 * gs["match_id"].n_unique()
                    / max(completed.filter(
                        (pl.col("home_score") + pl.col("away_score")) > 0
                    ).height, 1),
                    2,
                ),
            },
            "shootouts_joined": completed.filter(
                pl.col("shootout_winner_id").is_not_null()
            ).height,
        }
    )
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    (MANIFEST_DIR / "data_quality.json").write_text(json.dumps(report, indent=2))
    log.info("build complete", **{k: v for k, v in report.items() if isinstance(v, int)})
    return report


if __name__ == "__main__":
    build_all()
