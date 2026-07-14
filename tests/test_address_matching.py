import pytest
import asyncio
from unittest.mock import Mock, patch
import sys
import os
from typing import Dict, Any

# Add the parent directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import NormalizedAddress, ComponentSimilarities
from app.address_parser import AddressParser, RegionDetector
from app.fuzzy_matcher import FuzzyMatcher, TransliterationMatcher
from app.rule_based_filter import RuleBasedFilter
from app.matcher import AddressMatcher
from app.config import AddressMatchingConfig, RegionalConfig


class TestRegionDetection:
    """Test regional address detection functionality."""
    
    def setup_method(self):
        """Setup test components."""
        self.region_detector = RegionDetector()
    
    def test_us_address_detection(self):
        """Test detection of US addresses."""
        us_addresses = [
            "123 Main St, Anytown, CA 90210",
            "456 Oak Avenue, New York, NY 10001",
            "789 Pine Rd, Austin, TX 73301",
            "1600 Pennsylvania Avenue NW, Washington, DC 20500"
        ]
        
        for address in us_addresses:
            region = self.region_detector.detect_region(address)
            assert region == 'US', f"Failed to detect US region for: {address}"
    
    def test_uk_address_detection(self):
        """Test detection of UK addresses."""
        uk_addresses = [
            "10 Downing Street, London SW1A 2AA",
            "221B Baker Street, London NW1 6XE",
            "The Old Rectory, Little Wilbraham, Cambridge CB21 5JY",
            "Flat 2, 15 High Street, Edinburgh EH1 1SR"
        ]
        
        for address in uk_addresses:
            region = self.region_detector.detect_region(address)
            assert region == 'UK', f"Failed to detect UK region for: {address}"
    
    def test_german_address_detection(self):
        """Test detection of German addresses."""
        german_addresses = [
            "Musterstraße 123, 12345 Berlin",
            "Hauptstraße 45, 80331 München",
            "Am Markt 7, 20095 Hamburg",
            "Gartenweg 12, 50667 Köln"
        ]
        
        for address in german_addresses:
            region = self.region_detector.detect_region(address)
            assert region == 'DE', f"Failed to detect German region for: {address}"
    
    def test_indian_address_detection(self):
        """Test detection of Indian addresses."""
        indian_addresses = [
            "Flat 2B, Krishna Nagar, Pune 411001",
            "House No. 45, Sector 17, Chandigarh 160017",
            "123/4, M.G. Road, Bangalore 560001",
            "Plot 67, Banjara Hills, Hyderabad 500034"
        ]
        
        for address in indian_addresses:
            region = self.region_detector.detect_region(address)
            assert region == 'IN', f"Failed to detect Indian region for: {address}"
    
    def test_canadian_address_detection(self):
        """Test detection of Canadian addresses."""
        canadian_addresses = [
            "123 Main Street, Toronto, ON M5V 3A8",
            "456 Rue Saint-Denis, Montreal, QC H2X 3L4",
            "789 Granville Street, Vancouver, BC V6Z 1K3"
        ]
        
        for address in canadian_addresses:
            region = self.region_detector.detect_region(address)
            assert region == 'CA', f"Failed to detect Canadian region for: {address}"

    def test_no_false_positives_from_ambiguous_tokens(self):
        """US state codes / 'No.' must not map to Canada/India/Norway."""
        cases = [
            ("123 Main St, Anytown, CA 90210", "US"),
            ("100 Main St, Indianapolis, IN 46204", "US"),
            ("House No. 45, Sector 17, Chandigarh 160017", "IN"),
            ("Musterstraße 123, 12345 Berlin", "DE"),
        ]
        for address, expected in cases:
            assert self.region_detector.detect_region(address) == expected, address


