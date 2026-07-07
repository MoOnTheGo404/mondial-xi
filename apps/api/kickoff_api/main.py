"""Kickoff Atlas API."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from kickoff_api.db import init_db
from kickoff_api.errors import (
    http_exception_handler,
    unhandled_exception_handler,
    validation_exception_handler,
)
from kickoff_api.routers import (
    fixtures,
    models_meta,
    players,
    predictions,
    simulations,
    system,
    teams,
    tournaments,
)
from kickoff_api.settings import settings
from kickoff_api.state import STATE

log = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    STATE.load()
    if STATE.ready:
        # lightweight startup jobs: snapshot genuinely-upcoming fixtures and
        # score any snapshots whose fixtures have since completed.
        from kickoff_api.snapshots import score_snapshots, snapshot_upcoming

        try:
            created = snapshot_upcoming(STATE)
            scored = score_snapshots(STATE)
            log.info("snapshot jobs done", created=created, scored=scored)
        except Exception as exc:  # noqa: BLE001 — jobs must not block serving
            log.error("snapshot job failed", error=str(exc))
    yield


app = FastAPI(
    title="Kickoff Atlas API",
    version="1.0.0",
    description=(
        "International football forecasting & tournament simulation. "
        "Open-data core (CC0), chronologically evaluated models, honest "
        "provider capability reporting."
    ),
    lifespan=lifespan,
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

PREFIX = "/api/v1"
app.include_router(system.router, prefix=PREFIX)
app.include_router(teams.router, prefix=PREFIX)
app.include_router(players.router, prefix=PREFIX)
app.include_router(fixtures.router, prefix=PREFIX)
app.include_router(predictions.router, prefix=PREFIX)
app.include_router(simulations.router, prefix=PREFIX)
app.include_router(models_meta.router, prefix=PREFIX)
app.include_router(tournaments.router, prefix=PREFIX)
