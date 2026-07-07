"""API integration tests over the real artifacts (skipped if not built)."""

import os
import tempfile

import pytest

from kickoff_ml.config import ARTIFACTS_DIR

pytestmark = pytest.mark.skipif(
    not (ARTIFACTS_DIR / "prediction_bundle.joblib").exists(),
    reason="artifacts not built (run `make data && make train`)",
)

os.environ.setdefault(
    "KICKOFF_DATABASE_URL",
    f"sqlite:///{tempfile.gettempdir()}/kickoff_test.db",
)


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient

    from kickoff_api.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["ready"] is True


def test_system_status(client):
    d = client.get("/api/v1/system/status").json()
    assert d["completed_matches"] > 40_000
    assert d["model_version"]
    assert d["data_cutoff"] >= "2026-01-01"


def test_providers_honest_capabilities(client):
    d = client.get("/api/v1/providers").json()
    names = {p["name"]: p for p in d["providers"]}
    assert names["open-data-core"]["available"] is True
    # without a credential the API adapter must report unavailable, not fake
    if not os.environ.get("FOOTBALL_DATA_API_KEY"):
        assert names["football-data.org"]["available"] is False
        assert "not configured" in names["football-data.org"]["detail"]
    caps = {c["capability"] for c in d["unavailable_capabilities"]}
    assert "confirmed_lineups" in caps


def test_teams_list_and_detail(client):
    d = client.get("/api/v1/teams?search=braz").json()
    assert any(t["team_id"] == "brazil" for t in d["teams"])
    t = client.get("/api/v1/teams/brazil").json()
    assert t["elo"] and t["matches_played"] > 500
    assert t["flag_code"] == "br"
    assert t["record"]["home"]["played"] > 0
    assert "squad_note" in t


def test_team_matches_filters(client):
    d = client.get("/api/v1/teams/brazil/matches?venue=neutral&limit=5").json()
    assert d["total"] > 100
    assert all(m["neutral"] for m in d["matches"])


def test_unknown_team_404_consistent_error(client):
    r = client.get("/api/v1/teams/atlantis")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "http_error"


def test_players_search(client):
    d = client.get("/api/v1/players?search=messi").json()
    assert d["total"] >= 1
    p = d["players"][0]
    assert p["availability"]["status"] == "unknown"
    assert "NOT an overall player-quality rating" in p["impact_note"]


def test_player_detail_with_fixture_impact(client):
    d = client.get("/api/v1/players/argentina/lionel-messi").json()
    assert d["goals"] > 30
    assert len(d["recent_goals"]) > 0


def test_fixtures_upcoming(client):
    d = client.get("/api/v1/fixtures?status=upcoming").json()
    assert d["total"] >= 1
    fx = d["fixtures"][0]
    assert fx["status"] == "scheduled"
    assert fx["home"]["flag_code"] is not None


def test_fixture_detail_scheduled_has_prediction(client):
    d = client.get("/api/v1/fixtures?status=upcoming").json()
    fid = d["fixtures"][0]["match_id"]
    fx = client.get(f"/api/v1/fixtures/{fid}").json()
    p = fx["prediction"]["probabilities"]
    assert abs(p["home"] + p["draw"] + p["away"] - 1) < 1e-3
    assert fx["head_to_head"]["total"] >= 0


def test_fixture_lineups_honestly_unavailable(client):
    d = client.get("/api/v1/fixtures?status=upcoming").json()
    fid = d["fixtures"][0]["match_id"]
    lu = client.get(f"/api/v1/fixtures/{fid}/lineups").json()
    assert lu["status"] == "unavailable"
    assert "licensed provider" in lu["reason"]


def test_availability_defaults_unknown(client):
    d = client.get("/api/v1/fixtures?status=upcoming").json()
    fid = d["fixtures"][0]["match_id"]
    av = client.get(f"/api/v1/fixtures/{fid}/availability").json()
    for side in ("home", "away"):
        assert all(p["status"] == "unknown" for p in av["availability"][side])


def test_prediction_valid(client):
    r = client.post(
        "/api/v1/predictions/match",
        json={"home_id": "brazil", "away_id": "germany", "neutral": True},
    )
    d = r.json()
    assert r.status_code == 200
    assert d["model_version"] and d["data_cutoff"]
    assert len(d["top_scorelines"]) == 6


def test_prediction_invalid_inputs(client):
    r = client.post(
        "/api/v1/predictions/match",
        json={"home_id": "brazil", "away_id": "brazil"},
    )
    assert r.status_code == 422
    r2 = client.post(
        "/api/v1/predictions/match",
        json={"home_id": "x", "away_id": "DROP TABLE;"},
    )
    assert r2.status_code == 422
    assert r2.json()["error"]["code"] == "validation_error"


def test_scenario_compare(client):
    r = client.post(
        "/api/v1/predictions/compare",
        json={
            "home_id": "argentina", "away_id": "france",
            "scenario_b": {"home_absences": ["argentina/lionel-messi"]},
        },
    )
    d = r.json()
    assert d["delta"]["probabilities_pp"]["home"] < 0
    assert any("lionel-messi" in c for c in d["delta"]["what_changed"])


def test_simulation_deterministic_and_capped(client):
    a = client.post("/api/v1/simulations/tournament", json={"n_sims": 2000, "seed": 5}).json()
    b = client.post("/api/v1/simulations/tournament", json={"n_sims": 2000, "seed": 5}).json()
    assert a["teams"][0]["reach"] == b["teams"][0]["reach"]
    over = client.post("/api/v1/simulations/tournament", json={"n_sims": 10_000_000})
    assert over.status_code == 422


def test_simulation_locked_result(client):
    body = {
        "n_sims": 3000, "seed": 11,
        "locked": [{"round": "QF", "team_a": "france", "team_b": "morocco", "winner": "morocco"}],
    }
    d = client.post("/api/v1/simulations/tournament", json=body).json()
    france = next(t for t in d["teams"] if t["team_id"] == "france")
    assert france["reach"]["SF"] == 0.0  # France cannot pass a locked QF loss


def test_models_metrics_from_artifacts(client):
    d = client.get("/api/v1/models/metrics").json()
    assert d["metrics"]["champion"] in d["comparison"]
    assert d["metrics"]["champion_test"]["log_loss"] < 1.0
    assert len(d["calibration"]["test_reliability"]) > 5


def test_tournament_detail_real_groups(client):
    d = client.get("/api/v1/tournaments/wc2026").json()
    gi = {r["team_id"]: r for r in d["groups"]["I"]}
    assert gi["france"]["points"] == 9  # matches independently verified table
    assert gi["iraq"]["points"] == 0


def test_archive_separates_prospective_and_backtest(client):
    d = client.get("/api/v1/predictions/archive").json()
    assert "immutable" in d["prospective"]["label"]
    assert d["backtest_summary"]["label"].startswith("Historical backtest")
