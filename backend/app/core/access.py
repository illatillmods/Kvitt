from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


AccessTier = Literal["free", "premium"]

FEATURE_RECEIPT_SCANNING = "receipt_scanning"
FEATURE_ITEM_EXTRACTION = "item_extraction"
FEATURE_PRODUCT_TRACKING = "product_tracking"
FEATURE_BASIC_STATISTICS = "basic_statistics"
FEATURE_ADVANCED_HABIT_INSIGHTS = "advanced_habit_insights"
FEATURE_DEEPER_TRENDS = "deeper_trends"
FEATURE_ADVANCED_FILTERING = "advanced_filtering"
FEATURE_EXPORT = "export"
FEATURE_FORECASTING = "forecasting"

FREE_FEATURES = {
    FEATURE_RECEIPT_SCANNING,
    FEATURE_ITEM_EXTRACTION,
    FEATURE_PRODUCT_TRACKING,
    FEATURE_BASIC_STATISTICS,
}

PREMIUM_FEATURES = {
    FEATURE_ADVANCED_HABIT_INSIGHTS,
    FEATURE_DEEPER_TRENDS,
    FEATURE_ADVANCED_FILTERING,
    FEATURE_EXPORT,
    FEATURE_FORECASTING,
}


@dataclass(frozen=True)
class AccessContext:
    tier: AccessTier

    @property
    def enabled_features(self) -> set[str]:
        if self.tier == "premium":
            return FREE_FEATURES | PREMIUM_FEATURES
        return set(FREE_FEATURES)

    def allows(self, feature_key: str) -> bool:
        return feature_key in self.enabled_features


def normalize_access_tier(value: str | None, *, default: AccessTier = "free") -> AccessTier:
    normalized = (value or default).strip().lower()
    if normalized == "premium":
        return "premium"
    return "free"


def build_access_context(value: str | None, *, default: AccessTier = "free") -> AccessContext:
    return AccessContext(tier=normalize_access_tier(value, default=default))