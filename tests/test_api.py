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
        "RATE_LIMITING": "false",
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
    main_module = _reload_app(
        monkeypatch,
        RATE_LIMITING="false",
    )
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


def test_rate_limit_returns_429(monkeypatch):
    main_module = _reload_app(
        monkeypatch,
        RATE_LIMITING="true",
        MAX_REQUESTS_PER_MINUTE="2",
    )
    payload = {
        "address1": "123 Main St, Anytown, CA 90210",
        "address2": "123 Main Street, Anytown, CA 90210",
    }
    with TestClient(main_module.app) as test_client:
        assert test_client.post("/match-addresses", json=payload).status_code == 200
        assert test_client.post("/match-addresses", json=payload).status_code == 200
        limited = test_client.post("/match-addresses", json=payload)
        assert limited.status_code == 429
        assert limited.json()["detail"] == "Rate limit exceeded"
        # Health remains available
        assert test_client.get("/health").status_code == 200


def test_metrics_and_request_id(client):
    test_client, _ = client
    response = test_client.get("/metrics")
    assert response.status_code == 200
    assert "address_matching_http_requests_total" in response.text

    match = test_client.post(
        "/match-addresses",
        headers={"X-Request-ID": "test-req-123"},
        json={
            "address1": "123 Main St, Anytown, CA 90210",
            "address2": "123 Main Street, Anytown, CA 90210",
        },
    )
    assert match.status_code == 200
    assert match.headers.get("X-Request-ID") == "test-req-123"

    metrics_resp = test_client.get("/metrics")
    assert "address_matching_match_requests_total" in metrics_resp.text


def test_google_provider_requires_api_key():
    from app.geocoders import build_provider

    provider = build_provider("google", api_key=None)
    assert provider.available is False
    assert provider.name == "google"


def test_none_geocoding_provider():
    from app.geocoding_service import GeocodingService

    service = GeocodingService(provider="none", enabled=True)
    assert service.geopy_available is False


def test_region_registry_is_single_source():
    from app.regions import RegionRegistry
    from app.fuzzy_matcher import RegionAwareWeights
    from app.rule_based_filter import RegionSpecificRules

    assert RegionAwareWeights.get_weights("IN") == RegionRegistry.get_weights("IN")
    assert RegionSpecificRules.get_config("DE") == RegionRegistry.get_rules("DE")
    assert "IN" in RegionRegistry.supported_regions()


def test_memory_rate_limit_backend():
    from app.rate_limit_backend import MemoryRateLimitBackend

    backend = MemoryRateLimitBackend()
    assert backend.allow("k", 2, 60.0)[0] is True
    assert backend.allow("k", 2, 60.0)[0] is True
    allowed, retry = backend.allow("k", 2, 60.0)
    assert allowed is False
    assert retry >= 1


def test_redis_backend_falls_back_without_url():
    from app.rate_limit_backend import build_rate_limit_backend, MemoryRateLimitBackend

    backend = build_rate_limit_backend("redis", redis_url=None)
    assert isinstance(backend, MemoryRateLimitBackend)


def test_tracing_noop_without_endpoint(monkeypatch):
    from fastapi import FastAPI

    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    from app.tracing import setup_tracing

    assert setup_tracing(FastAPI()) is False


def test_train_from_features_csv(tmp_path):
    from app.ml_model import AddressMatchingMLModel

    model = AddressMatchingMLModel(
        model_path=str(tmp_path / "m.pkl"),
        auto_train=False,
    )
    accuracy = model.train_from_features_csv(
        "data/sample_features.csv",
        save=True,
    )
    assert model.is_trained is True
    assert 0.0 <= accuracy <= 1.0
    assert (tmp_path / "m.pkl").exists()


def test_train_from_pairs_csv(tmp_path):
    from app.ml_model import AddressMatchingMLModel

    model = AddressMatchingMLModel(
        model_path=str(tmp_path / "pairs.pkl"),
        auto_train=False,
    )
    accuracy = model.train_from_labeled_pairs_csv(
        "data/sample_labeled_pairs.csv",
        save=True,
    )
    assert model.is_trained is True
    assert 0.0 <= accuracy <= 1.0
