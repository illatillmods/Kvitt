from dataclasses import dataclass, field
from typing import List, Optional

from app.services.parsing import ParsedLineItem, ParsedReceipt
from app.services.product_normalization import classify_product


@dataclass
class NormalizedLineItem:
    raw_description: str
    quantity: float
    unit_price: float
    total_price: float
    normalized_name: str
    category: Optional[str]
    # How confident the system is in the (name, category) classification.
    classification_confidence: float = 0.0
    # Which layer produced the classification (rule / mapping / ai / fallback).
    classification_source: Optional[str] = None
    # Internal notes for future debugging / admin tooling.
    debug_notes: List[str] = field(default_factory=list)


@dataclass
class NormalizedReceipt:
    merchant_name: Optional[str]
    purchase_datetime: Optional[str]
    total_amount: Optional[float]
    currency: str
    line_items: List[NormalizedLineItem]



def normalize_line_item(item: ParsedLineItem) -> NormalizedLineItem:
    # Classification of the product itself is delegated to the
    # layered product_normalization engine. Parsing of quantity/prices
    # stays local to this module.
    decision = classify_product(item.raw_description, country_code="SE")

    normalized_name = decision.normalized_name
    category: Optional[str] = decision.category

    qty = item.quantity if item.quantity is not None else 1.0
    if qty <= 0:
        qty = 1.0

    if item.total_price is not None:
        total_price = float(item.total_price)
    elif item.unit_price is not None:
        total_price = float(item.unit_price) * qty
    else:
        total_price = 0.0

    if item.unit_price is not None:
        unit_price = float(item.unit_price)
    elif qty:
        unit_price = total_price / qty if total_price else 0.0
    else:
        unit_price = 0.0

    return NormalizedLineItem(
        raw_description=item.raw_description,
        quantity=qty,
        unit_price=unit_price,
        total_price=total_price,
        normalized_name=normalized_name,
        category=category,
        classification_confidence=decision.confidence,
        classification_source=decision.source,
    )


def normalize_receipt(parsed: ParsedReceipt) -> NormalizedReceipt:
    return NormalizedReceipt(
        merchant_name=parsed.merchant_name,
        purchase_datetime=parsed.purchase_datetime.isoformat()
        if parsed.purchase_datetime
        else None,
        total_amount=float(parsed.total_amount) if parsed.total_amount is not None else None,
        currency=parsed.currency,
        line_items=[normalize_line_item(li) for li in parsed.line_items],
    )
