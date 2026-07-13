from typing import Optional, Dict, Any
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
    Enhanced address matcher that integrates all matching components with region awareness.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the address matcher with all components.
        
        Args:
            config: Configuration dictionary for various components
        """
        self.config = config or {}
        
        # Initialize components
        self.parser = AddressParser()
        self.region_detector = RegionDetector()
        
        # These will be initialized with region-specific settings
        self.fuzzy_matcher = None
        self.rule_filter = None
        
        # Initialize components that don't need region
        self.geocoding_service = GeocodingService(
            user_agent=self.config.get('geocoding_user_agent', 'address-matching-service'),
            timeout=int(self.config.get('geocoding_timeout', 10)),
        )
        self.ml_model = AddressMatchingMLModel(
            model_path=self.config.get('ml_model_path')
        )
        
        # Configuration parameters
        self.distance_threshold = self.config.get('distance_threshold', 50.0)  # meters
        self.use_ml_model = self.config.get('use_ml_model', True)
        self.use_geospatial = self.config.get('use_geospatial', True)
        self.auto_detect_region = self.config.get('auto_detect_region', True)
        self.default_region = self.config.get('default_region', 'US')
        
        # Region-specific thresholds
        self.region_thresholds = self.config.get('region_thresholds', {})
        
        logger.info("AddressMatcher initialized successfully with region awareness")
    
    def _initialize_region_components(self, region: str):
        """Initialize region-specific components."""
        # Initialize fuzzy matcher with region
        self.fuzzy_matcher = FuzzyMatcher(region=region)
        
        # Initialize rule filter with region
        rule_config = self.config.get('rules', {})
        if region in self.region_thresholds:
            rule_config.update(self.region_thresholds[region])
        
        self.rule_filter = RuleBasedFilter(config=rule_config, region=region)
        
        logger.debug(f"Initialized region-specific components for {region}")
    
    async def match_addresses(self, address1: str, address2: str, region: Optional[str] = None) -> AddressMatchResponse:
        """
        Match two addresses using all available methods with region awareness.
        
        Args:
            address1: First address string
            address2: Second address string
            region: Optional region override (auto-detected if not provided)
            
        Returns:
            AddressMatchResponse with detailed matching results
        """
        logger.info(f"Starting region-aware address matching process")
        
        try:
            # Step 1: Detect region if not provided
            detected_region = region
            if not detected_region and self.auto_detect_region:
                # Try to detect region from both addresses
                region1 = self.region_detector.detect_region(address1)
                region2 = self.region_detector.detect_region(address2)
                
                # Use the more specific region or fall back to default
                if region1 == region2:
                    detected_region = region1
                elif region1 != 'US' and region2 == 'US':  # US is default fallback
                    detected_region = region1
                elif region2 != 'US' and region1 == 'US':
                    detected_region = region2
                else:
                    detected_region = self.default_region
                    logger.warning(f"Region mismatch: {region1} vs {region2}, using default {detected_region}")
            
            if not detected_region:
                detected_region = self.default_region
            
            logger.info(f"Using region: {detected_region}")
            
            # Initialize region-specific components
            self._initialize_region_components(detected_region)
            
            # Step 2: Parse and normalize addresses
            logger.debug("Step 1: Parsing addresses")
            normalized_addr1 = self.parser.normalize_and_parse(address1)
            normalized_addr2 = self.parser.normalize_and_parse(address2)
            
            # Step 3: Compute fuzzy similarities with region awareness
            logger.debug("Step 2: Computing region-aware fuzzy similarities")
            component_similarities, overall_similarity = self.fuzzy_matcher.get_similarity_details(
                normalized_addr1, normalized_addr2, detected_region
            )
            
            # Step 4: Geospatial validation (if enabled)
            geospatial_distance = None
            geospatial_supports_match = None
            if self.use_geospatial:
                logger.debug("Step 3: Performing geospatial validation")
                geospatial_result = await self.geocoding_service.validate_addresses_geospatially(
                    address1, address2, self.distance_threshold
                )
                geospatial_distance = geospatial_result.get('distance_meters')
                # Only trust threshold when both addresses geocoded successfully.
                # GeocodingService returns `within_threshold` (not `match`).
                if geospatial_result.get('geocoding_successful'):
                    geospatial_supports_match = geospatial_result.get('within_threshold', False)
                else:
                    geospatial_supports_match = None
            
            # Step 5: Rule-based filtering with region awareness
            logger.debug("Step 4: Applying region-aware rule-based filtering")
            rule_based_decision = self.rule_filter.apply_rules(
                component_similarities, normalized_addr1, normalized_addr2, overall_similarity
            )
            
            # Step 6: ML model prediction (if enabled)
            ml_model_decision = None
            ml_confidence = None
            if self.use_ml_model:
                logger.debug("Step 5: Getting ML model prediction")
                # Use the existing ML model interface
                ml_model_decision, ml_confidence = self.ml_model.predict(
                    component_similarities, geospatial_distance, overall_similarity
                )
            
            # Step 7: Final decision logic with region awareness
            logger.debug("Step 6: Making region-aware final decision")
            final_match, final_confidence = self._make_final_decision(
                rule_based_decision, ml_model_decision, overall_similarity, 
                geospatial_distance, ml_confidence, detected_region, geospatial_supports_match
            )
            
            # Create detailed response
            details = MatchDetails(
                normalized_address1=normalized_addr1,
                normalized_address2=normalized_addr2,
                component_similarities=component_similarities,
                geospatial_distance_meters=geospatial_distance,
                rule_based_decision=rule_based_decision,
                ml_model_decision=ml_model_decision
            )
            
            response = AddressMatchResponse(
                match=final_match,
                confidence_score=final_confidence,
                details=details
            )
            
            logger.info(f"Address matching completed for region {detected_region}: match={final_match}, confidence={final_confidence:.3f}")
            return response
            
        except AddressMatchingError:
            raise
        except Exception as e:
            logger.exception("Unexpected error in address matching")
            raise AddressMatchingError("Address matching failed due to an internal error") from e
    
    def _prepare_ml_features(
        self,
        similarities: ComponentSimilarities,
        geospatial_distance: Optional[float],
        overall_similarity: float,
        region: str
    ) -> Dict[str, Any]:
        """Prepare enhanced ML features with region information."""
        features = {
            'overall_similarity': overall_similarity,
            'house_number_similarity': similarities.house_number or 0.0,
            'street_similarity': similarities.street or 0.0,
            'city_similarity': similarities.city or 0.0,
            'postal_code_similarity': similarities.postal_code or 0.0,
            'state_similarity': similarities.state or 0.0,
            'country_similarity': similarities.country or 0.0,
            'geospatial_distance': geospatial_distance or 1000.0,  # Default high distance
            'region': region,
            
            # Region-specific feature engineering
            'is_indian_address': 1.0 if region == 'IN' else 0.0,
            'is_european_address': 1.0 if region in ['UK', 'DE', 'FR', 'IT', 'ES', 'NL', 'SE', 'NO', 'CH'] else 0.0,
            'is_american_address': 1.0 if region in ['US', 'CA'] else 0.0,
            'is_oceanic_address': 1.0 if region == 'AU' else 0.0,
        }
        
        # Add region-specific computed features
        if region == 'IN':
            # Indian-specific features
            features['pincode_weight'] = (similarities.postal_code or 0.0) * 0.3
            features['city_flexibility'] = min(1.0, (similarities.city or 0.0) + 0.2)
        elif region in ['DE', 'NL', 'CH']:
            # Germanic address features
            features['house_number_precision'] = (similarities.house_number or 0.0) * 0.3
            features['postal_city_combo'] = ((similarities.postal_code or 0.0) + (similarities.city or 0.0)) / 2
        elif region == 'UK':
            # UK-specific features
            features['postcode_reliability'] = (similarities.postal_code or 0.0) * 0.25
            features['house_name_flexibility'] = 1.0 if (similarities.house_number or 0.0) > 0.3 else 0.0
        
        return features
    
    def _make_final_decision(
        self,
        rule_decision: bool,
        ml_decision: Optional[bool],
        overall_similarity: float,
        geospatial_distance: Optional[float],
        ml_confidence: Optional[float],
        region: str,
        geospatial_supports_match: Optional[bool] = None
    ) -> tuple[bool, float]:
        """
        Make the final matching decision based on all available signals with region awareness.
        
        Args:
            rule_decision: Decision from rule-based filter
            ml_decision: Decision from ML model (optional)
            overall_similarity: Overall fuzzy similarity score
            geospatial_distance: Distance in meters (optional)
            ml_confidence: ML model confidence (optional)
            region: Detected region
            geospatial_supports_match: Whether geospatial validation supports match
            
        Returns:
            Tuple of (final_decision, confidence_score)
        """
        # Region-specific decision logic
        if region == 'IN':
            # Indian addresses: prioritize pincode and be more lenient overall
            return self._make_indian_decision(
                rule_decision, ml_decision, overall_similarity, 
                geospatial_distance, ml_confidence, geospatial_supports_match
            )
        elif region in ['DE', 'NL', 'CH']:
            # Germanic addresses: strict precision required
            return self._make_germanic_decision(
                rule_decision, ml_decision, overall_similarity, 
                geospatial_distance, ml_confidence, geospatial_supports_match
            )
        elif region == 'UK':
            # UK addresses: postcode reliability, house name flexibility
            return self._make_uk_decision(
                rule_decision, ml_decision, overall_similarity, 
                geospatial_distance, ml_confidence, geospatial_supports_match
            )
        else:
            # Default logic for US/CA/AU and others
            return self._make_default_decision(
                rule_decision, ml_decision, overall_similarity, 
                geospatial_distance, ml_confidence, geospatial_supports_match
            )
    
    def _make_indian_decision(
        self, rule_decision: bool, ml_decision: Optional[bool], overall_similarity: float,
        geospatial_distance: Optional[float], ml_confidence: Optional[float],
        geospatial_supports_match: Optional[bool]
    ) -> tuple[bool, float]:
        """Make decision for Indian addresses."""
        # If rule-based filter says no match (especially for pincode), trust it
        if not rule_decision:
            confidence = 1.0 - overall_similarity if overall_similarity < 0.6 else 0.4
            return False, confidence
        
        # For Indian addresses, be more lenient if pincode matches
        if overall_similarity >= 0.6:  # Lower threshold for Indian addresses
            confidence = overall_similarity
            
            # Boost confidence if geospatial supports
            if geospatial_supports_match:
                confidence = min(1.0, confidence + 0.15)
            elif geospatial_distance and geospatial_distance <= self.distance_threshold:
                confidence = min(1.0, confidence + 0.1)
            
            # Use ML if available
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
        self, rule_decision: bool, ml_decision: Optional[bool], overall_similarity: float,
        geospatial_distance: Optional[float], ml_confidence: Optional[float],
        geospatial_supports_match: Optional[bool]
    ) -> tuple[bool, float]:
        """Make decision for German/Dutch/Swiss addresses."""
        # Germanic addresses require high precision
        if not rule_decision or overall_similarity < 0.75:
            confidence = 1.0 - overall_similarity
            return False, confidence
        
        # High precision required
        confidence = overall_similarity
        
        # Geospatial validation is important for Germanic addresses
        if geospatial_supports_match:
            confidence = min(1.0, confidence + 0.1)
        elif geospatial_distance and geospatial_distance > self.distance_threshold:
            confidence = max(0.1, confidence - 0.3)
            if geospatial_distance > 1000:  # Very large distance
                return False, 0.8
        
        # Use ML if available
        if ml_decision is not None and ml_confidence is not None:
            confidence = (confidence + ml_confidence) / 2
            return ml_decision, confidence
        
        return confidence >= 0.75, confidence
    
    def _make_uk_decision(
        self, rule_decision: bool, ml_decision: Optional[bool], overall_similarity: float,
        geospatial_distance: Optional[float], ml_confidence: Optional[float],
        geospatial_supports_match: Optional[bool]
    ) -> tuple[bool, float]:
        """Make decision for UK addresses."""
        # UK addresses: postcode is very reliable when present
        if not rule_decision:
            confidence = 1.0 - overall_similarity if overall_similarity < 0.7 else 0.3
            return False, confidence
        
        confidence = overall_similarity
        
        # UK postcode reliability boost
        if overall_similarity >= 0.7:
            confidence = min(1.0, confidence + 0.05)
        
        # Geospatial support
        if geospatial_supports_match:
            confidence = min(1.0, confidence + 0.1)
        
        # Use ML if available
        if ml_decision is not None and ml_confidence is not None:
            confidence = (confidence + ml_confidence) / 2
            return ml_decision, confidence
        
        return confidence >= 0.7, confidence
    
    def _make_default_decision(
        self, rule_decision: bool, ml_decision: Optional[bool], overall_similarity: float,
        geospatial_distance: Optional[float], ml_confidence: Optional[float],
        geospatial_supports_match: Optional[bool]
    ) -> tuple[bool, float]:
        """Make decision for US/CA/AU and other addresses (default logic)."""
        # If rule-based filter says no match, generally trust it (high precision)
        if not rule_decision:
            confidence = 1.0 - overall_similarity if overall_similarity < 0.7 else 0.3
            return False, confidence
        
        # If we have ML model prediction, use it as the primary signal
        if ml_decision is not None and ml_confidence is not None:
            # Adjust ML confidence based on geospatial validation
            adjusted_confidence = ml_confidence
            
            if geospatial_supports_match:
                # Geospatial validation supports the decision
                adjusted_confidence = min(1.0, adjusted_confidence + 0.1)
            elif geospatial_distance is not None:
                if geospatial_distance <= self.distance_threshold:
                    adjusted_confidence = min(1.0, adjusted_confidence + 0.1)
                else:
                    # Geospatial validation conflicts with the decision
                    if ml_decision:  # ML says match but distance is large
                        adjusted_confidence = max(0.1, adjusted_confidence - 0.2)
            
            return ml_decision, adjusted_confidence
        
        # Fallback to similarity-based decision
        match = overall_similarity >= 0.7
        confidence = overall_similarity if match else 1.0 - overall_similarity
        
        # Adjust based on geospatial distance
        if geospatial_supports_match:
            confidence = min(1.0, confidence + 0.1)
        elif geospatial_distance is not None:
            if geospatial_distance <= self.distance_threshold:
                confidence = min(1.0, confidence + 0.1)
            else:
                if match:  # High similarity but large distance
                    confidence = max(0.1, confidence - 0.3)
                    if geospatial_distance > 1000:  # Very large distance
                        match = False
                        confidence = 0.8
        
        return match, confidence
    
    def update_config(self, new_config: Dict[str, Any]):
        """
        Update configuration values.
        
        Args:
            new_config: Dictionary of new configuration values
        """
        self.config.update(new_config)
        
        # Update component configurations
        self.distance_threshold = self.config.get('distance_threshold', self.distance_threshold)
        self.use_ml_model = self.config.get('use_ml_model', self.use_ml_model)
        self.use_geospatial = self.config.get('use_geospatial', self.use_geospatial)
        self.auto_detect_region = self.config.get('auto_detect_region', self.auto_detect_region)
        self.default_region = self.config.get('default_region', self.default_region)
        
        logger.info(f"AddressMatcher configuration updated: {list(new_config.keys())}")
    
    def get_component_status(self) -> Dict[str, Any]:
        """
        Get the status of all matching components.
        
        Returns:
            Dictionary with component availability and configuration flags
        """
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
    
    async def batch_match_addresses(self, address_pairs: list[tuple[str, str]], region: Optional[str] = None) -> list[AddressMatchResponse]:
        """
        Match multiple address pairs efficiently with region awareness.
        
        Args:
            address_pairs: List of (address1, address2) tuples to match
            region: Optional region for all pairs (auto-detected if not provided)
            
        Returns:
            List of AddressMatchResponse objects
            
        Raises:
            AddressMatchingError: If any pair fails due to an internal error
        """
        results = []
        
        for addr1, addr2 in address_pairs:
            result = await self.match_addresses(addr1, addr2, region)
            results.append(result)
        
        return results
    
    def set_region_thresholds(self, region: str, thresholds: Dict[str, Any]):
        """
        Set region-specific thresholds.
        
        Args:
            region: Region code (e.g., 'US', 'IN', 'UK')
            thresholds: Dictionary of threshold values
        """
        if 'region_thresholds' not in self.config:
            self.config['region_thresholds'] = {}
        
        self.config['region_thresholds'][region] = thresholds
        self.region_thresholds[region] = thresholds
        
        logger.info(f"Updated thresholds for region {region}: {thresholds}")
    
    def get_supported_regions(self) -> list[str]:
        """Get list of supported regions."""
        return ['US', 'CA', 'UK', 'DE', 'FR', 'IT', 'ES', 'IN', 'AU', 'NL', 'SE', 'NO', 'CH'] 