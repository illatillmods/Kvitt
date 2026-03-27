from app.services.parsing import parse_receipt_text
from app.services.normalization import normalize_receipt
from app.services.product_normalization import classify_product
from app.services.product_normalization import engine
from app.services.product_normalization.models import NormalizationDecision


def test_normalization_handles_beer_energy_drink_and_chips():
    text = """KIOSK X
2024-05-01 12:00
ÖL 5,2% 50CL 2x 25,90
RB 250ML
CHIPS GRILL 19,90
MOMS 12% 10,00
SUMMA 71,70
"""

    parsed = parse_receipt_text(text)
    normalized = normalize_receipt(parsed)

    assert len(normalized.line_items) >= 2

    # Beer line
    beer = next(
        li
        for li in normalized.line_items
        if "ÖL" in li.raw_description or "OL" in li.raw_description.upper()
    )
    assert beer.category == "beer"
    assert "öl" in beer.normalized_name.lower()
    assert beer.classification_source == "rule"
    assert beer.classification_confidence >= 0.8

    # Energy drink abbreviation (RB -> Red Bull)
    rb = next(li for li in normalized.line_items if "RB" in li.raw_description)
    assert rb.category == "energy_drink"
    assert "red bull" in rb.normalized_name.lower()
    assert rb.classification_source == "mapping"
    assert rb.classification_confidence >= 0.8

    # Chips with flavor should stay chips but be categorized as snacks
    chips = next(li for li in normalized.line_items if "CHIPS" in li.raw_description.upper())
    assert chips.category == "snacks"
    assert "chips" in chips.normalized_name.lower()
    assert chips.classification_source == "rule"
    assert chips.classification_confidence >= 0.8


def test_classify_product_fallback_for_unknown_label():
    decision = classify_product("MYSTERY ITEM 123")
    assert decision.category == "other"
    assert decision.source == "fallback"
    assert 0.0 < decision.confidence <= 0.5
    # Name should be a lightly cleaned title-cased version
    assert decision.normalized_name.startswith("Mystery Item")


def test_classify_product_ai_semantic_categories_cover_manual_long_tail_items():
    coffee = classify_product("Islatte Havre")
    detergent = classify_product("Tvättmedel Color")
    headphones = classify_product("USB C Hörlurar")
    transport = classify_product("SL 30-dagarskort")

    assert coffee.category == "coffee_tea"
    assert coffee.source == "ai"

    assert detergent.category == "cleaning"
    assert detergent.source == "ai"

    assert headphones.category == "electronics"
    assert headphones.source == "ai"

    assert transport.category == "transport"
    assert transport.source == "ai"


def test_classify_product_prefers_openai_fallback_when_available(monkeypatch):
    monkeypatch.setattr(engine.rules_se, "apply_rules", lambda candidate: None)
    monkeypatch.setattr(engine.mappings_se, "lookup", lambda candidate: None)
    monkeypatch.setattr(
        engine.openai_classifier,
        "classify",
        lambda candidate: NormalizationDecision(
            normalized_name="Adobe Creative Cloud",
            category="subscription_service",
            confidence=0.88,
            source="ai",
            rule_id="openai.test",
        ),
    )
    monkeypatch.setattr(engine.ai_classifier, "classify", lambda candidate: None)

    decision = classify_product("ADOBE CC MARS 2026")

    assert decision.normalized_name == "Adobe Creative Cloud"
    assert decision.category == "subscription_service"
    assert decision.source == "ai"
    assert decision.rule_id == "openai.test"
