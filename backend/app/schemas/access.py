from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel


AccessTier = Literal["free", "premium"]
FeatureTier = Literal["free", "premium"]


class FeatureDefinition(BaseModel):
    key: str
    title: str
    description: str
    tier: FeatureTier
    enabled: bool


class AccessSnapshot(BaseModel):
    tier: AccessTier
    enabled_features: List[str]
    locked_features: List[str]
    upgrade_copy: str | None = None


class ProductStructure(BaseModel):
    current_tier: AccessTier
    principles: List[str]
    free_foundation: List[FeatureDefinition]
    premium_depth: List[FeatureDefinition]