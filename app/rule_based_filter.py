from typing import Dict, Any, Optional
from loguru import logger

from app.models import ComponentSimilarities, NormalizedAddress


class RegionSpecificRules:
    """Region-specific rules and thresholds for address matching."""
    
    REGIONAL_CONFIGS = {
        'US': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.7,
            'city_threshold': 0.7,  # Lowered to handle common abbreviations like NYC
            'house_number_threshold': 0.8,
            'overall_threshold': 0.7,
            'require_postal_code_match': False,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': True,
            'state_abbreviation_matching': True,
        },
        'CA': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.7,
            'city_threshold': 0.8,
            'house_number_threshold': 0.8,
            'overall_threshold': 0.7,
            'require_postal_code_match': False,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': True,
            'state_abbreviation_matching': True,
        },
        'UK': {
            'postal_code_threshold': 0.8,  # More flexible for UK postcodes
            'street_threshold': 0.75,
            'city_threshold': 0.8,
            'house_number_threshold': 0.7,  # More flexible for house names
            'overall_threshold': 0.7,
            'require_postal_code_match': False,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': True,
            'allow_house_names': True,
        },
        'DE': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.8,
            'city_threshold': 0.8,
            'house_number_threshold': 0.9,  # German addresses very precise
            'overall_threshold': 0.75,
            'require_postal_code_match': True,  # PLZ important
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': False,
        },
        'FR': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.75,
            'city_threshold': 0.8,
            'house_number_threshold': 0.8,
            'overall_threshold': 0.7,
            'require_postal_code_match': False,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': True,
        },
        'IT': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.75,
            'city_threshold': 0.8,
            'house_number_threshold': 0.8,
            'overall_threshold': 0.7,
            'require_postal_code_match': False,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': True,
        },
        'ES': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.75,
            'city_threshold': 0.8,
            'house_number_threshold': 0.8,
            'overall_threshold': 0.7,
            'require_postal_code_match': False,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': True,
        },
        'IN': {
            'postal_code_threshold': 0.9,  # Pincode very important
            'street_threshold': 0.6,  # More flexible for complex Indian addresses
            'city_threshold': 0.7,  # More flexible for city name variations
            'house_number_threshold': 0.6,  # Indian house numbers can be complex
            'overall_threshold': 0.65,  # Lower overall threshold
            'require_postal_code_match': True,  # Pincode critical
            'require_city_match': True,
            'require_street_match': False,  # Street info often inconsistent
            'allow_partial_house_number': True,
            'allow_area_locality_matching': True,  # Indian addresses have areas/localities
        },
        'AU': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.75,
            'city_threshold': 0.8,
            'house_number_threshold': 0.8,
            'overall_threshold': 0.7,
            'require_postal_code_match': False,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': True,
            'state_abbreviation_matching': True,
        },
        'NL': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.8,
            'city_threshold': 0.8,
            'house_number_threshold': 0.9,  # Very important in Dutch addresses
            'overall_threshold': 0.75,
            'require_postal_code_match': True,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': False,
        },
        'SE': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.75,
            'city_threshold': 0.8,
            'house_number_threshold': 0.8,
            'overall_threshold': 0.7,
            'require_postal_code_match': False,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': True,
        },
        'NO': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.75,
            'city_threshold': 0.8,
            'house_number_threshold': 0.8,
            'overall_threshold': 0.7,
            'require_postal_code_match': False,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': True,
        },
        'CH': {
            'postal_code_threshold': 0.9,
            'street_threshold': 0.8,
            'city_threshold': 0.8,
            'house_number_threshold': 0.9,
            'overall_threshold': 0.75,
            'require_postal_code_match': True,
            'require_city_match': True,
            'require_street_match': True,
            'allow_partial_house_number': False,
        },
    }
    
    @classmethod
    def get_config(cls, region: str) -> Dict[str, Any]:
        """Get region-specific configuration."""
        return cls.REGIONAL_CONFIGS.get(region, cls.REGIONAL_CONFIGS['US'])


