"""Device pool - loads device configs and manages ZKClient instances."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from abcfood_fingerprint.config import get_settings
from abcfood_fingerprint.zk.client import ZKClient
from abcfood_fingerprint.zk.models import DeviceConfig

logger = logging.getLogger(__name__)


class DevicePool:
    """Registry of ZKTeco devices with lazy client creation."""

    def __init__(self, config_path: Optional[str] = None):
        self._devices: Dict[str, DeviceConfig] = {}
        self._clients: Dict[str, ZKClient] = {}
        path = config_path or get_settings().ZK_MACHINES_CONFIG
        self._load_config(path)

    def _load_config(self, config_path: str) -> None:
        """Load device configurations from YAML file."""
        p = Path(config_path)
        if not p.is_file():
            logger.warning("Machines config not found: %s", config_path)
            return

        with open(p) as f:
            data = yaml.safe_load(f)

        devices = data.get("devices", {})
        for key, cfg in devices.items():
            self._devices[key] = DeviceConfig(
                name=cfg.get("name", key),
                ip=cfg["ip"],
                port=cfg.get("port", 4370),
                password=cfg.get("password", 0),
                model=cfg.get("model", ""),
                serial=cfg.get("serial", ""),
            )
        logger.info("Loaded %d devices from %s", len(self._devices), config_path)

    def get_client(self, device_key: str) -> ZKClient:
        """Get or create a ZKClient for the given device key."""
        if device_key not in self._devices:
            raise KeyError(f"Unknown device: {device_key}. Available: {list(self._devices.keys())}")

        if device_key not in self._clients:
            self._clients[device_key] = ZKClient(self._devices[device_key])

        return self._clients[device_key]

    def get_config(self, device_key: str) -> DeviceConfig:
        """Get device config by key."""
        if device_key not in self._devices:
            raise KeyError(f"Unknown device: {device_key}. Available: {list(self._devices.keys())}")
        return self._devices[device_key]

    def list_devices(self) -> Dict[str, DeviceConfig]:
        """Return all registered devices."""
        return dict(self._devices)

    def device_keys(self) -> List[str]:
        """Return all device keys."""
        return list(self._devices.keys())


# Lazy-loaded singleton
_pool: Optional[DevicePool] = None


def get_pool() -> DevicePool:
    """Get the global device pool (lazy loaded)."""
    global _pool
    if _pool is None:
        _pool = DevicePool()
    return _pool
