"""Fingerprint template operations."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from abcfood_fingerprint.zk.models import ZKFingerprint
from abcfood_fingerprint.zk.pool import DevicePool, get_pool

logger = logging.getLogger(__name__)


def get_fingerprints(
    device_key: str,
    user_id: Optional[str] = None,
    pool: Optional[DevicePool] = None,
) -> List[ZKFingerprint]:
    """Get fingerprint templates from a device, optionally filtered by user."""
    p = pool or get_pool()
    client = p.get_client(device_key)

    with client.connect() as c:
        templates = c.get_fingerprints()

    if user_id:
        templates = [t for t in templates if t.user_id == user_id]

    logger.info("Got %d fingerprints from %s (user=%s)", len(templates), device_key, user_id)
    return templates


def count_fingerprints(
    device_key: str,
    pool: Optional[DevicePool] = None,
) -> int:
    """Count fingerprint templates on a device."""
    p = pool or get_pool()
    client = p.get_client(device_key)
    with client.connect() as c:
        templates = c.get_fingerprints()
    return len(templates)


def get_fingerprint_summary(
    device_key: str,
    pool: Optional[DevicePool] = None,
) -> Dict[str, int]:
    """Get fingerprint count per user on a device."""
    templates = get_fingerprints(device_key, pool=pool)
    summary: Dict[str, int] = {}
    for t in templates:
        summary[t.user_id] = summary.get(t.user_id, 0) + 1
    return summary
