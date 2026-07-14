"""
Single source of truth for region-specific matching behavior.

Fuzzy weights and rule thresholds used at runtime are defined here.
Other modules should import from this registry instead of duplicating maps.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional


# Component weights for overall fuzzy similarity (must sum ~1.0)
REGIONAL_WEIGHTS: Dict[str, Dict[str, float]] = {
    "US": {
        "house_number": 0.25,
        "street": 0.30,
        "city": 0.20,
        "postal_code": 0.20,
        "state": 0.05,
        "country": 0.00,
    },
    "CA": {
        "house_number": 0.25,
        "street": 0.30,
        "city": 0.20,
        "postal_code": 0.20,
        "state": 0.05,
        "country": 0.00,
    },
    "UK": {
        "house_number": 0.20,
        "street": 0.35,
        "city": 0.25,
        "postal_code": 0.15,
        "state": 0.05,
        "country": 0.00,
    },
    "DE": {
        "house_number": 0.30,
        "street": 0.35,
        "city": 0.20,
        "postal_code": 0.15,
        "state": 0.00,
        "country": 0.00,
    },
    "FR": {
        "house_number": 0.25,
        "street": 0.35,
        "city": 0.25,
        "postal_code": 0.15,
        "state": 0.00,
        "country": 0.00,
    },
    "IT": {
        "house_number": 0.25,
        "street": 0.35,
        "city": 0.25,
        "postal_code": 0.15,
        "state": 0.00,
        "country": 0.00,
    },
    "ES": {
        "house_number": 0.25,
        "street": 0.35,
        "city": 0.25,
        "postal_code": 0.15,
        "state": 0.00,
        "country": 0.00,
    },
    "IN": {
        "house_number": 0.15,
        "street": 0.25,
        "city": 0.30,
        "postal_code": 0.25,
        "state": 0.05,
        "country": 0.00,
    },
    "AU": {
        "house_number": 0.25,
        "street": 0.30,
        "city": 0.20,
        "postal_code": 0.20,
        "state": 0.05,
        "country": 0.00,
    },
    "NL": {
        "house_number": 0.30,
        "street": 0.35,
        "city": 0.20,
        "postal_code": 0.15,
        "state": 0.00,
        "country": 0.00,
    },
    "SE": {
        "house_number": 0.25,
        "street": 0.35,
        "city": 0.25,
        "postal_code": 0.15,
        "state": 0.00,
        "country": 0.00,
    },
    "NO": {
        "house_number": 0.25,
        "street": 0.35,
        "city": 0.25,
        "postal_code": 0.15,
        "state": 0.00,
        "country": 0.00,
    },
    "CH": {
        "house_number": 0.30,
        "street": 0.35,
        "city": 0.20,
        "postal_code": 0.15,
        "state": 0.00,
        "country": 0.00,
    },
}

# Rule-based filter thresholds and flags
REGIONAL_RULES: Dict[str, Dict[str, Any]] = {
    "US": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.7,
        "city_threshold": 0.7,
        "house_number_threshold": 0.8,
        "overall_threshold": 0.7,
        "require_postal_code_match": False,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": True,
        "state_abbreviation_matching": True,
    },
    "CA": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.7,
        "city_threshold": 0.8,
        "house_number_threshold": 0.8,
        "overall_threshold": 0.7,
        "require_postal_code_match": False,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": True,
        "state_abbreviation_matching": True,
    },
    "UK": {
        "postal_code_threshold": 0.8,
        "street_threshold": 0.75,
        "city_threshold": 0.8,
        "house_number_threshold": 0.7,
        "overall_threshold": 0.7,
        "require_postal_code_match": False,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": True,
        "allow_house_names": True,
    },
    "DE": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.8,
        "city_threshold": 0.8,
        "house_number_threshold": 0.9,
        "overall_threshold": 0.75,
        "require_postal_code_match": True,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": False,
    },
    "FR": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.75,
        "city_threshold": 0.8,
        "house_number_threshold": 0.8,
        "overall_threshold": 0.7,
        "require_postal_code_match": False,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": True,
    },
    "IT": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.75,
        "city_threshold": 0.8,
        "house_number_threshold": 0.8,
        "overall_threshold": 0.7,
        "require_postal_code_match": False,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": True,
    },
    "ES": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.75,
        "city_threshold": 0.8,
        "house_number_threshold": 0.8,
        "overall_threshold": 0.7,
        "require_postal_code_match": False,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": True,
    },
    "IN": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.6,
        "city_threshold": 0.7,
        "house_number_threshold": 0.6,
        "overall_threshold": 0.65,
        "require_postal_code_match": True,
        "require_city_match": True,
        "require_street_match": False,
        "allow_partial_house_number": True,
        "allow_area_locality_matching": True,
    },
    "AU": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.75,
        "city_threshold": 0.8,
        "house_number_threshold": 0.8,
        "overall_threshold": 0.7,
        "require_postal_code_match": False,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": True,
        "state_abbreviation_matching": True,
    },
    "NL": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.8,
        "city_threshold": 0.8,
        "house_number_threshold": 0.9,
        "overall_threshold": 0.75,
        "require_postal_code_match": True,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": False,
    },
    "SE": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.75,
        "city_threshold": 0.8,
        "house_number_threshold": 0.8,
        "overall_threshold": 0.7,
        "require_postal_code_match": False,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": True,
    },
    "NO": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.75,
        "city_threshold": 0.8,
        "house_number_threshold": 0.8,
        "overall_threshold": 0.7,
        "require_postal_code_match": False,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": True,
    },
    "CH": {
        "postal_code_threshold": 0.9,
        "street_threshold": 0.8,
        "city_threshold": 0.8,
        "house_number_threshold": 0.9,
        "overall_threshold": 0.75,
        "require_postal_code_match": True,
        "require_city_match": True,
        "require_street_match": True,
        "allow_partial_house_number": False,
    },
}

REGION_META: Dict[str, Dict[str, Any]] = {
    "US": {"name": "United States", "geocoding_country_bias": "US", "transliteration": False},
    "CA": {"name": "Canada", "geocoding_country_bias": "CA", "transliteration": False},
    "UK": {"name": "United Kingdom", "geocoding_country_bias": "GB", "transliteration": False},
    "DE": {"name": "Germany", "geocoding_country_bias": "DE", "transliteration": False},
    "FR": {"name": "France", "geocoding_country_bias": "FR", "transliteration": False},
    "IT": {"name": "Italy", "geocoding_country_bias": "IT", "transliteration": False},
    "ES": {"name": "Spain", "geocoding_country_bias": "ES", "transliteration": False},
    "IN": {"name": "India", "geocoding_country_bias": "IN", "transliteration": True},
    "AU": {"name": "Australia", "geocoding_country_bias": "AU", "transliteration": False},
    "NL": {"name": "Netherlands", "geocoding_country_bias": "NL", "transliteration": False},
    "SE": {"name": "Sweden", "geocoding_country_bias": "SE", "transliteration": False},
    "NO": {"name": "Norway", "geocoding_country_bias": "NO", "transliteration": False},
    "CH": {"name": "Switzerland", "geocoding_country_bias": "CH", "transliteration": False},
}


class RegionRegistry:
    """Lookup helpers for region-specific matching configuration."""

    DEFAULT_REGION = "US"

    @classmethod
    def supported_regions(cls) -> List[str]:
        return sorted(set(REGIONAL_WEIGHTS) | set(REGIONAL_RULES) | set(REGION_META))

    @classmethod
    def normalize(cls, region: Optional[str]) -> str:
        if not region:
            return cls.DEFAULT_REGION
        code = region.strip().upper()
        return code if code in REGIONAL_RULES else cls.DEFAULT_REGION

    @classmethod
    def get_weights(cls, region: str) -> Dict[str, float]:
        code = cls.normalize(region)
        return deepcopy(REGIONAL_WEIGHTS.get(code, REGIONAL_WEIGHTS[cls.DEFAULT_REGION]))

    @classmethod
    def get_rules(cls, region: str) -> Dict[str, Any]:
        code = cls.normalize(region)
        return deepcopy(REGIONAL_RULES.get(code, REGIONAL_RULES[cls.DEFAULT_REGION]))

    @classmethod
    def get_meta(cls, region: str) -> Dict[str, Any]:
        code = cls.normalize(region)
        return deepcopy(REGION_META.get(code, REGION_META[cls.DEFAULT_REGION]))

    @classmethod
    def get_template(cls, region: str) -> Dict[str, Any]:
        """Full template compatible with AddressMatchingConfig expectations."""
        code = cls.normalize(region)
        meta = cls.get_meta(code)
        rules = cls.get_rules(code)
        weights = cls.get_weights(code)
        return {
            "name": meta.get("name", code),
            "fuzzy_matching": {
                "region_weights": weights,
                "transliteration_support": bool(meta.get("transliteration", False)),
                "case_sensitive": False,
            },
            "rule_based_filter": rules,
            "geocoding": {
                "country_bias": meta.get("geocoding_country_bias", code),
                "max_distance_threshold": 100.0 if code in {"US", "CA", "AU"} else 50.0,
                "use_structured_geocoding": True,
            },
            "ml_model": {
                "use_regional_features": True,
                "confidence_threshold": 0.7,
            },
            "address_parser": {
                "use_libpostal": True,
                "state_abbreviations": bool(rules.get("state_abbreviation_matching", False)),
            },
        }
