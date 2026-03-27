from app.services.parsing import parse_receipt_text
from app.services.normalization import normalize_receipt


def test_parse_and_normalize_simple_swedish_receipt():
    text = """ICA KVITTO
2024-03-22 18:45
Red Bull 25,90
OL STARK 6-P 89,00
CHIPS DILL 19,90
SUMMA 134,80
"""

    parsed = parse_receipt_text(text)
    assert parsed.merchant_name.startswith("ICA")
    assert len(parsed.line_items) == 3

    # Ensure we preserve original lines and notes
    for item in parsed.line_items:
        assert item.original_line
        assert item.confidence > 0

    normalized = normalize_receipt(parsed)
    categories = {li.category for li in normalized.line_items}
    assert "energy_drink" in categories
    assert "beer" in categories or None in categories
    assert "snacks" in categories
