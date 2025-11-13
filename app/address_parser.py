import re
from typing import Dict, Optional, List, Tuple
from loguru import logger

try:
    import postal.parser as postal_parser
    import postal.expand as postal_expand
    POSTAL_AVAILABLE = True
    logger.info("Postal library is available")
except ImportError:
    POSTAL_AVAILABLE = False
    logger.warning("Postal library not available, using fallback parser")

from app.models import NormalizedAddress


class RegionDetector:
    """Detect the region/country of an address for region-specific parsing."""
    
    # Postal code patterns for different regions
    POSTAL_PATTERNS = {
        'US': r'\b\d{5}(-\d{4})?\b',  # 12345 or 12345-6789
        'CA': r'\b[A-Z]\d[A-Z]\s?\d[A-Z]\d\b',  # K1A 0A6
        'UK': r'\b[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}\b',  # SW1A 1AA
        'DE': r'\b\d{5}\b',  # 12345
        'FR': r'\b\d{5}\b',  # 75001
        'IT': r'\b\d{5}\b',  # 00118
        'ES': r'\b\d{5}\b',  # 28001
        'IN': r'\b\d{6}\b',  # 110001 (pincode)
        'AU': r'\b\d{4}\b',  # 2000
        'NL': r'\b\d{4}\s?[A-Z]{2}\b',  # 1012 AB
        'SE': r'\b\d{3}\s?\d{2}\b',  # 123 45
        'NO': r'\b\d{4}\b',  # 0150
        'CH': r'\b\d{4}\b',  # 8001
    }
    
    # Country indicators
    COUNTRY_INDICATORS = {
        'US': ['usa', 'united states', 'america', 'us'],
        'CA': ['canada', 'can', 'ca'],
        'UK': ['uk', 'united kingdom', 'britain', 'england', 'scotland', 'wales'],
        'DE': ['germany', 'deutschland', 'de'],
        'FR': ['france', 'fr'],
        'IT': ['italy', 'italia', 'it'],
        'ES': ['spain', 'españa', 'es'],
        'IN': ['india', 'bharat', 'in'],
        'AU': ['australia', 'au'],
        'NL': ['netherlands', 'holland', 'nl'],
        'SE': ['sweden', 'sverige', 'se'],
        'NO': ['norway', 'norge', 'no'],
        'CH': ['switzerland', 'schweiz', 'ch'],
    }
    
    @classmethod
    def detect_region(cls, address: str) -> str:
        """Detect the region/country of an address."""
        address_lower = address.lower()
        
        # First check for explicit country mentions using word boundaries
        for country_code, indicators in cls.COUNTRY_INDICATORS.items():
            for indicator in indicators:
                # Use word boundaries to avoid false positives like "in" matching "main"
                pattern = r'\b' + re.escape(indicator) + r'\b'
                if re.search(pattern, address_lower):
                    return country_code
        
        # Check postal code patterns
        for country_code, pattern in cls.POSTAL_PATTERNS.items():
            if re.search(pattern, address, re.IGNORECASE):
                return country_code
        
        # Default to US if no clear indicators
        return 'US'


