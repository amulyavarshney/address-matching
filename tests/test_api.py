"""HTTP/API tests for the FastAPI surface."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


def _reload_app(monkeypatch, **env):
    """Reload main with given env overrides."""
    defaults = {
        "USE_ML_MODEL": "false",
        "USE_GEOSPATIAL": "false",
        "LOG_LEVEL": "WARNING",
        "CORS_ORIGINS": "*",
        "ML_AUTO_TRAIN": "false",
    }
    defaults.update(env)
    for key, value in defaults.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    if "API_KEY" not in env:
        monkeypatch.delenv("API_KEY", raising=False)

    import importlib
    import main as main_module

    importlib.reload(main_module)
    return main_module


@pytest.fixture
def client(monkeypatch):
    main_module = _reload_app(monkeypatch)
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


def test_match_addresses_rejects_blank(client):
    test_client, _ = client
    response = test_client.post(
        "/match-addresses",
        json={"address1": "   ", "address2": "123 Main St"},
    )
    assert response.status_code == 422


def test_match_addresses_rejects_too_long(client):
    test_client, _ = client
    response = test_client.post(
        "/match-addresses",
        json={"address1": "x" * 501, "address2": "123 Main St"},
    )
    assert response.status_code == 422


def test_match_addresses_internal_error_returns_500(client):
    test_client, main_module = client
    with patch.object(
        main_module.app.state.matcher,
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


def test_batch_match_addresses(client):
    test_client, _ = client
    response = test_client.post(
        "/match-addresses/batch",
        json={
            "region": "US",
            "pairs": [
                {
                    "address1": "123 Main St, Anytown, CA 90210",
                    "address2": "123 Main Street, Anytown, CA 90210",
                },
                {
                    "address1": "1 Infinite Loop, Cupertino, CA 95014",
                    "address2": "1 Infinite Loop, Cupertino, California 95014",
                },
            ],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert len(body["results"]) == 2
    assert "match" in body["results"][0]


def test_batch_rejects_empty_pairs(client):
    test_client, _ = client
    response = test_client.post("/match-addresses/batch", json={"pairs": []})
    assert response.status_code == 422


def test_api_key_required_when_configured(monkeypatch):
    main_module = _reload_app(monkeypatch, API_KEY="secret-key")
    with TestClient(main_module.app) as test_client:
        denied = test_client.post(
            "/match-addresses",
            json={
                "address1": "123 Main St, Anytown, CA 90210",
                "address2": "123 Main Street, Anytown, CA 90210",
            },
        )
        assert denied.status_code == 401

        allowed = test_client.post(
            "/match-addresses",
            headers={"X-API-Key": "secret-key"},
            json={
                "address1": "123 Main St, Anytown, CA 90210",
                "address2": "123 Main Street, Anytown, CA 90210",
            },
        )
        assert allowed.status_code == 200
        assert test_client.get("/health").status_code == 200


def test_cors_origins_from_env(monkeypatch):
    main_module = _reload_app(
        monkeypatch,
        CORS_ORIGINS="https://app.example.com,https://admin.example.com",
    )
    with TestClient(main_module.app) as test_client:
        response = test_client.options(
            "/match-addresses",
            headers={
                "Origin": "https://app.example.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        assert response.status_code == 200
        assert (
            response.headers.get("access-control-allow-origin")
            == "https://app.example.com"
        )


def test_library_import_does_not_require_server():
    from app import AddressMatcher, create_matcher

    matcher = create_matcher(
        {"use_ml_model": False, "use_geospatial": False, "ml_auto_train": False}
    )
    assert isinstance(matcher, AddressMatcher)
