from typing import Optional, Dict, Any, Tuple
from loguru import logger

from app.models import AddressMatchResponse, MatchDetails, NormalizedAddress, ComponentSimilarities
from app.address_parser import AddressParser, RegionDetector
from app.fuzzy_matcher import FuzzyMatcher
from app.rule_based_filter import RuleBasedFilter
from app.geocoding_service import GeocodingService
from app.ml_model import AddressMatchingMLModel


class AddressMatchingError(Exception):
    """Raised when address matching fails due to an unexpected internal error."""


class AddressMatcher:
    """
    Region-aware address matcher integrating parse, fuzzy, rules, ML, and geocoding.

    Safe for concurrent use: region-specific components are created per call.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        self.parser = AddressParser()
        self.region_detector = RegionDetector()

        self.geocoding_service = GeocodingService(
            user_agent=self.config.get(
                'geocoding_user_agent', 'address-matching-service'
            ),
            timeout=int(self.config.get('geocoding_timeout', 10)),
        )
        self.ml_model = AddressMatchingMLModel(
            model_path=self.config.get('ml_model_path'),
            auto_train=bool(self.config.get('ml_auto_train', False)),
            distance_threshold=float(self.config.get('distance_threshold', 50.0)),
        )

        self.distance_threshold = self.config.get('distance_threshold', 50.0)
        self.use_ml_model = self.config.get('use_ml_model', True)
        self.use_geospatial = self.config.get('use_geospatial', True)
        self.auto_detect_region = self.config.get('auto_detect_region', True)
        self.default_region = self.config.get('default_region', 'US')
        self.region_thresholds = self.config.get('region_thresholds', {})

        logger.info("AddressMatcher initialized successfully with region awareness")

    def _region_components(
        self, region: str
    ) -> Tuple[FuzzyMatcher, RuleBasedFilter]:
        """Build region-specific components for a single match call (thread-safe)."""
        rule_config = dict(self.config.get('rules', {}) or {})
        if region in self.region_thresholds:
            rule_config.update(self.region_thresholds[region])
        return (
            FuzzyMatcher(region=region),
            RuleBasedFilter(config=rule_config, region=region),
        )

    def _empty_response(self) -> AddressMatchResponse:
        return AddressMatchResponse(
            match=False,
            confidence_score=0.0,
            details=MatchDetails(
                normalized_address1=NormalizedAddress(),
                normalized_address2=NormalizedAddress(),
                component_similarities=ComponentSimilarities(),
                geospatial_distance_meters=None,
                rule_based_decision=False,
                ml_model_decision=None,
            ),
        )

    def _resolve_region(
        self, address1: str, address2: str, region: Optional[str]
    ) -> str:
        if region:
            return region.upper()

        if not self.auto_detect_region:
            return self.default_region

        region1 = self.region_detector.detect_region(address1)
        region2 = self.region_detector.detect_region(address2)

        if region1 == region2:
            return region1
        if region1 != 'US' and region2 == 'US':
            return region1
        if region2 != 'US' and region1 == 'US':
            return region2

        logger.warning(
            f"Region mismatch: {region1} vs {region2}, "
            f"using default {self.default_region}"
        )
        return self.default_region

    async def match_addresses(
        self,
        address1: str,
        address2: str,
        region: Optional[str] = None,
    ) -> AddressMatchResponse:
        """
        Match two addresses using all available methods with region awareness.
        """
        if not (address1 or "").strip() or not (address2 or "").strip():
            return self._empty_response()

        try:
            detected_region = self._resolve_region(address1, address2, region)
            logger.info(f"Using region: {detected_region}")

            fuzzy_matcher, rule_filter = self._region_components(detected_region)

            normalized_addr1 = self.parser.normalize_and_parse(address1)
            normalized_addr2 = self.parser.normalize_and_parse(address2)

            component_similarities, overall_similarity = (
                fuzzy_matcher.get_similarity_details(
                    normalized_addr1, normalized_addr2, detected_region
                )
            )

            geospatial_distance = None
            geospatial_supports_match = None
            if self.use_geospatial:
                geospatial_result = (
                    await self.geocoding_service.validate_addresses_geospatially(
                        address1, address2, self.distance_threshold
                    )
                )
                geospatial_distance = geospatial_result.get('distance_meters')
                if geospatial_result.get('geocoding_successful'):
                    geospatial_supports_match = geospatial_result.get(
                        'within_threshold', False
                    )

            rule_based_decision = rule_filter.apply_rules(
                component_similarities,
                normalized_addr1,
                normalized_addr2,
                overall_similarity,
            )

            ml_model_decision = None
            ml_confidence = None
            if self.use_ml_model:
                ml_model_decision, ml_confidence = self.ml_model.predict(
                    component_similarities,
                    geospatial_distance,
                    overall_similarity,
                )

            final_match, final_confidence = self._make_final_decision(
                rule_based_decision,
                ml_model_decision,
                overall_similarity,
                geospatial_distance,
                ml_confidence,
                detected_region,
                geospatial_supports_match,
            )

            response = AddressMatchResponse(
                match=final_match,
                confidence_score=final_confidence,
                details=MatchDetails(
                    normalized_address1=normalized_addr1,
                    normalized_address2=normalized_addr2,
                    component_similarities=component_similarities,
                    geospatial_distance_meters=geospatial_distance,
                    rule_based_decision=rule_based_decision,
                    ml_model_decision=ml_model_decision,
                ),
            )

            logger.info(
                f"Address matching completed for region {detected_region}: "
                f"match={final_match}, confidence={final_confidence:.3f}"
            )
            return response

        except AddressMatchingError:
            raise
        except Exception as e:
            logger.exception("Unexpected error in address matching")
            raise AddressMatchingError(
                "Address matching failed due to an internal error"
            ) from e

    def _make_final_decision(
        self,
        rule_decision: bool,
        ml_decision: Optional[bool],
        overall_similarity: float,
        geospatial_distance: Optional[float],
        ml_confidence: Optional[float],
        region: str,
        geospatial_supports_match: Optional[bool] = None,
    ) -> tuple[bool, float]:
        """Make the final matching decision with region-specific logic."""
        if region == 'IN':
            return self._make_indian_decision(
                rule_decision,
                ml_decision,
                overall_similarity,
                geospatial_distance,
                ml_confidence,
                geospatial_supports_match,
            )
        if region in ['DE', 'NL', 'CH']:
            return self._make_germanic_decision(
                rule_decision,
                ml_decision,
                overall_similarity,
                geospatial_distance,
                ml_confidence,
                geospatial_supports_match,
            )
        if region == 'UK':
            return self._make_uk_decision(
                rule_decision,
                ml_decision,
                overall_similarity,
                geospatial_distance,
                ml_confidence,
                geospatial_supports_match,
            )
        return self._make_default_decision(
            rule_decision,
            ml_decision,
            overall_similarity,
            geospatial_distance,
            ml_confidence,
            geospatial_supports_match,
        )

    def _make_indian_decision(
        self,
        rule_decision: bool,
        ml_decision: Optional[bool],
        overall_similarity: float,
        geospatial_distance: Optional[float],
        ml_confidence: Optional[float],
        geospatial_supports_match: Optional[bool],
    ) -> tuple[bool, float]:
        if not rule_decision:
            confidence = 1.0 - overall_similarity if overall_similarity < 0.6 else 0.4
            return False, confidence

        if overall_similarity >= 0.6:
            confidence = overall_similarity
            if geospatial_supports_match:
                confidence = min(1.0, confidence + 0.15)
            elif geospatial_distance and geospatial_distance <= self.distance_threshold:
                confidence = min(1.0, confidence + 0.1)

            if ml_decision is not None and ml_confidence is not None:
                if ml_decision:
                    confidence = (confidence + ml_confidence) / 2
                else:
                    confidence = max(0.3, confidence - 0.2)
                    if confidence < 0.5:
                        return False, confidence

            return True, confidence

        return False, 1.0 - overall_similarity

    def _make_germanic_decision(
        self,
        rule_decision: bool,
        ml_decision: Optional[bool],
        overall_similarity: float,
        geospatial_distance: Optional[float],
        ml_confidence: Optional[float],
        geospatial_supports_match: Optional[bool],
    ) -> tuple[bool, float]:
        if not rule_decision or overall_similarity < 0.75:
            confidence = 1.0 - overall_similarity
            return False, confidence

        confidence = overall_similarity
        if geospatial_supports_match:
            confidence = min(1.0, confidence + 0.1)
        elif geospatial_distance and geospatial_distance <= self.distance_threshold:
            confidence = min(1.0, confidence + 0.05)

        if ml_decision is not None and ml_confidence is not None:
            if ml_decision and ml_confidence > 0.8:
                confidence = (confidence + ml_confidence) / 2
            elif not ml_decision:
                return False, max(0.2, confidence - 0.3)

        return True, confidence

    def _make_uk_decision(
        self,
        rule_decision: bool,
        ml_decision: Optional[bool],
        overall_similarity: float,
        geospatial_distance: Optional[float],
        ml_confidence: Optional[float],
        geospatial_supports_match: Optional[bool],
    ) -> tuple[bool, float]:
        if not rule_decision:
            confidence = 1.0 - overall_similarity
            return False, confidence

        if overall_similarity >= 0.7:
            confidence = overall_similarity
            if geospatial_supports_match:
                confidence = min(1.0, confidence + 0.1)
            elif geospatial_distance and geospatial_distance <= self.distance_threshold:
                confidence = min(1.0, confidence + 0.05)

            if ml_decision is not None and ml_confidence is not None:
                confidence = (confidence + ml_confidence) / 2

            return True, confidence

        return False, 1.0 - overall_similarity

    def _make_default_decision(
        self,
        rule_decision: bool,
        ml_decision: Optional[bool],
        overall_similarity: float,
        geospatial_distance: Optional[float],
        ml_confidence: Optional[float],
        geospatial_supports_match: Optional[bool],
    ) -> tuple[bool, float]:
        if not rule_decision:
            confidence = 1.0 - overall_similarity
            return False, confidence

        if ml_decision is not None and ml_confidence is not None:
            match = ml_decision
            confidence = ml_confidence

            if geospatial_supports_match:
                confidence = min(1.0, confidence + 0.1)
            elif geospatial_distance is not None:
                if geospatial_distance <= self.distance_threshold:
                    confidence = min(1.0, confidence + 0.05)
                elif geospatial_distance > 1000:
                    match = False
                    confidence = 0.8
        else:
            match = overall_similarity >= 0.7
            confidence = overall_similarity if match else 1.0 - overall_similarity

            if geospatial_supports_match:
                confidence = min(1.0, confidence + 0.1)
            elif geospatial_distance is not None:
                if geospatial_distance <= self.distance_threshold:
                    confidence = min(1.0, confidence + 0.05)
                elif geospatial_distance > 1000:
                    match = False
                    confidence = 0.8

        return match, confidence

    def update_config(self, new_config: Dict[str, Any]):
        self.config.update(new_config)
        self.distance_threshold = self.config.get(
            'distance_threshold', self.distance_threshold
        )
        self.use_ml_model = self.config.get('use_ml_model', self.use_ml_model)
        self.use_geospatial = self.config.get('use_geospatial', self.use_geospatial)
        self.auto_detect_region = self.config.get(
            'auto_detect_region', self.auto_detect_region
        )
        self.default_region = self.config.get('default_region', self.default_region)
        logger.info(f"AddressMatcher configuration updated: {list(new_config.keys())}")

    def get_component_status(self) -> Dict[str, Any]:
        ml_ready = bool(
            self.ml_model
            and self.use_ml_model
            and getattr(self.ml_model, 'sklearn_available', False)
            and getattr(self.ml_model, 'is_trained', False)
        )
        return {
            'address_parser': True,
            'libpostal': bool(getattr(self.parser, 'postal_available', False)),
            'region_detection': True,
            'geopy': bool(getattr(self.geocoding_service, 'geopy_available', False)),
            'geospatial_enabled': self.use_geospatial,
            'sklearn': bool(
                self.ml_model and getattr(self.ml_model, 'sklearn_available', False)
            ),
            'ml_model_enabled': self.use_ml_model,
            'ml_model_ready': ml_ready,
            'default_region': self.default_region,
        }

    async def batch_match_addresses(
        self,
        address_pairs: list[tuple[str, str]],
        region: Optional[str] = None,
    ) -> list[AddressMatchResponse]:
        results = []
        for addr1, addr2 in address_pairs:
            results.append(await self.match_addresses(addr1, addr2, region))
        return results

    def set_region_thresholds(self, region: str, thresholds: Dict[str, Any]):
        if 'region_thresholds' not in self.config:
            self.config['region_thresholds'] = {}
        self.config['region_thresholds'][region] = thresholds
        self.region_thresholds[region] = thresholds
        logger.info(f"Updated thresholds for region {region}: {thresholds}")

    def get_supported_regions(self) -> list[str]:
        return [
            'US', 'CA', 'UK', 'DE', 'FR', 'IT', 'ES', 'IN',
            'AU', 'NL', 'SE', 'NO', 'CH',
        ]
