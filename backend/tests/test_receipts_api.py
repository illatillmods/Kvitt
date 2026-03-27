from tests.conftest import create_test_client


def test_demo_receipt_returns_normalized_items_and_persists():
    client = create_test_client()

    response = client.get("/api/v1/receipts/demo")
    assert response.status_code == 200

    payload = response.json()
    assert payload["receipt"]["merchant_name"] == "ICA KVITTO"
    assert payload["receipt"]["currency"] == "SEK"
    assert payload["status"] == "complete"
    assert len(payload["receipt"]["line_items"]) == 3
    assert payload["summary"]["item_count"] == 3
    assert payload["request_id"]
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


def test_manual_receipt_can_be_created_updated_and_deleted():
    client = create_test_client()

    create_response = client.post(
        "/api/v1/receipts/manual",
        json={
            "name": "Kaffe",
            "merchant_name": "Pressbyrån",
            "price": 45,
            "quantity": 1,
            "currency": "SEK",
        },
    )
    assert create_response.status_code == 201

    created = create_response.json()
    assert created["source"] == "manual"
    assert created["merchant_name"] == "Pressbyrån"
    assert created["line_items"][0]["raw_description"] == "Kaffe"
    assert created["line_items"][0]["total_price"] == 45
    assert created["line_items"][0]["category"] == "coffee_tea"

    history = client.get("/api/v1/receipts?limit=100")
    assert history.status_code == 200
    receipts = history.json()
    created_id = created["id"]
    assert any(receipt["id"] == created_id and receipt["source"] == "manual" for receipt in receipts)

    update_response = client.patch(
        f"/api/v1/receipts/manual/{created_id}",
        json={
            "name": "Islatte",
            "merchant_name": "7-Eleven",
            "price": 52,
            "quantity": 2,
        },
    )
    assert update_response.status_code == 200

    updated = update_response.json()
    assert updated["merchant_name"] == "7-Eleven"
    assert updated["line_items"][0]["raw_description"] == "Islatte"
    assert updated["line_items"][0]["quantity"] == 2
    assert updated["line_items"][0]["total_price"] == 52

    delete_response = client.delete(f"/api/v1/receipts/manual/{created_id}")
    assert delete_response.status_code == 204

    history_after_delete = client.get("/api/v1/receipts?limit=100")
    assert history_after_delete.status_code == 200
    deleted_ids = {receipt["id"] for receipt in history_after_delete.json()}
    assert created_id not in deleted_ids
