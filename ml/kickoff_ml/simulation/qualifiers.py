"""Generic qualification simulator for the WC-2030 outlook.

Real 2030 qualifying formats are mostly unannounced (see
data/tournaments/wc2030.json "assumptions"), so this module simulates a
GENERIC strength-seeded qualification per confederation:

- pool = confederation members (>= min matches), hosts excluded;
- pool <= 12 -> one double-round-robin league, top `quota` qualify;
- else -> `quota` snake-seeded groups, double round robin, winners qualify;
- best non-qualifiers feed the 2026-style inter-confederation playoff
  (2 seeds straight to finals; 3v6 & 4v5 semis) for 2 slots.

Vectorized across realizations within a fixed draw (pairings constant),
deterministic per seed. This approximates strength-ordered qualification
with realistic upset rates — it is NOT any confederation's actual path.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

MAXG = 10


@dataclass
class QualificationResult:
    """One block of realizations: qualified team lists per realization."""
    qualified: list[list[str]]          # per realization: direct qualifiers (all confeds)
    playoff_winners: list[list[str]]    # per realization: 2 playoff qualifiers


def _sample_matrix(model, home: str, away: str, neutral: bool, rng, n: int,
                   cache: dict) -> tuple[np.ndarray, np.ndarray]:
    key = (home, away, neutral)
    if key not in cache:
        m = model.score_matrix_for(home, away, neutral)
        cache[key] = m.flatten() / m.sum()
    flat = cache[key]
    draw = rng.choice(len(flat), size=n, p=flat)
    return draw // (MAXG + 1), draw % (MAXG + 1)


def _snake_groups(pool: list[str], n_groups: int) -> list[list[str]]:
    """Seeded snake draw: pool must be sorted strongest-first."""
    groups: list[list[str]] = [[] for _ in range(n_groups)]
    for i, t in enumerate(pool):
        rnd, pos = divmod(i, n_groups)
        idx = pos if rnd % 2 == 0 else n_groups - 1 - pos
        groups[idx].append(t)
    return groups


def _league(model, teams: list[str], rng, n: int, cache: dict) -> np.ndarray:
    """Double round robin; returns rank order (team indices, best first) per
    realization as an (n, len(teams)) array. Tiebreak: points, GD, GF, Elo."""
    k = len(teams)
    pts = np.zeros((n, k), dtype=np.int32)
    gd = np.zeros((n, k), dtype=np.int32)
    gf = np.zeros((n, k), dtype=np.int32)
    for i in range(k):
        for j in range(k):
            if i == j:
                continue
            hg, ag = _sample_matrix(model, teams[i], teams[j], False, rng, n, cache)
            pts[:, i] += np.where(hg > ag, 3, np.where(hg == ag, 1, 0))
            pts[:, j] += np.where(ag > hg, 3, np.where(hg == ag, 1, 0))
            gd[:, i] += hg - ag
            gd[:, j] += ag - hg
            gf[:, i] += hg
            gf[:, j] += ag
    elo = np.array([model.rating(t) for t in teams])
    key = pts * 1e9 + gd * 1e6 + gf * 1e3 + elo / 3000.0
    return np.argsort(-key, axis=1)


def simulate_confederation(
    model, pool_sorted: list[str], quota: int, rng, n: int, cache: dict
) -> tuple[list[list[str]], list[list[str]]]:
    """Returns (qualified per realization, playoff-candidates per realization).

    playoff candidates = ranked best non-qualifiers (first entry used per
    playoff slot the confederation holds).
    """
    if quota <= 0 or not pool_sorted:
        return [[] for _ in range(n)], [pool_sorted[:2] for _ in range(n)]
    if len(pool_sorted) <= max(12, quota + 2) or quota == len(pool_sorted):
        order = _league(model, pool_sorted, rng, n, cache)
        qualified = [[pool_sorted[t] for t in order[s, :quota]] for s in range(n)]
        candidates = [[pool_sorted[t] for t in order[s, quota:quota + 2]] for s in range(n)]
        return qualified, candidates

    groups = _snake_groups(pool_sorted, quota)
    winners: list[list[str]] = [[] for _ in range(n)]
    runner_pool: list[list[tuple[float, str]]] = [[] for _ in range(n)]
    for g in groups:
        order = _league(model, g, rng, n, cache)
        for s in range(n):
            winners[s].append(g[order[s, 0]])
            ru = g[order[s, 1]]
            runner_pool[s].append((model.rating(ru), ru))
    candidates = [
        [t for _, t in sorted(rp, reverse=True)[:2]] for rp in runner_pool
    ]
    return winners, candidates


def playoff(model, entrants: list[str], rng, cache: dict) -> list[str]:
    """2026-style inter-confederation playoff (single realization):
    seeds 1-2 (by Elo) straight to finals; SF: 3v6, 4v5; two final winners
    qualify. Neutral venue, draws resolved by the ET/shootout path."""

    def winner(a: str, b: str) -> str:
        hg, ag = _sample_matrix(model, a, b, True, rng, 1, cache)
        if hg[0] != ag[0]:
            return a if hg[0] > ag[0] else b
        ehg, eag = _sample_matrix(model, a, b, True, rng, 1, cache)  # ET proxy
        if ehg[0] != eag[0]:
            return a if ehg[0] > eag[0] else b
        return a if rng.random() < 0.5 else b

    seeds = sorted(entrants, key=model.rating, reverse=True)
    if len(seeds) < 6:
        return seeds[:2]
    sf1 = winner(seeds[2], seeds[5])
    sf2 = winner(seeds[3], seeds[4])
    return [winner(seeds[0], sf1), winner(seeds[1], sf2)]
