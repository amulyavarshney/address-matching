import os
from typing import Optional, Tuple, Dict, Any
from loguru import logger
import time
import asyncio
from functools import lru_cache

try:
    from geopy.geocoders import Nominatim
    from geopy.distance import geodesic
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    GEOPY_AVAILABLE = True
    logger.info("Geopy library is available")
except ImportError:
    GEOPY_AVAILABLE = False
    logger.warning("Geopy library not available, geospatial validation disabled")


class GeocodingService:
    """
    Geocoding service for address validation and distance calculation.
    """
    
    def __init__(self, user_agent: str = "address-matching-service", timeout: int = 10):
        """
        Initialize geocoding service.
        
        Args:
            user_agent: User agent string for geocoding requests
            timeout: Timeout for geocoding requests in seconds
        """
        self.user_agent = user_agent
        self.timeout = timeout
        self.geopy_available = GEOPY_AVAILABLE
        
        if self.geopy_available:
            self.geolocator = Nominatim(user_agent=user_agent, timeout=timeout)
        else:
            self.geolocator = None
            
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 second between requests to be respectful
        
        logger.info(f"GeocodingService initialized with user_agent: {user_agent}")
    
    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        """
        Geocode an address to get latitude and longitude.
        
        Args:
            address: Address string to geocode
            
        Returns:
            Tuple of (latitude, longitude) or None if geocoding fails
        """
        if not self.geopy_available:
            logger.debug("Geopy not available, skipping geocoding")
            return None
            
        if not address or not address.strip():
            return None
        
        try:
            # Rate limiting
            await self._rate_limit()
            
            # Use cached geocoding if available
            result = await self._geocode_with_cache(address.strip())
            
            if result and result.latitude and result.longitude:
                coords = (float(result.latitude), float(result.longitude))
                logger.debug(f"Geocoded '{address}' to {coords}")
                return coords
            else:
                logger.debug(f"Could not geocode address: {address}")
                return None
                
        except GeocoderTimedOut:
            logger.warning(f"Geocoding timeout for address: {address}")
            return None
        except GeocoderServiceError as e:
            logger.warning(f"Geocoding service error for address '{address}': {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error geocoding address '{address}': {e}")
            return None
    
    async def _rate_limit(self):
        """Implement rate limiting for geocoding requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last_request
            await asyncio.sleep(wait_time)
        
        self.last_request_time = time.time()
    
    @lru_cache(maxsize=1000)
    def _geocode_cached(self, address: str):
        """Cached geocoding to avoid repeated requests for same addresses."""
        if self.geolocator is not None:
            return self.geolocator.geocode(address)
        return None
    
    async def _geocode_with_cache(self, address: str):
        """Async wrapper for cached geocoding."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._geocode_cached, address)
    
    def calculate_distance(
        self, 
        coords1: Tuple[float, float], 
        coords2: Tuple[float, float]
    ) -> float:
        """
        Calculate distance between two coordinate pairs.
        
        Args:
            coords1: First coordinate pair (lat, lon)
            coords2: Second coordinate pair (lat, lon)
            
        Returns:
            Distance in meters
        """
        if not self.geopy_available:
            logger.debug("Geopy not available, cannot calculate distance")
            return float('inf')
        
        try:
            distance = geodesic(coords1, coords2).meters
            logger.debug(f"Distance between {coords1} and {coords2}: {distance:.2f} meters")
            return distance
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return float('inf')
    
    async def get_distance_between_addresses(
        self, 
        address1: str, 
        address2: str
    ) -> Optional[float]:
        """
        Get distance between two addresses in meters.
        
        Args:
            address1: First address
            address2: Second address
            
        Returns:
            Distance in meters or None if geocoding fails
        """
        logger.debug(f"Getting distance between '{address1}' and '{address2}'")
        
        # Geocode both addresses
        coords1 = await self.geocode_address(address1)
        coords2 = await self.geocode_address(address2)
        
        if coords1 is None or coords2 is None:
            logger.debug("Could not geocode one or both addresses")
            return None
        
        return self.calculate_distance(coords1, coords2)
    
    def is_within_threshold(self, distance_meters: Optional[float], threshold: float = 50.0) -> bool:
        """
        Check if distance is within acceptable threshold.
        
        Args:
            distance_meters: Distance in meters
            threshold: Maximum acceptable distance in meters
            
        Returns:
            True if within threshold or distance is None
        """
        if distance_meters is None:
            # If we can't calculate distance, don't penalize
            return True
        
        return distance_meters <= threshold
    
    async def validate_addresses_geospatially(
        self, 
        address1: str, 
        address2: str,
        distance_threshold: float = 50.0
    ) -> Dict[str, Any]:
        """
        Perform geospatial validation of two addresses.
        
        Args:
            address1: First address
            address2: Second address
            distance_threshold: Maximum acceptable distance in meters
            
        Returns:
            Dictionary with validation results
        """
        result = {
            'distance_meters': None,
            'within_threshold': True,
            'coords1': None,
            'coords2': None,
            'geocoding_successful': False
        }
        
        if not self.geopy_available:
            logger.debug("Geopy not available, skipping geospatial validation")
            return result
        
        try:
            # Get coordinates for both addresses
            coords1 = await self.geocode_address(address1)
            coords2 = await self.geocode_address(address2)
            
            result['coords1'] = coords1
            result['coords2'] = coords2
            
            if coords1 and coords2:
                result['geocoding_successful'] = True
                distance = self.calculate_distance(coords1, coords2)
                result['distance_meters'] = distance
                result['within_threshold'] = self.is_within_threshold(distance, distance_threshold)
                
                logger.info(f"Geospatial validation: distance={distance:.2f}m, within_threshold={result['within_threshold']}")
            else:
                logger.debug("Geocoding failed for one or both addresses")
                
        except Exception as e:
            logger.error(f"Error in geospatial validation: {e}")
        
        return result
    
    def clear_cache(self):
        """Clear the geocoding cache."""
        if hasattr(self, '_geocode_cached'):
            self._geocode_cached.cache_clear()
            logger.info("Geocoding cache cleared") 