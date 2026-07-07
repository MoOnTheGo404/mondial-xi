"""Repository paths and shared constants."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Locate the repository root.

    Honors KICKOFF_REPO_ROOT (used by Docker / deployed layouts); otherwise
    walks up from this file until a directory containing `data/` and
    `pyproject.toml` is found.
    """
    env = os.environ.get("KICKOFF_REPO_ROOT")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / "data").exists():
            return parent
    # Fresh checkout before `make data`: fall back to the workspace root
    # (two levels above the ml/ package).
    return here.parents[2]


ROOT = repo_root()
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MANIFEST_DIR = DATA_DIR / "manifests"
FIXTURES_DIR = DATA_DIR / "fixtures"
ARTIFACTS_DIR = ROOT / "ml" / "artifacts"

# Evaluation windows (chronological; see docs/methodology.md).
TRAIN_END = "2018-12-31"      # ratings warm-up + model fitting
VALIDATION_END = "2022-12-31"  # model selection & calibration fitting
# Test window: 2023-01-01 .. dataset cutoff (untouched until champion chosen)
