"""Sweden-specific deterministic normalization rules.

These rules encode domain knowledge that is cheap to maintain in code,
like how to interpret common abbreviations or alcohol percentages.

They run before the mapping repository, and should aim to be
high-precision (avoid guessing too broadly).
"""

from __future__ import annotations

import re
from typing import Optional

from .models import NormalizationDecision, ProductCandidate


def _looks_like_beer(candidate: ProductCandidate) -> bool:
    tokens = {t.lower() for t in candidate.tokens}
    ascii_tokens = {t.lower() for t in candidate.ascii_tokens}

    if "öl" in tokens or "ol" in ascii_tokens:
        return True
    if "starköl" in tokens or "starkol" in ascii_tokens:
        return True
    # Strong hint via alcohol percent + size
    if candidate.alcohol_percent and candidate.alcohol_percent >= 3.5 and candidate.size_ml:
        # avoid misclassifying wine by requiring small-ish package
        if 200 <= candidate.size_ml <= 1000:
            return True
    return False


def _beer_decision(candidate: ProductCandidate) -> NormalizationDecision:
    base = candidate.base_label or candidate.cleaned_label
    # Prefer a Swedish style name. We deliberately do NOT include size
    # in the display name so the UI can show compact product labels
    # like "Öl" / "Starköl" without "50 cl" etc.
    if "stark" in base.lower() or (candidate.alcohol_percent and candidate.alcohol_percent >= 4.5):
        name = "Starköl"
    else:
        name = "Öl"

    return NormalizationDecision(
        normalized_name=name,
        category="beer",
        confidence=0.9,
        source="rule",
        rule_id="se.beer.generic",
    )


def _looks_like_chips(candidate: ProductCandidate) -> bool:
    for t in candidate.tokens:
        if t.lower() == "chips":
            return True
    return False


def _chips_decision(candidate: ProductCandidate) -> NormalizationDecision:
    # We intentionally keep the flavor in the name if present, but
    # normalize the category to a stable concept (snacks).
    #
    # Use the base_label (with sizes/percent removed) and strip any
    # trailing numbers that are likely prices, as well as common
    # weight markers like "200g" so the display name stays
    # brand/flavour-focused (e.g. "Estrella Grillchips").
    base = candidate.base_label
    parts = []
    for p in base.split():
        low = p.lower()
        if low.isdigit():
            continue
        if re.fullmatch(r"\d+(g|gr|gram)", low):
            continue
        parts.append(p)
    if not parts:
        parts = candidate.tokens or [candidate.cleaned_label]
    name = " ".join(parts).title()
    return NormalizationDecision(
        normalized_name=name,
        category="snacks",
        confidence=0.85,
        source="rule",
        rule_id="se.snacks.chips",
    )


def _looks_like_loose_candy(candidate: ProductCandidate) -> bool:
    for t in candidate.tokens:
        low = t.lower()
        if low in {"lösgodis", "losgodis", "plockgodis"}:
            return True
    return False


def _loose_candy_decision(candidate: ProductCandidate) -> NormalizationDecision:
    return NormalizationDecision(
        normalized_name="Lösgodis",
        category="candy",
        confidence=0.9,
        source="rule",
        rule_id="se.candy.loose",
    )


def apply_rules(candidate: ProductCandidate) -> Optional[NormalizationDecision]:
    """Run high-precision Sweden-specific rules.

    Rules are ordered by specificity; the first matching rule wins.
    """

    if _looks_like_beer(candidate):
        return _beer_decision(candidate)

    if _looks_like_chips(candidate):
        return _chips_decision(candidate)

    if _looks_like_loose_candy(candidate):
        return _loose_candy_decision(candidate)

    return None
