"""Open-Meteo weather provider (keyless, CC-BY 4.0 attribution, free
non-commercial tier). Used for DISPLAY and scenario context only — weather is
not a trained model feature (see docs/data-source-evaluation.md).
"""

from __future__ import annotations

import time

import httpx
import structlog

from kickoff_ml.providers.base import ProviderStatus, utcnow_iso

log = structlog.get_logger()

ATTRIBUTION = "Weather data by Open-Meteo.com (CC BY 4.0)"
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CACHE_TTL = 1800.0


class OpenMeteoProvider:
    name = "open-meteo"

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._geo_cache: dict[str, tuple[float, float] | None] = {}
        self._fc_cache: dict[str, tuple[float, dict | None]] = {}
        self._last_error: str | None = None

    def _geocode(self, city: str) -> tuple[float, float] | None:
        if city in self._geo_cache:
            return self._geo_cache[city]
        try:
            resp = httpx.get(GEO_URL, params={"name": city, "count": 1}, timeout=10)
            resp.raise_for_status()
            results = resp.json().get("results") or []
            coords = (results[0]["latitude"], results[0]["longitude"]) if results else None
        except httpx.HTTPError as exc:
            log.warning("geocode failed", city=city, error=str(exc))
            self._last_error = str(exc)
            coords = None
        self._geo_cache[city] = coords
        return coords

    def forecast_for(self, city: str, iso_date: str) -> dict | None:
        """Daily forecast for a city+date within the 16-day horizon, else None."""
        if not self.enabled:
            return None
        key = f"{city}|{iso_date}"
        cached = self._fc_cache.get(key)
        if cached and time.time() - cached[0] < CACHE_TTL:
            return cached[1]
        coords = self._geocode(city)
        result: dict | None = None
        if coords:
            try:
                resp = httpx.get(
                    FORECAST_URL,
                    params={
                        "latitude": coords[0], "longitude": coords[1],
                        "daily": "temperature_2m_max,temperature_2m_min,"
                                 "precipitation_probability_max,wind_speed_10m_max",
                        "start_date": iso_date, "end_date": iso_date,
                        "timezone": "auto",
                    },
                    timeout=10,
                )
                resp.raise_for_status()
                d = resp.json().get("daily", {})
                if d.get("time"):
                    result = {
                        "city": city,
                        "date": iso_date,
                        "temp_max_c": d["temperature_2m_max"][0],
                        "temp_min_c": d["temperature_2m_min"][0],
                        "precipitation_prob_pct": d["precipitation_probability_max"][0],
                        "wind_max_kmh": d["wind_speed_10m_max"][0],
                        "retrieved_at": utcnow_iso(),
                        "attribution": ATTRIBUTION,
                    }
            except httpx.HTTPError as exc:
                log.warning("forecast failed", city=city, error=str(exc))
                self._last_error = str(exc)
        self._fc_cache[key] = (time.time(), result)
        return result

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            name=self.name,
            kind="api",
            available=self.enabled,
            capabilities=["matchday_weather_forecast"] if self.enabled else [],
            license_note="Free non-commercial tier; CC BY 4.0 attribution required",
            last_sync=utcnow_iso() if self._fc_cache else None,
            detail=self._last_error,
            attribution=ATTRIBUTION,
        )
