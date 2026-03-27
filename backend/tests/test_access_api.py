from tests.conftest import create_test_client


def test_product_structure_defaults_to_free_core_and_premium_depth():
    client = create_test_client()

    response = client.get("/api/v1/access/product-structure")
    assert response.status_code == 200

    payload = response.json()
    assert payload["current_tier"] == "free"
    free_keys = {item["key"] for item in payload["free_foundation"]}
    premium_keys = {item["key"] for item in payload["premium_depth"]}

    assert "receipt_scanning" in free_keys
    assert "item_extraction" in free_keys
    assert "product_tracking" in free_keys
    assert "basic_statistics" in free_keys
    assert "advanced_habit_insights" in premium_keys
    assert "deeper_trends" in premium_keys