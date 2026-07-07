"""Optional football-data.org adapter (free-tier credential).

Enabled only when FOOTBALL_DATA_API_KEY is set. Free tier includes the FIFA
World Cup; lineups/squads require a paid plan, so this adapter only claims
the capabilities the free tier actually provides. Terms require attribution
and prohibit bulk redistribution — we display, we do not re-serve raw data.

Rate limiting: free tier allows 10 requests/minute; we throttle, retry on
429 with the advertised wait, and cache responses for CACHE_TTL seconds.
"""

from __future__ import annotations

import os
import time
from typing import Any

import httpx
import structlog

from kickoff_ml.entities.teams import build_team
from kickoff_ml.providers.base import Fixture, ProviderStatus, utcnow_iso

log = structlog.get_logger()

BASE_URL = "https://api.football-data.org/v4"
CACHE_TTL = 600.0
ATTRIBUTION = "Football data provided by the Football-Data.org API"


class FootballDataProvider:
    name = "football-data.org"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.environ.get("FOOTBALL_DATA_API_KEY")
        self._cache: dict[str, tuple[float, Any]] = {}
        self._last_request = 0.0

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def _get(self, path: str) -> dict | None:
        if self.api_key is None:
            return None
        now = time.time()
        cached = self._cache.get(path)
        if cached and now - cached[0] < CACHE_TTL:
            return cached[1]
        # throttle: >=6s between calls (10/min free tier)
        wait = 6.0 - (now - self._last_request)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(3):
            try:
                self._last_request = time.time()
                resp = httpx.get(
                    f"{BASE_URL}{path}",
                    headers={"X-Auth-Token": self.api_key},
                    timeout=15,
                )
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get("X-RequestCounter-Reset", "10"))
                    log.warning("rate limited", path=path, wait=retry_after)
                    time.sleep(min(retry_after, 30))
                    continue
                resp.raise_for_status()
                data = resp.json()
                self._cache[path] = (time.time(), data)
                return data
            except httpx.HTTPError as exc:
                log.warning("football-data request failed", path=path,
                            attempt=attempt, error=str(exc))
                time.sleep(2**attempt)
        return None

    def upcoming_fixtures(self) -> list[Fixture]:
        data = self._get("/competitions/WC/matches?status=SCHEDULED")
        if not data:
            return []
        retrieved = utcnow_iso()
        out = []
        for m in data.get("matches", []):
            home = build_team(m["homeTeam"]["name"]) if m["homeTeam"]["name"] else None
            away = build_team(m["awayTeam"]["name"]) if m["awayTeam"]["name"] else None
            if not home or not away:
                continue
            out.append(
                Fixture(
                    fixture_id=f"fd-{m['id']}",
                    date=m["utcDate"][:10],
                    home_id=home.team_id,
                    away_id=away.team_id,
                    tournament="FIFA World Cup",
                    status="scheduled",
                    source=self.name,
                    retrieved_at=retrieved,
                    extra={"stage": m.get("stage"), "utc_kickoff": m["utcDate"]},
                )
            )
        return out

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            kind="api",
            available=self.available,
            capabilities=(
                ["live_fixtures", "standings"] if self.available else []
            ),
            license_note=(
                "Free tier; attribution required; no bulk redistribution; "
                "lineups/squads require a paid plan (not claimed)"
            ),
            last_sync=utcnow_iso() if (self.available and self._cache) else None,
            detail=None if self.available else "FOOTBALL_DATA_API_KEY not configured",
            attribution=ATTRIBUTION if self.available else None,
        )
