"""Tests for matcher.py — stdlib only, no GRAMPS needed.

Run from project root:
    python3 -m unittest GrampsSearch.tests.test_matcher -v
Or:
    cd GrampsSearch && python3 -m unittest tests.test_matcher -v
"""

import os
import sys
import unittest

_HERE = os.path.dirname(__file__)
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from api.base import ExternalPerson
from matcher import (
    extract_year,
    year_proximity,
    _sim_surname,
    score_candidate,
    filter_and_rank,
)


def _cand(given="", surname="", birth_date=None, birth_place="",
          death_date=None, death_place="", source="test", source_id="1"):
    return ExternalPerson(
        source=source,
        source_id=source_id,
        given=given,
        surname=surname,
        birth_date=birth_date,
        birth_place=birth_place,
        death_date=death_date,
        death_place=death_place,
    )


def _local(given="", surname="", birth_year=None, birth_place="",
           death_year=None, death_place=""):
    return {
        "given": given,
        "surname": surname,
        "birth": {
            "date": (birth_year,) if birth_year is not None else None,
            "place": birth_place,
        },
        "death": {
            "date": (death_year,) if death_year is not None else None,
            "place": death_place,
        },
    }


class ExtractYearTest(unittest.TestCase):

    def test_pure_year(self):
        self.assertEqual(extract_year("1850"), 1850)

    def test_year_in_date_text(self):
        self.assertEqual(extract_year("3 Mei 1850"), 1850)

    def test_abt_prefix(self):
        self.assertEqual(extract_year("abt. 1850"), 1850)

    def test_none(self):
        self.assertIsNone(extract_year(None))

    def test_empty(self):
        self.assertIsNone(extract_year(""))

    def test_no_year(self):
        self.assertIsNone(extract_year("onbekend"))

    def test_twenty_first_century(self):
        self.assertEqual(extract_year("2024-06-01"), 2024)

    def test_three_digit_ignored(self):
        self.assertIsNone(extract_year("850 AD"))

    def test_first_year_wins(self):
        self.assertEqual(extract_year("1850 - 1920"), 1850)


class YearProximityTest(unittest.TestCase):

    def test_exact_match(self):
        self.assertEqual(year_proximity(1850, 1850), 1.0)

    def test_within_default_window(self):
        self.assertEqual(year_proximity(1850, 1853), 1.0)

    def test_at_window_edge(self):
        self.assertEqual(year_proximity(1850, 1847), 1.0)

    def test_just_outside_window_decays(self):
        self.assertAlmostEqual(year_proximity(1850, 1854), 2 / 3, places=5)

    def test_mid_decay(self):
        self.assertAlmostEqual(year_proximity(1850, 1855), 1 / 3, places=5)

    def test_at_2x_window_zero(self):
        self.assertEqual(year_proximity(1850, 1856), 0.0)

    def test_beyond_decay_zero(self):
        self.assertEqual(year_proximity(1850, 1900), 0.0)

    def test_none_inputs(self):
        self.assertEqual(year_proximity(None, 1850), 0.0)
        self.assertEqual(year_proximity(1850, None), 0.0)
        self.assertEqual(year_proximity(None, None), 0.0)

    def test_custom_window(self):
        self.assertEqual(year_proximity(1850, 1855, window=5), 1.0)
        self.assertEqual(year_proximity(1850, 1860, window=5), 0.0)


class SimSurnameTest(unittest.TestCase):

    def test_exact_match(self):
        self.assertEqual(_sim_surname("Berg", "Berg"), 1.0)

    def test_tussen_on_one_side(self):
        self.assertEqual(_sim_surname("van der Berg", "Berg"), 1.0)

    def test_tussen_on_both_sides(self):
        self.assertEqual(_sim_surname("van der Berg", "de Berg"), 1.0)

    def test_case_insensitive(self):
        self.assertEqual(_sim_surname("VAN DER BERG", "berg"), 1.0)

    def test_empty_returns_zero(self):
        self.assertEqual(_sim_surname("", "Berg"), 0.0)
        self.assertEqual(_sim_surname("Berg", ""), 0.0)

    def test_compound_surname_not_fully_stripped(self):
        # Leading non-tussen 'Alberda' blocks further stripping.
        # So 'Alberda van Bloemersma' core stays as-is, vs 'Bloemersma'.
        score = _sim_surname("Alberda van Bloemersma", "Bloemersma")
        self.assertLess(score, 1.0)
        self.assertGreater(score, 0.4)

    def test_different_surnames(self):
        self.assertLess(_sim_surname("Berg", "Jansen"), 0.5)


