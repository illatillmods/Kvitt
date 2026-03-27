from tests.conftest import create_test_client


def test_api_health_returns_service_metadata():
    client = create_test_client()

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "KVITT API",
        "environment": "local",
        "version": "0.1.0",
    }
