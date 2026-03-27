"""Normalization engine orchestration.

This coordinates the different layers:

1. Text pre-processing / feature extraction -> ProductCandidate
2. Deterministic rules (rules_se)
3. Mapping repository (mappings_se)
4. Optional AI-assisted fallback (not yet implemented)
"""

from __future__ import annotations

from typing import Optional

from .models import NormalizationDecision, ProductCandidate
from . import mappings_se, rules_se
from .text_utils import (
    extract_alcohol_percent,
    extract_size_ml,
    normalize_whitespace,
    strip_accents,
    strip_pack_size,
    tokenize,
)


def build_candidate(raw_label: str) -> ProductCandidate:
    """Turn a raw receipt label into a :class:`ProductCandidate`.

    The candidate keeps both the original text and several increasingly
    normalized forms that can be used by rules and mappings.
    """

    cleaned = normalize_whitespace(raw_label)
    size_stripped, size_ml = extract_size_ml(cleaned)
    abv_stripped, abv = extract_alcohol_percent(size_stripped)
    pack_stripped = strip_pack_size(abv_stripped)

    tokens = tokenize(pack_stripped)
    ascii_tokens = tokenize(strip_accents(pack_stripped))

    # Heuristic brand hint: first non-size token
    brand_hint: Optional[str] = tokens[0].lower() if tokens else None

    # Base label: remove obvious noise like size/% but keep words
    base_label = pack_stripped.lower()

    return ProductCandidate(
        raw_label=raw_label,
        cleaned_label=cleaned,
        base_label=base_label,
        tokens=tokens,
        ascii_tokens=ascii_tokens,
        brand_hint=brand_hint,
        size_ml=size_ml,
        alcohol_percent=abv,
    )


def classify_product(raw_label: str, country_code: str = "SE") -> NormalizationDecision:
    """Classify a raw label into a normalization decision.

    For now we only implement Sweden-specific logic, but the signature
    leaves room for multi-country support.
    """

    # Currently we ignore country_code and assume SE; later we can
    # dispatch to different rule/mapping sets per country.
    candidate = build_candidate(raw_label)

    # 1) Deterministic rules
    decision: Optional[NormalizationDecision] = rules_se.apply_rules(candidate)
    if decision and decision.confidence >= 0.8:
        return decision

    # 2) Mapping repository (extensible "database")
    decision = mappings_se.lookup(candidate)
    if decision:
        return decision

    # 3) (Future) AI-assisted fallback could inspect candidate here.
    # For now we just do a light normalization of the label.
    fallback_name = candidate.cleaned_label.title()
    return NormalizationDecision(
        normalized_name=fallback_name,
        category=None,
        confidence=0.2,
        source="fallback",
    )
