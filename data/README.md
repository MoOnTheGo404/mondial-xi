# data/

- `raw/` *(gitignored)* — immutable downloaded CSVs (CC0). Recreate:
  `uv run python -m kickoff_ml.ingestion.download`
- `processed/` *(gitignored)* — validated parquet + player registry.
  Recreate: `uv run python -m kickoff_ml.ingestion.build && uv run python -m kickoff_ml.models.players`
- `manifests/` *(committed)* — per-file provenance (URL, retrieval time,
  license, SHA-256, rows, date range) + `data_quality.json`.
- `fixtures/` *(committed)* — miniature deterministic test slices.
- `tournaments/` *(committed)* — versioned, source-cited rule configs.
- `kickoff.db` *(gitignored)* — SQLite prediction-snapshot store.

Licensing: see docs/data-card.md and docs/data-source-evaluation.md.
