from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, UniqueConstraint, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from kickoff_api.settings import settings


class Base(DeclarativeBase):
    pass


class PredictionSnapshot(Base):
    """Immutable record of a genuine prospective forecast.

    A snapshot is never updated after kickoff; re-forecasts before kickoff
    are inserted as new rows with a distinct content hash and version label.
    Post-match scoring fills the result columns without touching the
    original payload.
    """

    __tablename__ = "prediction_snapshots"
    __table_args__ = (UniqueConstraint("fixture_id", "content_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fixture_id: Mapped[str] = mapped_column(String(120), index=True)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC)
    )
    kickoff_date: Mapped[str] = mapped_column(String(10))
    home_id: Mapped[str] = mapped_column(String(80))
    away_id: Mapped[str] = mapped_column(String(80))
    model_version: Mapped[str] = mapped_column(String(40))
    data_cutoff: Mapped[str] = mapped_column(String(10))
    lineup_status: Mapped[str] = mapped_column(String(30), default="none_available")
    version_label: Mapped[str] = mapped_column(String(40), default="pre_tournament")
    payload: Mapped[dict] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))

    # post-match scoring (filled once, later)
    result_home: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_away: Mapped[int | None] = mapped_column(Integer, nullable=True)
    outcome: Mapped[str | None] = mapped_column(String(1), nullable=True)
    p_outcome: Mapped[float | None] = mapped_column(Float, nullable=True)
    rps: Mapped[float | None] = mapped_column(Float, nullable=True)
    brier: Mapped[float | None] = mapped_column(Float, nullable=True)
    log_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    top_pick_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    scored_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


engine = create_engine(settings.database_url, connect_args=(
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
))
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()
