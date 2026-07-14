"""Pluggable geocoding providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Tuple

from loguru import logger

try:
    from geopy.geocoders import Nominatim, GoogleV3, MapBox
    from geopy.exc import GeocoderTimedOut, GeocoderServiceError
    GEOPY_AVAILABLE = True
except ImportError:
    Nominatim = GoogleV3 = MapBox = None  # type: ignore

    class GeocoderTimedOut(Exception):
        pass

    class GeocoderServiceError(Exception):
        pass

    GEOPY_AVAILABLE = False


class GeocodeProvider(ABC):
    """Interface for address → (lat, lon) providers."""

    name: str = "base"

    @property
    @abstractmethod
    def available(self) -> bool:
        ...

    @abstractmethod
    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        """Synchronous geocode. Return (lat, lon) or None."""


class NoneProvider(GeocodeProvider):
    name = "none"

    @property
    def available(self) -> bool:
        return False

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        return None


class NominatimProvider(GeocodeProvider):
    name = "nominatim"

    def __init__(self, user_agent: str = "address-matching-service", timeout: int = 10):
        self._geolocator = None
        if GEOPY_AVAILABLE and Nominatim is not None:
            self._geolocator = Nominatim(user_agent=user_agent, timeout=timeout)

    @property
    def available(self) -> bool:
        return self._geolocator is not None

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        if not self._geolocator:
            return None
        location = self._geolocator.geocode(address)
        if location and location.latitude is not None and location.longitude is not None:
            return float(location.latitude), float(location.longitude)
        return None


class GoogleProvider(GeocodeProvider):
    name = "google"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self._geolocator = None
        if GEOPY_AVAILABLE and GoogleV3 is not None and api_key:
            self._geolocator = GoogleV3(api_key=api_key, timeout=timeout)
        elif not api_key:
            logger.warning("GEOCODING_API_KEY required for google provider")

    @property
    def available(self) -> bool:
        return self._geolocator is not None

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        if not self._geolocator:
            return None
        location = self._geolocator.geocode(address)
        if location and location.latitude is not None and location.longitude is not None:
            return float(location.latitude), float(location.longitude)
        return None


class MapboxProvider(GeocodeProvider):
    name = "mapbox"

    def __init__(self, api_key: Optional[str] = None, timeout: int = 10):
        self._geolocator = None
        if GEOPY_AVAILABLE and MapBox is not None and api_key:
            self._geolocator = MapBox(api_key=api_key, timeout=timeout)
        elif not api_key:
            logger.warning("GEOCODING_API_KEY / MAPBOX_ACCESS_TOKEN required for mapbox")

    @property
    def available(self) -> bool:
        return self._geolocator is not None

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        if not self._geolocator:
            return None
        location = self._geolocator.geocode(address)
        if location and location.latitude is not None and location.longitude is not None:
            return float(location.latitude), float(location.longitude)
        return None


def build_provider(
    provider: str,
    *,
    user_agent: str = "address-matching-service",
    timeout: int = 10,
    api_key: Optional[str] = None,
) -> GeocodeProvider:
    name = (provider or "nominatim").strip().lower()
    if name in {"none", "off", "disabled"}:
        return NoneProvider()
    if name == "google":
        return GoogleProvider(api_key=api_key, timeout=timeout)
    if name == "mapbox":
        return MapboxProvider(api_key=api_key, timeout=timeout)
    if name == "nominatim":
        return NominatimProvider(user_agent=user_agent, timeout=timeout)
    logger.warning(
        "Unknown geocoding provider %r; falling back to none. "
        "Supported: nominatim, google, mapbox, none",
        name,
    )
    return NoneProvider()
