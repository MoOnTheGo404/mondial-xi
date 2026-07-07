from kickoff_ml.entities.teams import (
    FLAG_CODES,
    build_team,
    canonicalize,
    slugify,
)


def test_slugify_accents_and_spaces():
    assert slugify("Côte d'Ivoire") == "cote-d-ivoire"
    assert slugify("São Tomé and Príncipe") == "sao-tome-and-principe"
    assert slugify("Bosnia and Herzegovina") == "bosnia-and-herzegovina"


def test_former_name_resolution():
    # Upstream former_names.csv maps era names to current identities.
    assert canonicalize("Zaïre") == ("dr-congo", "DR Congo")
    assert canonicalize("Soviet Union") == ("russia", "Russia")
    assert canonicalize("Gold Coast") == ("ghana", "Ghana")


def test_dissolved_states_stay_distinct():
    t = build_team("Czechoslovakia")
    assert t.team_id == "czechoslovakia"
    assert t.is_historical
    assert t.flag_code is None  # no licensed modern flag — UI fallback


def test_gb_subdivision_flags():
    assert FLAG_CODES["England"] == "gb-eng"
    assert FLAG_CODES["Scotland"] == "gb-sct"
    assert FLAG_CODES["Wales"] == "gb-wls"
    assert FLAG_CODES["Northern Ireland"] == "gb-nir"
    assert FLAG_CODES["Kosovo"] == "xk"


def test_confederations():
    assert build_team("Brazil").confederation == "CONMEBOL"
    assert build_team("Japan").confederation == "AFC"
    assert build_team("Yorkshire").confederation == "OTHER"
