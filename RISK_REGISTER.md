# Risk register

| ID | Risk | Likelihood | Impact | Mitigation | Status |
|----|------|-----------|--------|------------|--------|
| R-01 | Temporal leakage in rolling features inflates metrics | Med | Critical | Feature builder emits before state update; dedicated leakage tests; walk-forward eval | Mitigated by tests |
| R-02 | No live-data credential → fixtures/injuries/lineups empty | Certain (this env) | Med | Provider interfaces + graceful empty states + local fixture providers for tests; docs/provider-setup.md | Accepted, documented |
| R-03 | Player-impact estimates from goalscorers only → biased toward attackers | High | Med | Strong shrinkage to position/team priors; UI labels estimates "attack-side, scoring-derived"; never presented as overall quality | Mitigated by design |
| R-04 | WC-2026 draw/groups knowledge is post-cutoff → risk of fabrication | Med | High | Verify groups & format from current web sources with citations; if unverifiable, ship clearly-labeled demo tournament | Resolved in research |
| R-05 | martj42 dataset community-maintained → occasional errors/dupes | Med | Low | Schema+score validation, dedupe, sanity checks in data-quality report | Mitigated |
| R-06 | Docker not installed locally → compose unverified | Certain | Low | Author Dockerfiles/compose; CI builds images; README states verification status honestly | Accepted, documented |
| R-07 | 10k-run simulation too slow for interactive use | Low | Med | Vectorized NumPy engine, profiled; server-side cap + seed determinism | Mitigated, measured |
| R-08 | Elo init bias for early-era teams | Med | Low | Long warm-up burn-in excluded from evaluation window; time decay | Mitigated |
| R-09 | Flag rendering for historical/non-ISO teams | High | Low | Explicit mapping table + neutral fallback glyph + text labels | Mitigated |
| R-10 | CSV export formula injection | Low | Med | Sanitize leading =,+,-,@ on export | Mitigated |
| R-11 | Model artifact unpickling trust | Low | Med | Artifacts only loaded from repo-local path; documented trust assumption in docs/security.md | Documented |
| R-12 | Scope explosion (11 pages) → unfinished controls | High | High | Vertical-slice order; no dead buttons rule; cut breadth before depth | Managed via TASKS.md |
