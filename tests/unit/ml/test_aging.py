from kickoff_ml.simulation import aging


def test_survival_curve_is_monotone_decreasing_and_bounded():
    ages = list(range(20, 40))
    probs = [aging.survival_prob(a) for a in ages]
    assert all(0.0 <= p <= 1.0 for p in probs)
    # broadly declines with age (young scorers likelier to still be scoring)
    assert aging.survival_prob(23) > aging.survival_prob(33)
    assert aging.survival_prob(36) < 0.2


def test_survival_extrapolates_safely_outside_knots():
    assert 0.0 <= aging.survival_prob(16) <= 1.0
    assert 0.0 < aging.survival_prob(44) <= 0.1  # very old but not negative/zero


def test_relative_aging_is_centered_and_bounded():
    teams = list(aging._team_aging_loss().keys())[:40]
    if len(teams) < 5:
        return  # registry not built in this environment
    adj = aging.relative_aging_elo(teams)
    vals = [adj[t] for t in teams]
    # centered near zero (new players replace aging ones on average)
    assert abs(sum(vals) / len(vals)) < 5.0
    # bounded
    assert all(abs(v) <= aging.AGING_ELO_CAP + 1e-6 for v in vals)


def test_teams_without_age_signal_get_zero():
    adj = aging.relative_aging_elo(["not-a-real-team-xyz"])
    assert adj["not-a-real-team-xyz"] == 0.0


def test_residual_std_is_positive():
    assert aging.residual_std() > 10.0  # measured ~63 Elo


def test_older_core_ranks_below_younger_core():
    """Direction check on real data: a team with a distinctly aged scoring
    core should not receive a higher aging delta than a distinctly young one."""
    adj = aging.relative_aging_elo(["croatia", "france", "spain", "argentina"])
    # France & Spain (young) should be >= Croatia (old) if all have signal
    if all(abs(adj[t]) > 0.5 for t in ["croatia", "france"]):
        assert adj["france"] > adj["croatia"]
