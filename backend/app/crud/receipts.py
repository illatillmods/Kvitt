from __future__ import annotations

from datetime import datetime
from typing import List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.time import utc_now
from app.models.merchant import Merchant
from app.models.ocr_result import OcrResultRecord
from app.models.parsed_line_item_record import ParsedLineItemRecord
from app.models.product import Product
from app.models.receipt import Receipt
from app.models.receipt_ingestion import ReceiptIngestion
from app.models.line_item import LineItem
from app.services.ocr import OCRResult
from app.services.product_normalization import classify_product
from app.services.parsing import ParsedReceipt
from app.services.normalization import NormalizedReceipt

MANUAL_RECEIPT_MARKER = "__manual_entry__"


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


def _serialize_ocr_blocks(ocr_result: OCRResult) -> dict | None:
    if not ocr_result.blocks:
        return None

    return {
        "blocks": [
            {
                "bbox": (
                    None
                    if block.bbox is None
                    else {
                        "x": block.bbox.x,
                        "y": block.bbox.y,
                        "width": block.bbox.width,
                        "height": block.bbox.height,
                    }
                ),
                "lines": [
                    {
                        "text": line.text,
                        "bbox": (
                            None
                            if line.bbox is None
                            else {
                                "x": line.bbox.x,
                                "y": line.bbox.y,
                                "width": line.bbox.width,
                                "height": line.bbox.height,
                            }
                        ),
                        "words": [
                            {
                                "text": word.text,
                                "confidence": word.confidence,
                                "bbox": (
                                    None
                                    if word.bbox is None
                                    else {
                                        "x": word.bbox.x,
                                        "y": word.bbox.y,
                                        "width": word.bbox.width,
                                        "height": word.bbox.height,
                                    }
                                ),
                            }
                            for word in line.words
                        ],
                    }
                    for line in block.lines
                ],
            }
            for block in ocr_result.blocks
        ]
    }


def create_receipt_ingestion(
    db: Session,
    *,
    source: str,
    original_filename: str | None = None,
    content_type: str | None = None,
) -> ReceiptIngestion:
    ingestion = ReceiptIngestion(
        source=source,
        status="pending",
        original_filename=original_filename,
        content_type=content_type,
    )
    db.add(ingestion)
    db.flush([ingestion])
    return ingestion


def record_ocr_result(
    db: Session,
    *,
    ingestion: ReceiptIngestion,
    ocr_result: OCRResult,
) -> OcrResultRecord:
    record = OcrResultRecord(
        ingestion_id=ingestion.id,
        provider=ocr_result.provider,
        raw_text=ocr_result.raw_text,
        blocks=_serialize_ocr_blocks(ocr_result),
        meta=ocr_result.meta,
    )
    db.add(record)
    db.flush([record])
    return record


def record_parsed_line_items(
    db: Session,
    *,
    ocr_result_record: OcrResultRecord,
    parsed_receipt: ParsedReceipt,
) -> list[ParsedLineItemRecord]:
    records: list[ParsedLineItemRecord] = []
    for line_index, item in enumerate(parsed_receipt.line_items):
        record = ParsedLineItemRecord(
            ocr_result_id=ocr_result_record.id,
            line_index=line_index,
            raw_description=item.raw_description,
            original_line=item.original_line,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
            confidence=item.confidence,
            notes={"notes": item.notes},
        )
        db.add(record)
        records.append(record)

    if records:
        db.flush(records)
    return records


def create_receipt_from_normalized(
    db: Session,
    normalized: NormalizedReceipt,
    raw_text: str | None = None,
    ingestion: ReceiptIngestion | None = None,
    parsed_line_items: list[ParsedLineItemRecord] | None = None,
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
        ingestion_id=ingestion.id if ingestion else None,
        purchase_datetime=purchase_dt,
        total_amount=normalized.total_amount,
        currency=normalized.currency,
        raw_text=raw_text,
    )
    db.add(receipt)
    db.flush([receipt])

    for index, item in enumerate(normalized.line_items):
        product = _get_or_create_product(
            db,
            normalized_name=item.normalized_name,
            category=item.category,
        )

        line = LineItem(
            receipt_id=receipt.id,
            product_id=product.id,
            parsed_line_item_id=(
                parsed_line_items[index].id
                if parsed_line_items and index < len(parsed_line_items)
                else None
            ),
            raw_description=item.raw_description,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price,
        )
        db.add(line)

    db.commit()
    db.refresh(receipt)
    return receipt


