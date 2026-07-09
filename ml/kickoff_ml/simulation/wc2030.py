"""WC-2030 Outlook: qualification -> final draw -> tournament, end to end.

Pipeline per draw-block (deterministic per seed):
1. simulate one qualification realization per confederation (generic model),
2. run the inter-confederation playoff for the last 2 slots,
3. pot-draw the 48 qualified teams with the 2026 constraints
   (4 Elo pots of 12, hosts Pot 1; max 1 per confederation per group,
   UEFA max 2),
4. run the 2026-template tournament engine from scratch for that draw.

Aggregating over B independent blocks averages qualification + draw luck.
Every documented assumption is echoed in the API response.
"""

from __future__ import annotations

import json
import math

import numpy as np
import polars as pl

from kickoff_ml.config import ROOT
from kickoff_ml.simulation import aging
from kickoff_ml.simulation.engine import TournamentConfig, TournamentSimulator
from kickoff_ml.simulation.qualifiers import playoff, simulate_confederation
from kickoff_ml.simulation.wc2026_state import ET_MEAN_SCALE

ROUNDS = ["R32", "R16", "QF", "SF", "F", "champion"]


def config_2030() -> dict:
    return json.loads((ROOT / "data" / "tournaments" / "wc2030.json").read_text())


class AgedMatchModel:
    """Wraps the bundle model with per-team 2030 rating deltas (deterministic
    aging + this realization's 4-year uncertainty noise).

    The Dixon–Coles goal model consumes only `elo_diff_eff`, which enters the
    Poisson GLM linearly, so a rating shift s = (delta_home − delta_away)
    multiplies the base expected goals analytically:
        mu_home(s) = mu_home(0) · exp(+k_h · s)
        mu_away(s) = mu_away(0) · exp(−k_a · s)
    with k = coef / scaler_std for each side. Base expected goals at s=0 are
    computed once per pairing and shared across every realization (via
    `base_cache`) — this replaces tens of thousands of per-call GLM/DataFrame
    builds with a handful, keeping the whole 2030 outlook interactive.
    `rating()` returns base+delta for seeding.
    """

    def __init__(
        self, engine, delta: dict[str, float], importance: int, base_cache: dict
    ) -> None:
        self.engine = engine
        self.delta = delta
        self.importance = importance
        self.dc = engine.models["dixon_coles"]
        self.base_cache = base_cache
        self.k_h = float(self.dc.home.coef_[0] / self.dc.scaler_h.scale_[0])
        self.k_a = float(self.dc.away.coef_[0] / self.dc.scaler_a.scale_[0])

    def _base_mus(self, home: str, away: str, neutral: bool) -> tuple[float, float]:
        key = (home, away, neutral, self.importance)
        cached = self.base_cache.get(key)
        if cached is None:
            feats = self.engine._features(home, away, neutral, self.importance)
            mh, ma = self.dc.expected_goals(feats)
            cached = (float(mh[0]), float(ma[0]))
            self.base_cache[key] = cached
        return cached

    def _mus(self, home: str, away: str, neutral: bool) -> tuple[float, float]:
        mu_h0, mu_a0 = self._base_mus(home, away, neutral)
        shift = self.delta.get(home, 0.0) - self.delta.get(away, 0.0)
        mu_h = mu_h0 * math.exp(self.k_h * shift)
        mu_a = mu_a0 * math.exp(-self.k_a * shift)
        return min(max(mu_h, 0.05), 6.0), min(max(mu_a, 0.05), 6.0)

    def score_matrix_for(self, home: str, away: str, neutral: bool):
        mu_h, mu_a = self._mus(home, away, neutral)
        return self.dc.score_matrix(mu_h, mu_a)

    def et_matrix_for(self, home: str, away: str, neutral: bool):
        mu_h, mu_a = self._mus(home, away, neutral)
        return self.dc.score_matrix(mu_h * ET_MEAN_SCALE, mu_a * ET_MEAN_SCALE)

    def rating(self, team_id: str) -> float:
        return self.engine.rating(team_id) + self.delta.get(team_id, 0.0)


def _pot_draw(
    teams48: list[str], confed: dict[str, str], model, rng: np.random.Generator
) -> dict[str, list[str]] | None:
    """2026-template draw: 4 pots of 12 by Elo (hosts forced into Pot 1);
    constraint: max 1 per confederation per group, UEFA max 2. Retry-based;
    returns None if no valid assignment found (caller redraws)."""
    cfg = config_2030()
    hosts = [h for h in cfg["verified_facts"]["hosts_auto_qualified"] if h in teams48]
    others = sorted(
        (t for t in teams48 if t not in hosts), key=model.rating, reverse=True
    )
    pot1 = hosts + others[: 12 - len(hosts)]
    rest = others[12 - len(hosts):]
    pots = [pot1, rest[:12], rest[12:24], rest[24:36]]

    letters = [chr(ord("A") + i) for i in range(12)]
    for _attempt in range(200):
        groups: dict[str, list[str]] = {g: [] for g in letters}
        ok = True
        for pot in pots:
            order = list(pot)
            rng.shuffle(order)
            for team in order:
                c = confed.get(team, "OTHER")
                fill = min(len(groups[g]) for g in letters)
                cands = [
                    g for g in letters
                    if len(groups[g]) == fill  # one team per pot per group
                    and sum(1 for t in groups[g] if confed.get(t) == c)
                    < (2 if c == "UEFA" else 1)
                ]
                if not cands:
                    ok = False
                    break
                groups[cands[int(rng.integers(len(cands)))]].append(team)
            if not ok:
                break
        if ok and all(len(g) == 4 for g in groups.values()):
            return groups
    return None


