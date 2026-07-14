"""Pluggable geocoding providers."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional, Tuple

from loguru import logger

try:
    from geopy.geocoders import Nominatim, GoogleV3, MapBox
    from geopy.exc import (
        GeocoderTimedOut,
        GeocoderServiceError,
        GeocoderQueryError,
        GeocoderAuthenticationFailure,
        GeocoderInsufficientPrivileges,
        GeocoderQuotaExceeded,
    )

    GEOPY_AVAILABLE = True
except ImportError:
    Nominatim = GoogleV3 = MapBox = None  # type: ignore

    class GeocoderTimedOut(Exception):
        pass

    class GeocoderServiceError(Exception):
        pass

    class GeocoderQueryError(Exception):
        pass

    class GeocoderAuthenticationFailure(Exception):
        pass

    class GeocoderInsufficientPrivileges(Exception):
        pass

    class GeocoderQuotaExceeded(Exception):
        pass

    GEOPY_AVAILABLE = False


def resolve_geocoding_api_key(
    provider: str,
    explicit: Optional[str] = None,
) -> Optional[str]:
    """
    Resolve API key for a provider.

    Precedence:
      - explicit argument
      - provider-specific env (GOOGLE_MAPS_API_KEY / MAPBOX_ACCESS_TOKEN)
      - GEOCODING_API_KEY fallback
    """
    if explicit and str(explicit).strip():
        return str(explicit).strip()

    name = (provider or "").strip().lower()
    if name == "google":
        return (
            os.getenv("GOOGLE_MAPS_API_KEY")
            or os.getenv("GOOGLE_GEOCODING_API_KEY")
            or os.getenv("GEOCODING_API_KEY")
        )
    if name == "mapbox":
        return os.getenv("MAPBOX_ACCESS_TOKEN") or os.getenv("GEOCODING_API_KEY")
    return os.getenv("GEOCODING_API_KEY")


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
        location = self._geolocator.geocode(address, exactly_one=True)
        if location and location.latitude is not None and location.longitude is not None:
            return float(location.latitude), float(location.longitude)
        return None


class GoogleProvider(GeocodeProvider):
    name = "google"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 10,
        region: Optional[str] = None,
        language: Optional[str] = None,
    ):
        self._geolocator = None
        self._region = (region or "").strip().lower() or None
        self._language = (language or "").strip() or None
        key = resolve_geocoding_api_key("google", api_key)
        if GEOPY_AVAILABLE and GoogleV3 is not None and key:
            self._geolocator = GoogleV3(api_key=key, timeout=timeout)
        elif not key:
            logger.warning(
                "Google geocoding unavailable: set GOOGLE_MAPS_API_KEY "
                "(or GEOCODING_API_KEY)"
            )

    @property
    def available(self) -> bool:
        return self._geolocator is not None

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        if not self._geolocator:
            return None
        kwargs = {"exactly_one": True}
        if self._region:
            kwargs["region"] = self._region
        if self._language:
            kwargs["language"] = self._language
        try:
            location = self._geolocator.geocode(address, **kwargs)
        except (
            GeocoderAuthenticationFailure,
            GeocoderInsufficientPrivileges,
            GeocoderQuotaExceeded,
        ) as exc:
            logger.error("Google geocoding auth/quota error: %s", exc)
            raise
        except GeocoderQueryError as exc:
            logger.warning("Google geocoding query error: %s", exc)
            return None
        if location and location.latitude is not None and location.longitude is not None:
            return float(location.latitude), float(location.longitude)
        return None


class MapboxProvider(GeocodeProvider):
    name = "mapbox"

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = 10,
        country: Optional[str] = None,
    ):
        self._geolocator = None
        self._country = (country or "").strip().upper() or None
        key = resolve_geocoding_api_key("mapbox", api_key)
        if GEOPY_AVAILABLE and MapBox is not None and key:
            self._geolocator = MapBox(api_key=key, timeout=timeout)
        elif not key:
            logger.warning(
                "Mapbox geocoding unavailable: set MAPBOX_ACCESS_TOKEN "
                "(or GEOCODING_API_KEY)"
            )

    @property
    def available(self) -> bool:
        return self._geolocator is not None

    def geocode(self, address: str) -> Optional[Tuple[float, float]]:
        if not self._geolocator:
            return None
        kwargs = {"exactly_one": True}
        if self._country:
            kwargs["country"] = self._country
        try:
            location = self._geolocator.geocode(address, **kwargs)
        except (
            GeocoderAuthenticationFailure,
            GeocoderInsufficientPrivileges,
            GeocoderQuotaExceeded,
        ) as exc:
            logger.error("Mapbox geocoding auth/quota error: %s", exc)
            raise
        except GeocoderQueryError as exc:
            logger.warning("Mapbox geocoding query error: %s", exc)
            return None
        if location and location.latitude is not None and location.longitude is not None:
            return float(location.latitude), float(location.longitude)
        return None


def build_provider(
    provider: str,
    *,
    user_agent: str = "address-matching-service",
    timeout: int = 10,
    api_key: Optional[str] = None,
    region: Optional[str] = None,
    language: Optional[str] = None,
    country: Optional[str] = None,
) -> GeocodeProvider:
    name = (provider or "nominatim").strip().lower()
    if name in {"none", "off", "disabled"}:
        return NoneProvider()
    if name == "google":
        return GoogleProvider(
            api_key=api_key,
            timeout=timeout,
            region=region,
            language=language,
        )
    if name == "mapbox":
        return MapboxProvider(
            api_key=api_key,
            timeout=timeout,
            country=country,
        )
    if name == "nominatim":
        return NominatimProvider(user_agent=user_agent, timeout=timeout)
    logger.warning(
        "Unknown geocoding provider %r; falling back to none. "
        "Supported: nominatim, google, mapbox, none",
        name,
    )
    return NoneProvider()
