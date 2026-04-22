"""Tests for the Dutch name parser — stdlib only, no GRAMPS needed.

Run from project root:
    python3 -m unittest GrampsSearch.tests.test_names -v
Or:
    cd GrampsSearch && python3 -m unittest tests.test_names -v
"""

import os
import sys
import unittest

# Allow running as `python3 -m unittest tests.test_names` from GrampsSearch/
_HERE = os.path.dirname(__file__)
_PARENT = os.path.dirname(_HERE)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

from names import parse_name, strip_tussenvoegsel, NameParts


class SimpleNamesTest(unittest.TestCase):

    def test_empty(self):
        self.assertEqual(parse_name(""), NameParts())
        self.assertEqual(parse_name("   "), NameParts())

    def test_single_token_is_surname(self):
        r = parse_name("Vries")
        self.assertEqual(r.given, "")
        self.assertEqual(r.surname, "Vries")
        self.assertEqual(r.tussenvoegsel, "")
        self.assertEqual(r.patronymic, "")

    def test_plain_given_surname(self):
        r = parse_name("Jan Vries")
        self.assertEqual(r.given, "Jan")
        self.assertEqual(r.surname, "Vries")
        self.assertEqual(r.tussenvoegsel, "")

    def test_multi_given_plain_surname(self):
        r = parse_name("Jan Hendrik Vries")
        self.assertEqual(r.given, "Jan Hendrik")
        self.assertEqual(r.surname, "Vries")


class TussenvoegselTest(unittest.TestCase):

    def test_simple_van(self):
        r = parse_name("Jan van Vries")
        self.assertEqual(r.given, "Jan")
        self.assertEqual(r.tussenvoegsel, "van")
        self.assertEqual(r.surname, "Vries")

    def test_van_der(self):
        r = parse_name("Johannes van der Berg")
        self.assertEqual(r.given, "Johannes")
        self.assertEqual(r.tussenvoegsel, "van der")
        self.assertEqual(r.surname, "Berg")

    def test_apostrophe_t(self):
        r = parse_name("Piet 't Hooft")
        self.assertEqual(r.given, "Piet")
        self.assertEqual(r.tussenvoegsel, "'t")
        self.assertEqual(r.surname, "Hooft")

    def test_full_surname_display(self):
        r = parse_name("Jan de Vries")
        self.assertEqual(r.full_surname(), "de Vries")

    def test_no_tussen_full_surname_equals_surname(self):
        r = parse_name("Jan Vries")
        self.assertEqual(r.full_surname(), "Vries")


class CommaReorderedTest(unittest.TestCase):

    def test_plain_comma(self):
        r = parse_name("Vries, Jan")
        self.assertEqual(r.given, "Jan")
        self.assertEqual(r.surname, "Vries")
        self.assertEqual(r.tussenvoegsel, "")

    def test_comma_with_trailing_tussen_on_right(self):
        # Archive form: surname first, tussen follows given.
        r = parse_name("Bloemersma, Jan van")
        self.assertEqual(r.given, "Jan")
        self.assertEqual(r.tussenvoegsel, "van")
        self.assertEqual(r.surname, "Bloemersma")

    def test_comma_with_tussen_on_left(self):
        r = parse_name("de Vries, Jan")
        self.assertEqual(r.given, "Jan")
        self.assertEqual(r.tussenvoegsel, "de")
        self.assertEqual(r.surname, "Vries")

    def test_comma_apostrophe_t(self):
        r = parse_name("'t Hooft, Piet")
        self.assertEqual(r.given, "Piet")
        self.assertEqual(r.tussenvoegsel, "'t")
        self.assertEqual(r.surname, "Hooft")


class ParenStrippedTest(unittest.TestCase):

    def test_alias_parens_removed(self):
        r = parse_name("Jan (Johannes) de Vries")
        self.assertEqual(r.given, "Jan")
        self.assertEqual(r.tussenvoegsel, "de")
        self.assertEqual(r.surname, "Vries")

    def test_trailing_parens(self):
        r = parse_name("Jan de Vries (alias)")
        self.assertEqual(r.given, "Jan")
        self.assertEqual(r.surname, "Vries")


class CompoundSurnameTest(unittest.TestCase):
    """Plain form is ambiguous; comma form is authoritative."""

    def test_comma_form_preserves_compound(self):
        r = parse_name("Alberda van Bloemersma, Jan")
        self.assertEqual(r.given, "Jan")
        self.assertEqual(r.tussenvoegsel, "")
        self.assertEqual(r.surname, "Alberda van Bloemersma")

    def test_comma_form_compound_with_multi_given(self):
        r = parse_name("Alberda van Bloemersma, Jan Hendrik")
        self.assertEqual(r.given, "Jan Hendrik")
        self.assertEqual(r.surname, "Alberda van Bloemersma")

    def test_comma_form_leading_particle_stripped(self):
        r = parse_name("van Alberda van Bloemersma, Jan")
        self.assertEqual(r.given, "Jan")
        self.assertEqual(r.tussenvoegsel, "van")
        self.assertEqual(r.surname, "Alberda van Bloemersma")

    def test_plain_form_compound_ambiguous_fallback(self):
        # Known limitation: non-comma input gets the literal split.
        r = parse_name("Jan Alberda van Bloemersma")
        self.assertEqual(r.given, "Jan Alberda")
        self.assertEqual(r.tussenvoegsel, "van")
        self.assertEqual(r.surname, "Bloemersma")


class PatronymicTest(unittest.TestCase):

    def test_jansz_with_given(self):
        r = parse_name("Willem Jansz")
        self.assertEqual(r.given, "Willem")
        self.assertEqual(r.surname, "")
        self.assertEqual(r.patronymic, "Jansz")

    def test_jansz_abbreviated(self):
        r = parse_name("Willem Jansz.")
        self.assertEqual(r.given, "Willem")
        self.assertEqual(r.patronymic, "Jansz.")

    def test_janszoon(self):
        r = parse_name("Willem Janszoon")
        self.assertEqual(r.patronymic, "Janszoon")

    def test_jansdr(self):
        r = parse_name("Marijke Jansdr")
        self.assertEqual(r.given, "Marijke")
        self.assertEqual(r.patronymic, "Jansdr")

    def test_patronymic_with_surname(self):
        r = parse_name("Willem Jansz de Vries")
        self.assertEqual(r.given, "Willem Jansz")
        self.assertEqual(r.tussenvoegsel, "de")
        self.assertEqual(r.surname, "Vries")
        # Non-terminal patronymic is left in the given chunk because the
        # surname follows it.
        self.assertEqual(r.patronymic, "")

    def test_standalone_single_token_no_false_patronymic(self):
        # A single token that happens to look patronymic-ish still treated
        # as surname — we only pop when multiple tokens exist.
        r = parse_name("Jansz")
        self.assertEqual(r.surname, "Jansz")
        self.assertEqual(r.patronymic, "")


class StripTussenvoegselTest(unittest.TestCase):

    def test_strip_leading_particles(self):
        self.assertEqual(strip_tussenvoegsel("van der Berg"), ("van der", "Berg"))

    def test_no_particles(self):
        self.assertEqual(strip_tussenvoegsel("Berg"), ("", "Berg"))

    def test_empty(self):
        self.assertEqual(strip_tussenvoegsel(""), ("", ""))


if __name__ == "__main__":
    unittest.main()
