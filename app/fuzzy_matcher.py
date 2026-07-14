from typing import Dict, Optional, Tuple, List
from loguru import logger
import re

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
    logger.debug("RapidFuzz library is available")
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logger.debug("RapidFuzz library not available, using fallback similarity")

from app.models import NormalizedAddress, ComponentSimilarities


class TransliterationMatcher:
    """Handle transliteration and script variations for international addresses."""
    
    # Common transliteration mappings
    TRANSLITERATION_MAPPINGS = {
        # Devanagari to Roman (Hindi/Sanskrit)
        'देवनागरी': ['devanagari', 'devnagri'],
        'दिल्ली': ['delhi', 'dilli'],
        'मुंबई': ['mumbai', 'bombay'],
        'बेंगलुरु': ['bengaluru', 'bangalore'],
        'हैदराबाद': ['hyderabad', 'haidarabad'],
        'कोलकाता': ['kolkata', 'calcutta'],
        'चेन्नई': ['chennai', 'madras'],
        'पुणे': ['pune', 'poona'],
        'नगर': ['nagar', 'nagr'],
        'रोड': ['road', 'rd'],
        'स्ट्रीट': ['street', 'st'],
        
        # Common international variations
        'centre': ['center'],
        'colour': ['color'],
        'honour': ['honor'],
        'theatre': ['theater'],
        
        # European variations
        'straße': ['strasse', 'str', 'street', 'st'],
        'strasse': ['straße', 'str', 'street', 'st'],
        'platz': ['plaza', 'place'],
        'gasse': ['lane', 'ln'],
        
        # Common abbreviations and expansions
        'saint': ['st', 'saint'],
        'mount': ['mt', 'mount'],
        'fort': ['ft', 'fort'],
        'north': ['n', 'north', 'northern'],
        'south': ['s', 'south', 'southern'],
        'east': ['e', 'east', 'eastern'],
        'west': ['w', 'west', 'western'],
        
        # US City abbreviations and common variations
        'new york': ['nyc', 'ny', 'new york city'],
        'nyc': ['new york', 'new york city'],
        'los angeles': ['la', 'los angeles'],
        'la': ['los angeles'],
        'san francisco': ['sf', 'san fran'],
        'sf': ['san francisco'],
        'san antonio': ['san antonio', 'sa'],
        'chicago': ['chi', 'chicago'],
        'philadelphia': ['philly', 'philadelphia'],
        'philly': ['philadelphia'],
        'las vegas': ['vegas', 'las vegas'],
        'vegas': ['las vegas'],
    }
    
    @classmethod
    def normalize_for_comparison(cls, text: str) -> str:
        """Normalize text for better transliteration matching."""
        if not text:
            return ""
        
        text = text.lower().strip()
        
        # Apply transliteration mappings
        for original, variants in cls.TRANSLITERATION_MAPPINGS.items():
            if original in text:
                for variant in variants:
                    text = text.replace(original, variant)
                    break
        
        # Remove diacritics and special characters
        text = re.sub(r'[àáâãäåæçèéêëìíîïñòóôõöøùúûüý]', '', text)
        text = re.sub(r'[^\w\s-]', '', text)
        
        return text
    
    @classmethod
    def get_similarity_with_transliteration(cls, text1: str, text2: str, base_similarity: float) -> float:
        """Calculate similarity considering transliteration variations."""
        if not text1 or not text2:
            return base_similarity
        
        # Normalize both texts
        norm1 = cls.normalize_for_comparison(text1)
        norm2 = cls.normalize_for_comparison(text2)
        
        # If normalized versions match better, boost similarity
        if norm1 == norm2:
            return min(1.0, base_similarity + 0.2)
        
        # Check for partial matches with common transliterations
        for original, variants in cls.TRANSLITERATION_MAPPINGS.items():
            if (original in text1.lower() and any(v in text2.lower() for v in variants)) or \
               (original in text2.lower() and any(v in text1.lower() for v in variants)):
                return min(1.0, base_similarity + 0.1)
        
        return base_similarity


class RegionAwareWeights:
    """Region-specific component weights (delegates to RegionRegistry)."""

    @classmethod
    def get_weights(cls, region: str) -> Dict[str, float]:
        from app.regions import RegionRegistry
        return RegionRegistry.get_weights(region)