class TestAddressParser:
    """Test region-specific address parsing functionality."""
    
    def setup_method(self):
        """Setup test components."""
        self.parser = AddressParser()
    
    def test_us_address_parsing(self):
        """Test parsing of US addresses."""
        address = "123 Main Street, Anytown, CA 90210, USA"
        normalized = self.parser.normalize_and_parse(address)
        
        assert normalized.house_number == "123"
        assert "MAIN" in normalized.street.upper()
        assert normalized.city.upper() == "ANYTOWN"
        assert normalized.state.upper() == "CA"
        assert normalized.postal_code == "90210"
        assert normalized.country.upper() in ["USA", "US", "UNITED STATES"]
    
    def test_uk_address_parsing(self):
        """Test parsing of UK addresses."""
        address = "10 Downing Street, London SW1A 2AA, UK"
        normalized = self.parser.normalize_and_parse(address)
        
        assert normalized.house_number == "10"
        assert "DOWNING" in normalized.street.upper()
        assert normalized.city.upper() == "LONDON"
        assert "SW1A 2AA" in normalized.postal_code.upper()
    
    def test_german_address_parsing(self):
        """Test parsing of German addresses."""
        address = "Musterstraße 123, 12345 Berlin, Deutschland"
        normalized = self.parser.normalize_and_parse(address)
        
        assert normalized.house_number == "123"
        assert "MUSTER" in normalized.street.upper()
        assert normalized.city.upper() == "BERLIN"
        assert normalized.postal_code == "12345"
    
    def test_indian_address_parsing(self):
        """Test parsing of Indian addresses."""
        address = "Flat 2B, Krishna Nagar, Pune 411001, Maharashtra, India"
        normalized = self.parser.normalize_and_parse(address)
        
        assert "2B" in normalized.house_number or "2B" in normalized.street
        assert "KRISHNA" in normalized.street.upper() or "NAGAR" in normalized.street.upper()
        assert normalized.city.upper() == "PUNE"
        assert normalized.postal_code == "411001"
    
    def test_french_address_parsing(self):
        """Test parsing of French addresses."""
        address = "123 Rue de la Paix, 75001 Paris, France"
        normalized = self.parser.normalize_and_parse(address)
        
        assert normalized.house_number == "123"
        assert "PAIX" in normalized.street.upper()
        assert normalized.city.upper() == "PARIS"
        assert normalized.postal_code == "75001"


class TestFuzzyMatcher:
    """Test region-aware fuzzy matching functionality."""
    
    def setup_method(self):
        """Setup test components."""
        self.us_matcher = FuzzyMatcher(region='US')
        self.uk_matcher = FuzzyMatcher(region='UK')
        self.german_matcher = FuzzyMatcher(region='DE')
        self.indian_matcher = FuzzyMatcher(region='IN')
    
    def test_us_address_matching(self):
        """Test fuzzy matching for US addresses."""
        addr1 = NormalizedAddress(
            house_number="123",
            street="MAIN STREET",
            city="ANYTOWN",
            state="CALIFORNIA",
            postal_code="90210",
            country="USA"
        )
        addr2 = NormalizedAddress(
            house_number="123",
            street="MAIN ST",
            city="ANYTOWN",
            state="CA",
            postal_code="90210",
            country="UNITED STATES"
        )
        
        similarities, overall = self.us_matcher.get_similarity_details(addr1, addr2)
        
        assert similarities.house_number > 0.9
        assert similarities.street > 0.8  # Should handle ST vs STREET
        assert similarities.city > 0.9
        assert similarities.state > 0.8  # Should handle CA vs CALIFORNIA
        assert similarities.postal_code > 0.9
        assert overall > 0.8
    
    def test_uk_address_matching(self):
        """Test fuzzy matching for UK addresses."""
        addr1 = NormalizedAddress(
            house_number="10",
            street="DOWNING STREET",
            city="LONDON",
            postal_code="SW1A 2AA",
            country="UK"
        )
        addr2 = NormalizedAddress(
            house_number="10",
            street="DOWNING ST",
            city="LONDON",
            postal_code="SW1A2AA",  # No space
            country="UNITED KINGDOM"
        )
        
        similarities, overall = self.uk_matcher.get_similarity_details(addr1, addr2)
        
        assert similarities.house_number > 0.9
        assert similarities.street > 0.8
        assert similarities.city > 0.9
        assert similarities.postal_code > 0.7  # Should handle spacing differences
        assert overall > 0.8
    
    def test_german_address_matching(self):
        """Test fuzzy matching for German addresses."""
        addr1 = NormalizedAddress(
            house_number="123",
            street="MUSTERSTRASSE",
            city="BERLIN",
            postal_code="12345",
            country="DEUTSCHLAND"
        )
        addr2 = NormalizedAddress(
            house_number="123",
            street="MUSTER STR",
            city="BERLIN",
            postal_code="12345",
            country="GERMANY"
        )
        
        similarities, overall = self.german_matcher.get_similarity_details(addr1, addr2)
        
        assert similarities.house_number > 0.9
        assert similarities.street > 0.7  # Should handle STRASSE vs STR
        assert similarities.city > 0.9
        assert similarities.postal_code > 0.9
        assert overall > 0.8
    
    def test_indian_address_matching(self):
        """Test fuzzy matching for Indian addresses."""
        addr1 = NormalizedAddress(
            house_number="2B",
            street="KRISHNA NAGAR",
            city="MUMBAI",
            state="MAHARASHTRA",
            postal_code="400001",
            country="INDIA"
        )
        addr2 = NormalizedAddress(
            house_number="2-B",
            street="KRISHNA NGR",
            city="BOMBAY",  # Old name for Mumbai
            state="MH",
            postal_code="400001",
            country="INDIA"
        )
        
        similarities, overall = self.indian_matcher.get_similarity_details(addr1, addr2)
        
        assert similarities.house_number > 0.7  # Should handle 2B vs 2-B
        assert similarities.street > 0.7  # Should handle NAGAR vs NGR
        assert similarities.city > 0.8  # Should handle Mumbai/Bombay variation
        assert similarities.postal_code > 0.9  # Pincode should match exactly
        assert overall > 0.7  # Lower threshold for Indian addresses
    
    def test_transliteration_matching(self):
        """Test transliteration support for international addresses."""
        # Test Hindi/Devanagari transliteration
        hindi_text1 = "नई दिल्ली"
        hindi_text2 = "NEW DELHI"
        
        similarity = TransliterationMatcher.get_similarity_with_transliteration(
            hindi_text1, hindi_text2, 0.5
        )
        
        assert similarity >= 0.6  # Should boost similarity due to transliteration


