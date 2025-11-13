from pydantic import BaseModel
from typing import Optional, Dict, Any


class AddressMatchRequest(BaseModel):
    """Request model for address matching."""
    address1: str
    address2: str
    
    class Config:
        schema_extra = {
            "example": {
                "address1": "221B Baker St., London NW1 6XE, UK",
                "address2": "221-B Baker Street, NW1 6XE London, United Kingdom"
            }
        }


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
    
    class Config:
        schema_extra = {
            "example": {
                "match": True,
                "confidence_score": 0.92,
                "details": {
                    "normalized_address1": {
                        "house_number": "221B",
                        "street": "Baker Street",
                        "city": "London",
                        "postal_code": "NW1 6XE",
                        "country": "UK"
                    },
                    "normalized_address2": {
                        "house_number": "221-B",
                        "street": "Baker Street",
                        "city": "London",
                        "postal_code": "NW1 6XE",
                        "country": "United Kingdom"
                    },
                    "component_similarities": {
                        "house_number": 0.9,
                        "street": 1.0,
                        "city": 1.0,
                        "postal_code": 1.0,
                        "country": 0.8
                    },
                    "geospatial_distance_meters": 12.5,
                    "rule_based_decision": True,
                    "ml_model_decision": True
                }
            }
        } 