def create_manual_receipt(
    db: Session,
    *,
    name: str,
    price: float,
    quantity: float = 1,
    currency: str = "SEK",
    purchase_datetime: datetime | None = None,
    merchant_name: str | None = None,
) -> Receipt:
    merchant = _get_or_create_merchant(db, merchant_name.strip() if merchant_name else None)
    normalized_name = name.strip()
    classification = classify_product(normalized_name, country_code="SE")
    total_price = float(price)
    quantity_value = float(quantity)
    unit_price = total_price / quantity_value if quantity_value else total_price

    receipt = Receipt(
        merchant=merchant,
        purchase_datetime=purchase_datetime or utc_now(),
        total_amount=total_price,
        currency=currency.upper(),
        raw_text=MANUAL_RECEIPT_MARKER,
    )
    db.add(receipt)
    db.flush([receipt])

    product = _get_or_create_product(
        db,
        normalized_name=classification.normalized_name,
        category=classification.category,
    )

    line = LineItem(
        receipt_id=receipt.id,
        product_id=product.id,
        raw_description=normalized_name,
        quantity=quantity_value,
        unit_price=unit_price,
        total_price=total_price,
    )
    db.add(line)
    db.commit()
    db.refresh(receipt)
    return receipt


def get_receipt(db: Session, receipt_id: UUID) -> Receipt | None:
    stmt = select(Receipt).where(Receipt.id == receipt_id)
    return db.execute(stmt).scalar_one_or_none()


def is_manual_receipt(receipt: Receipt) -> bool:
    return receipt.raw_text == MANUAL_RECEIPT_MARKER


def update_manual_receipt(
    db: Session,
    *,
    receipt: Receipt,
    name: str | None = None,
    price: float | None = None,
    quantity: float | None = None,
    purchase_datetime: datetime | None = None,
    merchant_name: str | None = None,
) -> Receipt:
    if not is_manual_receipt(receipt):
        raise ValueError("Only manual receipts can be updated")

    line_item = receipt.line_items[0] if receipt.line_items else None
    if line_item is None:
        raise ValueError("Manual receipt is missing its line item")

    next_name = name.strip() if name is not None else line_item.raw_description
    next_price = float(price) if price is not None else float(line_item.total_price)
    next_quantity = float(quantity) if quantity is not None else float(line_item.quantity)
    next_unit_price = next_price / next_quantity if next_quantity else next_price
    classification = classify_product(next_name, country_code="SE")

    receipt.purchase_datetime = purchase_datetime or receipt.purchase_datetime
    receipt.total_amount = next_price
    if merchant_name is not None:
        trimmed_merchant_name = merchant_name.strip()
        receipt.merchant = _get_or_create_merchant(db, trimmed_merchant_name or None)

    product = _get_or_create_product(
        db,
        normalized_name=classification.normalized_name,
        category=classification.category,
    )
    line_item.raw_description = next_name
    line_item.quantity = next_quantity
    line_item.total_price = next_price
    line_item.unit_price = next_unit_price
    line_item.product_id = product.id

    db.add(receipt)
    db.add(line_item)
    db.commit()
    db.refresh(receipt)
    return receipt


def delete_receipt(db: Session, receipt: Receipt) -> None:
    db.delete(receipt)
    db.commit()


def list_receipts(db: Session, limit: int = 20, offset: int = 0) -> List[Receipt]:
    stmt = (
        select(Receipt)
        .order_by(Receipt.purchase_datetime.desc().nullslast(), Receipt.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(db.scalars(stmt).all())
