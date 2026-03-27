from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.line_item import LineItem
from app.models.merchant import Merchant
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


class ProductPurchaseTraceDTO:
    def __init__(
        self,
        *,
        receipt_id: str | None,
        line_item_id: int | None,
        merchant_name: str | None,
        normalized_name: str,
        category: Optional[str],
        raw_description: str,
        quantity: float,
        total_price: float,
        currency: str,
        purchase_datetime: Optional[datetime],
    ) -> None:
        self.receipt_id = receipt_id
        self.line_item_id = line_item_id
        self.merchant_name = merchant_name
        self.normalized_name = normalized_name
        self.category = category
        self.raw_description = raw_description
        self.quantity = float(quantity)
        self.total_price = float(total_price)
        self.currency = currency
        self.purchase_datetime = purchase_datetime


class ProductSearchSummaryDTO:
    def __init__(
        self,
        *,
        query: str,
        matched_product_count: int,
        total_spend: float,
        purchase_count: int,
        last_purchase_at: Optional[datetime],
        top_weekday: Optional[str],
        top_time_of_day: Optional[str],
    ) -> None:
        self.query = query
        self.matched_product_count = int(matched_product_count)
        self.total_spend = float(total_spend)
        self.purchase_count = int(purchase_count)
        self.last_purchase_at = last_purchase_at
        self.top_weekday = top_weekday
        self.top_time_of_day = top_time_of_day


class TimeBucketInsightDTO:
    def __init__(self, *, label: str, total_spend: float, purchase_count: int) -> None:
        self.label = label
        self.total_spend = float(total_spend)
        self.purchase_count = int(purchase_count)


class ProductSearchResultDTO:
    def __init__(
        self,
        *,
        summary: ProductSearchSummaryDTO,
        matched_products: List[ProductInsightDTO],
        purchases: List[ProductPurchaseTraceDTO],
        weekday_pattern: List[TimeBucketInsightDTO],
        time_of_day_pattern: List[TimeBucketInsightDTO],
    ) -> None:
        self.summary = summary
        self.matched_products = matched_products
        self.purchases = purchases
        self.weekday_pattern = weekday_pattern
        self.time_of_day_pattern = time_of_day_pattern


class ProductSearchSuggestionDTO:
    def __init__(self, *, label: str, type: str, match_count: int) -> None:
        self.label = label
        self.type = type
        self.match_count = int(match_count)


_WEEKDAY_LABELS = [
    "Måndag",
    "Tisdag",
    "Onsdag",
    "Torsdag",
    "Fredag",
    "Lördag",
    "Söndag",
]

_TIME_OF_DAY_LABELS = ("Morgon", "Eftermiddag", "Kväll", "Sen kväll")


def _search_filter(search: str):
    like = f"%{search.lower()}%"
    return func.lower(Product.normalized_name).like(like) | func.coalesce(
        func.lower(Product.category), ""
    ).like(like)


def _time_of_day_label(ts: datetime) -> str:
    hour = ts.hour
    if 5 <= hour < 12:
        return "Morgon"
    if 12 <= hour < 18:
        return "Eftermiddag"
    if 18 <= hour < 23:
        return "Kväll"
    return "Sen kväll"


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
        stmt = stmt.where(_search_filter(search))

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


