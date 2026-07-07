"""Vectorized Monte Carlo tournament engine.

Supports: configurable groups/fixtures, 2026 tiebreaker order (with the
documented conduct/ranking approximation), best-thirds qualification with
constraint-based slot allocation, bracket templates, extra time, penalties,
locked results, deterministic seeds.

Performance approach: match scorelines are sampled from the Dixon–Coles
score matrix of each pairing (cached per pairing), vectorized across all
simulations with a single categorical draw. Group rankings use an exact
tie-breaking routine memoized on the group's score pattern.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Protocol

import numpy as np

MAXG = 10  # score matrix support per team (matches models.goals.MAX_GOALS)


class MatchModel(Protocol):
    def score_matrix_for(self, home_id: str, away_id: str, neutral: bool) -> np.ndarray: ...
    def et_matrix_for(self, home_id: str, away_id: str, neutral: bool) -> np.ndarray: ...
    def rating(self, team_id: str) -> float: ...


@dataclass
class GroupFixture:
    group: str
    home: str
    away: str
    home_goals: int | None = None   # None -> to be simulated
    away_goals: int | None = None
    neutral: bool = True


@dataclass
class KnockoutResult:
    """A completed (real or locked) knockout match."""
    home: str
    away: str
    home_goals: int
    away_goals: int
    winner: str  # explicit — covers shootouts


@dataclass
class TournamentConfig:
    tournament_id: str
    name: str
    groups: dict[str, list[str]]
    r32_template: list[dict]          # first knockout round slots (W_/RU_/T3_)
    round_names: list[str]            # e.g. ["R32","R16","QF","SF","F"]
    folds: list[list[list[int]]]      # fold[0] uses template match numbers,
    #                                   later folds use previous-round indices
    best_thirds: int = 0              # how many third-placed teams advance
    config_version: str = "0"
    sources: list[str] = field(default_factory=list)

    @classmethod
    def from_json(cls, path: str | Path) -> TournamentConfig:
        d = json.loads(Path(path).read_text())
        folds = [d["r16_fold"], d["qf_fold"], d["sf_fold"], [[0, 1]]]
        return cls(
            tournament_id=d["tournament_id"], name=d["name"], groups=d["groups"],
            r32_template=d["r32_template"],
            round_names=d["format"]["knockout_rounds"],
            folds=folds,
            best_thirds=d["format"].get("best_thirds", 0),
            config_version=d.get("config_version", "0"), sources=d.get("sources", []),
        )


# --------------------------------------------------------------------------
# Exact group ranking with 2026 tiebreakers (memoized on score pattern)
# --------------------------------------------------------------------------

@lru_cache(maxsize=200_000)
def rank_group(scores: tuple[tuple[int, int], ...], elo_order: tuple[int, ...]) -> tuple[int, ...]:
    """Rank 4 teams (indices 0..3) given the 6 round-robin scorelines.

    `scores` is ((h,a) for match order [(0,1),(2,3),(0,2),(1,3),(0,3),(1,2)]).
    `elo_order` ranks teams by rating (0 = highest) — the documented proxy for
    the conduct + FIFA-ranking criteria (open data has neither).
    Returns team indices best-to-worst.
    """
    pairs = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
    pts = [0] * 4
    gd = [0] * 4
    gf = [0] * 4
    results: dict[frozenset[int], tuple[int, int, int, int]] = {}
    for (i, j), (hg, ag) in zip(pairs, scores, strict=True):
        pts[i] += 3 if hg > ag else (1 if hg == ag else 0)
        pts[j] += 3 if ag > hg else (1 if hg == ag else 0)
        gd[i] += hg - ag
        gd[j] += ag - hg
        gf[i] += hg
        gf[j] += ag
        results[frozenset((i, j))] = (i, j, hg, ag)

    def h2h_key(team: int, tied: tuple[int, ...]) -> tuple[int, int, int]:
        p = d = f = 0
        for other in tied:
            if other == team:
                continue
            i, _j, hg, ag = results[frozenset((team, other))]
            mine, theirs = (hg, ag) if i == team else (ag, hg)
            p += 3 if mine > theirs else (1 if mine == theirs else 0)
            d += mine - theirs
            f += mine
        return (p, d, f)

    # sort by points desc, then resolve tied clusters with the official order
    order = sorted(range(4), key=lambda t: -pts[t])
    final: list[int] = []
    i = 0
    while i < 4:
        cluster = [t for t in order if pts[t] == pts[order[i]]]
        if len(cluster) == 1:
            final.append(cluster[0])
        else:
            tied = tuple(cluster)
            cluster.sort(
                key=lambda t: (
                    h2h_key(t, tied),                 # 1–3: H2H pts/GD/GF among tied
                    gd[t], gf[t],                      # 4–5: overall GD, goals
                    -elo_order.index(t),               # 6–7 proxy (higher elo first)
                ),
                reverse=True,
            )
            final.extend(cluster)
        i += len(cluster)
    return tuple(final)


# --------------------------------------------------------------------------
# Best-thirds slot allocation (constraint satisfaction over allowed groups)
# --------------------------------------------------------------------------

def allocate_thirds(qualified: list[str], template: list[dict]) -> dict[int, str] | None:
    """Assign qualified third-place groups (letters) to T3_* slots.

    FIFA's Annex C (495 published combinations) is not publicly retrievable;
    we solve the same constraints by deterministic backtracking. Returns
    {match_number: group_letter} or None if infeasible (shouldn't happen).
    """
    slots = [(t["match"], set(t["away"].removeprefix("T3_"))) for t in template
             if t["away"].startswith("T3_")]
    slots.sort(key=lambda s: len(s[1]))
    remaining = sorted(qualified)

    def backtrack(idx: int, avail: list[str], acc: dict[int, str]) -> dict[int, str] | None:
        if idx == len(slots):
            return acc
        match_no, allowed = slots[idx]
        for g in avail:
            if g in allowed:
                res = backtrack(idx + 1, [x for x in avail if x != g], {**acc, match_no: g})
                if res:
                    return res
        return None

    return backtrack(0, remaining, {})


# --------------------------------------------------------------------------
# The simulator
# --------------------------------------------------------------------------

class TournamentSimulator:
    def __init__(self, config: TournamentConfig, model: MatchModel) -> None:
        self.cfg = config
        self.model = model
        self.teams = sorted({t for g in config.groups.values() for t in g})
        self.tidx = {t: k for k, t in enumerate(self.teams)}
        self._matrix_cache: dict[tuple[str, str, bool, bool], np.ndarray] = {}

    # --- sampling helpers ---------------------------------------------------

    def _matrix(self, home: str, away: str, neutral: bool, et: bool = False) -> np.ndarray:
        key = (home, away, neutral, et)
        if key not in self._matrix_cache:
            m = (self.model.et_matrix_for if et else self.model.score_matrix_for)(home, away, neutral)
            self._matrix_cache[key] = m.flatten() / m.sum()
        return self._matrix_cache[key]

    def _sample_scores(self, rng: np.random.Generator, home: str, away: str,
                       neutral: bool, n: int, et: bool = False) -> tuple[np.ndarray, np.ndarray]:
        flat = self._matrix(home, away, neutral, et)
        draw = rng.choice(len(flat), size=n, p=flat)
        return draw // (MAXG + 1), draw % (MAXG + 1)

    # --- main entry -----------------------------------------------------------

    def simulate(
        self,
        group_fixtures: list[GroupFixture],
        n_sims: int = 10_000,
        seed: int = 42,
        completed_knockout: dict[str, list[KnockoutResult]] | None = None,
        locked_knockout: dict[str, dict[frozenset[str], str]] | None = None,
        r32_pairs: list[tuple[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Run the tournament n_sims times.

        completed_knockout: real results per round ("R32", "R16", ...) —
        pinned in every simulation.
        locked_knockout: {"QF": {frozenset({a, b}): winner_id}} user locks.
        r32_pairs: known real R32 pairings in template order — used when the
        real bracket is already drawn, bypassing the thirds-allocation
        approximation entirely.
        """
        rng = np.random.default_rng(seed)
        completed_knockout = completed_knockout or {}
        locked_knockout = locked_knockout or {}
        nT = len(self.teams)

        # ---- 1) group stage -------------------------------------------------
        letters = sorted(self.cfg.groups)
        pair_order = [(0, 1), (2, 3), (0, 2), (1, 3), (0, 3), (1, 2)]
        # per group: scores[6][n_sims][2]
        group_scores: dict[str, np.ndarray] = {}
        for g in letters:
            members = self.cfg.groups[g]
            fx = [f for f in group_fixtures if f.group == g]
            arr = np.empty((6, n_sims, 2), dtype=np.int8)
            for slot, (i, j) in enumerate(pair_order):
                a, b = members[i], members[j]
                f = next(
                    (x for x in fx if {x.home, x.away} == {a, b}), None
                )
                if f is not None and f.home_goals is not None and f.away_goals is not None:
                    fixed_a, fixed_b = (
                        (f.home_goals, f.away_goals) if f.home == a
                        else (f.away_goals, f.home_goals)
                    )
                    arr[slot, :, 0] = fixed_a
                    arr[slot, :, 1] = fixed_b
                else:
                    neutral = f.neutral if f is not None else True
                    venue_home, venue_away = (a, b)
                    if f is not None and f.home == b:
                        venue_home, venue_away = (b, a)
                    hg_arr, ag_arr = self._sample_scores(rng, venue_home, venue_away, neutral, n_sims)
                    if venue_home == a:
                        arr[slot, :, 0], arr[slot, :, 1] = hg_arr, ag_arr
                    else:
                        arr[slot, :, 0], arr[slot, :, 1] = ag_arr, hg_arr
            group_scores[g] = arr

        # rank every group in every sim (memoized exact ranking)
        winners = {g: np.empty(n_sims, dtype=np.int16) for g in letters}
        runners = {g: np.empty(n_sims, dtype=np.int16) for g in letters}
        thirds = {g: np.empty(n_sims, dtype=np.int16) for g in letters}
        thirds_stats = {g: np.empty((n_sims, 3), dtype=np.int16) for g in letters}
        group_rank_dist = np.zeros((nT, 4), dtype=np.int64)

        for g in letters:
            members = self.cfg.groups[g]
            elo_order = tuple(np.argsort([-self.model.rating(t) for t in members]).tolist())
            arr = group_scores[g]
            for s in range(n_sims):
                scores = tuple((int(arr[k, s, 0]), int(arr[k, s, 1])) for k in range(6))
                ranking = rank_group(scores, elo_order)
                winners[g][s] = self.tidx[members[ranking[0]]]
                runners[g][s] = self.tidx[members[ranking[1]]]
                third_local = ranking[2]
                thirds[g][s] = self.tidx[members[third_local]]
                # third's points/gd/gf for best-thirds ranking
                pts = gd = gf = 0
                for (i, j), (hg, ag) in zip(pair_order, scores, strict=True):
                    if i == third_local:
                        pts += 3 if hg > ag else (1 if hg == ag else 0)
                        gd += hg - ag
                        gf += hg
                    elif j == third_local:
                        pts += 3 if ag > hg else (1 if hg == ag else 0)
                        gd += ag - hg
                        gf += ag
                thirds_stats[g][s] = (pts, gd, gf)
                for pos, local in enumerate(ranking):
                    group_rank_dist[self.tidx[members[local]], pos] += 1

        # ---- 2) best thirds (only if the format uses them) --------------------
        n_groups = len(letters)
        n_thirds = self.cfg.best_thirds
        qualified_mask = np.zeros((n_sims, n_groups), dtype=bool)
        if n_thirds > 0:
            # composite ranking key: pts, gd, gf, then elo (documented proxy)
            third_key = np.empty((n_sims, n_groups))
            for gi, g in enumerate(letters):
                st = thirds_stats[g]
                elo_third = np.array([self.model.rating(self.teams[t]) for t in thirds[g]])
                third_key[:, gi] = (
                    st[:, 0] * 1e9 + st[:, 1] * 1e6 + st[:, 2] * 1e3 + elo_third / 3000.0
                )
            topk = np.argsort(-third_key, axis=1)[:, :n_thirds]
            rows = np.repeat(np.arange(n_sims), n_thirds)
            qualified_mask[rows, topk.flatten()] = True

        # ---- 3) build first knockout round pairings per sim -------------------
        round_names = self.cfg.round_names
        n_rounds = len(round_names)
        # reach columns: 0=group, 1..n_rounds=per knockout round, last=champion
        reach = np.zeros((nT, n_rounds + 2), dtype=np.int64)
        for g in letters:
            for t in self.cfg.groups[g]:
                reach[self.tidx[t], 0] = n_sims

        n_first = len(self.cfg.r32_template)
        home_slots = np.empty((n_first, n_sims), dtype=np.int16)
        away_slots = np.empty((n_first, n_sims), dtype=np.int16)

        # thirds allocation memoized per qualified-set
        alloc_cache: dict[frozenset[str], dict[int, str]] = {}

        def slot_team(ref: str, s: int, alloc: dict[int, str], match_no: int) -> int:
            if ref.startswith("W_"):
                return winners[ref[2:]][s]
            if ref.startswith("RU_"):
                return runners[ref[3:]][s]
            return thirds[alloc[match_no]][s]

        if r32_pairs is not None:
            for mi, (pair_home, pair_away) in enumerate(r32_pairs):
                home_slots[mi, :] = self.tidx[pair_home]
                away_slots[mi, :] = self.tidx[pair_away]
        else:
            letters_arr = np.array(letters)
            for s in range(n_sims):
                q = frozenset(letters_arr[qualified_mask[s]].tolist())
                if q not in alloc_cache:
                    solved = allocate_thirds(sorted(q), self.cfg.r32_template)
                    alloc_cache[q] = solved or {}
                alloc = alloc_cache[q]
                for mi, tpl in enumerate(self.cfg.r32_template):
                    home_slots[mi, s] = slot_team(tpl["home"], s, alloc, tpl["match"])
                    away_slots[mi, s] = slot_team(tpl["away"], s, alloc, tpl["match"])

        # ---- 4) knockout rounds ----------------------------------------------
        def play_round(
            round_name: str, h_arr: np.ndarray, a_arr: np.ndarray, round_col: int
        ) -> np.ndarray:
            """h_arr/a_arr: (n_matches, n_sims) team indices. Returns winners."""
            n_matches = h_arr.shape[0]
            out = np.empty_like(h_arr)
            fixed = {  # real completed results for this round
                frozenset((r.home, r.away)): r for r in completed_knockout.get(round_name, [])
            }
            locks = locked_knockout.get(round_name, {})
            for mi in range(n_matches):
                hs_col, as_col = h_arr[mi], a_arr[mi]
                for hv, av in {(int(h), int(a)) for h, a in zip(hs_col, as_col, strict=True)}:
                    mask = (hs_col == hv) & (as_col == av)
                    idx = np.where(mask)[0]
                    th, ta = self.teams[hv], self.teams[av]
                    key = frozenset((th, ta))
                    if key in fixed:
                        out[mi, idx] = self.tidx[fixed[key].winner]
                        continue
                    if key in locks:
                        out[mi, idx] = self.tidx[locks[key]]
                        continue
                    hg, ag = self._sample_scores(rng, th, ta, True, len(idx))
                    win = np.where(hg > ag, hv, av)
                    drawn = hg == ag
                    if drawn.any():
                        d_idx = np.where(drawn)[0]
                        ehg, eag = self._sample_scores(rng, th, ta, True, len(d_idx), et=True)
                        et_win = np.where(ehg > eag, hv, av)
                        still = ehg == eag
                        pens = rng.random(len(d_idx)) < 0.5
                        et_win = np.where(still, np.where(pens, hv, av), et_win)
                        win[d_idx] = et_win
                    out[mi, idx] = win
            # count reach for winners' NEXT round at caller; here count participants
            for mi in range(n_matches):
                np.add.at(reach[:, round_col], h_arr[mi], 1)
                np.add.at(reach[:, round_col], a_arr[mi], 1)
            return out

        # first round from template slots, then fold chain from config
        w = play_round(round_names[0], home_slots, away_slots, 1)
        m2i = {tpl["match"]: i for i, tpl in enumerate(self.cfg.r32_template)}
        for ri, fold in enumerate(self.cfg.folds[: n_rounds - 1], start=1):
            if ri == 1:
                fold_h = np.stack([w[m2i[fa]] for fa, _ in fold])
                fold_a = np.stack([w[m2i[fb]] for _, fb in fold])
            else:
                fold_h = np.stack([w[fa] for fa, _ in fold])
                fold_a = np.stack([w[fb] for _, fb in fold])
            w = play_round(round_names[ri], fold_h, fold_a, ri + 1)
        np.add.at(reach[:, n_rounds + 1], w[0], 1)

        # ---- 5) aggregate ------------------------------------------------------
        table = []
        for team_id, k in self.tidx.items():
            reach_dict = {
                name: reach[k, i + 1] / n_sims for i, name in enumerate(round_names)
            }
            reach_dict["champion"] = reach[k, n_rounds + 1] / n_sims
            table.append(
                {
                    "team_id": team_id,
                    "reach": reach_dict,
                    "group_rank_dist": (group_rank_dist[k] / n_sims).round(4).tolist(),
                }
            )
        table.sort(key=lambda r: -r["reach"]["champion"])
        return {
            "tournament_id": self.cfg.tournament_id,
            "config_version": self.cfg.config_version,
            "n_sims": n_sims,
            "seed": seed,
            "teams": table,
        }
