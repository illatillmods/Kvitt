from dataclasses import dataclass, field
from typing import List, Literal, Optional


@dataclass
class ProductCandidate:
    """Intermediate representation of a parsed product label.

    This keeps a clear separation between the raw receipt label and the
    structured features we extract from it (tokens, size, ABV, etc.).
    """

    raw_label: str
    # Lowercased, trimmed label with obvious noise removed
    cleaned_label: str
    # Further simplified form with sizes / percentages stripped out
    base_label: str
    tokens: List[str] = field(default_factory=list)
    ascii_tokens: List[str] = field(default_factory=list)
    brand_hint: Optional[str] = None
    size_ml: Optional[int] = None
    alcohol_percent: Optional[float] = None


NormalizationSource = Literal["rule", "mapping", "ai", "fallback"]


@dataclass
class NormalizationDecision:
    """Result of classifying a :class:`ProductCandidate`.

    - normalized_name is what we ideally show to users
    - category is a stable, analytics-friendly label (e.g. "beer")
    - confidence is 0–1 and allows us to gate future AI usage
    - source indicates which layer produced the decision
    """

    normalized_name: str
    category: Optional[str]
    confidence: float
    source: NormalizationSource
    rule_id: Optional[str] = None
    mapping_key: Optional[str] = None
