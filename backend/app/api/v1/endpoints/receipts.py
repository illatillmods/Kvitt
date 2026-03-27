import logging
from time import perf_counter

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.core.errors import ReceiptProcessingError
from app.core.time import utc_now
from app.crud.receipts import (
    create_manual_receipt,
    create_receipt_ingestion,
    create_receipt_from_normalized,
    delete_receipt,
    get_receipt,
    is_manual_receipt,
    list_receipts,
    record_ocr_result,
    record_parsed_line_items,
    update_manual_receipt,
)
from app.models.receipt import Receipt as ReceiptModel
from app.schemas.receipt import (
    LineItem,
    ManualReceiptCreate,
    ManualReceiptUpdate,
    Receipt,
    ReceiptScanResult,
    ReceiptScanSummary,
    ReceiptScanWarning,
)
from app.services.ocr import DummyOCRClient, OCRBlock, OCRClient, OCRLine, OCRResult
from app.services.ocr_pipeline import run_ocr_pipeline
from app.services.parsing import parse_receipt_text
from app.services.normalization import NormalizedReceipt, normalize_receipt
from app.services.receipt_diagnostics import ScanDiagnostics, analyze_scan

router = APIRouter()
logger = logging.getLogger(__name__)

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


def get_ocr_client() -> OCRClient:
    return DummyOCRClient()


def _build_receipt_response(
    receipt: Receipt,
    processing_ms: int,
    diagnostics: ScanDiagnostics,
    request_id: str | None,
) -> ReceiptScanResult:
    return ReceiptScanResult(
        receipt=receipt,
        processing_ms=processing_ms,
        status=diagnostics.status,
        warnings=[
            ReceiptScanWarning(code=warning.code, message=warning.message, severity=warning.severity)
            for warning in diagnostics.warnings
        ],
        summary=ReceiptScanSummary(
            item_count=diagnostics.summary.item_count,
            low_confidence_item_count=diagnostics.summary.low_confidence_item_count,
            ambiguous_item_count=diagnostics.summary.ambiguous_item_count,
            missing_fields=diagnostics.summary.missing_fields,
            text_length=diagnostics.summary.text_length,
        ),
        request_id=request_id,
    )


def _ensure_receipt_is_viable(diagnostics: ScanDiagnostics) -> None:
    if diagnostics.summary.text_length == 0:
        raise ReceiptProcessingError(
            code="ocr_no_text",
            message="Vi kunde inte läsa någon text från kvittobilden.",
            stage="ocr",
            suggestions=[
                "Fotografera kvittot i bättre ljus.",
                "Se till att hela kvittot är med i bilden.",
                "Lägg in köpet manuellt om problemet kvarstår.",
            ],
        )

    if diagnostics.summary.item_count == 0 and "total_amount" in diagnostics.summary.missing_fields:
        raise ReceiptProcessingError(
            code="receipt_unreadable",
            message="Kvittot kunde inte tydas tillräckligt för att skapa köp.",
            stage="parsing",
            suggestions=[
                "Försök igen med en rakare och skarpare bild.",
                "Undvik skuggor och avskurna kanter.",
                "Använd manuell registrering om kvittot är svårt att läsa.",
            ],
        )


