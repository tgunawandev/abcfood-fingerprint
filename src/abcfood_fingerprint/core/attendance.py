"""Attendance record operations."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Dict, List, Optional

from abcfood_fingerprint.zk.models import ZKAttendance
from abcfood_fingerprint.zk.pool import DevicePool, get_pool

logger = logging.getLogger(__name__)


def get_attendance(
    device_key: str,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    pool: Optional[DevicePool] = None,
    use_cache: bool = True,
) -> List[ZKAttendance]:
    """Get attendance records from a device with optional date filtering.

    Tries the in-memory cache first (instant). Falls back to device fetch
    on cache miss or when ``use_cache=False``.
    """
    if use_cache:
        from abcfood_fingerprint.core.cache import get_cache

        cached = get_cache().get(device_key, date_from, date_to)
        if cached is not None:
            logger.info(
                "Cache hit for %s: %d records (from=%s to=%s)",
                device_key,
                len(cached),
                date_from,
                date_to,
            )
            return cached

    # Cache miss — fetch from device (slow)
    p = pool or get_pool()
    client = p.get_client(device_key)

    with client.connect() as c:
        records = c.get_attendance()

    if date_from:
        records = [r for r in records if r.timestamp >= date_from]
    if date_to:
        records = [r for r in records if r.timestamp <= date_to]

    records.sort(key=lambda r: r.timestamp)
    logger.info(
        "Got %d attendance records from %s (filtered from=%s to=%s)",
        len(records),
        device_key,
        date_from,
        date_to,
    )
    return records


def count_attendance(
    device_key: str,
    pool: Optional[DevicePool] = None,
) -> int:
    """Count attendance records on a device (fast, uses read_sizes)."""
    p = pool or get_pool()
    client = p.get_client(device_key)
    with client.connect() as c:
        sizes = c.read_sizes()
    return sizes["records"]


def format_for_odoo(
    records: List[ZKAttendance],
    device_key: str,
    device_name: str,
) -> List[Dict[str, str]]:
    """Format attendance records for Odoo hr.fingerprint.log import.

    Maps to fields: machine_code, machine_name, device_id, date, time,
    attendance_type, punch_type.
    """
    formatted = []
    punch_types = {0: "Check-In", 1: "Check-Out", 2: "Break-Out", 3: "Break-In", 4: "OT-In", 5: "OT-Out"}

    for r in records:
        formatted.append(
            {
                "machine_code": device_key,
                "machine_name": device_name,
                "device_id": r.user_id,
                "date": r.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "time": r.timestamp.strftime("%H:%M:%S"),
                "attendance_type": "regular",
                "punch_type": punch_types.get(r.status, str(r.status)),
            }
        )
    return formatted


def clear_attendance(
    device_key: str,
    pool: Optional[DevicePool] = None,
) -> None:
    """Clear all attendance records from a device."""
    p = pool or get_pool()
    client = p.get_client(device_key)
    with client.connect() as c:
        c.clear_attendance()
    logger.info("Cleared attendance on device %s", device_key)
