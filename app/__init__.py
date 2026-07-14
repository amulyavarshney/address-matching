"""Public library API for address matching."""

from app.matcher import AddressMatcher, AddressMatchingError
from app.config import AddressMatchingConfig, RegionalConfig
from app.regions import RegionRegistry
from app.models import (
    AddressMatchRequest,
    AddressMatchResponse,
    BatchAddressMatchRequest,
    BatchAddressMatchResponse,
    NormalizedAddress,
    ComponentSimilarities,
    MatchDetails,
)
from app.factory import create_app, create_matcher

__all__ = [
    "AddressMatcher",
    "AddressMatchingError",
    "AddressMatchingConfig",
    "RegionalConfig",
    "RegionRegistry",
    "AddressMatchRequest",
    "AddressMatchResponse",
    "BatchAddressMatchRequest",
    "BatchAddressMatchResponse",
    "NormalizedAddress",
    "ComponentSimilarities",
    "MatchDetails",
    "create_app",
    "create_matcher",
]

__version__ = "1.2.0"
