from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.crud.products import get_product_insights
from app.schemas.analytics import ProductInsight

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
