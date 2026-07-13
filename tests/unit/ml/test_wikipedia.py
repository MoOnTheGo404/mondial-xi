"""The Wikipedia results overlay must take only *completed*, real matches — and
never invent a score or accept a placeholder bracket slot."""

from kickoff_ml.ingestion.wikipedia import parse_matches

WIKITEXT = """
==Quarter-finals==

===France vs Morocco===
{{Football box
|date={{Start date|2026|7|9}}
|team1={{#invoke:flag|fb-rt|FRA}}
|score={{score link|2026 FIFA World Cup knockout stage#France vs Morocco|2–0}}
|team2={{#invoke:flag|fb|MAR}}
|goals1=[[Kylian Mbappé]]
}}

===Spain vs Belgium===
{{Football box
|date={{Start date|2026|7|10}}
|team1={{#invoke:flag|fb-rt|ESP}}
|score={{score link|2026 FIFA World Cup knockout stage#Spain vs Belgium|Match report}}
|team2={{#invoke:flag|fb|BEL}}
}}

==Semi-finals==

===France vs Winner Match 98===
{{Football box
|date={{Start date|2026|7|15}}
|score={{score link|x|9–0}}
}}

===Netherlands vs Portugal===
{{Football box
|date={{Start date|2026|7|11}}
|score=1–1
|aet=yes
|penalties1=4
|penalties2=2
}}
"""


def test_parses_completed_match():
    rows = parse_matches(WIKITEXT)
    by_pair = {(r["home_team"], r["away_team"]): r for r in rows}
    fm = by_pair[("France", "Morocco")]
    assert fm["home_score"] == "2" and fm["away_score"] == "0"
    assert fm["date"] == "2026-07-09"
    assert fm["tournament"] == "FIFA World Cup"


def test_scheduled_match_emitted_with_na_score():
    # Spain v Belgium has a "Match report" link, not a score: the pairing is
    # known but unplayed, so it becomes a scheduled fixture (NA scores, like
    # martj42's own future rows) — never an invented result.
    rows = parse_matches(WIKITEXT)
    sb = next(r for r in rows if (r["home_team"], r["away_team"]) == ("Spain", "Belgium"))
    assert sb["home_score"] == "NA" and sb["away_score"] == "NA"
    assert sb["date"] == "2026-07-10"


def test_rejects_placeholder_bracket_slot():
    # "Winner Match 98" is not a real team, so a bogus 9–0 is never emitted.
    rows = parse_matches(WIKITEXT)
    assert all("Winner" not in r["away_team"] for r in rows)
    assert not any(r["home_score"] == "9" for r in rows)


def test_reads_shootout_winner():
    rows = parse_matches(WIKITEXT)
    np = next(r for r in rows if r["home_team"] == "Netherlands")
    assert np["home_score"] == "1" and np["away_score"] == "1"
    assert np["shootout_winner"] == "Netherlands"  # won the penalties 4–2