class TestRuleBasedFilter:
    """Test region-specific rule-based filtering."""
    
    def setup_method(self):
        """Setup test components."""
        self.us_filter = RuleBasedFilter(region='US')
        self.uk_filter = RuleBasedFilter(region='UK')
        self.german_filter = RuleBasedFilter(region='DE')
        self.indian_filter = RuleBasedFilter(region='IN')
    
    def test_us_rule_filtering(self):
        """Test US-specific rule filtering."""
        addr1 = NormalizedAddress(
            house_number="123",
            street="MAIN STREET",
            city="ANYTOWN",
            state="CALIFORNIA",
            postal_code="90210"
        )
        addr2 = NormalizedAddress(
            house_number="123",
            street="MAIN ST",
            city="ANYTOWN",
            state="CA",
            postal_code="90210"
        )
        
        similarities = ComponentSimilarities(
            house_number=0.95,
            street=0.85,
            city=0.95,
            state=0.85,
            postal_code=0.95
        )
        
        result = self.us_filter.apply_rules(similarities, addr1, addr2, 0.85)
        assert result is True
    
    def test_uk_rule_filtering_house_names(self):
        """Test UK-specific rule filtering with house names."""
        addr1 = NormalizedAddress(
            house_number="THE OLD RECTORY",
            street="HIGH STREET",
            city="CAMBRIDGE",
            postal_code="CB21 5JY"
        )
        addr2 = NormalizedAddress(
            house_number="OLD RECTORY",
            street="HIGH ST",
            city="CAMBRIDGE",
            postal_code="CB215JY"
        )
        
        similarities = ComponentSimilarities(
            house_number=0.75,  # Lower similarity for house names
            street=0.85,
            city=0.95,
            postal_code=0.85
        )
        
        result = self.uk_filter.apply_rules(similarities, addr1, addr2, 0.80)
        assert result is True  # Should pass due to UK house name flexibility
    
    def test_german_rule_filtering_strict(self):
        """Test German-specific strict rule filtering."""
        addr1 = NormalizedAddress(
            house_number="123",
            street="MUSTERSTRASSE",
            city="BERLIN",
            postal_code="12345"
        )
        addr2 = NormalizedAddress(
            house_number="124",  # Different house number
            street="MUSTERSTRASSE",
            city="BERLIN",
            postal_code="12345"
        )
        
        similarities = ComponentSimilarities(
            house_number=0.6,  # Low house number similarity
            street=0.95,
            city=0.95,
            postal_code=0.95
        )
        
        result = self.german_filter.apply_rules(similarities, addr1, addr2, 0.80)
        assert result is False  # Should fail due to strict German house number requirement
    
    def test_indian_rule_filtering_pincode_priority(self):
        """Test Indian-specific rule filtering with pincode priority."""
        addr1 = NormalizedAddress(
            house_number="2B",
            street="KRISHNA NAGAR",
            city="PUNE",
            state="MAHARASHTRA",
            postal_code="411001"
        )
        addr2 = NormalizedAddress(
            house_number="2-B",
            street="K NAGAR",  # Very different street
            city="PUNE",
            state="MH",
            postal_code="411001"  # Same pincode
        )
        
        similarities = ComponentSimilarities(
            house_number=0.7,
            street=0.4,  # Low street similarity
            city=0.9,
            state=0.8,
            postal_code=0.95  # High pincode similarity
        )
        
        result = self.indian_filter.apply_rules(similarities, addr1, addr2, 0.70)
        assert result is True  # Should pass due to pincode match and Indian flexibility


