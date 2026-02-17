"""Shared test fixtures."""
from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch):
    """Set default env vars for tests."""
    defaults = {
        "ZK_MACHINES_CONFIG": "config/machines.yml",
        "API_KEY": "test-api-key",
        "S3_ACCESS_KEY": "test",
        "S3_SECRET_KEY": "test",
        "S3_BUCKET": "test-bucket",
        "S3_ENDPOINT": "https://test.endpoint.com",
        "S3_REGION": "us-east-1",
        "ODOO_HOST": "localhost",
        "ODOO_PORT": "8069",
        "ODOO_PROTOCOL": "jsonrpc",
        "ODOO_DB": "test",
        "ODOO_USER": "admin",
        "ODOO_PASSWORD": "admin",
        "ENVIRONMENT": "test",
    }
    for k, v in defaults.items():
        monkeypatch.setenv(k, v)

    # Reset singleton
    import abcfood_fingerprint.config as cfg

    cfg._settings = None
    yield
    cfg._settings = None


@pytest.fixture
def mock_zk_conn():
    """Create a mock ZK connection."""
    conn = MagicMock()
    conn.get_users.return_value = []
    conn.get_attendance.return_value = []
    conn.get_templates.return_value = []
    conn.get_firmware_version.return_value = "Ver 6.60"
    conn.get_serialnumber.return_value = "97622"
    conn.get_platform.return_value = "ZMM220_TFT"
    conn.get_device_name.return_value = "X100-C"
    conn.get_mac.return_value = "00:17:61:XX:XX:XX"
    conn.get_time.return_value = None
    return conn
