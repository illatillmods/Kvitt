from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


ReceiptSource = Literal["scan", "manual"]


class LineItemBase(BaseModel):
    raw_description: str
    quantity: float
    unit_price: float
    total_price: float
    normalized_name: Optional[str] = None
    category: Optional[str] = None


class LineItem(LineItemBase):
    id: int | None = None
    model_config = ConfigDict(from_attributes=True)


class ReceiptBase(BaseModel):
    merchant_name: Optional[str] = None
    purchase_datetime: Optional[datetime] = None
    total_amount: Optional[float] = None
    currency: str = "SEK"


class Receipt(ReceiptBase):
    id: UUID | None = None
    source: ReceiptSource = "scan"
    line_items: List[LineItem] = []
    model_config = ConfigDict(from_attributes=True)


class ManualReceiptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    merchant_name: Optional[str] = Field(default=None, max_length=255)
    price: float = Field(gt=0)
    quantity: float = Field(default=1, gt=0)
    currency: str = Field(default="SEK", min_length=2, max_length=3)
    purchase_datetime: Optional[datetime] = None


class ManualReceiptUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    merchant_name: Optional[str] = Field(default=None, max_length=255)
    price: Optional[float] = Field(default=None, gt=0)
    quantity: Optional[float] = Field(default=None, gt=0)
    purchase_datetime: Optional[datetime] = None


class ReceiptScanWarning(BaseModel):
    code: str
    message: str
    severity: Literal["info", "warning", "error"] = "warning"


class ReceiptScanSummary(BaseModel):
    item_count: int
    low_confidence_item_count: int
    ambiguous_item_count: int
    missing_fields: list[str] = []
    text_length: int


class ReceiptScanResult(BaseModel):
    receipt: Receipt
    processing_ms: int
    status: Literal["complete", "partial"] = "complete"
    warnings: list[ReceiptScanWarning] = []
    summary: ReceiptScanSummary
    request_id: str | None = None