class TestRegionalConfiguration:
    """Test regional configuration system."""
    
    def test_regional_config_loading(self):
        """Test loading of regional configurations."""
        regional_config = RegionalConfig()
        
        # Test US config
        us_config = regional_config.get_region_config('US')
        assert us_config['name'] == 'United States'
        assert us_config['rule_based_filter']['state_abbreviation_matching'] is True
        
        # Test Indian config
        in_config = regional_config.get_region_config('IN')
        assert in_config['name'] == 'India'
        assert in_config['rule_based_filter']['require_postal_code_match'] is True
        assert in_config['fuzzy_matching']['transliteration_support'] is True
        
        # Test German config
        de_config = regional_config.get_region_config('DE')
        assert de_config['name'] == 'Germany'
        assert de_config['rule_based_filter']['house_number_threshold'] == 0.9
    
    def test_address_matching_config(self):
        """Test comprehensive address matching configuration."""
        # Test with different regions (ignore process env for determinism)
        us_config = AddressMatchingConfig(region='US', apply_env=False)
        assert us_config.region == 'US'
        
        rule_config = us_config.get_component_config('rule_based_filter')
        assert rule_config['state_abbreviation_matching'] is True
        
        in_config = AddressMatchingConfig(region='IN', apply_env=False)
        assert in_config.region == 'IN'
        
        rule_config = in_config.get_component_config('rule_based_filter')
        assert rule_config['overall_threshold'] == 0.65  # Lower for Indian addresses
    
    def test_config_validation(self):
        """Test configuration validation."""
        config = AddressMatchingConfig(region='US', apply_env=False)
        errors = config.validate_config()
        assert len(errors) == 0  # Should have no validation errors
        
        # Test invalid config
        config.update_config({
            'rule_based_filter': {
                'overall_threshold': 1.5  # Invalid threshold > 1.0
            }
        })
        errors = config.validate_config()
        assert len(errors) > 0  # Should have validation errors

    def test_environment_overrides_and_matcher_config(self, monkeypatch):
        """Env vars should override defaults and flatten for AddressMatcher."""
        monkeypatch.setenv('ADDRESS_MATCHING_REGION', 'UK')
        monkeypatch.setenv('USE_ML_MODEL', 'false')
        monkeypatch.setenv('USE_GEOSPATIAL', 'true')
        monkeypatch.setenv('DISTANCE_THRESHOLD', '75.5')
        monkeypatch.setenv('GEOCODING_USER_AGENT', 'test-agent')
        monkeypatch.setenv('GEOCODING_TIMEOUT', '15')
        monkeypatch.setenv('OVERALL_THRESHOLD', '0.85')
        monkeypatch.setenv('REQUIRE_CITY_MATCH', 'false')
        monkeypatch.setenv('ML_MODEL_PATH', '/tmp/model.pkl')
        monkeypatch.setenv('API_HOST', '127.0.0.1')
        monkeypatch.setenv('API_PORT', '9000')
        monkeypatch.setenv('LOG_LEVEL', 'DEBUG')

        config = AddressMatchingConfig(region='US', apply_env=True)
        assert config.region == 'UK'

        matcher_config = config.to_matcher_config()
        assert matcher_config['default_region'] == 'UK'
        assert matcher_config['use_ml_model'] is False
        assert matcher_config['use_geospatial'] is True
        assert matcher_config['distance_threshold'] == 75.5
        assert matcher_config['geocoding_user_agent'] == 'test-agent'
        assert matcher_config['geocoding_timeout'] == 15
        assert matcher_config['ml_model_path'] == '/tmp/model.pkl'
        assert matcher_config['rules']['overall_threshold'] == 0.85
        assert matcher_config['rules']['require_city_match'] is False
        assert matcher_config['api_host'] == '127.0.0.1'
        assert matcher_config['api_port'] == 9000
        assert matcher_config['log_level'] == 'DEBUG'

        matcher = AddressMatcher(matcher_config)
        assert matcher.use_ml_model is False
        assert matcher.use_geospatial is True
        assert matcher.distance_threshold == 75.5
        assert matcher.default_region == 'UK'
        assert matcher.geocoding_service.user_agent == 'test-agent'
        assert matcher.geocoding_service.timeout == 15

    def test_disable_flags_override_use_flags(self, monkeypatch):
        """DISABLE_* flags should win over USE_* toggles."""
        monkeypatch.setenv('USE_ML_MODEL', 'true')
        monkeypatch.setenv('DISABLE_ML_MODEL', '1')
        monkeypatch.setenv('USE_GEOSPATIAL', 'true')
        monkeypatch.setenv('DISABLE_GEOSPATIAL', '1')

        config = AddressMatchingConfig(region='US', apply_env=True)
        matcher_config = config.to_matcher_config()
        assert matcher_config['use_ml_model'] is False
        assert matcher_config['use_geospatial'] is False


