from tests.conftest import create_test_client


def test_demo_receipt_returns_normalized_items_and_persists():
    client = create_test_client()

    response = client.get("/api/v1/receipts/demo")
    assert response.status_code == 200

    payload = response.json()
    assert payload["receipt"]["merchant_name"] == "ICA KVITTO"
    assert payload["receipt"]["currency"] == "SEK"
    assert len(payload["receipt"]["line_items"]) == 3
    assert {item["category"] for item in payload["receipt"]["line_items"]} >= {
        "energy_drink",
        "snacks",
    }

    # History endpoint should now return at least one receipt
    history = client.get("/api/v1/receipts")
    assert history.status_code == 200
    receipts = history.json()
    assert isinstance(receipts, list)
    assert len(receipts) >= 1
