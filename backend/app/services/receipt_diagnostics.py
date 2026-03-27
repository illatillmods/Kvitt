from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from app.services.normalization import NormalizedReceipt
from app.services.ocr import OCRResult
from app.services.parsing import ParsedReceipt


Severity = Literal["info", "warning", "error"]
ScanStatus = Literal["complete", "partial"]


@dataclass(slots=True)
class ScanWarning:
    code: str
    message: str
    severity: Severity = "warning"


@dataclass(slots=True)
class ScanSummary:
    item_count: int
    low_confidence_item_count: int
    ambiguous_item_count: int
    missing_fields: list[str] = field(default_factory=list)
    text_length: int = 0


@dataclass(slots=True)
class ScanDiagnostics:
    status: ScanStatus
    warnings: list[ScanWarning]
    summary: ScanSummary


def analyze_scan(
    ocr_result: OCRResult,
    parsed_receipt: ParsedReceipt,
    normalized_receipt: NormalizedReceipt,
) -> ScanDiagnostics:
    warnings: list[ScanWarning] = []
    missing_fields: list[str] = []
    text_length = len((ocr_result.raw_text or "").strip())
    item_count = len(parsed_receipt.line_items)
    low_confidence_item_count = sum(item.confidence < 0.6 for item in parsed_receipt.line_items)
    ambiguous_item_count = sum(
        item.classification_confidence < 0.55
        or item.classification_source == "fallback"
        or item.category is None
        for item in normalized_receipt.line_items
    )

    if not parsed_receipt.merchant_name:
        missing_fields.append("merchant_name")
        warnings.append(
            ScanWarning(
                code="merchant_missing",
                message="Butiksnamnet kunde inte läsas ut tydligt.",
            )
        )

    if not parsed_receipt.purchase_datetime:
        missing_fields.append("purchase_datetime")
        warnings.append(
            ScanWarning(
                code="purchase_datetime_missing",
                message="Köpdatum eller tid saknas i kvittotolkningen.",
                severity="info",
            )
        )

    if parsed_receipt.total_amount is None:
        missing_fields.append("total_amount")
        warnings.append(
            ScanWarning(
                code="total_missing",
                message="Totalsumman kunde inte läsas ut säkert.",
            )
        )

    if item_count == 0:
        warnings.append(
            ScanWarning(
                code="no_items_extracted",
                message="Inga tydliga köp kunde extraheras från kvittot.",
                severity="error",
            )
        )

    if low_confidence_item_count:
        warnings.append(
            ScanWarning(
                code="low_confidence_items",
                message=f"{low_confidence_item_count} rad(er) är osäkert tolkade.",
            )
        )

    if ambiguous_item_count:
        warnings.append(
            ScanWarning(
                code="ambiguous_normalization",
                message=f"{ambiguous_item_count} vara/varor kunde inte normaliseras entydigt.",
            )
        )

    if parsed_receipt.total_amount is not None and item_count > 0:
        extracted_total = sum((item.total_price or 0.0) for item in parsed_receipt.line_items)
        if extracted_total > 0 and abs(extracted_total - parsed_receipt.total_amount) > 1.0:
            warnings.append(
                ScanWarning(
                    code="partial_extraction",
                    message="Summan från varuraderna matchar inte kvittots total.",
                )
            )

    status: ScanStatus = "complete"
    if warnings:
        status = "partial"

    return ScanDiagnostics(
        status=status,
        warnings=warnings,
        summary=ScanSummary(
            item_count=item_count,
            low_confidence_item_count=low_confidence_item_count,
            ambiguous_item_count=ambiguous_item_count,
            missing_fields=missing_fields,
            text_length=text_length,
        ),
    )