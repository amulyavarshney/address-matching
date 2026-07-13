"""HTTP/API tests for the FastAPI surface."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """Import app with ML/geocoding disabled for fast deterministic tests."""
    monkeypatch.setenv("USE_ML_MODEL", "false")
    monkeypatch.setenv("USE_GEOSPATIAL", "false")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    # Ensure a clean import of main with the env above
    import importlib
    import main as main_module

    importlib.reload(main_module)
    with TestClient(main_module.app) as test_client:
        yield test_client, main_module


def test_root(client):
    test_client, _ = client
    response = test_client.get("/")
    assert response.status_code == 200
    assert "running" in response.json()["message"].lower()


def test_health_liveness(client):
    test_client, _ = client
    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_health_ready(client):
    test_client, _ = client
    response = test_client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["address_parser"] is True
    assert body["components"]["geospatial_enabled"] is False
    assert body["components"]["ml_model_enabled"] is False


def test_match_addresses_success(client):
    test_client, _ = client
    response = test_client.post(
        "/match-addresses",
        json={
            "address1": "123 Main Street, Anytown, CA 90210, USA",
            "address2": "123 Main St, Anytown, California 90210, United States",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert "match" in body
    assert "confidence_score" in body
    assert "details" in body
    assert body["confidence_score"] >= 0.0


def test_match_addresses_validation_error(client):
    test_client, _ = client
    response = test_client.post("/match-addresses", json={"address1": "only one"})
    assert response.status_code == 422


def test_match_addresses_internal_error_returns_500(client):
    test_client, main_module = client
    with patch.object(
        main_module.matcher,
        "match_addresses",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        response = test_client.post(
            "/match-addresses",
            json={
                "address1": "123 Main St, Anytown, CA 90210",
                "address2": "123 Main Street, Anytown, CA 90210",
            },
        )
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error during address matching"
