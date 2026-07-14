"""Application and matcher factories for library and server use."""

from __future__ import annotations

import os
import sys
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.auth import APIKeyMiddleware
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
    logger.add(sys.stderr, level=matcher_config.get("log_level", "INFO"))

    app = FastAPI(
        title="Address Matching Service",
        description=(
            "A RESTful microservice for address matching with fuzzy matching, "
            "ML, and geospatial validation"
        ),
        version="1.1.0",
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

    matcher = AddressMatcher(matcher_config)
    app.state.matcher = matcher
    app.state.config_manager = manager
    app.state.matcher_config = matcher_config
    app.state.api_settings = api_settings

    logger.info(
        "AddressMatcher ready "
        f"(region={matcher_config.get('default_region')}, "
        f"ml={matcher_config.get('use_ml_model')}, "
        f"geospatial={matcher_config.get('use_geospatial')}, "
        f"cors_origins={cors_origins}, "
        f"api_key_required={bool(api_settings.get('api_key'))})"
    )

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
        Returns 503 when geospatial is enabled but geopy is unavailable.
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
            issues.append("geospatial enabled but geopy unavailable")
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

    @app.post("/match-addresses", response_model=AddressMatchResponse)
    async def match_addresses(request: AddressMatchRequest):
        try:
            logger.info(
                "Matching addresses: "
                f"'{format_address_for_log(request.address1)}' vs "
                f"'{format_address_for_log(request.address2)}'"
            )
            result = await matcher.match_addresses(
                request.address1, request.address2
            )
            logger.info(
                f"Match result: {result.match} "
                f"(confidence: {result.confidence_score})"
            )
            return result
        except AddressMatchingError:
            logger.exception("Address matching failed")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during address matching",
            )
        except Exception:
            logger.exception("Unexpected error matching addresses")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during address matching",
            )

    @app.post("/match-addresses/batch", response_model=BatchAddressMatchResponse)
    async def match_addresses_batch(request: BatchAddressMatchRequest):
        try:
            logger.info(
                f"Batch matching {len(request.pairs)} pair(s)"
                + (f" region={request.region}" if request.region else "")
            )
            pairs = [(p.address1, p.address2) for p in request.pairs]
            results = await matcher.batch_match_addresses(
                pairs, region=request.region
            )
            return BatchAddressMatchResponse(results=results, count=len(results))
        except AddressMatchingError:
            logger.exception("Batch address matching failed")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during address matching",
            )
        except Exception:
            logger.exception("Unexpected error in batch address matching")
            raise HTTPException(
                status_code=500,
                detail="Internal server error during address matching",
            )

    return app
