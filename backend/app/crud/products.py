from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.line_item import LineItem
from app.models.product import Product
from app.models.receipt import Receipt


class ProductInsightDTO:
    def __init__(
        self,
        product_id: int,
        normalized_name: str,
        category: Optional[str],
        total_spend: float,
        purchase_count: int,
        last_purchase_at: Optional[datetime],
    ) -> None:
        self.product_id = product_id
        self.normalized_name = normalized_name
        self.category = category
        self.total_spend = float(total_spend)
        self.purchase_count = int(purchase_count)
        self.last_purchase_at = last_purchase_at


def get_product_insights(
    db: Session,
    limit: int = 50,
    search: Optional[str] = None,
) -> List[ProductInsightDTO]:
    """Aggregate basic per-product stats from line items.

    For MVP we group globally (no per-user partitioning yet).
    """

    stmt = (
        select(
            Product.id,
            Product.normalized_name,
            Product.category,
            func.coalesce(func.sum(LineItem.total_price), 0),
            func.count(LineItem.id),
            func.max(Receipt.purchase_datetime),
        )
        .join(LineItem, LineItem.product_id == Product.id)
        .join(Receipt, Receipt.id == LineItem.receipt_id)
        .group_by(Product.id, Product.normalized_name, Product.category)
        .order_by(func.sum(LineItem.total_price).desc())
        .limit(limit)
    )

    if search:
        like = f"%{search.lower()}%"
        stmt = stmt.where(
            func.lower(Product.normalized_name).like(like)
            | func.coalesce(func.lower(Product.category), "").like(like)
        )

    rows = db.execute(stmt).all()

    return [
        ProductInsightDTO(
            product_id=row[0],
            normalized_name=row[1],
            category=row[2],
            total_spend=row[3] or 0.0,
            purchase_count=row[4] or 0,
            last_purchase_at=row[5],
        )
        for row in rows
    ]
