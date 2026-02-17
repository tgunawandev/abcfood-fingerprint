"""pyzk wrapper with retry, timeout, and thread safety."""
from __future__ import annotations

import base64
import logging
import threading
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from abcfood_fingerprint.zk.models import (
    DeviceConfig,
    ZKAttendance,
    ZKDeviceInfo,
    ZKFingerprint,
    ZKUser,
)

logger = logging.getLogger(__name__)

# Connection timeout in seconds
CONNECTION_TIMEOUT = 60


class ZKClient:
    """Thread-safe wrapper around pyzk for ZKTeco device communication."""

    def __init__(self, config: DeviceConfig):
        self.config = config
        self._lock = threading.Lock()
        self._conn = None

    @contextmanager
    def connect(self) -> Generator[ZKClient, None, None]:
        """Context manager for device connection with thread lock."""
        from zk import ZK

        with self._lock:
            zk = ZK(
                self.config.ip,
                port=self.config.port,
                timeout=CONNECTION_TIMEOUT,
                password=self.config.password,
                ommit_ping=False,
            )
            try:
                self._conn = zk.connect()
                logger.info(
                    "Connected to %s (%s:%d)",
                    self.config.name,
                    self.config.ip,
                    self.config.port,
                )
                yield self
            finally:
                if self._conn:
                    try:
                        self._conn.disconnect()
                    except Exception:
                        pass
                    self._conn = None
                    logger.info("Disconnected from %s", self.config.name)

    @contextmanager
    def _write_mode(self) -> Generator[None, None, None]:
        """Disable device during write operations, always re-enable."""
        if not self._conn:
            raise RuntimeError("Not connected to device")
        try:
            self._conn.disable_device()
            yield
        finally:
            try:
                self._conn.enable_device()
            except Exception as e:
                logger.error("Failed to re-enable device %s: %s", self.config.name, e)

    def _ensure_connected(self) -> None:
        if not self._conn:
            raise RuntimeError("Not connected. Use 'with client.connect() as c:'")

    # --- Read Operations ---

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_users(self) -> List[ZKUser]:
        """Get all users from the device."""
        self._ensure_connected()
        raw_users = self._conn.get_users() or []
        users = []
        for u in raw_users:
            users.append(
                ZKUser(
                    uid=u.uid,
                    user_id=str(u.user_id),
                    name=u.name or "",
                    privilege=u.privilege,
                    password=u.password or "",
                    group_id=str(u.group_id) if hasattr(u, "group_id") else "0",
                    card=u.card if hasattr(u, "card") else 0,
                )
            )
        logger.info("Got %d users from %s", len(users), self.config.name)
        return users

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_attendance(self) -> List[ZKAttendance]:
        """Get all attendance records from the device."""
        self._ensure_connected()
        raw_records = self._conn.get_attendance() or []
        records = []
        for r in raw_records:
            records.append(
                ZKAttendance(
                    uid=r.uid if hasattr(r, "uid") else 0,
                    user_id=str(r.user_id),
                    timestamp=r.timestamp,
                    status=r.status,
                    punch=r.punch if hasattr(r, "punch") else 0,
                )
            )
        logger.info("Got %d attendance records from %s", len(records), self.config.name)
        return records

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_fingerprints(self) -> List[ZKFingerprint]:
        """Get all fingerprint templates from the device."""
        self._ensure_connected()
        templates = []
        try:
            raw_templates = self._conn.get_templates() or []
            for t in raw_templates:
                if t.template:
                    templates.append(
                        ZKFingerprint(
                            uid=t.uid,
                            user_id=str(t.uid),
                            finger_index=t.fid,
                            template=base64.b64encode(t.template).decode("ascii"),
                            valid=t.valid if hasattr(t, "valid") else 1,
                        )
                    )
        except Exception as e:
            logger.warning("Failed to get templates from %s: %s", self.config.name, e)
        logger.info("Got %d fingerprint templates from %s", len(templates), self.config.name)
        return templates

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, max=10))
    def get_device_info(self) -> ZKDeviceInfo:
        """Get device information using read_sizes() for fast record counts."""
        self._ensure_connected()
        firmware = ""
        serial = ""
        platform = ""
        device_name = ""
        mac = ""
        try:
            firmware = self._conn.get_firmware_version() or ""
        except Exception:
            pass
        try:
            serial = self._conn.get_serialnumber() or ""
        except Exception:
            pass
        try:
            platform = self._conn.get_platform() or ""
        except Exception:
            pass
        try:
            device_name = self._conn.get_device_name() or ""
        except Exception:
            pass
        try:
            mac = self._conn.get_mac() or ""
        except Exception:
            pass

        # Use read_sizes() for fast record counts (~0.1s vs 138s for get_attendance)
        user_count = 0
        fp_count = 0
        attendance_count = 0
        try:
            self._conn.read_sizes()
            user_count = getattr(self._conn, "users", 0) or 0
            fp_count = getattr(self._conn, "fingers", 0) or 0
            attendance_count = getattr(self._conn, "records", 0) or 0
        except Exception:
            logger.warning("read_sizes() failed for %s, counts will be 0", self.config.name)

        device_time = None
        try:
            device_time = self._conn.get_time()
        except Exception:
            pass

        return ZKDeviceInfo(
            firmware_version=str(firmware),
            serial_number=str(serial),
            platform=str(platform),
            device_name=str(device_name),
            mac_address=str(mac),
            user_count=user_count,
            fp_count=fp_count,
            attendance_count=attendance_count,
            device_time=device_time,
        )

    def read_sizes(self) -> dict:
        """Read device record counts (fast, no data transfer)."""
        self._ensure_connected()
        self._conn.read_sizes()
        return {
            "users": getattr(self._conn, "users", 0) or 0,
            "fingers": getattr(self._conn, "fingers", 0) or 0,
            "records": getattr(self._conn, "records", 0) or 0,
            "faces": getattr(self._conn, "faces", 0) or 0,
        }

    def get_time(self) -> Optional[datetime]:
        """Get device time."""
        self._ensure_connected()
        try:
            return self._conn.get_time()
        except Exception as e:
            logger.error("Failed to get time from %s: %s", self.config.name, e)
            return None

    def ping(self) -> bool:
        """Check if device is reachable (already connected = online)."""
        return self._conn is not None

    # --- Write Operations ---

    def set_user(
        self,
        uid: int,
        name: str,
        privilege: int = 0,
        password: str = "",
        group_id: str = "0",
        user_id: str = "",
        card: int = 0,
    ) -> None:
        """Create or update a user on the device."""
        self._ensure_connected()
        with self._write_mode():
            self._conn.set_user(
                uid=uid,
                name=name,
                privilege=privilege,
                password=password,
                group_id=group_id,
                user_id=user_id,
                card=card,
            )
            logger.info("Set user uid=%d name=%s on %s", uid, name, self.config.name)

    def delete_user(self, uid: int) -> None:
        """Delete a user from the device."""
        self._ensure_connected()
        with self._write_mode():
            self._conn.delete_user(uid=uid)
            logger.info("Deleted user uid=%d from %s", uid, self.config.name)

    def set_time(self, new_time: datetime) -> None:
        """Set device time."""
        self._ensure_connected()
        with self._write_mode():
            self._conn.set_time(new_time)
            logger.info("Set time on %s to %s", self.config.name, new_time)

    def clear_attendance(self) -> None:
        """Clear all attendance records from the device."""
        self._ensure_connected()
        with self._write_mode():
            self._conn.clear_attendance()
            logger.info("Cleared attendance on %s", self.config.name)

    def restart(self) -> None:
        """Restart the device."""
        self._ensure_connected()
        self._conn.restart()
        logger.info("Restarted device %s", self.config.name)

    def set_fingerprint(self, uid: int, finger_index: int, template_b64: str) -> None:
        """Set a fingerprint template on the device."""
        self._ensure_connected()
        template_bytes = base64.b64decode(template_b64)
        with self._write_mode():
            self._conn.save_user_template(
                user=None, fingers=[{"fid": finger_index, "template": template_bytes}], uid=uid
            )
            logger.info(
                "Set fingerprint uid=%d finger=%d on %s", uid, finger_index, self.config.name
            )
