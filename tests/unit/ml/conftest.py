import polars as pl
import pytest

from kickoff_ml.config import FIXTURES_DIR


@pytest.fixture(scope="session")
def core8() -> pl.DataFrame:
    """354 real matches between 8 major teams since 1990 (committed fixture)."""
    df = pl.read_csv(
        FIXTURES_DIR / "matches_core8.csv",
        schema_overrides={"home_score": pl.Int32, "away_score": pl.Int32},
    )
    return df.with_columns(pl.col("date").str.to_date())


@pytest.fixture(scope="session")
def wc2022() -> pl.DataFrame:
    df = pl.read_csv(
        FIXTURES_DIR / "matches_wc2022.csv",
        schema_overrides={"home_score": pl.Int32, "away_score": pl.Int32},
    )
    return df.with_columns(pl.col("date").str.to_date())
