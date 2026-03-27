from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import List, Optional


@dataclass
class ParsedLineItem:
    """Structured representation of a probable item row.

    - raw_description: cleaned label portion of the line
    - quantity / unit_price / total_price: optional, filled when detectable
    - original_line: full original line for traceability
    - confidence: heuristic confidence 0–1 that this is an item row
    - notes: parsing notes for internal debugging
    """

    raw_description: str
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    total_price: Optional[float] = None
    original_line: str = ""
    confidence: float = 0.5
    notes: List[str] = field(default_factory=list)


@dataclass
class ParsedReceipt:
    merchant_name: Optional[str]
    purchase_datetime: Optional[datetime]
    total_amount: Optional[float]
    currency: str
    line_items: List[ParsedLineItem]


_PRICE_PATTERN = re.compile(r"(?P<amount>\d{1,4}[,.]\d{2})(?!\d)")
_DATE_PATTERN = re.compile(r"(20\d{2}-\d{2}-\d{2})[ T](\d{2}:\d{2})?")

# Heuristics for classifying / parsing Swedish receipt lines
_TOTAL_KEYWORDS = re.compile(r"\b(SUMMA|TOTAL|ATT BETALA|BETALA)\b", re.IGNORECASE)
_NON_ITEM_KEYWORDS = re.compile(
    r"\b(MOMS|VAT|RABATT|KORT|CARD|MASTERCARD|VISA|KONTANT|SWISH|CHANGE)\b",
    re.IGNORECASE,
)

_PRODUCT_HINTS = [
    "OL",  # ÖL often appears as OL in OCR
    "ÖL",
    "SNUS",
    "CHIPS",
    "RB",
    "RED BULL",
    "MONSTER",
    "POWER KING",
    "CL",
    "ML",
    "G",
]


def _parse_amount(s: str) -> float:
    return float(s.replace(",", "."))


def _looks_like_potential_item(line: str) -> bool:
    upper = line.upper()
    if _TOTAL_KEYWORDS.search(upper) or _NON_ITEM_KEYWORDS.search(upper):
        return False
    # Short or purely numeric lines are unlikely to be items
    if len(line.strip()) < 3:
        return False
    if not re.search(r"[A-ZÅÄÖ]", upper):
        return False
    return True


def _has_product_hint(line: str) -> bool:
    upper = line.upper()
    return any(hint in upper for hint in _PRODUCT_HINTS)


def parse_receipt_text(text: str, default_currency: str = "SEK") -> ParsedReceipt:
    """Rule-based Swedish-biased parser.

    - Assumes decimal comma or dot
    - Extracts merchant + datetime where possible
    - Identifies totals and VAT / payment lines and skips them as items
    - Produces probable item rows with partial data where necessary
    """

    raw_lines = [l for l in text.splitlines() if l.strip()]
    lines = [l.strip() for l in raw_lines]
    merchant_name: Optional[str] = None
    purchase_dt: Optional[datetime] = None
    total_amount: Optional[float] = None
    items: List[ParsedLineItem] = []

    for i, line in enumerate(lines):
        original_line = raw_lines[i]
        if i == 0:
            merchant_name = line[:80]

        # Try to extract date/time anywhere
        if not purchase_dt:
            m = _DATE_PATTERN.search(line)
            if m:
                try:
                    purchase_dt = datetime.fromisoformat(m.group(1) + (" " + m.group(2) if m.group(2) else ""))
                except ValueError:
                    pass

        # TOTAL / SUMMA line updates overall total but is not an item
        if _TOTAL_KEYWORDS.search(line):
            m = _PRICE_PATTERN.search(line)
            if m:
                try:
                    total_amount = _parse_amount(m.group("amount"))
                except ValueError:
                    pass
            continue

        # Skip obvious non-item lines like VAT, payment, card info
        if _NON_ITEM_KEYWORDS.search(line):
            continue

        if not _looks_like_potential_item(line):
            continue

        # Price detection (may be missing on some product descriptor lines)
        price_matches = list(_PRICE_PATTERN.finditer(line))
        quantity: Optional[float] = None
        unit_price: Optional[float] = None
        total_price: Optional[float] = None
        description = line
        notes: List[str] = []
        confidence = 0.5

        if price_matches:
            last_price_match = price_matches[-1]
            amount = _parse_amount(last_price_match.group("amount"))
            description = line[: last_price_match.start()].strip()

            # Quantity parsing like "2x Cola" or "Cola 2 ST"
            qty_match = re.search(r"(\d+)\s*[xX]", description)
            if qty_match:
                quantity = float(qty_match.group(1))
                description = description[: qty_match.start()].strip() or description[qty_match.end() :].strip()
                notes.append("quantity_from_2x")
            else:
                qty_match = re.search(r"(\d+)\s*(ST|PKT|PCK|PCS)", description, re.IGNORECASE)
                if qty_match:
                    quantity = float(qty_match.group(1))
                    notes.append("quantity_from_unit_token")

            if quantity is not None and quantity > 0:
                unit_price = amount
                total_price = amount * quantity
            else:
                total_price = amount

            confidence = 0.9
            notes.append("price_detected")
        else:
            # No price on this line: consider creating a low-confidence
            # candidate only if it looks like a product descriptor.
            if not _has_product_hint(line):
                continue
            description = line.strip()
            notes.append("no_price_detected")
            confidence = 0.3

        items.append(
            ParsedLineItem(
                raw_description=description or line,
                quantity=quantity,
                unit_price=unit_price,
                total_price=total_price,
                original_line=original_line,
                confidence=confidence,
                notes=notes,
            )
        )

    return ParsedReceipt(
        merchant_name=merchant_name,
        purchase_datetime=purchase_dt,
        total_amount=total_amount,
        currency=default_currency,
        line_items=items,
    )
