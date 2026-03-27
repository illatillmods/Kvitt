from time import perf_counter

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.crud.receipts import create_receipt_from_normalized, list_receipts
from app.models.receipt import Receipt as ReceiptModel
from app.schemas.receipt import LineItem, Receipt, ReceiptScanResult
from app.services.ocr import DummyOCRClient
from app.services.ocr_pipeline import run_ocr_pipeline
from app.services.parsing import parse_receipt_text
from app.services.normalization import NormalizedReceipt, normalize_receipt

router = APIRouter()

_DEMO_RECEIPT_TEXT = """ICA KVITTO
2024-03-22 18:45
Red Bull 25,90
OL STARK 6-P 89,00
CHIPS DILL 19,90
SUMMA 134,80
"""


def _normalize_text(text: str) -> NormalizedReceipt:
    parsed = parse_receipt_text(text)
    return normalize_receipt(parsed)


def _build_receipt_response(normalized: NormalizedReceipt, processing_ms: int) -> ReceiptScanResult:
    receipt = Receipt(
        merchant_name=normalized.merchant_name,
        purchase_datetime=normalized.purchase_datetime,
        total_amount=normalized.total_amount,
        currency=normalized.currency,
        line_items=[
            LineItem(
                raw_description=li.raw_description,
                quantity=li.quantity,
                unit_price=li.unit_price,
                total_price=li.total_price,
                normalized_name=li.normalized_name,
                category=li.category,
            )
            for li in normalized.line_items
        ],
    )
    return ReceiptScanResult(receipt=receipt, processing_ms=processing_ms)


def _receipt_model_to_schema(model: ReceiptModel) -> Receipt:
    merchant_name = model.merchant.name if model.merchant else None
    purchase_datetime = model.purchase_datetime.isoformat() if model.purchase_datetime else None

    return Receipt(
        id=model.id,
        merchant_name=merchant_name,
        purchase_datetime=purchase_datetime,
        total_amount=float(model.total_amount) if model.total_amount is not None else None,
        currency=model.currency,
        line_items=[
            LineItem(
                raw_description=li.raw_description,
                quantity=float(li.quantity),
                unit_price=float(li.unit_price),
                total_price=float(li.total_price),
                normalized_name=li.product.normalized_name if li.product else None,
                category=li.product.category if li.product else None,
            )
            for li in model.line_items
        ],
    )


@router.get("/demo", response_model=ReceiptScanResult)
async def demo_receipt(db: Session = Depends(get_db_session)) -> ReceiptScanResult:
    start = perf_counter()
    normalized = _normalize_text(_DEMO_RECEIPT_TEXT)
    create_receipt_from_normalized(db, normalized, raw_text=_DEMO_RECEIPT_TEXT)
    processing_ms = int((perf_counter() - start) * 1000)
    return _build_receipt_response(normalized, processing_ms=processing_ms)


@router.post("/scan", response_model=ReceiptScanResult)
async def scan_receipt(
    image: UploadFile = File(...),
    db: Session = Depends(get_db_session),
) -> ReceiptScanResult:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported in MVP")

    ocr_client = DummyOCRClient()

    start = perf_counter()
    content = await image.read()
    pipeline_output = await run_ocr_pipeline(ocr_client, content)
    normalized = normalize_receipt(pipeline_output.parsed_receipt)
    create_receipt_from_normalized(db, normalized, raw_text=pipeline_output.ocr_result.raw_text)
    elapsed_ms = int((perf_counter() - start) * 1000)

    return _build_receipt_response(normalized, processing_ms=elapsed_ms)


@router.get("", response_model=list[Receipt])
async def list_receipts_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
) -> list[Receipt]:
    receipts = list_receipts(db, limit=limit, offset=offset)
    return [_receipt_model_to_schema(r) for r in receipts]
