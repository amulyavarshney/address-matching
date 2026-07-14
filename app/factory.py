"""Application and matcher factories for library and server use."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from loguru import logger

from app.auth import APIKeyMiddleware
from app.rate_limit import RateLimitMiddleware
from app.observability import RequestIdMiddleware, metrics, get_request_id
from app.config import AddressMatchingConfig
from app.logging_utils import format_address_for_log
from app.matcher import AddressMatcher, AddressMatchingError
from app.models import (
    AddressMatchRequest,
    AddressMatchResponse,
    BatchAddressMatchRequest,
    BatchAddressMatchResponse,
)


def create_matcher(
    config: Optional[Dict[str, Any]] = None,
    *,
    region: str = "US",
    apply_env: bool = False,
    config_file: Optional[str] = None,
) -> AddressMatcher:
    """
    Build an AddressMatcher for library use.

    By default environment overrides are ignored so embedding the library is
    deterministic. Pass apply_env=True to honor process env / .env values.
    """
    if config is not None:
        return AddressMatcher(config)

    manager = AddressMatchingConfig(
        config_file=config_file,
        region=region,
        apply_env=apply_env,
    )
    return AddressMatcher(manager.to_matcher_config())


def create_app(
    config_manager: Optional[AddressMatchingConfig] = None,
    *,
    apply_env: bool = True,
) -> FastAPI:
    """
    Create a configured FastAPI application.

    Separates server wiring from import-time side effects so the matching
    library can be imported without starting an HTTP service.
    """
    manager = config_manager or AddressMatchingConfig(
        config_file=os.getenv("CONFIG_FILE"),
        region=os.getenv("ADDRESS_MATCHING_REGION", "US"),
        apply_env=apply_env,
    )
    matcher_config = manager.to_matcher_config()
    api_settings = manager.to_api_settings()

    logger.remove()
    logger.configure(extra={"request_id": "-"})
    logger.add(
        sys.stderr,
        level=matcher_config.get("log_level", "INFO"),
        format=(
            "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | "
            "request_id={extra[request_id]} | {message}"
        ),
    )

    app = FastAPI(
        title="Address Matching Service",
        description=(
            "A RESTful microservice for address matching with fuzzy matching, "
            "ML, and geospatial validation"
        ),
        version="1.2.0",
    )

    cors_origins = api_settings["cors_origins"]
    allow_credentials = cors_origins != ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    app.add_middleware(APIKeyMiddleware, api_key=api_settings.get("api_key"))
    app.add_middleware(
        RateLimitMiddleware,
        enabled=bool(api_settings.get("rate_limiting", True)),
        max_requests_per_minute=int(api_settings.get("max_requests_per_minute", 60)),
        backend_name=str(api_settings.get("rate_limit_backend", "memory")),
        redis_url=api_settings.get("redis_url"),
    )
    app.add_middleware(RequestIdMiddleware)

    # Optional OpenTelemetry (no-op unless OTEL_EXPORTER_OTLP_ENDPOINT is set)
    from app.tracing import setup_tracing

    setup_tracing(app, service_name="address-matching")

    matcher = AddressMatcher(matcher_config)
    app.state.matcher = matcher
    app.state.config_manager = manager
    app.state.matcher_config = matcher_config
    app.state.api_settings = api_settings

    logger.bind(request_id="-").info(
        "AddressMatcher ready "
        f"(region={matcher_config.get('default_region')}, "
        f"ml={matcher_config.get('use_ml_model')}, "
        f"geospatial={matcher_config.get('use_geospatial')}, "
        f"geocoding_provider={matcher_config.get('geocoding_provider')}, "
        f"cors_origins={cors_origins}, "
        f"api_key_required={bool(api_settings.get('api_key'))})"
    )

    def _log(message: str) -> None:
        logger.bind(request_id=get_request_id()).info(message)

    @app.get("/")
    async def root():
        return {"message": "Address Matching Service is running"}

    @app.get("/health")
    async def health():
        """Liveness probe — process is up."""
        return {"status": "healthy"}

    @app.get("/health/ready")
    async def health_ready(response: Response):
        """
        Readiness probe — core components are usable.
        Returns 503 when geospatial is enabled but provider is unavailable.
        ML falls back to heuristics when untrained, so it is a soft check.
        """
        components = matcher.get_component_status()
        checks = {
            "address_parser": components.get("address_parser", False),
            "region_detection": components.get("region_detection", False),
        }
        issues = []
        warnings = []

        if components.get("geospatial_enabled") and not components.get("geopy"):
            issues.append("geospatial enabled but geocoding provider unavailable")
        if components.get("ml_model_enabled") and not components.get("ml_model_ready"):
            warnings.append("ml model enabled but using heuristic fallback")

        ready = all(checks.values()) and not issues
        payload = {
            "status": "ready" if ready else "not_ready",
            "checks": checks,
            "components": components,
            "issues": issues,
            "warnings": warnings,
        }
        if not ready:
            response.status_code = 503
        return payload

    @app.get("/metrics")
    async def prometheus_metrics():
        """Prometheus-compatible metrics exposition."""
        return PlainTextResponse(
            metrics.render_prometheus(),
            media_type="text/plain; version=0.0.4; charset=utf-8",
        )

    @app.post("/match-addresses", response_model=AddressMatchResponse)
    async def match_addresses(request: AddressMatchRequest):
        try:
            _log(
                "Matching addresses: "
                f"'{format_address_for_log(request.address1)}' vs "
                f"'{format_address_for_log(request.address2)}'"
            )
            result = await matcher.match_addresses(
                request.address1, request.address2
            )
            metrics.observe_match(result.match)
            _log(
                f"Match result: {result.match} "
                f"(confidence: {result.confidence_score})"
            )
            return result
        except AddressMatchingError:
            metrics.observe_match_error()
            logger.bind(request_id=get_request_id()).exception(
                "Address matching failed"
            )
            raise HTTPException(
                status_code=500,
                detail="Internal server error during address matching",
            )
        except Exception:
            metrics.observe_match_error()
            logger.bind(request_id=get_request_id()).exception(
                "Unexpected error matching addresses"
            )
            raise HTTPException(
                status_code=500,
                detail="Internal server error during address matching",
            )

    @app.post("/match-addresses/batch", response_model=BatchAddressMatchResponse)
    async def match_addresses_batch(request: BatchAddressMatchRequest):
        try:
            _log(
                f"Batch matching {len(request.pairs)} pair(s)"
                + (f" region={request.region}" if request.region else "")
            )
            pairs = [(p.address1, p.address2) for p in request.pairs]
            results = await matcher.batch_match_addresses(
                pairs, region=request.region
            )
            for item in results:
                metrics.observe_match(item.match)
            return BatchAddressMatchResponse(results=results, count=len(results))
        except AddressMatchingError:
            metrics.observe_match_error()
            logger.bind(request_id=get_request_id()).exception(
                "Batch address matching failed"
            )
            raise HTTPException(
                status_code=500,
                detail="Internal server error during address matching",
            )
        except Exception:
            metrics.observe_match_error()
            logger.bind(request_id=get_request_id()).exception(
                "Unexpected error in batch address matching"
            )
            raise HTTPException(
                status_code=500,
                detail="Internal server error during address matching",
            )

    return app
