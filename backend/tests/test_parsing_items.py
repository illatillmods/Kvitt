from app.services.parsing import parse_receipt_text


def test_parses_complex_quantity_and_price_line():
    text = """KIOSK X
2024-05-01 12:00
ÖL 5,2% 50CL 2x 25,90
RB 250ML
CHIPS GRILL 19,90
MOMS 12% 10,00
SUMMA 71,70
"""

    parsed = parse_receipt_text(text)

    # Should classify three item-like lines; VAT and totals excluded.
    assert len(parsed.line_items) >= 2

    labels = [li.raw_description for li in parsed.line_items]
    assert any("ÖL" in label or "OL" in label for label in labels)
    assert any("CHIPS" in label.upper() for label in labels)

    # The beer line should have quantity 2 and a reasonable total
    beer = next(li for li in parsed.line_items if "ÖL" in li.original_line or "OL" in li.original_line.upper())
    assert beer.quantity == 2
    assert beer.unit_price is not None
    assert beer.total_price is not None
    assert beer.total_price == beer.unit_price * beer.quantity


def test_parses_lines_without_price_as_low_confidence_items():
    text = """BUTIK Y
RB 250ML
CHIPS GRILL
SUMMA 0,00
"""

    parsed = parse_receipt_text(text)

    # RB line might be recognized as a product descriptor
    products = [li for li in parsed.line_items if "RB" in li.original_line or "CHIPS" in li.original_line.upper()]
    assert len(products) >= 1

    for li in products:
        assert li.total_price is None or li.total_price == 0
        assert li.confidence <= 0.5
        assert "no_price_detected" in li.notes


def test_excludes_totals_and_vat_lines():
    text = """ICA KVITTO
MOMS 12% 10,00
MOMS 25% 12,50
ATT BETALA 200,00
"""

    parsed = parse_receipt_text(text)
    assert parsed.total_amount == 200.00
    assert parsed.line_items == []