class ScoreCandidateTest(unittest.TestCase):

    def test_perfect_match_all_fields(self):
        local = _local("Jan", "Vries", 1850, "Amsterdam", 1920, "Rotterdam")
        cand = _cand("Jan", "Vries", "1850", "Amsterdam", "1920", "Rotterdam")
        s = score_candidate(local, cand)
        self.assertAlmostEqual(s.total, 1.0, places=5)
        self.assertEqual(s.name, 1.0)
        self.assertEqual(s.birth, 1.0)
        self.assertEqual(s.death, 1.0)
        self.assertEqual(s.place, 1.0)

    def test_name_only_local_renormalizes(self):
        # No events at all locally → only name slot contributes.
        local = _local("Jan", "Vries")
        cand = _cand("Jan", "Vries", "1850", "Amsterdam", "1920")
        s = score_candidate(local, cand)
        self.assertAlmostEqual(s.total, 1.0, places=5)

    def test_birth_only_local(self):
        local = _local("Jan", "Vries", 1850)
        cand = _cand("Jan", "Vries", "1850")
        s = score_candidate(local, cand)
        # name(0.5) + birth(0.2) both = 1 → total 1.0
        self.assertAlmostEqual(s.total, 1.0, places=5)

    def test_name_mismatch_low(self):
        local = _local("Jan", "Vries")
        cand = _cand("Piet", "Jansen")
        s = score_candidate(local, cand)
        self.assertLess(s.total, 0.5)

    def test_tussen_surname_matches_core(self):
        local = _local("Jan", "Berg", 1850)
        cand = _cand("Jan", "van der Berg", "1850")
        s = score_candidate(local, cand)
        self.assertAlmostEqual(s.name, 1.0, places=5)
        self.assertAlmostEqual(s.total, 1.0, places=5)

    def test_year_decay_drops_total(self):
        local = _local("Jan", "Vries", 1850)
        near = _cand("Jan", "Vries", "1853")
        far = _cand("Jan", "Vries", "1870")
        self.assertGreater(score_candidate(local, near).total,
                           score_candidate(local, far).total)

    def test_place_fallback_death(self):
        # No local birth place, only death place; candidate has both.
        local = _local("Jan", "Vries", death_year=1920, death_place="Rotterdam")
        cand = _cand("Jan", "Vries", death_date="1920",
                     birth_place="Unused", death_place="Rotterdam")
        s = score_candidate(local, cand)
        self.assertEqual(s.place, 1.0)

    def test_missing_place_present_flag_off(self):
        # No local places at all → place slot excluded from renorm.
        local = _local("Jan", "Vries", 1850, death_year=1920)
        cand_no_place = _cand("Jan", "Vries", "1850", death_date="1920")
        cand_with_place = _cand("Jan", "Vries", "1850", "Amsterdam",
                                 "1920", "Rotterdam")
        # Both should score ≈1.0: with place, place_score=0 but slot
        # excluded; without place too.
        s1 = score_candidate(local, cand_no_place)
        self.assertAlmostEqual(s1.total, 1.0, places=5)
        s2 = score_candidate(local, cand_with_place)
        self.assertAlmostEqual(s2.total, 1.0, places=5)


class FilterAndRankTest(unittest.TestCase):

    def test_threshold_drops_bad(self):
        local = _local("Jan", "Vries", 1850)
        good = _cand("Jan", "Vries", "1850")
        bad = _cand("Piet", "Jansen", "1600")
        result = filter_and_rank(local, [good, bad])
        self.assertEqual(len(result), 1)
        self.assertIs(result[0][1], good)

    def test_sort_descending(self):
        local = _local("Jan", "Vries", 1850)
        exact = _cand("Jan", "Vries", "1850", source_id="a")
        close = _cand("Jan", "Vries", "1854", source_id="b")
        result = filter_and_rank(local, [close, exact])
        self.assertIs(result[0][1], exact)
        self.assertIs(result[1][1], close)
        self.assertGreaterEqual(result[0][0].total, result[1][0].total)

    def test_empty_input(self):
        local = _local("Jan", "Vries")
        self.assertEqual(filter_and_rank(local, []), [])

    def test_custom_threshold(self):
        local = _local("Jan", "Vries", 1850)
        lukewarm = _cand("Jan", "Vries", "1854")  # year decay pulls total down
        # With a very high threshold nothing passes
        self.assertEqual(filter_and_rank(local, [lukewarm], min_score=0.99), [])
        # With a low threshold it passes
        self.assertEqual(len(filter_and_rank(local, [lukewarm], min_score=0.1)), 1)


if __name__ == "__main__":
    unittest.main()
