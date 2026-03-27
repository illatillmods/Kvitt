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
