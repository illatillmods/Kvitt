"""In-memory mapping repository for Swedish product normalization.

This is deliberately structured like a tiny "database" so we can later
move it to a real table or admin-managed store without changing the
normalization engine API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .models import NormalizationDecision, ProductCandidate


@dataclass
class MappingEntry:
    key: str  # canonical key, lowercased (e.g. "red bull")
    category: str
    normalized_name: str
    synonyms: List[str]
    # Later: we could add product_id, created_by, created_at, etc.


# Seed mappings with a few high-value Swedish kiosk/grocery items.
# The goal is not completeness but having a structure that is easy to
# extend and, in the future, hydrate from a real DB.
_SE_MAPPINGS: List[MappingEntry] = [
    MappingEntry(
        key="red bull",
        category="energy_drink",
        normalized_name="Red Bull",
        synonyms=["rb", "redbull"],
    ),
    MappingEntry(
        key="monster",
        category="energy_drink",
        normalized_name="Monster",
        synonyms=["monster"],
    ),
    MappingEntry(
        key="power king",
        category="energy_drink",
        normalized_name="Powerking",
        synonyms=["powerking", "power king"],
    ),
    MappingEntry(
        key="nocco",
        category="energy_drink",
        normalized_name="Nocco",
        synonyms=["nocco"],
    ),
    MappingEntry(
        key="celsius",
        category="energy_drink",
        normalized_name="Celsius",
        synonyms=["celsius"],
    ),
]


# Pre-compute synonym -> entry lookups for fast matching
_SYNONYM_INDEX: Dict[str, MappingEntry] = {}
for entry in _SE_MAPPINGS:
    _SYNONYM_INDEX[entry.key] = entry
    for syn in entry.synonyms:
        _SYNONYM_INDEX[syn.lower()] = entry


def lookup(candidate: ProductCandidate) -> Optional[NormalizationDecision]:
    """Look up a candidate in the Swedish mapping repository.

    Matching strategy:
    - direct token match against synonyms (e.g. "rb" -> Red Bull)
    - base_label containment checks (e.g. "red bull sugarfree" -> Red Bull)
    """

    tokens = {t.lower() for t in candidate.tokens}

    # Direct token hit
    for token in tokens:
        entry = _SYNONYM_INDEX.get(token)
        if entry:
            return NormalizationDecision(
                normalized_name=entry.normalized_name,
                category=entry.category,
                confidence=0.9,
                source="mapping",
                mapping_key=entry.key,
            )

    # Fallback: substring match on base_label
    base = candidate.base_label.lower()
    for key, entry in _SYNONYM_INDEX.items():
        if key in base:
            return NormalizationDecision(
                normalized_name=entry.normalized_name,
                category=entry.category,
                confidence=0.8,
                source="mapping",
                mapping_key=entry.key,
            )

    return None
