from typing import Optional, Tuple, Dict, Any
from loguru import logger
import time
import asyncio
from functools import lru_cache

from app.logging_utils import format_address_for_log
from app.geocoders import (
    GEOPY_AVAILABLE,
    GeocodeProvider,
    build_provider,
    GeocoderTimedOut,
    GeocoderServiceError,
)

try:
    from geopy.distance import geodesic
except ImportError:
    geodesic = None  # type: ignore


class GeocodingService:
    """
    Geocoding service for address validation and distance calculation.

    Providers (GEOCODING_PROVIDER):
      - nominatim: OpenStreetMap Nominatim (dev / low volume)
      - google: Google Geocoding API (requires GEOCODING_API_KEY)
      - mapbox: Mapbox Geocoding API (requires GEOCODING_API_KEY or MAPBOX_ACCESS_TOKEN)
      - none: disabled (no external calls)
    """

    def __init__(
        self,
        user_agent: str = "address-matching-service",
        timeout: int = 10,
        provider: str = "nominatim",
        enabled: bool = True,
        api_key: Optional[str] = None,
        min_request_interval: float = 1.0,
    ):
        self.user_agent = user_agent
        self.timeout = timeout
        self.provider_name = (provider or "nominatim").strip().lower()
        self.enabled = bool(enabled) and self.provider_name not in {
            "none",
            "off",
            "disabled",
        }
        self.api_key = api_key

        if self.enabled:
            self._provider: GeocodeProvider = build_provider(
                self.provider_name,
                user_agent=user_agent,
                timeout=timeout,
                api_key=api_key,
            )
        else:
            self._provider = build_provider("none")

        # Back-compat flag used by readiness / status checks
        self.geopy_available = self._provider.available

        if self.geopy_available:
            logger.debug("GeocodingService provider=%s ready", self._provider.name)
        else:
            logger.debug(
                "GeocodingService unavailable (provider=%s enabled=%s)",
                self.provider_name,
                self.enabled,
            )

        # Nominatim needs polite spacing; commercial APIs can be faster
        if self.provider_name == "nominatim":
            self.min_request_interval = max(1.0, float(min_request_interval))
        else:
            self.min_request_interval = max(0.0, float(min_request_interval))

        self.last_request_time = 0.0
        self._rate_lock: Optional[asyncio.Lock] = None

    def _get_rate_lock(self) -> asyncio.Lock:
        if self._rate_lock is None:
            self._rate_lock = asyncio.Lock()
        return self._rate_lock

    async def geocode_address(self, address: str) -> Optional[Tuple[float, float]]:
        if not self._provider.available:
            logger.debug("Geocoding provider unavailable, skipping")
            return None

        if not address or not address.strip():
            return None

        try:
            await self._rate_limit()
            coords = await self._geocode_with_cache(address.strip())
            if coords:
                logger.debug(
                    f"Geocoded '{format_address_for_log(address)}' to {coords}"
                )
                return coords
            logger.debug(
                f"Could not geocode address: {format_address_for_log(address)}"
            )
            return None
        except GeocoderTimedOut:
            logger.warning(
                f"Geocoding timeout for address: {format_address_for_log(address)}"
            )
            return None
        except GeocoderServiceError as e:
            logger.warning(
                f"Geocoding service error for address "
                f"'{format_address_for_log(address)}': {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Unexpected error geocoding address "
                f"'{format_address_for_log(address)}': {e}"
            )
            return None

    async def _rate_limit(self):
        if self.min_request_interval <= 0:
            return
        async with self._get_rate_lock():
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.min_request_interval:
                await asyncio.sleep(self.min_request_interval - elapsed)
            self.last_request_time = time.time()

    @lru_cache(maxsize=1000)
    def _geocode_cached(self, address: str) -> Optional[Tuple[float, float]]:
        return self._provider.geocode(address)

    async def _geocode_with_cache(self, address: str) -> Optional[Tuple[float, float]]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._geocode_cached, address)

    def calculate_distance(
        self,
        coords1: Tuple[float, float],
        coords2: Tuple[float, float],
    ) -> float:
        if geodesic is None:
            logger.debug("geopy distance unavailable")
            return float("inf")
        try:
            distance = geodesic(coords1, coords2).meters
            logger.debug(
                f"Distance between {coords1} and {coords2}: {distance:.2f} meters"
            )
            return distance
        except Exception as e:
            logger.error(f"Error calculating distance: {e}")
            return float("inf")

    async def get_distance_between_addresses(
        self,
        address1: str,
        address2: str,
    ) -> Optional[float]:
        logger.debug(
            "Getting distance between "
            f"'{format_address_for_log(address1)}' and "
            f"'{format_address_for_log(address2)}'"
        )
        coords1 = await self.geocode_address(address1)
        coords2 = await self.geocode_address(address2)
        if coords1 is None or coords2 is None:
            return None
        return self.calculate_distance(coords1, coords2)

    def is_within_threshold(
        self,
        distance_meters: Optional[float],
        threshold: float = 50.0,
    ) -> bool:
        if distance_meters is None:
            return True
        return distance_meters <= threshold

    async def validate_addresses_geospatially(
        self,
        address1: str,
        address2: str,
        distance_threshold: float = 50.0,
    ) -> Dict[str, Any]:
        result = {
            "distance_meters": None,
            "within_threshold": True,
            "coords1": None,
            "coords2": None,
            "geocoding_successful": False,
            "provider": self._provider.name,
        }

        if not self._provider.available:
            logger.debug("Geocoding unavailable, skipping geospatial validation")
            return result

        try:
            coords1 = await self.geocode_address(address1)
            coords2 = await self.geocode_address(address2)
            result["coords1"] = coords1
            result["coords2"] = coords2

            if coords1 and coords2:
                result["geocoding_successful"] = True
                distance = self.calculate_distance(coords1, coords2)
                result["distance_meters"] = distance
                result["within_threshold"] = self.is_within_threshold(
                    distance, distance_threshold
                )
                logger.info(
                    f"Geospatial validation: distance={distance:.2f}m, "
                    f"within_threshold={result['within_threshold']}, "
                    f"provider={self._provider.name}"
                )
            else:
                logger.debug("Geocoding failed for one or both addresses")
        except Exception as e:
            logger.error(f"Error in geospatial validation: {e}")

        return result

    def clear_cache(self):
        if hasattr(self, "_geocode_cached"):
            self._geocode_cached.cache_clear()
            logger.info("Geocoding cache cleared")
