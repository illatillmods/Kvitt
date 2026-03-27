from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ProductInsight(BaseModel):
    product_id: int
    normalized_name: str
    category: Optional[str] = None
    total_spend: float
    purchase_count: int
    last_purchase_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TimeBucketInsight(BaseModel):
    label: str
    total_spend: float
    purchase_count: int


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
