from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class LineItemBase(BaseModel):
    raw_description: str
    quantity: float
    unit_price: float
    total_price: float
    normalized_name: Optional[str] = None
    category: Optional[str] = None


class LineItem(LineItemBase):
    id: int | None = None

    class Config:
        from_attributes = True


class ReceiptBase(BaseModel):
    merchant_name: Optional[str] = None
    purchase_datetime: Optional[datetime] = None
    total_amount: Optional[float] = None
    currency: str = "SEK"


class Receipt(ReceiptBase):
    id: UUID | None = None
    line_items: List[LineItem] = []

    class Config:
        from_attributes = True


class ReceiptScanResult(BaseModel):
    receipt: Receipt
    processing_ms: int
