"""Tests for configuration module."""
from __future__ import annotations

from abcfood_fingerprint.config import Settings, get_settings


def test_settings_defaults():
    """Test that settings load with defaults."""
    settings = get_settings()
    assert settings.API_PORT == 8000
    assert settings.API_KEY == "test-api-key"
    assert settings.ENVIRONMENT == "test"
    assert settings.BACKUP_RETENTION_DAYS == 90


def test_cors_origins():
    """Test CORS origin parsing."""
    settings = get_settings()
    origins = settings.cors_origins
    assert isinstance(origins, list)
    assert len(origins) >= 1


def test_settings_singleton():
    """Test that get_settings returns the same instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2
