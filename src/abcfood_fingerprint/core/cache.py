"""Thread-safe in-memory attendance cache per device."""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from abcfood_fingerprint.zk.models import ZKAttendance
from abcfood_fingerprint.zk.pool import DevicePool, get_pool

logger = logging.getLogger(__name__)


class _DeviceCacheEntry:
    """Cache data for a single device."""

    __slots__ = ("records", "fetched_at", "count", "is_loading", "error")

    def __init__(self) -> None:
        self.records: List[ZKAttendance] = []
        self.fetched_at: Optional[datetime] = None
        self.count: int = 0
        self.is_loading: bool = False
        self.error: Optional[str] = None


class AttendanceCache:
    """Thread-safe in-memory attendance cache.

    Stores all attendance records per device.  ``refresh()`` fetches from the
    ZK device (slow, ~138s) and replaces the in-memory copy.  ``get()``
    returns filtered records instantly from memory.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, _DeviceCacheEntry] = {}

    # -- write --

    def refresh(self, device_key: str, pool: Optional[DevicePool] = None) -> int:
        """Fetch all attendance records from the device and store in cache.

        Returns the number of records fetched.
        """
        # Mark loading (quick lock)
        with self._lock:
            entry = self._data.setdefault(device_key, _DeviceCacheEntry())
            entry.is_loading = True
            entry.error = None

        # Fetch outside lock (slow I/O)
        try:
            p = pool or get_pool()
            client = p.get_client(device_key)
            with client.connect() as c:
                records = c.get_attendance()

            # Store result (quick lock)
            with self._lock:
                entry.records = records
                entry.fetched_at = datetime.now()
                entry.count = len(records)
                entry.is_loading = False

            logger.info(
                "Cache refreshed for %s: %d records", device_key, len(records)
            )
            return len(records)

        except Exception as exc:
            with self._lock:
                entry.is_loading = False
                entry.error = str(exc)
            logger.error("Cache refresh failed for %s: %s", device_key, exc)
            raise

    # -- read --

    def get(
        self,
        device_key: str,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> Optional[List[ZKAttendance]]:
        """Return filtered records from cache, or ``None`` on cache miss."""
        with self._lock:
            entry = self._data.get(device_key)
            if entry is None or entry.fetched_at is None:
                return None
            # Copy reference (list is replaced atomically on refresh)
            records = entry.records

        # Filter outside lock
        result = records
        if date_from:
            result = [r for r in result if r.timestamp >= date_from]
        if date_to:
            result = [r for r in result if r.timestamp <= date_to]

        result.sort(key=lambda r: r.timestamp)
        return result

    def get_count(self, device_key: str) -> Optional[int]:
        """Return cached record count, or ``None`` on cache miss."""
        with self._lock:
            entry = self._data.get(device_key)
            if entry is None or entry.fetched_at is None:
                return None
            return entry.count

    def get_records_raw(self, device_key: str) -> Optional[List[ZKAttendance]]:
        """Return unfiltered copy of cached records for backup use."""
        with self._lock:
            entry = self._data.get(device_key)
            if entry is None or entry.fetched_at is None:
                return None
            return list(entry.records)

    def get_status(self, device_key: str) -> Dict[str, Any]:
        """Return cache metadata for a device."""
        with self._lock:
            entry = self._data.get(device_key)
            if entry is None:
                return {
                    "device": device_key,
                    "cached": False,
                    "fetched_at": None,
                    "count": 0,
                    "is_loading": False,
                    "error": None,
                }
            return {
                "device": device_key,
                "cached": entry.fetched_at is not None,
                "fetched_at": entry.fetched_at.isoformat() if entry.fetched_at else None,
                "count": entry.count,
                "is_loading": entry.is_loading,
                "error": entry.error,
            }

    def all_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Return cache status for all known devices."""
        with self._lock:
            keys = list(self._data.keys())
        return {k: self.get_status(k) for k in keys}


# Module-level singleton
_cache: Optional[AttendanceCache] = None


def get_cache() -> AttendanceCache:
    """Get the global attendance cache (lazy loaded)."""
    global _cache
    if _cache is None:
        _cache = AttendanceCache()
    return _cache
