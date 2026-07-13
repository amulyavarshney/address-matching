from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger
import os
import sys
from dotenv import load_dotenv

from app.models import AddressMatchRequest, AddressMatchResponse
from app.matcher import AddressMatcher, AddressMatchingError
from app.config import AddressMatchingConfig
from app.logging_utils import format_address_for_log

# Load environment variables before building config
load_dotenv()

# Build runtime config from defaults + optional file + env overrides
_config_manager = AddressMatchingConfig(
    config_file=os.getenv('CONFIG_FILE'),
    region=os.getenv('ADDRESS_MATCHING_REGION', 'US'),
)
_matcher_config = _config_manager.to_matcher_config()

# Apply configured log level
logger.remove()
logger.add(sys.stderr, level=_matcher_config.get('log_level', 'INFO'))

app = FastAPI(
    title="Address Matching Service",
    description="A RESTful microservice for address matching with fuzzy matching, ML, and geospatial validation",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the address matcher with wired configuration
matcher = AddressMatcher(_matcher_config)
logger.info(
    "AddressMatcher ready "
    f"(region={_matcher_config.get('default_region')}, "
    f"ml={_matcher_config.get('use_ml_model')}, "
    f"geospatial={_matcher_config.get('use_geospatial')})"
)

@app.get("/")
async def root():
    return {"message": "Address Matching Service is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

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

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=_matcher_config.get('api_host', '0.0.0.0'),
        port=int(_matcher_config.get('api_port', 8000)),
    )
