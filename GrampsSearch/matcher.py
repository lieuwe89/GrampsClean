"""Matching logic — score external candidates against a local person.

Pure stdlib: no external deps. Uses difflib for string similarity
and a simple year-proximity check on dates.
"""

import re
from difflib import SequenceMatcher
from dataclasses import dataclass
from typing import Optional


YEAR_RE = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def _sim(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def extract_year(date_text: Optional[str]) -> Optional[int]:
    if not date_text:
        return None
    m = YEAR_RE.search(str(date_text))
    return int(m.group(1)) if m else None


def year_proximity(a: Optional[int], b: Optional[int], window: int = 3) -> float:
    """1.0 if both within `window` years. Linear decay to 0 at 2*window."""
    if a is None or b is None:
        return 0.0
    diff = abs(a - b)
    if diff <= window:
        return 1.0
    if diff >= 2 * window:
        return 0.0
    return 1.0 - (diff - window) / window


@dataclass
class MatchScore:
    total: float
    name: float
    birth: float
    death: float
    place: float


def score_candidate(local: dict, candidate) -> MatchScore:
    """
    local: dict from GrampsDb.person_summary
    candidate: api.base.ExternalPerson
    """
    name_score = 0.5 * _sim(local.get("given", ""), candidate.given) \
        + 0.5 * _sim(local.get("surname", ""), candidate.surname)

    local_birth_year = (local.get("birth") or {}).get("date")
    local_birth_year = local_birth_year[0] if local_birth_year else None
    local_death_year = (local.get("death") or {}).get("date")
    local_death_year = local_death_year[0] if local_death_year else None

    birth_score = year_proximity(local_birth_year, extract_year(candidate.birth_date))
    death_score = year_proximity(local_death_year, extract_year(candidate.death_date))

    local_birth_place = (local.get("birth") or {}).get("place", "")
    local_death_place = (local.get("death") or {}).get("place", "")
    place_score = max(
        _sim(local_birth_place, candidate.birth_place),
        _sim(local_death_place, candidate.death_place),
    )

    total = 0.5 * name_score + 0.2 * birth_score + 0.2 * death_score + 0.1 * place_score
    return MatchScore(total=total, name=name_score, birth=birth_score, death=death_score, place=place_score)


def filter_and_rank(local: dict, candidates, min_score: float = 0.55):
    scored = [(score_candidate(local, c), c) for c in candidates]
    scored = [(s, c) for s, c in scored if s.total >= min_score]
    scored.sort(key=lambda x: x[0].total, reverse=True)
    return scored
