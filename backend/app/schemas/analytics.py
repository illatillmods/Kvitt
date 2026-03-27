from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from app.schemas.access import AccessSnapshot


class ProductInsight(BaseModel):
    product_id: int
    normalized_name: str
    category: Optional[str] = None
    total_spend: float
    purchase_count: int
    last_purchase_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class TimeBucketInsight(BaseModel):
    label: str
    total_spend: float
    purchase_count: int


class ProductPurchaseTrace(BaseModel):
    receipt_id: str | None = None
    line_item_id: int | None = None
    merchant_name: str | None = None
    normalized_name: str
    category: str | None = None
    raw_description: str
    quantity: float
    total_price: float
    currency: str
    purchase_datetime: datetime | None = None


class ProductSearchSummary(BaseModel):
    query: str
    matched_product_count: int
    total_spend: float
    purchase_count: int
    last_purchase_at: datetime | None = None
    top_weekday: str | None = None
    top_time_of_day: str | None = None


class ProductSearchSuggestion(BaseModel):
    label: str
    type: str
    match_count: int


class ProductSearchResult(BaseModel):
    summary: ProductSearchSummary
    matched_products: List[ProductInsight]
    purchases: List[ProductPurchaseTrace]
    weekday_pattern: List[TimeBucketInsight]
    time_of_day_pattern: List[TimeBucketInsight]
    access: AccessSnapshot


class HabitInsightOut(BaseModel):
    label: str
    monthly_cost_estimate: float
    frequency_per_month: float
    explanation: str


class InsightHighlight(BaseModel):
    text: str


class InsightsSummary(BaseModel):
    period_days: int
    generated_at: datetime

    top_products: List[ProductInsight]
    top_recurring_products: List[ProductInsight]

    weekday_vs_weekend: List[TimeBucketInsight]
    time_of_day: List[TimeBucketInsight]

    habits: List[HabitInsightOut]
    highlights: List[InsightHighlight]
    access: AccessSnapshot
