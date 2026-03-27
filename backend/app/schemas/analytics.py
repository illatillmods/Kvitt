from datetime import datetime
from typing import Optional

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