class AddressParser:
    """
    Enhanced address parser supporting Indian, European, and American address formats.
    """
    
    def __init__(self):
        self.postal_available = POSTAL_AVAILABLE
        self.region_detector = RegionDetector()
        
        # Regional abbreviation mappings
        self.abbreviations = {
            'US': self._get_us_abbreviations(),
            'CA': self._get_ca_abbreviations(),
            'UK': self._get_uk_abbreviations(),
            'DE': self._get_de_abbreviations(),
            'FR': self._get_fr_abbreviations(),
            'IT': self._get_it_abbreviations(),
            'ES': self._get_es_abbreviations(),
            'IN': self._get_in_abbreviations(),
            'AU': self._get_au_abbreviations(),
            'NL': self._get_nl_abbreviations(),
            'SE': self._get_se_abbreviations(),
            'NO': self._get_no_abbreviations(),
            'CH': self._get_ch_abbreviations(),
        }
        
    def normalize_and_parse(self, address: str) -> NormalizedAddress:
        """
        Parse and normalize an address string into components.
        
        Args:
            address: Raw address string
            
        Returns:
            NormalizedAddress object with parsed components
        """
        if not address or not address.strip():
            return NormalizedAddress()
            
        address = address.strip()
        
        # Detect region for region-specific processing
        region = self.region_detector.detect_region(address)
        
        if self.postal_available:
            return self._parse_with_postal(address, region)
        else:
            return self._parse_with_fallback(address, region)
    
    def _parse_with_postal(self, address: str, region: str) -> NormalizedAddress:
        """Parse address using libpostal with region-specific processing."""
        try:
            # Pre-normalize for better postal parsing
            normalized_addr = self._pre_normalize_address(address, region)
            
            # First expand the address to normalize abbreviations
            expanded = postal_expand.expand_address(normalized_addr)
            if expanded:
                normalized_addr = expanded[0]  # Take the first expansion
            
            # Parse the address into components
            parsed = postal_parser.parse_address(normalized_addr)
            
            components = {}
            for component, label in parsed:
                if label == 'house_number':
                    components['house_number'] = component
                elif label == 'road':
                    components['street'] = component
                elif label == 'city':
                    components['city'] = component
                elif label == 'postcode':
                    components['postal_code'] = component
                elif label == 'state':
                    components['state'] = component
                elif label == 'country':
                    components['country'] = component
            
            # Post-process for region-specific adjustments
            components = self._post_process_components(components, region, address)
            
            return NormalizedAddress(**components)
            
        except Exception as e:
            logger.error(f"Error parsing address with postal: {e}")
            return self._parse_with_fallback(address, region)
    
    def _parse_with_fallback(self, address: str, region: str) -> NormalizedAddress:
        """
        Enhanced fallback parser with region-specific patterns.
        """
        components = {}
        
        # Normalize the address
        normalized = self._normalize_address(address, region)
        
        # Apply region-specific parsing
        if region == 'IN':
            components = self._parse_indian_address(normalized)
        elif region in ['UK', 'IE']:
            components = self._parse_uk_address(normalized)
        elif region in ['DE', 'AT']:
            components = self._parse_german_address(normalized)
        elif region == 'FR':
            components = self._parse_french_address(normalized)
        elif region in ['IT', 'ES', 'PT']:
            components = self._parse_southern_european_address(normalized)
        elif region in ['SE', 'NO', 'DK', 'FI']:
            components = self._parse_nordic_address(normalized)
        elif region == 'CA':
            components = self._parse_canadian_address(normalized)
        elif region == 'AU':
            components = self._parse_australian_address(normalized)
        else:  # Default to US/international parsing
            components = self._parse_us_address(normalized)
        
        # Extract common components that work across regions
        if not components:
            components = self._parse_generic_address(normalized)
            
        return NormalizedAddress(**components)
    
    def _parse_indian_address(self, address: str) -> Dict[str, str]:
        """Parse Indian address format with pincode, area, landmark support."""
        components = {}
        
        # Extract pincode (6 digits)
        pincode_match = re.search(r'\b(\d{6})\b', address)
        if pincode_match:
            components['postal_code'] = pincode_match.group(1)
            address = address.replace(pincode_match.group(0), '').strip()
        
        # Extract state (often at the end)
        indian_states = ['andhra pradesh', 'arunachal pradesh', 'assam', 'bihar', 'chhattisgarh', 
                        'goa', 'gujarat', 'haryana', 'himachal pradesh', 'jharkhand', 'karnataka',
                        'kerala', 'madhya pradesh', 'maharashtra', 'manipur', 'meghalaya', 'mizoram',
                        'nagaland', 'odisha', 'punjab', 'rajasthan', 'sikkim', 'tamil nadu', 'telangana',
                        'tripura', 'uttar pradesh', 'uttarakhand', 'west bengal', 'delhi', 'mumbai',
                        'kolkata', 'chennai', 'bangalore', 'hyderabad', 'pune', 'ahmedabad']
        
        for state in indian_states:
            if state in address.lower():
                components['state'] = state.title()
                address = re.sub(re.escape(state), '', address, flags=re.IGNORECASE).strip()
                break
        
        # Extract city/district (common Indian city names)
        parts = [part.strip() for part in address.split(',')]
        
        # House/flat number often starts with flat, apartment, house, etc.
        house_match = re.search(r'^(flat|apartment|house|plot|door|no\.?)\s*[#-]?\s*([a-z0-9/-]+)', address, re.IGNORECASE)
        if house_match:
            components['house_number'] = house_match.group(2)
            address = address[len(house_match.group(0)):].strip()
        else:
            # Extract leading number
            number_match = re.match(r'^([0-9]+[a-z]?[-/]?[0-9]*[a-z]?)\s+', address)
            if number_match:
                components['house_number'] = number_match.group(1)
                address = address[len(number_match.group(0)):].strip()
        
        # Remaining parsing for street and area
        parts = [part.strip() for part in address.split(',') if part.strip()]
        
        if len(parts) >= 1:
            components['street'] = parts[0]
        if len(parts) >= 2:
            components['city'] = parts[-1]  # City usually last
            if len(parts) >= 3:
                # Middle parts could be area/locality
                components['area'] = ', '.join(parts[1:-1])
        
        return components
    
    def _parse_uk_address(self, address: str) -> Dict[str, str]:
        """Parse UK address format with postcode support."""
        components = {}
        
        # Extract UK postcode (complex pattern)
        postcode_match = re.search(r'\b([A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})\b', address, re.IGNORECASE)
        if postcode_match:
            components['postal_code'] = postcode_match.group(1).upper()
            address = address.replace(postcode_match.group(0), '').strip()
        
        # Extract country
        for country in ['uk', 'united kingdom', 'england', 'scotland', 'wales', 'northern ireland']:
            if country in address.lower():
                components['country'] = 'UK'
                address = re.sub(re.escape(country), '', address, flags=re.IGNORECASE).strip()
                break
        
        # Extract house number/name (can be at start)
        house_match = re.match(r'^([0-9]+[a-z]?[-]?[a-z]?|[a-z\s]+house|[a-z\s]+cottage|[a-z\s]+flat)\s+', address, re.IGNORECASE)
        if house_match:
            components['house_number'] = house_match.group(1).strip()
            address = address[len(house_match.group(0)):].strip()
        
        # Split by comma for remaining parts
        parts = [part.strip() for part in address.split(',') if part.strip()]
        
        if len(parts) >= 1:
            components['street'] = parts[0]
        if len(parts) >= 2:
            components['city'] = parts[-1]
        if len(parts) >= 3:
            # Could be area/county
            components['state'] = parts[-2]
        
        return components
    
    def _parse_german_address(self, address: str) -> Dict[str, str]:
        """Parse German address format (PLZ + Stadt)."""
        components = {}
        
        # Extract German postal code (5 digits)
        plz_match = re.search(r'\b(\d{5})\b', address)
        if plz_match:
            components['postal_code'] = plz_match.group(1)
            address = address.replace(plz_match.group(0), '').strip()
        
        # Extract country
        for country in ['germany', 'deutschland', 'de']:
            if country in address.lower():
                components['country'] = 'Germany'
                address = re.sub(re.escape(country), '', address, flags=re.IGNORECASE).strip()
                break
        
        # German format: Street Number, PLZ City
        parts = [part.strip() for part in address.split(',') if part.strip()]
        
        if len(parts) >= 1:
            # First part usually contains street and house number
            street_part = parts[0]
            # House number usually at the end
            number_match = re.search(r'\s+(\d+[a-z]?)\s*$', street_part, re.IGNORECASE)
            if number_match:
                components['house_number'] = number_match.group(1)
                components['street'] = street_part[:number_match.start()].strip()
            else:
                components['street'] = street_part
        
        if len(parts) >= 2:
            components['city'] = parts[1]
        
        return components
    
    def _parse_french_address(self, address: str) -> Dict[str, str]:
        """Parse French address format."""
        components = {}
        
        # Extract French postal code (5 digits)
        postal_match = re.search(r'\b(\d{5})\b', address)
        if postal_match:
            components['postal_code'] = postal_match.group(1)
            address = address.replace(postal_match.group(0), '').strip()
        
        # Extract country
        for country in ['france', 'fr']:
            if country in address.lower():
                components['country'] = 'France'
                address = re.sub(re.escape(country), '', address, flags=re.IGNORECASE).strip()
                break
        
        # French format: Number Street, Postal City
        parts = [part.strip() for part in address.split(',') if part.strip()]
        
        if len(parts) >= 1:
            # Extract house number from beginning
            number_match = re.match(r'^(\d+[a-z]?)\s+', parts[0])
            if number_match:
                components['house_number'] = number_match.group(1)
                components['street'] = parts[0][len(number_match.group(0)):].strip()
            else:
                components['street'] = parts[0]
        
        if len(parts) >= 2:
            components['city'] = parts[1]
        
        return components
    
    def _parse_southern_european_address(self, address: str) -> Dict[str, str]:
        """Parse Italian/Spanish/Portuguese address format."""
        components = {}
        
        # Extract postal code (5 digits)
        postal_match = re.search(r'\b(\d{5})\b', address)
        if postal_match:
            components['postal_code'] = postal_match.group(1)
            address = address.replace(postal_match.group(0), '').strip()
        
        # Extract country
        countries = {'italy': 'Italy', 'italia': 'Italy', 'spain': 'Spain', 'españa': 'Spain', 
                    'portugal': 'Portugal'}
        for country, standard_name in countries.items():
            if country in address.lower():
                components['country'] = standard_name
                address = re.sub(re.escape(country), '', address, flags=re.IGNORECASE).strip()
                break
        
        result = self._parse_generic_address(address, components)
        return result if result is not None else components
    
    def _parse_nordic_address(self, address: str) -> Dict[str, str]:
        """Parse Nordic address format (Sweden, Norway, Denmark, Finland)."""
        components = {}
        
        # Extract postal codes (various Nordic formats)
        postal_patterns = {
            'SE': r'\b(\d{3}\s?\d{2})\b',  # Sweden: 123 45
            'NO': r'\b(\d{4})\b',  # Norway: 0150
            'DK': r'\b(\d{4})\b',  # Denmark: 1000
            'FI': r'\b(\d{5})\b',  # Finland: 00100
        }
        
        for pattern in postal_patterns.values():
            postal_match = re.search(pattern, address)
            if postal_match:
                components['postal_code'] = postal_match.group(1)
                address = address.replace(postal_match.group(0), '').strip()
                break
        
        result = self._parse_generic_address(address, components)
        return result if result is not None else components
    
    def _parse_canadian_address(self, address: str) -> Dict[str, str]:
        """Parse Canadian address format."""
        components = {}
        
        # Extract Canadian postal code
        postal_match = re.search(r'\b([A-Z]\d[A-Z]\s?\d[A-Z]\d)\b', address, re.IGNORECASE)
        if postal_match:
            components['postal_code'] = postal_match.group(1).upper()
            address = address.replace(postal_match.group(0), '').strip()
        
        # Extract province abbreviations
        ca_provinces = ['AB', 'BC', 'MB', 'NB', 'NL', 'NT', 'NS', 'NU', 'ON', 'PE', 'QC', 'SK', 'YT']
        for province in ca_provinces:
            if f' {province} ' in address.upper() or address.upper().endswith(f' {province}'):
                components['state'] = province
                address = re.sub(f'\\b{province}\\b', '', address, flags=re.IGNORECASE).strip()
                break
        
        result = self._parse_us_address(address, components)
        return result if result is not None else components
    
    def _parse_australian_address(self, address: str) -> Dict[str, str]:
        """Parse Australian address format."""
        components = {}
        
        # Extract Australian postal code (4 digits)
        postal_match = re.search(r'\b(\d{4})\b', address)
        if postal_match:
            components['postal_code'] = postal_match.group(1)
            address = address.replace(postal_match.group(0), '').strip()
        
        # Extract state abbreviations
        au_states = ['NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT']
        for state in au_states:
            if f' {state} ' in address.upper() or address.upper().endswith(f' {state}'):
                components['state'] = state
                address = re.sub(f'\\b{state}\\b', '', address, flags=re.IGNORECASE).strip()
                break
        
        result = self._parse_generic_address(address, components)
        return result if result is not None else components
    
    def _parse_us_address(self, address: str, existing_components: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Parse US address format."""
        components = existing_components or {}
        
        # Extract US postal code (5 or 9 digits)
        if 'postal_code' not in components:
            postal_match = re.search(r'\b(\d{5}(-\d{4})?)\b', address)
            if postal_match:
                components['postal_code'] = postal_match.group(1)
                address = address.replace(postal_match.group(0), '').strip()
        
        # Extract state abbreviations
        us_states = ['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 
                    'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 
                    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 
                    'VA', 'WA', 'WV', 'WI', 'WY', 'DC']
        
        for state in us_states:
            if f' {state} ' in address.upper() or address.upper().endswith(f' {state}'):
                components['state'] = state
                address = re.sub(f'\\b{state}\\b', '', address, flags=re.IGNORECASE).strip()
                break
        
        # Clean up trailing commas and extra spaces after removing postal code and state
        address = re.sub(r'\s*,\s*$', '', address).strip()
        address = re.sub(r'\s+', ' ', address)
        
        result = self._parse_generic_address(address, components)
        return result if result is not None else components
    
    def _parse_generic_address(self, address: str, existing_components: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Generic address parsing for any format."""
        components = existing_components or {}
        
        # Extract house number (at the beginning)
        if 'house_number' not in components:
            house_match = re.match(r'^(\d+[A-Z]?[-]?[A-Z]?)\s+', address, re.IGNORECASE)
            if house_match:
                components['house_number'] = house_match.group(1)
                address = address[len(house_match.group(0)):].strip()
        
        # Split remaining parts by comma and filter out empty parts
        parts = [part.strip() for part in address.split(',') if part.strip()]
        
        if len(parts) >= 1 and 'street' not in components:
            components['street'] = parts[0]
        if len(parts) >= 2 and 'city' not in components:
            components['city'] = parts[-1]  # City usually last
        if len(parts) >= 3 and 'state' not in components:
            components['state'] = parts[-2]  # State usually second to last
            
        return components
    
    def _normalize_address(self, address: str, region: str) -> str:
        """
        Enhanced address normalization with region-specific abbreviations.
        """
        # Convert to uppercase for consistent processing
        normalized = address.upper()
        
        # Apply region-specific abbreviation expansions
        region_abbrevs = self.abbreviations.get(region, {})
        for pattern, replacement in region_abbrevs.items():
            normalized = re.sub(pattern, replacement, normalized)
        
        # Remove extra whitespace and normalize punctuation
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = re.sub(r'[.,;]+', ',', normalized)
        
        return normalized.strip()
    
    def _pre_normalize_address(self, address: str, region: str) -> str:
        """Pre-normalize address before sending to postal."""
        # Light normalization to help postal parsing
        normalized = address.strip()
        
        # Fix common formatting issues
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized
    
    def _post_process_components(self, components: Dict[str, str], region: str, original_address: str) -> Dict[str, str]:
        """Post-process components for region-specific adjustments."""
        # Add region-specific post-processing logic here
        if region == 'IN' and 'postal_code' in components:
            # Ensure Indian postal codes are 6 digits
            postal = components['postal_code']
            if len(postal) == 6 and postal.isdigit():
                components['postal_code'] = postal
            else:
                # Try to extract 6-digit pincode from original
                pincode_match = re.search(r'\b(\d{6})\b', original_address)
                if pincode_match:
                    components['postal_code'] = pincode_match.group(1)
        
        return components
    
    # Regional abbreviation dictionaries
    def _get_us_abbreviations(self) -> Dict[str, str]:
        """US address abbreviations."""
        return {
            r'\bST\.?\b': 'STREET',
            r'\bAVE\.?\b': 'AVENUE',
            r'\bRD\.?\b': 'ROAD',
            r'\bDR\.?\b': 'DRIVE',
            r'\bLN\.?\b': 'LANE',
            r'\bBLVD\.?\b': 'BOULEVARD',
            r'\bCT\.?\b': 'COURT',
            r'\bPL\.?\b': 'PLACE',
            r'\bAPT\.?\b': 'APARTMENT',
            r'\bSTE\.?\b': 'SUITE',
            r'\bN\.?\b': 'NORTH',
            r'\bS\.?\b': 'SOUTH',
            r'\bE\.?\b': 'EAST',
            r'\bW\.?\b': 'WEST',
            r'\bNE\.?\b': 'NORTHEAST',
            r'\bNW\.?\b': 'NORTHWEST',
            r'\bSE\.?\b': 'SOUTHEAST',
            r'\bSW\.?\b': 'SOUTHWEST'
        }
    
    def _get_ca_abbreviations(self) -> Dict[str, str]:
        """Canadian address abbreviations."""
        abbrevs = self._get_us_abbreviations()  # Start with US abbreviations
        abbrevs.update({
            r'\bCRES\.?\b': 'CRESCENT',
            r'\bHWY\.?\b': 'HIGHWAY',
            r'\bTRL\.?\b': 'TRAIL',
        })
        return abbrevs
    
    def _get_uk_abbreviations(self) -> Dict[str, str]:
        """UK address abbreviations."""
        return {
            r'\bST\.?\b': 'STREET',
            r'\bRD\.?\b': 'ROAD',
            r'\bAVE\.?\b': 'AVENUE',
            r'\bLN\.?\b': 'LANE',
            r'\bCL\.?\b': 'CLOSE',
            r'\bGDNS\.?\b': 'GARDENS',
            r'\bPK\.?\b': 'PARK',
            r'\bSQ\.?\b': 'SQUARE',
            r'\bTER\.?\b': 'TERRACE',
            r'\bCRES\.?\b': 'CRESCENT',
            r'\bGR\.?\b': 'GROVE',
            r'\bHILL\.?\b': 'HILL',
            r'\bFLAT\.?\b': 'FLAT',
        }
    
    def _get_de_abbreviations(self) -> Dict[str, str]:
        """German address abbreviations."""
        return {
            r'\bSTR\.?\b': 'STRASSE',
            r'\bALLEE\.?\b': 'ALLEE',
            r'\bWEG\.?\b': 'WEG',
            r'\bPLATZ\.?\b': 'PLATZ',
            r'\bGASSE\.?\b': 'GASSE',
        }
    
    def _get_fr_abbreviations(self) -> Dict[str, str]:
        """French address abbreviations."""
        return {
            r'\bRUE\.?\b': 'RUE',
            r'\bAV\.?\b': 'AVENUE',
            r'\bBD\.?\b': 'BOULEVARD',
            r'\bPL\.?\b': 'PLACE',
            r'\bIMP\.?\b': 'IMPASSE',
        }
    
    def _get_it_abbreviations(self) -> Dict[str, str]:
        """Italian address abbreviations."""
        return {
            r'\bVIA\.?\b': 'VIA',
            r'\bP\.ZA\.?\b': 'PIAZZA',
            r'\bV\.LE\.?\b': 'VIALE',
            r'\bCORSO\.?\b': 'CORSO',
        }
    
    def _get_es_abbreviations(self) -> Dict[str, str]:
        """Spanish address abbreviations."""
        return {
            r'\bC/\.?\b': 'CALLE',
            r'\bAV\.?\b': 'AVENIDA',
            r'\bPL\.?\b': 'PLAZA',
            r'\bPSEO\.?\b': 'PASEO',
        }
    
    def _get_in_abbreviations(self) -> Dict[str, str]:
        """Indian address abbreviations."""
        return {
            r'\bST\.?\b': 'STREET',
            r'\bRD\.?\b': 'ROAD',
            r'\bAVE\.?\b': 'AVENUE',
            r'\bCOLONY\.?\b': 'COLONY',
            r'\bSECTOR\.?\b': 'SECTOR',
            r'\bBLOCK\.?\b': 'BLOCK',
            r'\bPHASE\.?\b': 'PHASE',
            r'\bNAGAR\.?\b': 'NAGAR',
            r'\bPURA\.?\b': 'PURA',
            r'\bGRAM\.?\b': 'GRAM',
            r'\bVILLAGE\.?\b': 'VILLAGE',
            r'\bTEHSIL\.?\b': 'TEHSIL',
            r'\bDIST\.?\b': 'DISTRICT',
        }
    
    def _get_au_abbreviations(self) -> Dict[str, str]:
        """Australian address abbreviations."""
        return {
            r'\bST\.?\b': 'STREET',
            r'\bRD\.?\b': 'ROAD',
            r'\bAVE\.?\b': 'AVENUE',
            r'\bLN\.?\b': 'LANE',
            r'\bCCT\.?\b': 'CIRCUIT',
            r'\bCL\.?\b': 'CLOSE',
            r'\bCT\.?\b': 'COURT',
            r'\bCR\.?\b': 'CRESCENT',
            r'\bDR\.?\b': 'DRIVE',
            r'\bESP\.?\b': 'ESPLANADE',
            r'\bGR\.?\b': 'GROVE',
            r'\bHWY\.?\b': 'HIGHWAY',
            r'\bPDE\.?\b': 'PARADE',
            r'\bPL\.?\b': 'PLACE',
            r'\bTCE\.?\b': 'TERRACE',
        }
    
    def _get_nl_abbreviations(self) -> Dict[str, str]:
        """Dutch address abbreviations."""
        return {
            r'\bSTR\.?\b': 'STRAAT',
            r'\bLAAN\.?\b': 'LAAN',
            r'\bWEG\.?\b': 'WEG',
            r'\bPLEIN\.?\b': 'PLEIN',
        }
    
    def _get_se_abbreviations(self) -> Dict[str, str]:
        """Swedish address abbreviations."""
        return {
            r'\bGATA\.?\b': 'GATA',
            r'\bVÄG\.?\b': 'VÄG',
            r'\bTORG\.?\b': 'TORG',
            r'\bPLAN\.?\b': 'PLAN',
        }
    
    def _get_no_abbreviations(self) -> Dict[str, str]:
        """Norwegian address abbreviations."""
        return {
            r'\bGT\.?\b': 'GATE',
            r'\bVEI\.?\b': 'VEI',
            r'\bTORG\.?\b': 'TORG',
            r'\bPL\.?\b': 'PLASS',
        }
    
    def _get_ch_abbreviations(self) -> Dict[str, str]:
        """Swiss address abbreviations."""
        return {
            r'\bSTR\.?\b': 'STRASSE',
            r'\bGASSE\.?\b': 'GASSE',
            r'\bWEG\.?\b': 'WEG',
            r'\bPLATZ\.?\b': 'PLATZ',
        }
    
    def get_address_components(self, address: str) -> Dict[str, Optional[str]]:
        """
        Get address components as a dictionary.
        """
        parsed = self.normalize_and_parse(address)
        return {
            'house_number': parsed.house_number,
            'street': parsed.street,
            'city': parsed.city,
            'postal_code': parsed.postal_code,
            'state': parsed.state,
            'country': parsed.country
        } 