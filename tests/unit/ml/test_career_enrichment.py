import typing
from datetime import date

from kickoff_ml.ingestion.wikidata_players import plausible
from kickoff_ml.models.players import _match_career


class TestPlausible:
    def test_accepts_normal_careers(self):
        assert plausible(204, 125)   # Messi-like
        assert plausible(233, 146)   # Ronaldo — the actual record; must not be "implausible"
        assert plausible(25, 30)     # old-era striker ratio ~1.2
        assert plausible(None, 10)   # goals without caps qualifier
        assert plausible(50, None)   # caps without goals

    def test_rejects_garbage(self):
        assert not plausible(68, 176)   # goals >> caps (bad Wikidata row seen live)
        assert not plausible(500, 100)  # impossible cap count
        assert not plausible(0, 0)      # zero caps
        assert not plausible(50, -1)


class TestMatchCareer:
    ROW: typing.ClassVar = {"caps": 100, "goals": 40, "dob": "1990-01-01", "qid": "Q1"}

    def test_single_plausible_candidate_matches(self):
        row, amb = _match_career(
            [self.ROW], date(2015, 1, 1), date(2024, 1, 1), recorded_goals=20
        )
        assert row is self.ROW and not amb

    def test_dob_inconsistent_candidate_rejected(self):
        # born 1950 but "scored" in 2024 at age 74 -> not this person
        old = {**self.ROW, "dob": "1950-01-01"}
        row, _amb = _match_career([old], date(2015, 1, 1), date(2024, 1, 1), 5)
        assert row is None

    def test_career_below_recorded_floor_rejected(self):
        stale = {**self.ROW, "goals": 10}
        row, _ = _match_career([stale], date(2015, 1, 1), date(2024, 1, 1), recorded_goals=30)
        assert row is None  # Wikidata says 10 but we recorded 30 -> wrong/stale match

    def test_two_plausible_same_name_players_is_ambiguous(self):
        a = {**self.ROW, "qid": "Q1", "dob": "1990-01-01"}
        b = {**self.ROW, "qid": "Q2", "dob": "1992-05-05"}
        row, amb = _match_career([a, b], date(2015, 1, 1), date(2024, 1, 1), 5)
        assert row is None and amb  # refuse to guess

    def test_dob_disambiguates_generations(self):
        father = {**self.ROW, "qid": "Q1", "dob": "1955-01-01"}
        son = {**self.ROW, "qid": "Q2", "dob": "1995-01-01"}
        row, amb = _match_career([father, son], date(2018, 1, 1), date(2025, 1, 1), 5)
        assert row is son and not amb

    def test_missing_dob_still_matches_when_alone(self):
        nodob = {"caps": 30, "goals": 8, "dob": None, "qid": "Q9"}
        row, amb = _match_career([nodob], date(2020, 1, 1), date(2025, 1, 1), 3)
        assert row is nodob and not amb
