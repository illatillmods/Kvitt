from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_access_context
from app.core.access import (
    FEATURE_ADVANCED_FILTERING,
    FEATURE_ADVANCED_HABIT_INSIGHTS,
    FEATURE_BASIC_STATISTICS,
    FEATURE_DEEPER_TRENDS,
    FEATURE_EXPORT,
    FEATURE_FORECASTING,
    FEATURE_ITEM_EXTRACTION,
    FEATURE_PRODUCT_TRACKING,
    FEATURE_RECEIPT_SCANNING,
    AccessContext,
)
from app.schemas.access import FeatureDefinition, ProductStructure

router = APIRouter()


@router.get("/product-structure", response_model=ProductStructure)
async def product_structure(
    access: AccessContext = Depends(get_access_context),
) -> ProductStructure:
    return ProductStructure(
        current_tier=access.tier,
        principles=[
            "Core value stays free: users must always understand what they spend money on.",
            "Premium deepens insight instead of blocking scanning, extraction, or tracking.",
            "Billing can be added later without changing the free foundation.",
        ],
        free_foundation=[
            FeatureDefinition(
                key=FEATURE_RECEIPT_SCANNING,
                title="Unlimited receipt scanning",
                description="Scan as many receipts as you want without hitting a paywall.",
                tier="free",
                enabled=access.allows(FEATURE_RECEIPT_SCANNING),
            ),
            FeatureDefinition(
                key=FEATURE_ITEM_EXTRACTION,
                title="Full item extraction",
                description="Every scanned receipt still breaks down into line items and products.",
                tier="free",
                enabled=access.allows(FEATURE_ITEM_EXTRACTION),
            ),
            FeatureDefinition(
                key=FEATURE_PRODUCT_TRACKING,
                title="Product tracking",
                description="Search purchases, inspect traceability, and see what you actually buy.",
                tier="free",
                enabled=access.allows(FEATURE_PRODUCT_TRACKING),
            ),
            FeatureDefinition(
                key=FEATURE_BASIC_STATISTICS,
                title="Basic statistics",
                description="Free includes spend totals, counts, and recurring product summaries.",
                tier="free",
                enabled=access.allows(FEATURE_BASIC_STATISTICS),
            ),
        ],
        premium_depth=[
            FeatureDefinition(
                key=FEATURE_ADVANCED_HABIT_INSIGHTS,
                title="Advanced habit insights",
                description="Habit-level explanations and recurring behavior analysis.",
                tier="premium",
                enabled=access.allows(FEATURE_ADVANCED_HABIT_INSIGHTS),
            ),
            FeatureDefinition(
                key=FEATURE_DEEPER_TRENDS,
                title="Deeper trends",
                description="Time-of-day and weekday pattern analysis beyond the basics.",
                tier="premium",
                enabled=access.allows(FEATURE_DEEPER_TRENDS),
            ),
            FeatureDefinition(
                key=FEATURE_ADVANCED_FILTERING,
                title="Advanced filtering",
                description="Richer segmentation and power-user drill-downs.",
                tier="premium",
                enabled=access.allows(FEATURE_ADVANCED_FILTERING),
            ),
            FeatureDefinition(
                key=FEATURE_EXPORT,
                title="Export",
                description="Structured export for spreadsheets and external workflows.",
                tier="premium",
                enabled=access.allows(FEATURE_EXPORT),
            ),
            FeatureDefinition(
                key=FEATURE_FORECASTING,
                title="Prediction and forecasting",
                description="Reserved for future premium forecasting features.",
                tier="premium",
                enabled=access.allows(FEATURE_FORECASTING),
            ),
        ],
    )