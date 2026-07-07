"""Human-facing WC-2026 tournament summary derived from real data:
group tables (with the 2026 tiebreakers applied) and the knockout bracket
as of the data cutoff.
"""

from __future__ import annotations

import polars as pl

from kickoff_ml.simulation.engine import TournamentConfig, rank_group
from kickoff_ml.simulation.wc2026_state import ROUND_DATES, config_path, load_state

PAIR_ORDER = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]


def group_tables(cfg: TournamentConfig, state: dict) -> dict[str, list[dict]]:
    tables: dict[str, list[dict]] = {}
    for g, members in sorted(cfg.groups.items()):
        fx = [f for f in state["group_fixtures"] if f.group == g]
        if len(fx) != 6 or any(f.home_goals is None for f in fx):
            tables[g] = [
                {"team_id": t, "played": 0, "points": 0, "gd": 0, "gf": 0, "ga": 0, "rank": i + 1}
                for i, t in enumerate(members)
            ]
            continue
        scores = []
        for i, j in PAIR_ORDER:
            a, b = members[i], members[j]
            f = next(x for x in fx if {x.home, x.away} == {a, b})
            hg, ag = (f.home_goals, f.away_goals) if f.home == a else (f.away_goals, f.home_goals)
            scores.append((hg, ag))
        ranking = rank_group(tuple(scores), tuple(range(4)))
        stats = {k: {"points": 0, "gf": 0, "ga": 0, "played": 0} for k in range(4)}
        for (i, j), (hg, ag) in zip(PAIR_ORDER, scores, strict=True):
            stats[i]["played"] += 1
            stats[j]["played"] += 1
            stats[i]["gf"] += hg
            stats[i]["ga"] += ag
            stats[j]["gf"] += ag
            stats[j]["ga"] += hg
            stats[i]["points"] += 3 if hg > ag else (1 if hg == ag else 0)
            stats[j]["points"] += 3 if ag > hg else (1 if hg == ag else 0)
        tables[g] = [
            {
                "team_id": members[k],
                "rank": pos + 1,
                "played": stats[k]["played"],
                "points": stats[k]["points"],
                "gf": stats[k]["gf"],
                "ga": stats[k]["ga"],
                "gd": stats[k]["gf"] - stats[k]["ga"],
            }
            for pos, k in enumerate(ranking)
        ]
    return tables


def bracket(cfg: TournamentConfig, state: dict, upcoming: pl.DataFrame) -> list[dict]:
    """Knockout rounds with completed results and known upcoming pairings."""
    rounds: list[dict] = []
    up_rows = [
        r for r in upcoming.iter_rows(named=True) if r["tournament"] == "FIFA World Cup"
    ]
    for rnd, (lo, hi) in ROUND_DATES.items():
        matches = []
        for r in state["completed_knockout"].get(rnd, []):
            matches.append(
                {
                    "home_id": r.home, "away_id": r.away,
                    "home_goals": r.home_goals, "away_goals": r.away_goals,
                    "winner_id": r.winner, "status": "finished",
                    "shootout": r.home_goals == r.away_goals,
                }
            )
        for r in up_rows:
            if lo <= r["date"] <= hi:
                matches.append(
                    {
                        "home_id": r["home_id"], "away_id": r["away_id"],
                        "date": str(r["date"]), "city": r["city"],
                        "status": "scheduled",
                    }
                )
        rounds.append({"round": rnd, "window": [str(lo), str(hi)], "matches": matches})
    return rounds


def tournament_summary(matches: pl.DataFrame, upcoming: pl.DataFrame) -> dict:
    cfg = TournamentConfig.from_json(config_path())
    state = load_state(matches, cfg)
    import json

    raw_cfg = json.loads(config_path().read_text())
    return {
        "tournament_id": cfg.tournament_id,
        "name": cfg.name,
        "config_version": cfg.config_version,
        "sources": cfg.sources,
        "format": raw_cfg["format"],
        "tiebreaker_notes": raw_cfg.get("tiebreaker_notes"),
        "groups": group_tables(cfg, state),
        "bracket": bracket(cfg, state, upcoming),
    }
