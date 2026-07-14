from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing import List, Optional
import os


def max_address_length() -> int:
    try:
        return max(1, int(os.getenv("MAX_ADDRESS_LENGTH", "500")))
    except ValueError:
        return 500


def max_batch_size() -> int:
    try:
        return max(1, int(os.getenv("MAX_BATCH_SIZE", "50")))
    except ValueError:
        return 50


class AddressMatchRequest(BaseModel):
    """Request model for address matching."""
    address1: str = Field(..., min_length=1)
    address2: str = Field(..., min_length=1)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "address1": "221B Baker St., London NW1 6XE, UK",
                "address2": "221-B Baker Street, NW1 6XE London, United Kingdom",
            }
        }
    )

    @field_validator("address1", "address2")
    @classmethod
    def strip_and_limit(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("address must not be blank")
        limit = max_address_length()
        if len(cleaned) > limit:
            raise ValueError(f"address exceeds max length of {limit}")
        return cleaned


class NormalizedAddress(BaseModel):
    """Normalized address components."""
    house_number: Optional[str] = None
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None


class ComponentSimilarities(BaseModel):
    """Similarity scores for address components."""
    house_number: Optional[float] = None
    street: Optional[float] = None
    city: Optional[float] = None
    postal_code: Optional[float] = None
    state: Optional[float] = None
    country: Optional[float] = None


class MatchDetails(BaseModel):
    """Detailed information about the address match."""
    normalized_address1: NormalizedAddress
    normalized_address2: NormalizedAddress
    component_similarities: ComponentSimilarities
    geospatial_distance_meters: Optional[float] = None
    rule_based_decision: bool
    ml_model_decision: Optional[bool] = None


class AddressMatchResponse(BaseModel):
    """Response model for address matching."""
    match: bool
    confidence_score: float
    details: MatchDetails

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "match": True,
                "confidence_score": 0.92,
                "details": {
                    "normalized_address1": {
                        "house_number": "221B",
                        "street": "Baker Street",
                        "city": "London",
                        "postal_code": "NW1 6XE",
                        "country": "UK",
                    },
                    "normalized_address2": {
                        "house_number": "221-B",
                        "street": "Baker Street",
                        "city": "London",
                        "postal_code": "NW1 6XE",
                        "country": "United Kingdom",
                    },
                    "component_similarities": {
                        "house_number": 0.9,
                        "street": 1.0,
                        "city": 1.0,
                        "postal_code": 1.0,
                        "country": 0.8,
                    },
                    "geospatial_distance_meters": 12.5,
                    "rule_based_decision": True,
                    "ml_model_decision": True,
                },
            }
        }
    )


class BatchAddressMatchRequest(BaseModel):
    """Request model for batch address matching."""
    pairs: List[AddressMatchRequest] = Field(
        ...,
        min_length=1,
        description="Address pairs to match",
    )
    region: Optional[str] = Field(
        default=None,
        description="Optional region code applied to all pairs",
        max_length=8,
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "region": "US",
                "pairs": [
                    {
                        "address1": "123 Main St, Anytown, CA 90210",
                        "address2": "123 Main Street, Anytown, CA 90210",
                    }
                ],
            }
        }
    )

    @field_validator("region")
    @classmethod
    def normalize_region(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        cleaned = value.strip().upper()
        return cleaned or None

    @model_validator(mode="after")
    def enforce_batch_limit(self):
        limit = max_batch_size()
        if len(self.pairs) > limit:
            raise ValueError(f"batch size exceeds max of {limit}")
        return self


class BatchAddressMatchResponse(BaseModel):
    """Response model for batch address matching."""
    results: List[AddressMatchResponse]
    count: int
