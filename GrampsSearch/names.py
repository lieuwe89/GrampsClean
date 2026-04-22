"""Dutch name parser — split a full-name string into given /
tussenvoegsel / surname / patronymic parts.

Pure stdlib. Handles:

- Dutch particles (tussenvoegsels): van, de, der, den, ten, ter, 't, ...
  Compound runs fall out naturally because each token is tested
  independently (e.g. 'van der', 'in 't', 'op de').
- Comma-reordered forms used by Dutch archives:
  'Bloemersma, Jan van'  -> given=Jan,  tussen=van,     surname=Bloemersma
  'Hooft, Piet 't'       -> given=Piet, tussen="'t",    surname=Hooft
- Parenthesised aliases: 'Jan (Johannes) de Vries' -> strips '(Johannes)'.
- Compound surnames via comma form (the archive form is unambiguous):
  'Alberda van Bloemersma, Jan' -> given=Jan, surname='Alberda van Bloemersma'.
  In plain (non-comma) form, 'Jan Alberda van Bloemersma' is resolved
  as given='Jan Alberda', tussen='van', surname='Bloemersma' — a known
  limitation; the input is ambiguous without a given-name dictionary.
- Trailing Dutch patronymics: 'Jansz', 'Janszoon', 'Jansz.', 'Jansdr'.
"""

import re
from dataclasses import dataclass
from typing import Tuple


TUSSENVOEGSELS = frozenset({
    "van", "de", "der", "den", "ten", "ter", "te", "het", "'t", "d'",
    "op", "in", "aan", "bij", "onder", "uit", "voor",
    "la", "le", "du", "des", "da", "do", "del",
    "von", "zu", "am",
})


_PATRONYMIC_RE = re.compile(
    r"""^
    [A-Za-zÀ-ÿ]+                  # stem (Jan, Pieter, ...)
    (?:
        sz(?:oon|\.|n\.)?         # Jansz, Janszoon, Jansz., Janszn.
      | sdr\.?                     # Jansdr
      | sd\.?                      # Jansd
      | zn\.?                      # Janszn
      | dr\.?                      # Jandr (rare)
    )
    $""",
    re.VERBOSE,
)

_PAREN_RE = re.compile(r"\s*\([^)]*\)\s*")


@dataclass
class NameParts:
    given: str = ""
    tussenvoegsel: str = ""
    surname: str = ""
    patronymic: str = ""

    def full_surname(self) -> str:
        """Surname with leading tussenvoegsel, joined for display."""
        if self.tussenvoegsel:
            return f"{self.tussenvoegsel} {self.surname}".strip()
        return self.surname


def parse_name(full: str) -> NameParts:
    if not full:
        return NameParts()

    s = _PAREN_RE.sub(" ", full)
    s = " ".join(s.split())
    if not s:
        return NameParts()

    if "," in s:
        return _parse_comma_form(s)
    return _parse_plain_form(s)


def _parse_plain_form(s: str) -> NameParts:
    tokens = s.split()

    patronymic = ""
    if len(tokens) > 1 and _PATRONYMIC_RE.match(tokens[-1]):
        patronymic = tokens.pop()

    if not tokens:
        return NameParts(patronymic=patronymic)

    lowered = [t.lower() for t in tokens]
    tussen_positions = [i for i, t in enumerate(lowered) if t in TUSSENVOEGSELS]

    if not tussen_positions:
        # No tussen — last token = surname, rest = given.
        if len(tokens) == 1:
            if patronymic:
                # 'Willem Jansz' → given='Willem', patronymic='Jansz'.
                return NameParts(given=tokens[0], patronymic=patronymic)
            return NameParts(surname=tokens[0])
        return NameParts(
            given=" ".join(tokens[:-1]),
            surname=tokens[-1],
            patronymic=patronymic,
        )

    last_t = tussen_positions[-1]
    start = last_t
    while start > 0 and lowered[start - 1] in TUSSENVOEGSELS:
        start -= 1
    tussen_seq = lowered[start:last_t + 1]
    surname_tail = tokens[last_t + 1:]
    remaining = tokens[:start]

    given = " ".join(remaining)
    tussen = " ".join(tussen_seq)
    surname = " ".join(surname_tail)

    # All-tussens edge (e.g. "van der") — fold into surname.
    if not surname and tussen:
        surname = tussen
        tussen = ""

    return NameParts(
        given=given,
        tussenvoegsel=tussen,
        surname=surname,
        patronymic=patronymic,
    )


def _parse_comma_form(s: str) -> NameParts:
    left, _, right = s.partition(",")
    left_tokens = left.strip().split()
    right_tokens = right.strip().split()

    # Right side may have a trailing tussen (archive form: "Surname, Given van").
    trailing = []
    while right_tokens and right_tokens[-1].lower() in TUSSENVOEGSELS:
        trailing.insert(0, right_tokens.pop().lower())

    # Left side: leading tussens are the surname particle; rest stays as
    # the surname unit (preserves compound surnames like 'Alberda van Bloemersma').
    left_tussens = []
    while left_tokens and left_tokens[0].lower() in TUSSENVOEGSELS:
        left_tussens.append(left_tokens.pop(0).lower())

    patronymic = ""
    if len(right_tokens) > 1 and _PATRONYMIC_RE.match(right_tokens[-1]):
        patronymic = right_tokens.pop()

    tussens = left_tussens + trailing
    given = " ".join(right_tokens)
    tussen = " ".join(tussens)
    surname = " ".join(left_tokens)

    if not surname and tussen:
        surname = tussen
        tussen = ""

    return NameParts(
        given=given,
        tussenvoegsel=tussen,
        surname=surname,
        patronymic=patronymic,
    )


def strip_tussenvoegsel(surname_text: str) -> Tuple[str, str]:
    """For a surname-only string, split leading tussens from the core.
    Returns (tussen, core). Useful when the local GRAMPS record keeps
    particle + surname joined in the surname field instead of using
    `Surname.prefix`.
    """
    if not surname_text:
        return "", ""
    tokens = surname_text.split()
    tussens = []
    while tokens and tokens[0].lower() in TUSSENVOEGSELS:
        tussens.append(tokens.pop(0).lower())
    return " ".join(tussens), " ".join(tokens)
