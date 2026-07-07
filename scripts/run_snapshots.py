"""Create/score prediction snapshots outside the API (cron-able).

Usage: uv run python scripts/run_snapshots.py
Designed for a scheduled job (see docs/deployment.md): refresh data first,
then snapshot new upcoming fixtures and score completed ones.
"""

from kickoff_api.db import init_db
from kickoff_api.snapshots import score_snapshots, snapshot_upcoming
from kickoff_api.state import STATE

init_db()
STATE.load()
if not STATE.ready:
    raise SystemExit(f"artifacts not ready: {STATE.load_error}")
created = snapshot_upcoming(STATE)
scored = score_snapshots(STATE)
print(f"snapshots created={created} scored={scored}")