def _receipt_model_to_schema(model: ReceiptModel) -> Receipt:
    merchant_name = model.merchant.name if model.merchant else None

    return Receipt(
        id=model.id,
        merchant_name=merchant_name,
        purchase_datetime=model.purchase_datetime,
        total_amount=float(model.total_amount) if model.total_amount is not None else None,
        currency=model.currency,
        source="manual" if is_manual_receipt(model) else "scan",
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
async def demo_receipt(request: Request, db: Session = Depends(get_db_session)) -> ReceiptScanResult:
    start = perf_counter()
    parsed_receipt = parse_receipt_text(_DEMO_RECEIPT_TEXT)
    normalized = _normalize_text(_DEMO_RECEIPT_TEXT)
    receipt = create_receipt_from_normalized(db, normalized, raw_text=_DEMO_RECEIPT_TEXT)
    processing_ms = int((perf_counter() - start) * 1000)
    diagnostics = analyze_scan(
        ocr_result=OCRResult(
            raw_text=_DEMO_RECEIPT_TEXT,
            blocks=[OCRBlock(lines=[OCRLine(text=line) for line in _DEMO_RECEIPT_TEXT.splitlines() if line])],
            provider="demo",
            meta={"source": "demo"},
        ),
        parsed_receipt=parsed_receipt,
        normalized_receipt=normalized,
    )
    return _build_receipt_response(
        _receipt_model_to_schema(receipt),
        processing_ms=processing_ms,
        diagnostics=diagnostics,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/scan", response_model=ReceiptScanResult)
async def scan_receipt(
    request: Request,
    image: UploadFile = File(...),
    db: Session = Depends(get_db_session),
) -> ReceiptScanResult:
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are supported in MVP")

    ocr_client = get_ocr_client()
    ingestion = create_receipt_ingestion(
        db,
        source="upload",
        original_filename=image.filename,
        content_type=image.content_type,
    )

    start = perf_counter()
    try:
        content = await image.read()
        if not content:
            raise ReceiptProcessingError(
                code="empty_upload",
                message="Den uppladdade bilden var tom.",
                stage="upload",
                suggestions=["Ta en ny bild av kvittot och försök igen."],
            )

        pipeline_output = await run_ocr_pipeline(ocr_client, content)
        ocr_record = record_ocr_result(db, ingestion=ingestion, ocr_result=pipeline_output.ocr_result)
        parsed_records = record_parsed_line_items(
            db,
            ocr_result_record=ocr_record,
            parsed_receipt=pipeline_output.parsed_receipt,
        )
        normalized = normalize_receipt(pipeline_output.parsed_receipt)
        diagnostics = analyze_scan(
            pipeline_output.ocr_result,
            pipeline_output.parsed_receipt,
            normalized,
        )
        _ensure_receipt_is_viable(diagnostics)

        ingestion.status = "processed" if diagnostics.status == "complete" else "partial"
        ingestion.processed_at = utc_now()
        ingestion.error_message = None

        persisted = create_receipt_from_normalized(
            db,
            normalized,
            raw_text=pipeline_output.ocr_result.raw_text,
            ingestion=ingestion,
            parsed_line_items=parsed_records,
        )
        elapsed_ms = int((perf_counter() - start) * 1000)

        if diagnostics.status == "partial":
            logger.warning(
                "receipt_scan_partial request_id=%s ingestion_id=%s warnings=%s",
                getattr(request.state, "request_id", None),
                ingestion.id,
                [warning.code for warning in diagnostics.warnings],
            )

        return _build_receipt_response(
            _receipt_model_to_schema(persisted),
            processing_ms=elapsed_ms,
            diagnostics=diagnostics,
            request_id=getattr(request.state, "request_id", None),
        )
    except ReceiptProcessingError as exc:
        ingestion.status = "failed"
        ingestion.processed_at = utc_now()
        ingestion.error_message = exc.message
        db.add(ingestion)
        db.commit()
        raise
    except Exception:
        ingestion.status = "failed"
        ingestion.processed_at = utc_now()
        ingestion.error_message = "Unexpected processing error"
        db.add(ingestion)
        db.commit()
        raise


@router.post("/manual", response_model=Receipt, status_code=201)
async def create_manual_receipt_endpoint(
    payload: ManualReceiptCreate,
    db: Session = Depends(get_db_session),
) -> Receipt:
    receipt = create_manual_receipt(
        db,
        name=payload.name,
        merchant_name=payload.merchant_name,
        price=payload.price,
        quantity=payload.quantity,
        currency=payload.currency,
        purchase_datetime=payload.purchase_datetime,
    )
    return _receipt_model_to_schema(receipt)


@router.patch("/manual/{receipt_id}", response_model=Receipt)
async def update_manual_receipt_endpoint(
    receipt_id: UUID,
    payload: ManualReceiptUpdate,
    db: Session = Depends(get_db_session),
) -> Receipt:
    receipt = get_receipt(db, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if not is_manual_receipt(receipt):
        raise HTTPException(status_code=400, detail="Only manual receipts can be updated")

    updated = update_manual_receipt(
        db,
        receipt=receipt,
        name=payload.name,
        merchant_name=payload.merchant_name,
        price=payload.price,
        quantity=payload.quantity,
        purchase_datetime=payload.purchase_datetime,
    )
    return _receipt_model_to_schema(updated)


@router.delete("/manual/{receipt_id}", status_code=204)
async def delete_manual_receipt_endpoint(
    receipt_id: UUID,
    db: Session = Depends(get_db_session),
) -> Response:
    receipt = get_receipt(db, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")
    if not is_manual_receipt(receipt):
        raise HTTPException(status_code=400, detail="Only manual receipts can be deleted")

    delete_receipt(db, receipt)
    return Response(status_code=204)


@router.get("", response_model=list[Receipt])
async def list_receipts_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db_session),
) -> list[Receipt]:
    receipts = list_receipts(db, limit=limit, offset=offset)
    return [_receipt_model_to_schema(r) for r in receipts]