def search_products(
    db: Session,
    *,
    search: str,
    purchase_limit: int = 50,
    product_limit: int = 12,
) -> ProductSearchResultDTO:
    query = search.strip()
    if not query:
        empty_summary = ProductSearchSummaryDTO(
            query="",
            matched_product_count=0,
            total_spend=0.0,
            purchase_count=0,
            last_purchase_at=None,
            top_weekday=None,
            top_time_of_day=None,
        )
        return ProductSearchResultDTO(
            summary=empty_summary,
            matched_products=[],
            purchases=[],
            weekday_pattern=[],
            time_of_day_pattern=[],
        )

    all_matches_stmt = (
        select(LineItem, Product, Receipt, Merchant)
        .join(Product, LineItem.product_id == Product.id)
        .join(Receipt, Receipt.id == LineItem.receipt_id)
        .outerjoin(Merchant, Merchant.id == Receipt.merchant_id)
        .where(_search_filter(query))
        .order_by(Receipt.purchase_datetime.desc().nullslast(), LineItem.id.desc())
    )
    all_rows = db.execute(all_matches_stmt).all()

    matched_products = get_product_insights(db, limit=product_limit, search=query)

    purchases = [
        ProductPurchaseTraceDTO(
            receipt_id=str(receipt.id) if receipt and receipt.id else None,
            line_item_id=line_item.id,
            merchant_name=merchant.name if merchant else None,
            normalized_name=product.normalized_name,
            category=product.category,
            raw_description=line_item.raw_description,
            quantity=float(line_item.quantity),
            total_price=float(line_item.total_price),
            currency=receipt.currency,
            purchase_datetime=receipt.purchase_datetime,
        )
        for line_item, product, receipt, merchant in all_rows[:purchase_limit]
    ]

    total_spend = 0.0
    purchase_count = 0
    last_purchase_at: datetime | None = None
    weekday_totals = {label: {"spend": 0.0, "count": 0} for label in _WEEKDAY_LABELS}
    time_of_day_totals = {
        label: {"spend": 0.0, "count": 0} for label in _TIME_OF_DAY_LABELS
    }

    for line_item, _product, receipt, _merchant in all_rows:
        if receipt is None:
            continue
        total_price = float(line_item.total_price or 0.0)
        purchase_count += 1
        total_spend += total_price

        if receipt.purchase_datetime:
            ts = receipt.purchase_datetime
            if last_purchase_at is None or ts > last_purchase_at:
                last_purchase_at = ts

            weekday_label = _WEEKDAY_LABELS[ts.weekday()]
            weekday_totals[weekday_label]["spend"] += total_price
            weekday_totals[weekday_label]["count"] += 1

            time_label = _time_of_day_label(ts)
            time_of_day_totals[time_label]["spend"] += total_price
            time_of_day_totals[time_label]["count"] += 1

    weekday_pattern = [
        TimeBucketInsightDTO(
            label=label,
            total_spend=data["spend"],
            purchase_count=data["count"],
        )
        for label, data in weekday_totals.items()
        if data["count"] > 0
    ]
    time_of_day_pattern = [
        TimeBucketInsightDTO(
            label=label,
            total_spend=data["spend"],
            purchase_count=data["count"],
        )
        for label, data in time_of_day_totals.items()
        if data["count"] > 0
    ]

    top_weekday = max(weekday_pattern, key=lambda item: item.purchase_count).label if weekday_pattern else None
    top_time_of_day = max(time_of_day_pattern, key=lambda item: item.purchase_count).label if time_of_day_pattern else None

    summary = ProductSearchSummaryDTO(
        query=query,
        matched_product_count=len(matched_products),
        total_spend=round(total_spend, 2),
        purchase_count=purchase_count,
        last_purchase_at=last_purchase_at,
        top_weekday=top_weekday,
        top_time_of_day=top_time_of_day,
    )

    return ProductSearchResultDTO(
        summary=summary,
        matched_products=matched_products,
        purchases=purchases,
        weekday_pattern=weekday_pattern,
        time_of_day_pattern=time_of_day_pattern,
    )


def get_product_search_suggestions(
    db: Session,
    *,
    search: str,
    limit: int = 8,
) -> List[ProductSearchSuggestionDTO]:
    query = search.strip()
    if not query:
        return []

    normalized_name_stmt = (
        select(
            Product.normalized_name,
            func.count(LineItem.id),
        )
        .join(LineItem, LineItem.product_id == Product.id)
        .where(func.lower(Product.normalized_name).like(f"%{query.lower()}%"))
        .group_by(Product.normalized_name)
        .order_by(func.count(LineItem.id).desc(), Product.normalized_name.asc())
        .limit(limit)
    )

    category_stmt = (
        select(
            Product.category,
            func.count(LineItem.id),
        )
        .join(LineItem, LineItem.product_id == Product.id)
        .where(
            Product.category.is_not(None),
            func.lower(Product.category).like(f"%{query.lower()}%"),
        )
        .group_by(Product.category)
        .order_by(func.count(LineItem.id).desc(), Product.category.asc())
        .limit(limit)
    )

    suggestions: List[ProductSearchSuggestionDTO] = []
    seen: set[tuple[str, str]] = set()

    for label, count in db.execute(normalized_name_stmt).all():
        key = (label, "product")
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(
            ProductSearchSuggestionDTO(label=label, type="product", match_count=count or 0)
        )

    for label, count in db.execute(category_stmt).all():
        if not label:
            continue
        key = (label, "category")
        if key in seen:
            continue
        seen.add(key)
        suggestions.append(
            ProductSearchSuggestionDTO(label=label, type="category", match_count=count or 0)
        )

    suggestions.sort(key=lambda item: item.match_count, reverse=True)
    return suggestions[:limit]
