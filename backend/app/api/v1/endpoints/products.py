from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_access_context, get_db_session
from app.core.access import (
    FEATURE_ADVANCED_FILTERING,
    FEATURE_BASIC_STATISTICS,
    FEATURE_DEEPER_TRENDS,
    FEATURE_PRODUCT_TRACKING,
    AccessContext,
)
from app.crud.products import (
    get_product_insights,
    get_product_search_suggestions,
    search_products,
)
from app.schemas.access import AccessSnapshot
from app.schemas.analytics import (
    ProductInsight,
    ProductPurchaseTrace,
    ProductSearchResult,
    ProductSearchSuggestion,
    ProductSearchSummary,
    TimeBucketInsight,
)

router = APIRouter()


@router.get("/insights", response_model=List[ProductInsight])
async def product_insights(
    q: Optional[str] = Query(default=None, description="Optional search query"),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db_session),
) -> List[ProductInsight]:
    insights = get_product_insights(db, limit=limit, search=q)
    return [
        ProductInsight(
            product_id=i.product_id,
            normalized_name=i.normalized_name,
            category=i.category,
            total_spend=i.total_spend,
            purchase_count=i.purchase_count,
            last_purchase_at=i.last_purchase_at,
        )
        for i in insights
    ]


@router.get("/search", response_model=ProductSearchResult)
async def product_search(
    q: str = Query(description="Normalized product/category search query"),
    purchase_limit: int = Query(default=50, ge=1, le=100),
    product_limit: int = Query(default=12, ge=1, le=50),
    db: Session = Depends(get_db_session),
    access: AccessContext = Depends(get_access_context),
) -> ProductSearchResult:
    result = search_products(
        db,
        search=q,
        purchase_limit=purchase_limit,
        product_limit=product_limit,
    )

    weekday_pattern = [
        TimeBucketInsight(
            label=item.label,
            total_spend=item.total_spend,
            purchase_count=item.purchase_count,
        )
        for item in result.weekday_pattern
    ]
    time_of_day_pattern = [
        TimeBucketInsight(
            label=item.label,
            total_spend=item.total_spend,
            purchase_count=item.purchase_count,
        )
        for item in result.time_of_day_pattern
    ]

    enabled_features = [FEATURE_PRODUCT_TRACKING, FEATURE_BASIC_STATISTICS]
    locked_features: list[str] = []
    upgrade_copy: str | None = None

    if access.allows(FEATURE_DEEPER_TRENDS):
        enabled_features.append(FEATURE_DEEPER_TRENDS)
        enabled_features.append(FEATURE_ADVANCED_FILTERING)
    else:
        weekday_pattern = []
        time_of_day_pattern = []
        locked_features.extend([FEATURE_DEEPER_TRENDS, FEATURE_ADVANCED_FILTERING])
        upgrade_copy = "Premium adds deeper trends and advanced filtering. Free still includes search, traceability, and basic stats."

    top_weekday = result.summary.top_weekday if access.allows(FEATURE_DEEPER_TRENDS) else None
    top_time_of_day = result.summary.top_time_of_day if access.allows(FEATURE_DEEPER_TRENDS) else None

    return ProductSearchResult(
        summary=ProductSearchSummary(
            query=result.summary.query,
            matched_product_count=result.summary.matched_product_count,
            total_spend=result.summary.total_spend,
            purchase_count=result.summary.purchase_count,
            last_purchase_at=result.summary.last_purchase_at,
            top_weekday=top_weekday,
            top_time_of_day=top_time_of_day,
        ),
        matched_products=[
            ProductInsight(
                product_id=item.product_id,
                normalized_name=item.normalized_name,
                category=item.category,
                total_spend=item.total_spend,
                purchase_count=item.purchase_count,
                last_purchase_at=item.last_purchase_at,
            )
            for item in result.matched_products
        ],
        purchases=[
            ProductPurchaseTrace(
                receipt_id=item.receipt_id,
                line_item_id=item.line_item_id,
                merchant_name=item.merchant_name,
                normalized_name=item.normalized_name,
                category=item.category,
                raw_description=item.raw_description,
                quantity=item.quantity,
                total_price=item.total_price,
                currency=item.currency,
                purchase_datetime=item.purchase_datetime,
            )
            for item in result.purchases
        ],
        weekday_pattern=weekday_pattern,
        time_of_day_pattern=time_of_day_pattern,
        access=AccessSnapshot(
            tier=access.tier,
            enabled_features=enabled_features,
            locked_features=locked_features,
            upgrade_copy=upgrade_copy,
        ),
    )


@router.get("/suggestions", response_model=List[ProductSearchSuggestion])
async def product_search_suggestions(
    q: str = Query(description="Autocomplete query for normalized product/category search"),
    limit: int = Query(default=8, ge=1, le=20),
    db: Session = Depends(get_db_session),
) -> List[ProductSearchSuggestion]:
    suggestions = get_product_search_suggestions(db, search=q, limit=limit)
    return [
        ProductSearchSuggestion(
            label=item.label,
            type=item.type,
            match_count=item.match_count,
        )
        for item in suggestions
    ]