class TestIntegratedAddressMatching:
    """Test integrated address matching with all components."""
    
    def setup_method(self):
        """Setup test components."""
        self.matcher = AddressMatcher({
            'use_ml_model': False,
            'use_geospatial': False,
            'ml_auto_train': False,
        })
    
    @pytest.mark.asyncio
    async def test_us_address_matching_integration(self):
        """Test complete US address matching flow."""
        address1 = "123 Main Street, Anytown, CA 90210, USA"
        address2 = "123 Main St, Anytown, California 90210, United States"
        
        result = await self.matcher.match_addresses(address1, address2, region='US')
        
        assert result.match is True
        assert result.confidence_score > 0.8
        assert result.details.normalized_address1.city.upper() == "ANYTOWN"
        assert result.details.normalized_address2.city.upper() == "ANYTOWN"
    
    @pytest.mark.asyncio
    async def test_uk_address_matching_integration(self):
        """Test complete UK address matching flow."""
        address1 = "10 Downing Street, London SW1A 2AA, UK"
        address2 = "10 Downing St, London SW1A2AA, United Kingdom"
        
        result = await self.matcher.match_addresses(address1, address2, region='UK')
        
        assert result.match is True
        assert result.confidence_score > 0.7
        assert result.details.component_similarities.postal_code > 0.7
    
    @pytest.mark.asyncio
    async def test_german_address_matching_integration(self):
        """Test complete German address matching flow."""
        address1 = "Musterstraße 123, 12345 Berlin, Deutschland"
        address2 = "Muster Str 123, 12345 Berlin, Germany"
        
        result = await self.matcher.match_addresses(address1, address2, region='DE')
        
        assert result.match is True
        assert result.confidence_score > 0.7
        assert result.details.component_similarities.house_number > 0.9
    
    @pytest.mark.asyncio
    async def test_indian_address_matching_integration(self):
        """Test complete Indian address matching flow."""
        address1 = "Flat 2B, Krishna Nagar, Mumbai 400001, Maharashtra, India"
        address2 = "2-B Krishna Ngr, Bombay 400001, MH, India"
        
        result = await self.matcher.match_addresses(address1, address2, region='IN')
        
        assert result.match is True
        assert result.confidence_score > 0.6  # Lower threshold for Indian addresses
        assert result.details.component_similarities.postal_code > 0.9  # Pincode should match well
    
    @pytest.mark.asyncio
    async def test_auto_region_detection(self):
        """Test automatic region detection in address matching."""
        # Test addresses from different regions without specifying region
        test_cases = [
            ("123 Main St, Anytown, CA 90210", "123 Main Street, Anytown, California 90210", 'US'),
            ("10 Downing Street, London SW1A 2AA", "10 Downing St, London SW1A 2AA", 'UK'),
            ("Musterstraße 123, 12345 Berlin", "Muster Str 123, 12345 Berlin", 'DE'),
            ("Krishna Nagar, Pune 411001", "K Nagar, Pune 411001", 'IN'),
        ]
        
        for addr1, addr2, expected_region in test_cases:
            result = await self.matcher.match_addresses(addr1, addr2)  # No region specified
            
            # Should detect correct region and match successfully
            assert result.match is True
            assert result.confidence_score > 0.6
    
    @pytest.mark.asyncio
    async def test_cross_region_mismatch(self):
        """Test that addresses from different regions don't match."""
        us_address = "123 Main Street, Anytown, CA 90210, USA"
        uk_address = "10 Downing Street, London SW1A 2AA, UK"
        
        result = await self.matcher.match_addresses(us_address, uk_address)
        
        assert result.match is False
        assert result.confidence_score < 0.5
    
    @pytest.mark.asyncio
    async def test_batch_processing_different_regions(self):
        """Test batch processing of addresses from different regions."""
        address_pairs = [
            ("123 Main St, Anytown, CA 90210", "123 Main Street, Anytown, CA 90210"),
            ("10 Downing Street, London SW1A 2AA", "10 Downing St, London SW1A 2AA"),
            ("Musterstraße 123, Berlin 12345", "Muster Str 123, Berlin 12345"),
            ("Krishna Nagar, Pune 411001", "K Nagar, Pune 411001"),
        ]
        
        results = await self.matcher.batch_match_addresses(address_pairs)
        
        assert len(results) == 4
        for result in results:
            assert result.match is True
            assert result.confidence_score > 0.6


