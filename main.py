from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger
import os
import sys
from dotenv import load_dotenv

from app.models import (
    AddressMatchRequest,
    AddressMatchResponse,
    BatchAddressMatchRequest,
    BatchAddressMatchResponse,
)
from app.matcher import AddressMatcher, AddressMatchingError
from app.config import AddressMatchingConfig
from app.logging_utils import format_address_for_log
from app.auth import APIKeyMiddleware

# Load environment variables before building config
load_dotenv()

# Build runtime config from defaults + optional file + env overrides
_config_manager = AddressMatchingConfig(
    config_file=os.getenv('CONFIG_FILE'),
    region=os.getenv('ADDRESS_MATCHING_REGION', 'US'),
)
_matcher_config = _config_manager.to_matcher_config()
_api_settings = _config_manager.to_api_settings()

# Apply configured log level
logger.remove()
logger.add(sys.stderr, level=_matcher_config.get('log_level', 'INFO'))

app = FastAPI(
    title="Address Matching Service",
    description="A RESTful microservice for address matching with fuzzy matching, ML, and geospatial validation",
    version="1.0.0"
)

# CORS — comma-separated origins via CORS_ORIGINS (default * for local use)
_cors_origins = _api_settings["cors_origins"]
_allow_credentials = _cors_origins != ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# API key auth (enabled only when API_KEY is set)
app.add_middleware(APIKeyMiddleware, api_key=_api_settings.get("api_key"))

# Initialize the address matcher with wired configuration
matcher = AddressMatcher(_matcher_config)
logger.info(
    "AddressMatcher ready "
    f"(region={_matcher_config.get('default_region')}, "
    f"ml={_matcher_config.get('use_ml_model')}, "
    f"geospatial={_matcher_config.get('use_geospatial')}, "
    f"cors_origins={_cors_origins}, "
    f"api_key_required={bool(_api_settings.get('api_key'))})"
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
    Returns 503 if required features are enabled but unavailable.
    """
    components = matcher.get_component_status()
    checks = {
        "address_parser": components.get("address_parser", False),
        "region_detection": components.get("region_detection", False),
    }
    issues = []

    if components.get("geospatial_enabled") and not components.get("geopy"):
        issues.append("geospatial enabled but geopy unavailable")
    if components.get("ml_model_enabled") and not components.get("ml_model_ready"):
        issues.append("ml model enabled but not ready")

    ready = all(checks.values()) and not issues
    payload = {
        "status": "ready" if ready else "not_ready",
        "checks": checks,
        "components": components,
        "issues": issues,
    }
    if not ready:
        response.status_code = 503
    return payload


@app.post("/match-addresses", response_model=AddressMatchResponse)
async def match_addresses(request: AddressMatchRequest):
    """
    Match two addresses and return similarity scores and decision.
    """
    try:
        logger.info(
            "Matching addresses: "
            f"'{format_address_for_log(request.address1)}' vs "
            f"'{format_address_for_log(request.address2)}'"
        )
        result = await matcher.match_addresses(request.address1, request.address2)
        logger.info(f"Match result: {result.match} (confidence: {result.confidence_score})")
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
    """
    Match multiple address pairs in one request.
    """
    try:
        logger.info(
            f"Batch matching {len(request.pairs)} pair(s)"
            + (f" region={request.region}" if request.region else "")
        )
        pairs = [(p.address1, p.address2) for p in request.pairs]
        results = await matcher.batch_match_addresses(pairs, region=request.region)
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


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=_matcher_config.get('api_host', '0.0.0.0'),
        port=int(_matcher_config.get('api_port', 8000)),
    )
