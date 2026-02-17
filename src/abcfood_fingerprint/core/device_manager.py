"""Device registry and health checks."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from abcfood_fingerprint.zk.models import DeviceConfig, DeviceStatus, ZKDeviceInfo
from abcfood_fingerprint.zk.pool import DevicePool, get_pool

logger = logging.getLogger(__name__)


def list_devices(pool: Optional[DevicePool] = None) -> Dict[str, DeviceConfig]:
    """List all configured devices."""
    p = pool or get_pool()
    return p.list_devices()


def get_device_status(device_key: str, pool: Optional[DevicePool] = None) -> DeviceStatus:
    """Get device status including connectivity and info."""
    p = pool or get_pool()
    config = p.get_config(device_key)
    status = DeviceStatus(key=device_key, config=config, last_check=datetime.now())

    client = p.get_client(device_key)
    try:
        with client.connect() as c:
            status.online = True
            status.info = c.get_device_info()
    except Exception as e:
        status.online = False
        status.error = str(e)
        logger.warning("Device %s offline: %s", device_key, e)

    return status


def get_all_device_statuses(pool: Optional[DevicePool] = None) -> List[DeviceStatus]:
    """Get status for all configured devices."""
    p = pool or get_pool()
    statuses = []
    for key in p.device_keys():
        statuses.append(get_device_status(key, p))
    return statuses


def ping_device(device_key: str, pool: Optional[DevicePool] = None) -> bool:
    """Ping a device to check connectivity."""
    p = pool or get_pool()
    client = p.get_client(device_key)
    try:
        with client.connect():
            return True
    except Exception:
        return False


def get_device_time(device_key: str, pool: Optional[DevicePool] = None) -> Optional[datetime]:
    """Get current time from a device."""
    p = pool or get_pool()
    client = p.get_client(device_key)
    with client.connect() as c:
        return c.get_time()


def sync_device_time(device_key: str, pool: Optional[DevicePool] = None) -> None:
    """Sync device time to current system time."""
    p = pool or get_pool()
    client = p.get_client(device_key)
    with client.connect() as c:
        c.set_time(datetime.now())
    logger.info("Synced time on device %s", device_key)


def restart_device(device_key: str, pool: Optional[DevicePool] = None) -> None:
    """Restart a device."""
    p = pool or get_pool()
    client = p.get_client(device_key)
    with client.connect() as c:
        c.restart()
    logger.info("Restarted device %s", device_key)