class TestPerformanceAndEdgeCases:
    """Test performance and edge cases for regional address matching."""
    
    def setup_method(self):
        """Setup test components."""
        self.matcher = AddressMatcher({
            'use_ml_model': False,
            'use_geospatial': False,
            'ml_auto_train': False,
        })
    
    @pytest.mark.asyncio
    async def test_empty_addresses(self):
        """Test handling of empty or malformed addresses."""
        result = await self.matcher.match_addresses("", "")
        assert result.match is False
        assert result.confidence_score == 0.0
    
    @pytest.mark.asyncio
    async def test_partial_addresses(self):
        """Test handling of partial address information."""
        partial1 = "Main Street, Anytown"
        partial2 = "Main St, Anytown"
        
        result = await self.matcher.match_addresses(partial1, partial2)
        assert result.confidence_score > 0.0  # Should still provide some matching
    
    @pytest.mark.asyncio
    async def test_mixed_language_addresses(self):
        """Test handling of addresses with mixed languages."""
        # Test with mixed English/Hindi
        address1 = "123 नई दिल्ली, India 110001"
        address2 = "123 New Delhi, India 110001"
        
        result = await self.matcher.match_addresses(address1, address2, region='IN')
        
        # Should handle transliteration
        assert result.match is True or result.confidence_score > 0.6
    
    def test_component_status_reporting(self):
        """Test that component status is reported correctly."""
        status = self.matcher.get_component_status()
        
        assert 'address_parser' in status
        assert 'region_detection' in status
        assert 'geopy' in status
        assert 'ml_model_ready' in status
        assert status['address_parser'] is True
        assert status['region_detection'] is True
        assert status['default_region'] == 'US'
    
    def test_supported_regions(self):
        """Test that all expected regions are supported."""
        supported_regions = self.matcher.get_supported_regions()
        
        expected_regions = ['US', 'CA', 'UK', 'DE', 'FR', 'IT', 'ES', 'IN', 'AU', 'NL', 'SE', 'NO', 'CH']
        for region in expected_regions:
            assert region in supported_regions