class RuleBasedFilter:
    """
    Enhanced rule-based filtering for address matching decisions with regional support.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, region: str = 'US'):
        """
        Initialize with configurable thresholds and region.
        
        Args:
            config: Configuration dictionary with threshold values
            region: Region/country code for region-specific rules
        """
        self.region = region
        self.region_rules = RegionSpecificRules()
        
        # Load region-specific defaults
        region_config = self.region_rules.get_config(region)
        
        # Override with user config if provided
        if config:
            region_config.update(config)
        
        self.config = region_config
        
        # Set individual thresholds
        self.postal_code_threshold = self.config.get('postal_code_threshold', 0.8)
        self.street_threshold = self.config.get('street_threshold', 0.7)
        self.city_threshold = self.config.get('city_threshold', 0.8)
        self.house_number_threshold = self.config.get('house_number_threshold', 0.8)
        self.overall_threshold = self.config.get('overall_threshold', 0.7)
        
        # Strict matching requirements
        self.require_postal_code_match = self.config.get('require_postal_code_match', False)
        self.require_city_match = self.config.get('require_city_match', True)
        self.require_street_match = self.config.get('require_street_match', True)
        
        # Region-specific features
        self.allow_partial_house_number = self.config.get('allow_partial_house_number', True)
        self.allow_house_names = self.config.get('allow_house_names', False)
        self.allow_area_locality_matching = self.config.get('allow_area_locality_matching', False)
        self.state_abbreviation_matching = self.config.get('state_abbreviation_matching', False)
        
        logger.info(f"RuleBasedFilter initialized for region {region} with config: {self.config}")
    
    def set_region(self, region: str):
        """Update the region and reload configuration."""
        self.region = region
        region_config = self.region_rules.get_config(region)
        self.config.update(region_config)
        self.__init__(self.config, region)
    
    def apply_rules(
        self, 
        similarities: ComponentSimilarities,
        addr1: NormalizedAddress,
        addr2: NormalizedAddress,
        overall_similarity: float
    ) -> bool:
        """
        Apply region-aware rule-based filtering to determine if addresses match.
        
        Args:
            similarities: Component similarity scores
            addr1: First normalized address
            addr2: Second normalized address
            overall_similarity: Overall similarity score
            
        Returns:
            Boolean decision whether addresses match
        """
        logger.debug(f"Applying region-specific rules for {self.region}")
        
        # Rule 1: Check overall similarity threshold
        if overall_similarity < self.overall_threshold:
            logger.debug(f"Overall similarity {overall_similarity} below threshold {self.overall_threshold}")
            return False
        
        # Rule 2: Region-specific postal code matching
        if not self._check_postal_code_rule(similarities, addr1, addr2):
            return False
        
        # Rule 3: City matching with region-specific flexibility
        if not self._check_city_rule(similarities, addr1, addr2):
            return False
        
        # Rule 4: Street matching with region-specific rules
        if not self._check_street_rule(similarities, addr1, addr2):
            return False
        
        # Rule 5: House number consistency check with region rules
        if not self._check_house_number_rule(similarities, addr1, addr2):
            return False
        
        # Rule 6: Country/region consistency check
        if not self._check_country_rule(similarities, addr1, addr2):
            return False
        
        # Rule 7: State/province matching for applicable regions
        if not self._check_state_rule(similarities, addr1, addr2):
            return False
        
        # Rule 8: Region-specific special rules
        if not self._check_region_specific_rules(similarities, addr1, addr2):
            return False
        
        logger.debug("All rules passed - addresses match")
        return True
    
    def _check_postal_code_rule(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """Enhanced postal code matching rule with region-specific logic."""
        if not self._should_check_postal_code(addr1, addr2):
            return True
        
        if similarities.postal_code is None:
            return not self.require_postal_code_match
        
        if similarities.postal_code < self.postal_code_threshold:
            logger.debug(f"Postal code similarity {similarities.postal_code} below threshold {self.postal_code_threshold}")
            
            # Region-specific postal code flexibility
            if self.region == 'UK':
                # UK postcodes can have spacing differences
                if similarities.postal_code > 0.7:  # More lenient for UK
                    return True
            elif self.region in ['CA']:
                # Canadian postal codes can have spacing/case differences
                if similarities.postal_code > 0.75:
                    return True
            elif self.region == 'IN':
                # Indian pincodes should match exactly
                return False
            
            return False
        
        return True
    
    def _check_city_rule(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """Enhanced city matching rule with regional variations."""
        if not self.require_city_match:
            return True
        
        if similarities.city is None:
            logger.debug("City information missing")
            return False
        
        if similarities.city < self.city_threshold:
            # Region-specific city name handling
            if self.region == 'IN':
                # Indian cities often have multiple names (Mumbai/Bombay, etc.)
                if self._check_indian_city_variations(addr1.city, addr2.city):
                    return True
            elif self.region == 'UK':
                # UK cities might have county variations
                if similarities.city > 0.6:  # More lenient for UK
                    return True
            
            logger.debug(f"City similarity {similarities.city} below threshold {self.city_threshold}")
            return False
        
        return True
    
    def _check_street_rule(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """Enhanced street matching rule with regional considerations."""
        if not self.require_street_match:
            return True
        
        if similarities.street is None:
            if self.region == 'IN' and self.allow_area_locality_matching:
                # For Indian addresses, missing street info might be acceptable if other components match well
                return True
            logger.debug("Street information missing")
            return False
        
        if similarities.street < self.street_threshold:
            # Region-specific street handling
            if self.region == 'IN':
                # Indian addresses often have complex area/locality info
                if similarities.street > 0.5:  # More lenient for Indian addresses
                    return True
            elif self.region in ['DE', 'NL', 'CH']:
                # German/Dutch/Swiss addresses are typically more structured
                logger.debug(f"Street similarity {similarities.street} below threshold {self.street_threshold}")
                return False
            
            logger.debug(f"Street similarity {similarities.street} below threshold {self.street_threshold}")
            return False
        
        return True
    
    def _check_house_number_rule(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """Enhanced house number consistency rule with regional flexibility."""
        # If both addresses have house numbers, they should be reasonably similar
        if addr1.house_number is not None and addr2.house_number is not None:
            if similarities.house_number is not None:
                if similarities.house_number < self.house_number_threshold:
                    # Region-specific house number handling
                    if self.region == 'UK' and self.allow_house_names:
                        # UK addresses might have house names vs numbers
                        if similarities.house_number > 0.3:  # Very lenient for house names
                            return True
                    elif self.region == 'IN' and self.allow_partial_house_number:
                        # Indian addresses often have complex flat/house numbering
                        if similarities.house_number > 0.4:
                            return True
                    elif self.region in ['DE', 'NL', 'CH']:
                        # German/Dutch/Swiss addresses require precise house numbers
                        logger.debug(f"House number similarity {similarities.house_number} below threshold {self.house_number_threshold}")
                        return False
                    
                    logger.debug(f"House number similarity {similarities.house_number} below threshold {self.house_number_threshold}")
                    return False
        
        return True
    
    def _check_country_rule(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """Enhanced country consistency rule."""
        # If both addresses have countries, they should match or be very similar
        if addr1.country is not None and addr2.country is not None:
            if similarities.country is not None:
                # Countries should have high similarity (accounting for variations like "UK" vs "United Kingdom")
                if similarities.country < 0.6:
                    # Check for common country variations
                    if self._check_country_variations(addr1.country, addr2.country):
                        return True
                    logger.debug(f"Country similarity {similarities.country} too low")
                    return False
        
        return True
    
    def _check_state_rule(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """Check state/province matching for applicable regions."""
        if not self.state_abbreviation_matching:
            return True
        
        if addr1.state is not None and addr2.state is not None:
            if similarities.state is not None:
                # Allow for abbreviation differences (e.g., "California" vs "CA")
                if similarities.state < 0.5:
                    if self.region in ['US', 'CA', 'AU']:
                        # Check for state abbreviation matches
                        if self._check_state_abbreviations(addr1.state, addr2.state):
                            return True
                    logger.debug(f"State similarity {similarities.state} too low")
                    return False
        
        return True
    
    def _check_region_specific_rules(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """Apply additional region-specific matching rules."""
        if self.region == 'IN':
            # Indian address specific rules
            return self._check_indian_specific_rules(similarities, addr1, addr2)
        elif self.region in ['DE', 'AT', 'CH']:
            # German-speaking countries
            return self._check_german_specific_rules(similarities, addr1, addr2)
        elif self.region == 'UK':
            # UK specific rules
            return self._check_uk_specific_rules(similarities, addr1, addr2)
        elif self.region in ['SE', 'NO', 'DK', 'FI']:
            # Nordic countries
            return self._check_nordic_specific_rules(similarities, addr1, addr2)
        
        return True  # No additional rules for other regions
    
    def _check_indian_specific_rules(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """Indian address specific matching rules."""
        # Rule: If pincode matches exactly, be more lenient with other components
        if similarities.postal_code and similarities.postal_code > 0.95:
            logger.debug("Indian pincode matches exactly, applying lenient rules")
            return True
        
        # Rule: Check for area/locality information in street field
        if addr1.street and addr2.street:
            indian_locality_terms = ['NAGAR', 'COLONY', 'SECTOR', 'PHASE', 'BLOCK', 'AREA']
            addr1_has_locality = any(term in addr1.street.upper() for term in indian_locality_terms)
            addr2_has_locality = any(term in addr2.street.upper() for term in indian_locality_terms)
            
            if addr1_has_locality and addr2_has_locality:
                # Both have locality info, require decent street similarity
                return similarities.street is None or similarities.street > 0.5
        
        return True
    
    def _check_german_specific_rules(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """German/Austrian/Swiss address specific rules."""
        # Rule: PLZ + City combination is very important
        if similarities.postal_code and similarities.city:
            if similarities.postal_code > 0.9 and similarities.city > 0.8:
                logger.debug("German PLZ+City combination matches well")
                return True
        
        # Rule: House number precision is important
        if similarities.house_number and similarities.house_number < 0.8:
            logger.debug("German house number similarity too low")
            return False
        
        return True
    
    def _check_uk_specific_rules(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """UK address specific matching rules."""
        # Rule: Postcode is very reliable when present
        if similarities.postal_code and similarities.postal_code > 0.8:
            logger.debug("UK postcode matches well, applying lenient rules")
            return True
        
        # Rule: Handle house names vs numbers
        if addr1.house_number and addr2.house_number:
            # Check if one might be a house name and other a number
            try:
                int(addr1.house_number)
                int(addr2.house_number)
                # Both are numbers, require good similarity
                return similarities.house_number is None or similarities.house_number > 0.7
            except ValueError:
                # At least one is not a pure number (might be house name)
                return similarities.house_number is None or similarities.house_number > 0.3
        
        return True
    
    def _check_nordic_specific_rules(self, similarities: ComponentSimilarities, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """Nordic countries address specific rules."""
        # Rule: Postal code + city combination is reliable
        if similarities.postal_code and similarities.city:
            if similarities.postal_code > 0.9 and similarities.city > 0.8:
                logger.debug("Nordic postal code+city combination matches well")
                return True
        
        return True
    
    def _should_check_postal_code(self, addr1: NormalizedAddress, addr2: NormalizedAddress) -> bool:
        """Check if postal code rule should be applied."""
        return (self.require_postal_code_match or 
                (addr1.postal_code is not None and addr2.postal_code is not None))
    
    def _check_indian_city_variations(self, city1: Optional[str], city2: Optional[str]) -> bool:
        """Check for common Indian city name variations."""
        if not city1 or not city2:
            return False
        
        city1_upper = city1.upper()
        city2_upper = city2.upper()
        
        variations = {
            'MUMBAI': ['BOMBAY'],
            'BENGALURU': ['BANGALORE'],
            'KOLKATA': ['CALCUTTA'],
            'CHENNAI': ['MADRAS'],
            'PUNE': ['POONA'],
            'THIRUVANANTHAPURAM': ['TRIVANDRUM'],
            'KOCHI': ['COCHIN'],
            'KOZHIKODE': ['CALICUT']
        }
        
        for standard, alts in variations.items():
            if (city1_upper == standard and city2_upper in alts) or \
               (city2_upper == standard and city1_upper in alts) or \
               (city1_upper in alts and city2_upper == standard) or \
               (city2_upper in alts and city1_upper == standard):
                return True
        
        return False
    
    def _check_country_variations(self, country1: str, country2: str) -> bool:
        """Check for common country name variations."""
        country1_upper = country1.upper()
        country2_upper = country2.upper()
        
        variations = {
            'UK': ['UNITED KINGDOM', 'BRITAIN', 'ENGLAND', 'SCOTLAND', 'WALES'],
            'USA': ['UNITED STATES', 'AMERICA', 'US'],
            'GERMANY': ['DEUTSCHLAND', 'DE'],
            'NETHERLANDS': ['HOLLAND', 'NL'],
        }
        
        for standard, alts in variations.items():
            if (country1_upper == standard and country2_upper in alts) or \
               (country2_upper == standard and country1_upper in alts) or \
               (country1_upper in alts and country2_upper == standard) or \
               (country2_upper in alts and country1_upper == standard):
                return True
        
        return False
    
    def _check_state_abbreviations(self, state1: str, state2: str) -> bool:
        """Check for state abbreviation matches."""
        state1_upper = state1.upper()
        state2_upper = state2.upper()
        
        if self.region == 'US':
            us_states = {
                'ALABAMA': 'AL', 'ALASKA': 'AK', 'ARIZONA': 'AZ', 'ARKANSAS': 'AR',
                'CALIFORNIA': 'CA', 'COLORADO': 'CO', 'CONNECTICUT': 'CT', 'DELAWARE': 'DE',
                'FLORIDA': 'FL', 'GEORGIA': 'GA', 'HAWAII': 'HI', 'IDAHO': 'ID',
                'ILLINOIS': 'IL', 'INDIANA': 'IN', 'IOWA': 'IA', 'KANSAS': 'KS',
                'KENTUCKY': 'KY', 'LOUISIANA': 'LA', 'MAINE': 'ME', 'MARYLAND': 'MD',
                'MASSACHUSETTS': 'MA', 'MICHIGAN': 'MI', 'MINNESOTA': 'MN', 'MISSISSIPPI': 'MS',
                'MISSOURI': 'MO', 'MONTANA': 'MT', 'NEBRASKA': 'NE', 'NEVADA': 'NV',
                'NEW HAMPSHIRE': 'NH', 'NEW JERSEY': 'NJ', 'NEW MEXICO': 'NM', 'NEW YORK': 'NY',
                'NORTH CAROLINA': 'NC', 'NORTH DAKOTA': 'ND', 'OHIO': 'OH', 'OKLAHOMA': 'OK',
                'OREGON': 'OR', 'PENNSYLVANIA': 'PA', 'RHODE ISLAND': 'RI', 'SOUTH CAROLINA': 'SC',
                'SOUTH DAKOTA': 'SD', 'TENNESSEE': 'TN', 'TEXAS': 'TX', 'UTAH': 'UT',
                'VERMONT': 'VT', 'VIRGINIA': 'VA', 'WASHINGTON': 'WA', 'WEST VIRGINIA': 'WV',
                'WISCONSIN': 'WI', 'WYOMING': 'WY'
            }
            
            for full_name, abbrev in us_states.items():
                if (state1_upper == full_name and state2_upper == abbrev) or \
                   (state2_upper == full_name and state1_upper == abbrev):
                    return True
        
        elif self.region == 'CA':
            ca_provinces = {
                'ALBERTA': 'AB', 'BRITISH COLUMBIA': 'BC', 'MANITOBA': 'MB',
                'NEW BRUNSWICK': 'NB', 'NEWFOUNDLAND AND LABRADOR': 'NL',
                'NORTHWEST TERRITORIES': 'NT', 'NOVA SCOTIA': 'NS', 'NUNAVUT': 'NU',
                'ONTARIO': 'ON', 'PRINCE EDWARD ISLAND': 'PE', 'QUEBEC': 'QC',
                'SASKATCHEWAN': 'SK', 'YUKON': 'YT'
            }
            
            for full_name, abbrev in ca_provinces.items():
                if (state1_upper == full_name and state2_upper == abbrev) or \
                   (state2_upper == full_name and state1_upper == abbrev):
                    return True
        
        elif self.region == 'AU':
            au_states = {
                'NEW SOUTH WALES': 'NSW', 'VICTORIA': 'VIC', 'QUEENSLAND': 'QLD',
                'WESTERN AUSTRALIA': 'WA', 'SOUTH AUSTRALIA': 'SA', 'TASMANIA': 'TAS',
                'AUSTRALIAN CAPITAL TERRITORY': 'ACT', 'NORTHERN TERRITORY': 'NT'
            }
            
            for full_name, abbrev in au_states.items():
                if (state1_upper == full_name and state2_upper == abbrev) or \
                   (state2_upper == full_name and state1_upper == abbrev):
                    return True
        
        return False
    
    def get_rule_details(
        self, 
        similarities: ComponentSimilarities,
        addr1: NormalizedAddress,
        addr2: NormalizedAddress,
        overall_similarity: float
    ) -> Dict[str, Any]:
        """
        Get detailed information about rule evaluation.
        
        Args:
            similarities: Component similarity scores
            addr1: First normalized address
            addr2: Second normalized address
            overall_similarity: Overall similarity score
            
        Returns:
            Dictionary with rule evaluation details
        """
        details = {
            'region': self.region,
            'overall_threshold_passed': overall_similarity >= self.overall_threshold,
            'postal_code_rule_passed': self._check_postal_code_rule(similarities, addr1, addr2),
            'city_rule_passed': self._check_city_rule(similarities, addr1, addr2),
            'street_rule_passed': self._check_street_rule(similarities, addr1, addr2),
            'house_number_rule_passed': self._check_house_number_rule(similarities, addr1, addr2),
            'country_rule_passed': self._check_country_rule(similarities, addr1, addr2),
            'state_rule_passed': self._check_state_rule(similarities, addr1, addr2),
            'region_specific_rules_passed': self._check_region_specific_rules(similarities, addr1, addr2),
            'thresholds_used': {
                'postal_code': self.postal_code_threshold,
                'street': self.street_threshold,
                'city': self.city_threshold,
                'house_number': self.house_number_threshold,
                'overall': self.overall_threshold
            },
            'requirements': {
                'require_postal_code_match': self.require_postal_code_match,
                'require_city_match': self.require_city_match,
                'require_street_match': self.require_street_match,
            },
            'regional_features': {
                'allow_partial_house_number': self.allow_partial_house_number,
                'allow_house_names': self.allow_house_names,
                'allow_area_locality_matching': self.allow_area_locality_matching,
                'state_abbreviation_matching': self.state_abbreviation_matching,
            }
        }
        
        return details
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update configuration values."""
        self.config.update(new_config)
        
        # Update individual threshold values
        self.postal_code_threshold = self.config.get('postal_code_threshold', self.postal_code_threshold)
        self.street_threshold = self.config.get('street_threshold', self.street_threshold)
        self.city_threshold = self.config.get('city_threshold', self.city_threshold)
        self.house_number_threshold = self.config.get('house_number_threshold', self.house_number_threshold)
        self.overall_threshold = self.config.get('overall_threshold', self.overall_threshold)
        
        # Update requirements
        self.require_postal_code_match = self.config.get('require_postal_code_match', self.require_postal_code_match)
        self.require_city_match = self.config.get('require_city_match', self.require_city_match)
        self.require_street_match = self.config.get('require_street_match', self.require_street_match)
        
        logger.info(f"RuleBasedFilter configuration updated: {list(new_config.keys())}") 