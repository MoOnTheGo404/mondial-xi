from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from fastapi import APIRouter, HTTPException, Query

from kickoff_api.helpers import require_ready, team_payload
from kickoff_api.state import STATE

router = APIRouter(tags=["predictions"])


class DoubtfulPlayer(BaseModel):
    player_id: str
    availability_prob: float = Field(0.5, ge=0.0, le=1.0)


class ScenarioBody(BaseModel):
    home_absences: list[str] = Field(default_factory=list, max_length=15)
    away_absences: list[str] = Field(default_factory=list, max_length=15)
    home_doubtful: list[DoubtfulPlayer] = Field(default_factory=list, max_length=15)
    away_doubtful: list[DoubtfulPlayer] = Field(default_factory=list, max_length=15)


class MatchPredictionRequest(BaseModel):
    home_id: str = Field(min_length=2, max_length=80)
    away_id: str = Field(min_length=2, max_length=80)
    neutral: bool = True
    importance: int = Field(4, ge=0, le=4)
    scenario: ScenarioBody | None = None

    @field_validator("home_id", "away_id")
    @classmethod
    def slug_only(cls, v: str) -> str:
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("team ids are kebab-case slugs")
        return v


class CompareRequest(BaseModel):
    home_id: str
    away_id: str
    neutral: bool = True
    importance: int = Field(4, ge=0, le=4)
    scenario_a: ScenarioBody | None = None
    scenario_b: ScenarioBody | None = None


def _to_scenario(body: ScenarioBody | None):
    from kickoff_ml.models.service import Scenario

    if body is None:
        return Scenario()
    return Scenario(
        home_absences=body.home_absences,
        away_absences=body.away_absences,
        home_doubtful=[(d.player_id, d.availability_prob) for d in body.home_doubtful],
        away_doubtful=[(d.player_id, d.availability_prob) for d in body.away_doubtful],
    )


def _enrich(pred: dict) -> dict:
    pred["teams"] = {
        "home": team_payload(pred["teams"]["home"]),
        "away": team_payload(pred["teams"]["away"]),
    }
    return pred


@router.post("/predictions/match")
def predict_match(req: MatchPredictionRequest) -> dict:
    require_ready()
    if req.home_id == req.away_id:
        raise HTTPException(422, "home_id and away_id must differ")
    pred = STATE.engine.predict(
        req.home_id, req.away_id, neutral=req.neutral,
        importance=req.importance, scenario=_to_scenario(req.scenario),
    )
    pred["kind"] = "user_scenario" if req.scenario else "custom_matchup"
    pred["label"] = (
        "User-created scenario — assumptions are user inputs, not provider data"
        if req.scenario else "Custom matchup forecast"
    )
    return _enrich(pred)


@router.post("/predictions/compare")
def compare_scenarios(req: CompareRequest) -> dict:
    require_ready()
    if req.home_id == req.away_id:
        raise HTTPException(422, "home_id and away_id must differ")
    a = STATE.engine.predict(
        req.home_id, req.away_id, neutral=req.neutral,
        importance=req.importance, scenario=_to_scenario(req.scenario_a),
    )
    b = STATE.engine.predict(
        req.home_id, req.away_id, neutral=req.neutral,
        importance=req.importance, scenario=_to_scenario(req.scenario_b),
    )
    delta_pp = {
        k: round(100 * (b["probabilities"][k] - a["probabilities"][k]), 2)
        for k in ("home", "draw", "away")
    }
    delta_xg = {
        k: round(b["expected_goals"][k] - a["expected_goals"][k], 3)
        for k in ("home", "away")
    }
    changes = []
    for side in ("home", "away"):
        pa = {p["player_id"] for p in a["player_assumptions"][side]}
        pb = {p["player_id"] for p in b["player_assumptions"][side]}
        for pid in pb - pa:
            changes.append(f"{side}: {pid} newly assumed unavailable/doubtful in B")
        for pid in pa - pb:
            changes.append(f"{side}: {pid} restored in B")
    return {
        "teams": {"home": team_payload(req.home_id), "away": team_payload(req.away_id)},
        "scenario_a": a,
        "scenario_b": b,
        "delta": {
            "probabilities_pp": delta_pp,
            "expected_goals": delta_xg,
            "advance_pp": round(
                100 * (b["knockout"]["advance_home"] - a["knockout"]["advance_home"]), 2
            ),
            "uncertainty": round(
                b["uncertainty"]["normalized_entropy"] - a["uncertainty"]["normalized_entropy"], 4
            ),
            "what_changed": changes or ["No player assumptions differ"],
        },
        "label": "Scenario comparison — user assumptions, not provider data",
    }


@router.get("/predictions/archive")
def prediction_archive(limit: int = Query(100, le=500)) -> dict:
    require_ready()
    from kickoff_api.snapshots import list_snapshots

    snaps = list_snapshots(limit)
    scored = [s for s in snaps if s["scores"]]
    cumulative = None
    if scored:
        n = len(scored)
        cumulative = {
            "n_scored": n,
            "mean_rps": round(sum(s["scores"]["rps"] for s in scored) / n, 5),
            "mean_brier": round(sum(s["scores"]["brier"] for s in scored) / n, 5),
            "mean_log_loss": round(sum(s["scores"]["log_loss"] for s in scored) / n, 5),
            "top_pick_accuracy": round(
                sum(1 for s in scored if s["scores"]["top_pick_correct"]) / n, 4
            ),
        }
    for s in snaps:
        s["home"] = team_payload(s["home_id"])
        s["away"] = team_payload(s["away_id"])
    backtest = None
    if not STATE.test_predictions.is_empty():
        backtest = {
            "label": "Historical backtest (chronological test window) — separate from published forecasts",
            "window": STATE.metrics["protocol"]["test_window"],
            "metrics": STATE.metrics["champion_test"],
        }
    return {
        "prospective": {
            "label": "Genuine prospective forecasts (immutable snapshots)",
            "snapshots": snaps,
            "cumulative": cumulative,
        },
        "backtest_summary": backtest,
    }