class TestGeospatialWiring:
    """Regression tests for geospatial result wiring into final decision."""

    @pytest.mark.asyncio
    async def test_within_threshold_is_used_when_geocoding_succeeds(self):
        """GeocodingService returns `within_threshold`, not `match`."""
        matcher = AddressMatcher({'use_geospatial': True, 'use_ml_model': False, 'ml_auto_train': False})
        captured = {}

        async def fake_geo(address1, address2, distance_threshold=50.0):
            return {
                'distance_meters': 12.0,
                'within_threshold': True,
                'geocoding_successful': True,
                'coords1': (37.0, -122.0),
                'coords2': (37.0, -122.0),
            }

        original_decision = matcher._make_final_decision

        def capture_decision(*args, **kwargs):
            captured['args'] = args
            return original_decision(*args, **kwargs)

        matcher.geocoding_service.validate_addresses_geospatially = fake_geo
        with patch.object(matcher, '_make_final_decision', side_effect=capture_decision):
            await matcher.match_addresses(
                "123 Main St, Anytown, CA 90210",
                "123 Main Street, Anytown, CA 90210",
                region='US',
            )

        # Positional args: rule, ml, similarity, distance, ml_conf, region, geospatial_supports_match
        assert captured['args'][3] == 12.0
        assert captured['args'][6] is True

    @pytest.mark.asyncio
    async def test_failed_geocoding_does_not_claim_support(self):
        """Default within_threshold=True must not boost when geocoding failed."""
        matcher = AddressMatcher({'use_geospatial': True, 'use_ml_model': False, 'ml_auto_train': False})
        captured = {}

        async def fake_geo(address1, address2, distance_threshold=50.0):
            return {
                'distance_meters': None,
                'within_threshold': True,  # service default when lookup fails
                'geocoding_successful': False,
                'coords1': None,
                'coords2': None,
            }

        original_decision = matcher._make_final_decision

        def capture_decision(*args, **kwargs):
            captured['args'] = args
            return original_decision(*args, **kwargs)

        matcher.geocoding_service.validate_addresses_geospatially = fake_geo
        with patch.object(matcher, '_make_final_decision', side_effect=capture_decision):
            await matcher.match_addresses(
                "123 Main St, Anytown, CA 90210",
                "123 Main Street, Anytown, CA 90210",
                region='US',
            )

        assert captured['args'][6] is None


class TestErrorPropagation:
    """Internal failures must surface as errors, not silent false negatives."""

    @pytest.mark.asyncio
    async def test_match_addresses_raises_on_internal_failure(self):
        from app.matcher import AddressMatchingError

        matcher = AddressMatcher({'use_geospatial': False, 'use_ml_model': False, 'ml_auto_train': False})
        with patch.object(
            matcher.parser,
            'normalize_and_parse',
            side_effect=RuntimeError('parser boom'),
        ):
            with pytest.raises(AddressMatchingError, match='internal error'):
                await matcher.match_addresses(
                    "123 Main St, Anytown, CA 90210",
                    "123 Main Street, Anytown, CA 90210",
                    region='US',
                )


class TestAddressLogRedaction:
    """Address PII must be hashed in logs by default."""

    def test_format_address_for_log_hashes_by_default(self, monkeypatch):
        from app.logging_utils import format_address_for_log

        monkeypatch.delenv('LOG_ADDRESS_PII', raising=False)
        address = "123 Main St, Anytown, CA 90210"
        token = format_address_for_log(address)
        assert 'Main St' not in token
        assert token.startswith('addr_sha256=')
        assert 'len=30' in token

    def test_format_address_for_log_allows_full_when_enabled(self, monkeypatch):
        from app.logging_utils import format_address_for_log

        monkeypatch.setenv('LOG_ADDRESS_PII', 'full')
        address = "123 Main St, Anytown, CA 90210"
        assert format_address_for_log(address) == address

    def test_format_address_for_log_empty(self, monkeypatch):
        from app.logging_utils import format_address_for_log

        monkeypatch.delenv('LOG_ADDRESS_PII', raising=False)
        assert format_address_for_log('') == '<empty>'
        assert format_address_for_log(None) == '<empty>'


if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 