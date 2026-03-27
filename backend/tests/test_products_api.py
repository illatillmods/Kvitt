from tests.conftest import create_test_client


def test_product_insights_after_demo_receipt():
    client = create_test_client()

    # Seed with a demo receipt
    demo_response = client.get("/api/v1/receipts/demo")
    assert demo_response.status_code == 200

    response = client.get("/api/v1/products/insights")
    assert response.status_code == 200
    insights = response.json()
    assert isinstance(insights, list)
    assert len(insights) >= 1

    first = insights[0]
    assert "normalized_name" in first
    assert "total_spend" in first
    assert "purchase_count" in first


def test_product_search_returns_normalized_matches_and_traceability():
    client = create_test_client()

    demo_response = client.get("/api/v1/receipts/demo")
    assert demo_response.status_code == 200

    response = client.get("/api/v1/products/search?q=energy")
    assert response.status_code == 200

    payload = response.json()
    assert payload["summary"]["query"] == "energy"
    assert payload["summary"]["purchase_count"] >= 1
    assert len(payload["matched_products"]) >= 1
    assert len(payload["purchases"]) >= 1

    first_purchase = payload["purchases"][0]
    assert first_purchase["normalized_name"]
    assert first_purchase["raw_description"]
    assert "receipt_id" in first_purchase
    assert payload["summary"]["top_time_of_day"] is None
    assert payload["access"]["tier"] == "free"
    assert "deeper_trends" in payload["access"]["locked_features"]
    assert payload["weekday_pattern"] == []


def test_product_search_includes_deeper_trends_for_premium():
    client = create_test_client()

    demo_response = client.get("/api/v1/receipts/demo")
    assert demo_response.status_code == 200

    response = client.get("/api/v1/products/search?q=energy", headers={"X-Kvitt-Tier": "premium"})
    assert response.status_code == 200

    payload = response.json()
    assert payload["access"]["tier"] == "premium"
    assert "deeper_trends" in payload["access"]["enabled_features"]
    assert isinstance(payload["weekday_pattern"], list)
    assert len(payload["weekday_pattern"]) >= 1


def test_product_search_suggestions_return_normalized_labels():
    client = create_test_client()

    demo_response = client.get("/api/v1/receipts/demo")
    assert demo_response.status_code == 200

    response = client.get("/api/v1/products/suggestions?q=en")
    assert response.status_code == 200

    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= 1
    assert "label" in payload[0]
    assert "type" in payload[0]
    assert payload[0]["type"] in {"product", "category"}