class FuzzyMatcher:
    """
    Enhanced fuzzy string matching for international address components.
    """
    
    def __init__(self, region: str = 'US', weights: Optional[Dict[str, float]] = None):
        self.rapidfuzz_available = RAPIDFUZZ_AVAILABLE
        self.region = region
        self.transliteration_matcher = TransliterationMatcher()
        self._weights_override = weights
        
    def set_region(self, region: str):
        """Set the region for region-specific matching."""
        self.region = region

    def _weights_for(self, region: str) -> Dict[str, float]:
        if self._weights_override:
            return self._weights_override
        return RegionAwareWeights.get_weights(region)
        
    def compute_component_similarities(
        self, 
        addr1: NormalizedAddress, 
        addr2: NormalizedAddress
    ) -> ComponentSimilarities:
        """
        Compute similarity scores for each address component with region awareness.
        
        Args:
            addr1: First normalized address
            addr2: Second normalized address
            
        Returns:
            ComponentSimilarities object with scores for each component
        """
        similarities = {}
        
        # Define components to compare
        components = [
            'house_number', 'street', 'city', 'postal_code', 'state', 'country'
        ]
        
        for component in components:
            val1 = getattr(addr1, component)
            val2 = getattr(addr2, component)
            
            if val1 is None or val2 is None:
                # If either component is missing, set similarity to None
                similarities[component] = None
            else:
                similarities[component] = self._compute_similarity(val1, val2, component)
        
        return ComponentSimilarities(**similarities)
    
    def _compute_similarity(self, str1: str, str2: str, component_type: str) -> float:
        """
        Compute similarity between two strings based on component type and region.
        
        Args:
            str1: First string
            str2: Second string
            component_type: Type of address component
            
        Returns:
            Similarity score between 0 and 1
        """
        if not str1 or not str2:
            return 0.0
            
        # Normalize strings
        str1 = str1.strip().upper()
        str2 = str2.strip().upper()
        
        if str1 == str2:
            return 1.0
        
        if self.rapidfuzz_available:
            similarity = self._compute_rapidfuzz_similarity(str1, str2, component_type)
        else:
            similarity = self._compute_fallback_similarity(str1, str2, component_type)
        
        # Apply transliteration enhancement
        similarity = self.transliteration_matcher.get_similarity_with_transliteration(
            str1, str2, similarity
        )
        
        # Apply region-specific adjustments
        similarity = self._apply_region_specific_adjustments(similarity, str1, str2, component_type)
        
        return min(1.0, similarity)
    
    def _compute_rapidfuzz_similarity(self, str1: str, str2: str, component_type: str) -> float:
        """
        Compute similarity using RapidFuzz library with enhanced algorithms.
        """
        # Different similarity algorithms based on component type and region
        if component_type == 'postal_code':
            # Postal codes should match exactly or very closely
            if self.region == 'IN':
                # Indian pincodes: exact match or very close
                score = fuzz.ratio(str1, str2)
            elif self.region in ['UK', 'CA']:
                # UK/Canadian postal codes: allow for formatting differences
                score = max(
                    fuzz.ratio(str1, str2),
                    fuzz.ratio(str1.replace(' ', ''), str2.replace(' ', ''))
                )
            else:
                score = fuzz.ratio(str1, str2)
                
        elif component_type == 'house_number':
            # House numbers: check various formats
            # Remove common prefixes/suffixes
            clean1 = re.sub(r'^(FLAT|APT|UNIT|SUITE|#)\s*', '', str1)
            clean2 = re.sub(r'^(FLAT|APT|UNIT|SUITE|#)\s*', '', str2)
            
            scores = [
                fuzz.ratio(str1, str2),
                fuzz.ratio(clean1, clean2),
                fuzz.token_set_ratio(str1, str2)
            ]
            score = max(scores)
            
        elif component_type in ['street', 'city']:
            # For streets and cities, use multiple algorithms
            scores = [
                fuzz.partial_ratio(str1, str2),
                fuzz.token_sort_ratio(str1, str2),
                fuzz.token_set_ratio(str1, str2)
            ]
            
            # Special handling for Indian addresses
            if self.region == 'IN':
                # Indian addresses often have complex locality names
                scores.append(fuzz.WRatio(str1, str2))
            
            score = max(scores)
            
        elif component_type == 'state':
            # State matching: allow abbreviations and full names
            score = max(
                fuzz.ratio(str1, str2),
                fuzz.partial_ratio(str1, str2),
                fuzz.token_set_ratio(str1, str2)
            )
            
        elif component_type == 'country':
            # Country matching: very flexible for variations
            score = max(
                fuzz.ratio(str1, str2),
                fuzz.partial_ratio(str1, str2),
                fuzz.token_set_ratio(str1, str2)
            )
            
        else:
            # Default algorithm
            score = fuzz.ratio(str1, str2)
        
        return score / 100.0  # Convert to 0-1 scale
    
    def _compute_fallback_similarity(self, str1: str, str2: str, component_type: str) -> float:
        """
        Enhanced fallback similarity computation using Levenshtein distance.
        """
        # Enhanced Levenshtein with component-specific weights
        def weighted_levenshtein_distance(s1: str, s2: str, component_type: str) -> int:
            if len(s1) < len(s2):
                s1, s2 = s2, s1
                
            if len(s2) == 0:
                return len(s1)
            
            # Component-specific character weights
            char_weights = self._get_character_weights(component_type)
                
            previous_row = list(range(len(s2) + 1))
            for i, c1 in enumerate(s1):
                current_row = [i + 1]
                for j, c2 in enumerate(s2):
                    insertions = previous_row[j + 1] + int(char_weights.get(c1, 1.0))
                    deletions = current_row[j] + int(char_weights.get(c2, 1.0))
                    
                    if c1 == c2:
                        substitutions = previous_row[j]
                    else:
                        # Lower cost for similar characters
                        sub_cost = self._get_substitution_cost(c1, c2, component_type)
                        substitutions = previous_row[j] + int(sub_cost)
                    
                    current_row.append(min(insertions, deletions, substitutions))
                previous_row = current_row
                
            return previous_row[-1]
        
        max_len = max(len(str1), len(str2))
        if max_len == 0:
            return 1.0
            
        distance = weighted_levenshtein_distance(str1, str2, component_type)
        similarity = 1.0 - (distance / (max_len * 2))  # Adjust for weighted costs
        
        # Apply component-specific adjustments
        similarity = self._apply_component_adjustments(similarity, str1, str2, component_type)
        
        return max(0.0, similarity)
    
    def _get_character_weights(self, component_type: str) -> Dict[str, float]:
        """Get character-specific weights for different components."""
        if component_type == 'postal_code':
            # All characters equally important in postal codes
            return {}
        elif component_type == 'house_number':
            # Numbers more important than letters
            return {str(i): 0.5 for i in range(10)}
        else:
            # Default weights
            return {}
    
    def _get_substitution_cost(self, c1: str, c2: str, component_type: str) -> float:
        """Get substitution cost between two characters."""
        # Similar looking characters have lower substitution cost
        similar_chars = {
            ('0', 'O'): 0.3,
            ('1', 'I'): 0.3,
            ('5', 'S'): 0.3,
            ('2', 'Z'): 0.3,
            ('8', 'B'): 0.3,
            ('6', 'G'): 0.3,
        }
        
        for (char1, char2), cost in similar_chars.items():
            if (c1 == char1 and c2 == char2) or (c1 == char2 and c2 == char1):
                return cost
        
        return 1.0  # Default substitution cost
    
    def _apply_component_adjustments(self, similarity: float, str1: str, str2: str, component_type: str) -> float:
        """Apply component-specific similarity adjustments."""
        if component_type == 'postal_code':
            # Postal codes should match more exactly
            if similarity < 0.8:
                similarity *= 0.5
        elif component_type == 'house_number':
            # House numbers are critical, penalize differences more
            if similarity < 0.9:
                similarity *= 0.7
        elif component_type in ['street', 'city'] and self.region == 'IN':
            # Indian street/city names can be more flexible
            if similarity > 0.6:
                similarity = min(1.0, similarity + 0.1)
        
        return similarity
    
    def _apply_region_specific_adjustments(self, similarity: float, str1: str, str2: str, component_type: str) -> float:
        """Apply region-specific similarity adjustments."""
        if self.region == 'IN':
            # Indian address specific adjustments
            if component_type == 'city':
                # Indian cities often have multiple names
                common_variations = {
                    'MUMBAI': ['BOMBAY'],
                    'BENGALURU': ['BANGALORE'],
                    'KOLKATA': ['CALCUTTA'],
                    'CHENNAI': ['MADRAS'],
                    'PUNE': ['POONA'],
                }
                
                for standard, variations in common_variations.items():
                    if (str1 == standard and str2 in variations) or \
                       (str2 == standard and str1 in variations):
                        return 1.0
            
            elif component_type == 'street':
                # Common Indian street terms
                if str1 and str2 and \
                   any(term in str1 for term in ['NAGAR', 'COLONY', 'SECTOR']) and \
                   any(term in str2 for term in ['NAGAR', 'COLONY', 'SECTOR']):
                    similarity = min(1.0, similarity + 0.1)
        
        elif self.region in ['UK', 'IE']:
            # UK/Ireland specific adjustments
            if component_type == 'street':
                # Handle UK street type variations
                uk_street_types = ['STREET', 'ROAD', 'LANE', 'AVENUE', 'CLOSE', 'CRESCENT']
                str1_has_type = any(stype in str1 for stype in uk_street_types)
                str2_has_type = any(stype in str2 for stype in uk_street_types)
                
                if str1_has_type != str2_has_type:
                    # One has street type, other doesn't - boost similarity
                    similarity = min(1.0, similarity + 0.05)
        
        elif self.region in ['DE', 'AT', 'CH']:
            # German-speaking countries
            if component_type == 'street':
                # Handle German street type variations
                german_street_types = ['STRASSE', 'WEG', 'PLATZ', 'ALLEE', 'GASSE']
                if any(stype in str1 for stype in german_street_types) and \
                   any(stype in str2 for stype in german_street_types):
                    similarity = min(1.0, similarity + 0.05)
        
        return similarity
    
    def compute_overall_similarity(self, similarities: ComponentSimilarities, region: str = None) -> float:
        """
        Compute an overall similarity score from component similarities using region-aware weights.
        
        Args:
            similarities: Component similarity scores
            region: Optional region override
            
        Returns:
            Overall similarity score between 0 and 1
        """
        # Use provided region or default to instance region
        use_region = region or self.region
        
        # Get region-specific weights
        weights = self._weights_for(use_region)
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for component, weight in weights.items():
            score = getattr(similarities, component)
            if score is not None:
                weighted_sum += score * weight
                total_weight += weight
        
        if total_weight == 0:
            return 0.0
            
        return weighted_sum / total_weight
    
    def get_similarity_details(
        self, 
        addr1: NormalizedAddress, 
        addr2: NormalizedAddress,
        region: str = None
    ) -> Tuple[ComponentSimilarities, float]:
        """
        Get detailed similarity analysis with region awareness.
        
        Args:
            addr1: First normalized address
            addr2: Second normalized address
            region: Optional region for similarity calculation
            
        Returns:
            Tuple of (component similarities, overall similarity score)
        """
        # Set region if provided
        if region:
            original_region = self.region
            self.set_region(region)
        
        try:
            component_similarities = self.compute_component_similarities(addr1, addr2)
            overall_similarity = self.compute_overall_similarity(component_similarities, region)
            
            logger.debug(f"Component similarities: {component_similarities}")
            logger.debug(f"Overall similarity: {overall_similarity}")
            
            return component_similarities, overall_similarity
        finally:
            # Restore original region if it was changed
            if region:
                self.set_region(original_region)
    
    def batch_compute_similarities(
        self, 
        address_pairs: List[Tuple[NormalizedAddress, NormalizedAddress]],
        region: str = None
    ) -> List[Tuple[ComponentSimilarities, float]]:
        """
        Compute similarities for multiple address pairs efficiently.
        
        Args:
            address_pairs: List of address pairs to compare
            region: Optional region for all comparisons
            
        Returns:
            List of (component similarities, overall similarity) tuples
        """
        results = []
        
        # Set region if provided
        if region:
            original_region = self.region
            self.set_region(region)
        
        try:
            for addr1, addr2 in address_pairs:
                similarities, overall = self.get_similarity_details(addr1, addr2)
                results.append((similarities, overall))
        finally:
            # Restore original region if it was changed
            if region:
                self.set_region(original_region)
        
        return results 