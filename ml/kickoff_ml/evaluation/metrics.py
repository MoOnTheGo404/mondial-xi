"""Probability-quality metrics for 3-way outcomes (order: H, D, A)."""

from __future__ import annotations

import numpy as np

CLASSES = ["H", "D", "A"]


def _onehot(y: np.ndarray) -> np.ndarray:
    return np.column_stack([(y == c).astype(float) for c in CLASSES])


def log_loss(y: np.ndarray, p: np.ndarray) -> float:
    p = np.clip(p, 1e-12, 1.0)
    return float(-(np.log(p) * _onehot(y)).sum(axis=1).mean())


def brier_multiclass(y: np.ndarray, p: np.ndarray) -> float:
    return float(((p - _onehot(y)) ** 2).sum(axis=1).mean())


def rps(y: np.ndarray, p: np.ndarray) -> float:
    """Ranked probability score over ordered outcomes H < D < A."""
    cum_p = np.cumsum(p, axis=1)
    cum_o = np.cumsum(_onehot(y), axis=1)
    return float(((cum_p - cum_o) ** 2)[:, :2].sum(axis=1).mean() / 2)


def accuracy(y: np.ndarray, p: np.ndarray) -> float:
    pred = np.array(CLASSES)[p.argmax(axis=1)]
    return float((pred == y).mean())


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    """ECE of the top-probability prediction."""
    conf = p.max(axis=1)
    correct = (np.array(CLASSES)[p.argmax(axis=1)] == y).astype(float)
    edges = np.linspace(0, 1, bins + 1)
    ece = 0.0
    for lo, hi in zip(edges[:-1], edges[1:], strict=True):
        mask = (conf > lo) & (conf <= hi)
        if mask.sum() == 0:
            continue
        ece += mask.mean() * abs(conf[mask].mean() - correct[mask].mean())
    return float(ece)


def reliability_bins(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    """Per-class reliability curve data (forecast prob vs observed freq)."""
    onehot = _onehot(y)
    out: list[dict] = []
    edges = np.linspace(0, 1, bins + 1)
    for k, c in enumerate(CLASSES):
        for lo, hi in zip(edges[:-1], edges[1:], strict=True):
            mask = (p[:, k] > lo) & (p[:, k] <= hi)
            if mask.sum() < 10:
                continue
            out.append(
                {
                    "class": c,
                    "bin_mid": float((lo + hi) / 2),
                    "forecast_mean": float(p[mask, k].mean()),
                    "observed_freq": float(onehot[mask, k].mean()),
                    "count": int(mask.sum()),
                }
            )
    return out


def confidence_buckets(y: np.ndarray, p: np.ndarray) -> list[dict]:
    """Top-pick accuracy grouped by forecast confidence."""
    conf = p.max(axis=1)
    correct = (np.array(CLASSES)[p.argmax(axis=1)] == y).astype(float)
    out = []
    for lo, hi in [(0.33, 0.45), (0.45, 0.55), (0.55, 0.65), (0.65, 0.8), (0.8, 1.0)]:
        mask = (conf >= lo) & (conf < hi)
        if mask.sum() == 0:
            continue
        out.append(
            {
                "bucket": f"{lo:.2f}–{hi:.2f}",
                "count": int(mask.sum()),
                "mean_confidence": float(conf[mask].mean()),
                "top_pick_accuracy": float(correct[mask].mean()),
            }
        )
    return out


def all_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    return {
        "log_loss": round(log_loss(y, p), 5),
        "brier": round(brier_multiclass(y, p), 5),
        "rps": round(rps(y, p), 5),
        "accuracy": round(accuracy(y, p), 5),
        "ece": round(expected_calibration_error(y, p), 5),
        "n": int(len(y)),
    }
