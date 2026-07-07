"""Prediction snapshot service — the auditable track record.

Rules enforced here (see docs/methodology.md#track-record):
- Snapshots are only created for fixtures that are genuinely in the future
  relative to the data cutoff (never retroactively).
- A snapshot row is immutable; a changed forecast before kickoff inserts a
  NEW row (distinct content hash + version label).
- Scoring after the match fills result columns only; the original payload
  is untouched.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import polars as pl
import structlog
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from kickoff_api.db import PredictionSnapshot, get_session

log = structlog.get_logger()


def _content_hash(payload: dict) -> str:
    canon = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canon.encode()).hexdigest()


def snapshot_upcoming(state, version_label: str = "dataset_snapshot") -> int:
    """Create snapshots for every upcoming fixture (idempotent by content)."""
    created = 0
    with get_session() as session:
        for fx in state.local_provider.upcoming_fixtures():
            pred = state.engine.predict(
                fx.home_id, fx.away_id, neutral=fx.neutral, importance=4
            )
            payload = {
                "fixture": {
                    "fixture_id": fx.fixture_id, "date": fx.date,
                    "home_id": fx.home_id, "away_id": fx.away_id,
                    "tournament": fx.tournament, "city": fx.city,
                    "neutral": fx.neutral, "source": fx.source,
                    "provider_retrieved_at": fx.retrieved_at,
                },
                "prediction": pred,
            }
            row = PredictionSnapshot(
                fixture_id=fx.fixture_id,
                kickoff_date=fx.date,
                home_id=fx.home_id,
                away_id=fx.away_id,
                model_version=pred["model_version"],
                data_cutoff=pred["data_cutoff"],
                lineup_status="none_available",
                version_label=version_label,
                payload=payload,
                content_hash=_content_hash(payload),
            )
            session.add(row)
            try:
                session.commit()
                created += 1
                log.info("snapshot created", fixture=fx.fixture_id)
            except IntegrityError:
                session.rollback()  # identical forecast already recorded
    return created


def score_snapshots(state) -> int:
    """Attach results & scores to snapshots whose fixtures have completed."""
    scored = 0
    matches = state.matches
    with get_session() as session:
        rows = session.scalars(
            select(PredictionSnapshot).where(PredictionSnapshot.scored_at.is_(None))
        ).all()
        for snap in rows:
            m = matches.filter(pl.col("match_id") == snap.fixture_id)
            if m.is_empty():
                continue
            r = m.to_dicts()[0]
            hs, as_ = r["home_score"], r["away_score"]
            outcome = "H" if hs > as_ else ("A" if hs < as_ else "D")
            p = snap.payload["prediction"]["probabilities"]
            probs = [p["home"], p["draw"], p["away"]]
            onehot = {"H": [1, 0, 0], "D": [0, 1, 0], "A": [0, 0, 1]}[outcome]
            cum_p = [probs[0], probs[0] + probs[1]]
            cum_o = [onehot[0], onehot[0] + onehot[1]]
            snap.result_home, snap.result_away = hs, as_
            snap.outcome = outcome
            snap.p_outcome = probs[{"H": 0, "D": 1, "A": 2}[outcome]]
            snap.rps = sum((cp - co) ** 2 for cp, co in zip(cum_p, cum_o, strict=True)) / 2
            snap.brier = sum((pr - o) ** 2 for pr, o in zip(probs, onehot, strict=True))
            import math

            snap.log_loss = -math.log(max(snap.p_outcome, 1e-12))
            snap.top_pick_correct = max(range(3), key=lambda i: probs[i]) == {
                "H": 0, "D": 1, "A": 2
            }[outcome]
            snap.scored_at = datetime.now(UTC)
            session.commit()
            scored += 1
            log.info("snapshot scored", fixture=snap.fixture_id, outcome=outcome)
    return scored


def list_snapshots(limit: int = 200) -> list[dict]:
    with get_session() as session:
        rows = session.scalars(
            select(PredictionSnapshot).order_by(
                PredictionSnapshot.kickoff_date.desc(),
                PredictionSnapshot.generated_at.desc(),
            ).limit(limit)
        ).all()
        return [
            {
                "id": s.id,
                "fixture_id": s.fixture_id,
                "generated_at": s.generated_at.isoformat(),
                "kickoff_date": s.kickoff_date,
                "home_id": s.home_id,
                "away_id": s.away_id,
                "model_version": s.model_version,
                "data_cutoff": s.data_cutoff,
                "lineup_status": s.lineup_status,
                "version_label": s.version_label,
                "content_hash": s.content_hash,
                "probabilities": s.payload["prediction"]["probabilities"],
                "expected_goals": s.payload["prediction"]["expected_goals"],
                "result": (
                    {"home": s.result_home, "away": s.result_away, "outcome": s.outcome}
                    if s.scored_at
                    else None
                ),
                "scores": (
                    {
                        "p_outcome": s.p_outcome, "rps": s.rps, "brier": s.brier,
                        "log_loss": s.log_loss, "top_pick_correct": s.top_pick_correct,
                    }
                    if s.scored_at
                    else None
                ),
            }
            for s in rows
        ]
