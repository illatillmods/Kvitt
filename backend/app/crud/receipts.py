from __future__ import annotations

from datetime import datetime
from typing import Iterable, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.merchant import Merchant
from app.models.product import Product
from app.models.receipt import Receipt
from app.models.line_item import LineItem
from app.services.normalization import NormalizedReceipt


def _get_or_create_merchant(db: Session, name: str | None, country_code: str = "SE") -> Merchant | None:
    if not name:
        return None

    stmt = select(Merchant).where(
        Merchant.name == name,
        Merchant.country_code == country_code,
    )
    merchant = db.execute(stmt).scalar_one_or_none()
    if merchant:
        return merchant

    merchant = Merchant(name=name, country_code=country_code)
    db.add(merchant)
    db.flush([merchant])
    return merchant


def _get_or_create_product(
    db: Session,
    normalized_name: str,
    category: str | None,
) -> Product:
    stmt = select(Product).where(
        Product.normalized_name == normalized_name,
        Product.category == category,
    )
    product = db.execute(stmt).scalar_one_or_none()
    if product:
        return product

    product = Product(normalized_name=normalized_name, category=category)
    db.add(product)
    db.flush([product])
    return product


def create_receipt_from_normalized(
    db: Session,
    normalized: NormalizedReceipt,
    raw_text: str | None = None,
) -> Receipt:
    """Persist a normalized receipt and its line items.

    For MVP we ignore user handling and store global history.
    """

    merchant = _get_or_create_merchant(db, normalized.merchant_name)

    purchase_dt: datetime | None = None
    if normalized.purchase_datetime:
        try:
            purchase_dt = datetime.fromisoformat(normalized.purchase_datetime)
        except ValueError:
            purchase_dt = None

    receipt = Receipt(
        merchant=merchant,
        purchase_datetime=purchase_dt,
        total_amount=normalized.total_amount,
        currency=normalized.currency,
        raw_text=raw_text,
    )
    db.add(receipt)
    db.flush([receipt])

    for item in normalized.line_items:
        product = _get_or_create_product(
            db,
            normalized_name=item.normalized_name,
            category=item.category,
        )

        line = LineItem(
            receipt_id=receipt.id,
            product_id=product.id,
            raw_description=item.raw_description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
        )
        db.add(line)

    db.commit()
    db.refresh(receipt)
    return receipt


def list_receipts(db: Session, limit: int = 20, offset: int = 0) -> List[Receipt]:
    stmt = (
        select(Receipt)
        .order_by(Receipt.purchase_datetime.desc().nullslast(), Receipt.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())
