from sqlalchemy import select

from app.api.v1.endpoints import receipts as receipt_endpoints
from app.models.ocr_result import OcrResultRecord
from app.models.parsed_line_item_record import ParsedLineItemRecord
from app.models.receipt import Receipt
from app.models.receipt_ingestion import ReceiptIngestion
from app.services.ocr import OCRBlock, OCRClient, OCRLine, OCRResult
from tests.conftest import create_test_client
from tests.utils_db import db_test_session


class EmptyTextOCRClient:
    async def extract(self, image_bytes: bytes) -> OCRResult:  # type: ignore[override]
        return OCRResult(raw_text="", blocks=[], provider="test-empty", meta={})


class UnreadableReceiptOCRClient:
    async def extract(self, image_bytes: bytes) -> OCRResult:  # type: ignore[override]
        lines = ["TACK FOR IDAG", "VALKOMMEN TILLBAKA"]
        return OCRResult(
            raw_text="\n".join(lines),
            blocks=[OCRBlock(lines=[OCRLine(text=line) for line in lines])],
            provider="test-unreadable",
            meta={},
        )


class PartialReceiptOCRClient:
    async def extract(self, image_bytes: bytes) -> OCRResult:  # type: ignore[override]
        lines = [
            "NARBUTIKEN",
            "MYSTERY ITEM 12,50",
            "RB 250ML",
        ]
        return OCRResult(
            raw_text="\n".join(lines),
            blocks=[OCRBlock(lines=[OCRLine(text=line) for line in lines])],
            provider="test-partial",
            meta={"quality": "messy"},
        )


def _patch_ocr_client(monkeypatch, client: OCRClient) -> None:
    monkeypatch.setattr(receipt_endpoints, "get_ocr_client", lambda: client)


def test_scan_returns_structured_error_for_empty_ocr(monkeypatch):
    _patch_ocr_client(monkeypatch, EmptyTextOCRClient())
    client = create_test_client()

    response = client.post(
        "/api/v1/receipts/scan",
        files={"image": ("receipt.jpg", b"fake-image", "image/jpeg")},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "ocr_no_text"
    assert payload["error"]["stage"] == "ocr"
    assert payload["error"]["retryable"] is True
    assert payload["error"]["request_id"]
    assert response.headers["x-request-id"] == payload["error"]["request_id"]

    with db_test_session() as db:
        ingestion = db.execute(select(ReceiptIngestion)).scalar_one()
        assert ingestion.status == "failed"
        assert ingestion.error_message == "Vi kunde inte läsa någon text från kvittobilden."


def test_scan_returns_structured_error_for_unreadable_receipt(monkeypatch):
    _patch_ocr_client(monkeypatch, UnreadableReceiptOCRClient())
    client = create_test_client()

    response = client.post(
        "/api/v1/receipts/scan",
        files={"image": ("receipt.jpg", b"fake-image", "image/jpeg")},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "receipt_unreadable"
    assert payload["error"]["stage"] == "parsing"
    assert len(payload["error"]["suggestions"]) >= 1


def test_scan_returns_partial_result_and_persists_trace_records(monkeypatch):
    _patch_ocr_client(monkeypatch, PartialReceiptOCRClient())
    client = create_test_client()

    response = client.post(
        "/api/v1/receipts/scan",
        files={"image": ("receipt.jpg", b"fake-image", "image/jpeg")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "partial"
    warning_codes = {warning["code"] for warning in payload["warnings"]}
    assert "total_missing" in warning_codes
    assert "ambiguous_normalization" in warning_codes
    assert payload["summary"]["item_count"] == 2
    assert payload["request_id"]

    with db_test_session() as db:
        ingestion = db.execute(select(ReceiptIngestion)).scalar_one()
        assert ingestion.status == "partial"

        ocr_records = db.execute(select(OcrResultRecord)).scalars().all()
        parsed_records = db.execute(select(ParsedLineItemRecord)).scalars().all()
        receipts = db.execute(select(Receipt)).scalars().all()

        assert len(ocr_records) == 1
        assert len(parsed_records) == 2
        assert len(receipts) == 1
        assert receipts[0].ingestion_id == ingestion.id