def simulate_wc2030(
    engine,
    teams_df: pl.DataFrame,
    n_sims: int = 5000,
    seed: int = 42,
    blocks: int = 16,
) -> dict:
    cfg = config_2030()
    rng = np.random.default_rng(seed)

    hosts: list[str] = cfg["verified_facts"]["hosts_auto_qualified"]
    quotas: dict[str, int] = cfg["quotas_after_hosts"]
    min_matches = cfg["min_team_matches"]

    eligible = teams_df.filter(~pl.col("is_historical"))
    confed_map = dict(zip(eligible["team_id"].to_list(), eligible["confederation"].to_list(), strict=True))
    pools: dict[str, list[str]] = {}
    for conf in quotas:
        pool = [
            t for t in eligible.filter(pl.col("confederation") == conf)["team_id"].to_list()
            if t not in hosts and engine.builder.elo.matches_played(t) >= min_matches
        ]
        pools[conf] = sorted(pool, key=engine.rating, reverse=True)

    # --- 2030 aging model: deterministic relative-aging deltas + measured
    #     4-year uncertainty (resampled per realization) -------------------
    all_teams = hosts + [t for p in pools.values() for t in p]
    aging_delta = aging.relative_aging_elo(all_teams)
    noise_sigma = aging.residual_std()
    aging_summary = aging.summary(all_teams)

    finals_cfg_raw = json.loads(
        (ROOT / "data" / "tournaments" / "wc2026.json").read_text()
    )
    base_cfg = TournamentConfig.from_json(ROOT / "data" / "tournaments" / "wc2026.json")

    qualify_counts: dict[str, int] = {}
    reach_counts: dict[str, dict[str, float]] = {}
    sims_per_block = max(n_sims // blocks, 50)
    total_sims = 0
    base_cache: dict = {}  # base expected goals per pairing, shared across blocks

    for b in range(blocks):
        # this realization's 2030 ratings: base + aging + fresh 4-year noise
        delta = {
            t: aging_delta.get(t, 0.0) + float(rng.normal(0.0, noise_sigma))
            for t in all_teams
        }
        model = AgedMatchModel(engine, delta, importance=2, base_cache=base_cache)
        finals_model = AgedMatchModel(engine, delta, importance=4, base_cache=base_cache)
        cache: dict = {}  # score matrices depend on this block's deltas

        # 1) one qualification realization (pools re-seeded by aged rating)
        qualified: list[str] = list(hosts)
        playoff_pool: list[str] = []
        candidate_lists: dict[str, list[str]] = {}
        for conf, quota in quotas.items():
            pool = sorted(pools[conf], key=model.rating, reverse=True)
            q, cand = simulate_confederation(model, pool, quota, rng, 1, cache)
            qualified.extend(q[0])
            candidate_lists[conf] = cand[0]
        for conf in cfg["playoff_candidates"]:
            options = [t for t in candidate_lists.get(conf, []) if t not in playoff_pool]
            if options:
                playoff_pool.append(options[0])
        qualified.extend(playoff(model, playoff_pool, rng, cache))
        qualified = qualified[:48]
        for t in qualified:
            qualify_counts[t] = qualify_counts.get(t, 0) + 1

        # 2) pot draw (seeded by aged rating) + 3) finals for this realization
        groups = _pot_draw(qualified, confed_map, model, rng)
        if groups is None:
            continue
        block_cfg = TournamentConfig(
            tournament_id="wc2030",
            name=cfg["name"],
            groups=groups,
            r32_template=base_cfg.r32_template,
            round_names=base_cfg.round_names,
            folds=base_cfg.folds,
            best_thirds=base_cfg.best_thirds,
            config_version=cfg["config_version"],
        )
        sim = TournamentSimulator(block_cfg, finals_model)
        from kickoff_ml.simulation.engine import GroupFixture

        fixtures = [
            GroupFixture(group=g, home=a, away=b)
            for g, members in groups.items()
            for i, a in enumerate(members)
            for b in members[i + 1:]
        ]
        res = sim.simulate(fixtures, n_sims=sims_per_block, seed=int(rng.integers(2**31)))
        total_sims += sims_per_block
        for row in res["teams"]:
            agg = reach_counts.setdefault(row["team_id"], dict.fromkeys(ROUNDS, 0.0))
            for r in ROUNDS:
                agg[r] += row["reach"][r] * sims_per_block

    table = []
    for t, cnt in qualify_counts.items():
        p_qual = cnt / blocks
        reach = reach_counts.get(t, dict.fromkeys(ROUNDS, 0.0))
        table.append(
            {
                "team_id": t,
                "is_host": t in hosts,
                "confederation": confed_map.get(t, "OTHER"),
                "p_qualify": 1.0 if t in hosts else round(p_qual, 4),
                # unconditional: averaged over blocks incl. those not qualified
                "reach": {r: round(reach[r] / max(total_sims, 1), 4) for r in ROUNDS},
            }
        )
    table.sort(key=lambda r: (-r["reach"]["champion"], -r["p_qualify"]))
    return {
        "tournament_id": "wc2030",
        "kind": "outlook",
        "name": cfg["name"],
        "config_version": cfg["config_version"],
        "n_sims": total_sims,
        "qualification_realizations": blocks,
        "seed": seed,
        "assumptions": cfg["assumptions"],
        "verified_facts": cfg["verified_facts"],
        "quotas_after_hosts": quotas,
        "aging_model": aging_summary,
        "teams": table,
        "finals_template": finals_cfg_raw["tournament_id"],
    }
