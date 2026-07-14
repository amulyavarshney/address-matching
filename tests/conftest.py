"""Shared pytest fixtures for deterministic library tests."""

import pytest

from app.matcher import AddressMatcher


@pytest.fixture
def matcher_config():
    return {
        "use_ml_model": False,
        "use_geospatial": False,
        "ml_auto_train": False,
        "default_region": "US",
        "auto_detect_region": True,
    }


@pytest.fixture
def matcher(matcher_config):
    return AddressMatcher(matcher_config)
