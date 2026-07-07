"""Provider interfaces and capability model.

The application composes small, swappable providers. Each declares its
capabilities and health so the UI can honestly show which features are
live, which are dataset-backed, and which are unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass
class ProviderStatus:
    name: str
    kind: str                      # "dataset" | "api" | "computed"
    available: bool
    capabilities: list[str]
    license_note: str
    last_sync: str | None = None   # ISO timestamp of the data's retrieval
    detail: str | None = None      # e.g. "credential not configured"
    attribution: str | None = None


@dataclass
class Fixture:
    fixture_id: str
    date: str
    home_id: str
    away_id: str
    tournament: str
    city: str | None = None
    country: str | None = None
    neutral: bool = True
    status: str = "scheduled"      # scheduled | finished
    home_score: int | None = None
    away_score: int | None = None
    source: str = "dataset"
    retrieved_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class CurrentFixtureProvider(Protocol):
    def upcoming_fixtures(self) -> list[Fixture]: ...
    def status(self) -> ProviderStatus: ...


@runtime_checkable
class WeatherProvider(Protocol):
    def forecast_for(self, city: str, iso_date: str) -> dict | None: ...
    def status(self) -> ProviderStatus: ...


def utcnow_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
