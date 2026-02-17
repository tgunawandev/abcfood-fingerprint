"""Tests for ZK client (mocked - no real device needed)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from abcfood_fingerprint.zk.client import ZKClient
from abcfood_fingerprint.zk.models import DeviceConfig


@pytest.fixture
def device_config():
    return DeviceConfig(
        name="TestDevice",
        ip="192.168.1.100",
        port=4370,
        password=0,
        model="X100-C",
        serial="12345",
    )


@pytest.fixture
def zk_client(device_config):
    return ZKClient(device_config)


def test_client_creation(zk_client, device_config):
    """Test ZKClient initialization."""
    assert zk_client.config == device_config
    assert zk_client._conn is None


def test_ensure_connected_raises(zk_client):
    """Test that operations fail when not connected."""
    with pytest.raises(RuntimeError, match="Not connected"):
        zk_client._ensure_connected()


@patch("abcfood_fingerprint.zk.client.ZK")
def test_connect_context_manager(mock_zk_class, zk_client):
    """Test connection context manager."""
    mock_instance = MagicMock()
    mock_conn = MagicMock()
    mock_zk_class.return_value = mock_instance
    mock_instance.connect.return_value = mock_conn

    with zk_client.connect() as client:
        assert client._conn is mock_conn

    mock_conn.disconnect.assert_called_once()
    assert zk_client._conn is None


@patch("abcfood_fingerprint.zk.client.ZK")
def test_get_users(mock_zk_class, zk_client):
    """Test get_users with mock connection."""
    mock_instance = MagicMock()
    mock_conn = MagicMock()
    mock_zk_class.return_value = mock_instance
    mock_instance.connect.return_value = mock_conn

    # Create mock user objects
    mock_user = MagicMock()
    mock_user.uid = 1
    mock_user.user_id = "123"
    mock_user.name = "Test User"
    mock_user.privilege = 0
    mock_user.password = ""
    mock_user.group_id = "0"
    mock_user.card = 0
    mock_conn.get_users.return_value = [mock_user]

    with zk_client.connect() as client:
        users = client.get_users()

    assert len(users) == 1
    assert users[0].user_id == "123"
    assert users[0].name == "Test User"


def test_device_config_model():
    """Test DeviceConfig pydantic model."""
    config = DeviceConfig(name="Test", ip="10.0.0.1")
    assert config.port == 4370
    assert config.password == 0
    assert config.model == ""
