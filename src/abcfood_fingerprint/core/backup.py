"""Backup and restore operations for device data."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from abcfood_fingerprint.storage.s3 import S3Client
from abcfood_fingerprint.zk.models import BackupRecord, ZKAttendance, ZKFingerprint, ZKUser
from abcfood_fingerprint.zk.pool import DevicePool, get_pool

logger = logging.getLogger(__name__)


def run_backup(
    device_key: str,
    pool: Optional[DevicePool] = None,
    include_attendance: bool = False,
) -> Dict[str, Any]:
    """Full backup of users + fingerprints (+ attendance) from a device to S3.

    When *include_attendance* is True, attendance records are included.
    The cache is tried first for attendance data; falls back to device fetch.

    Returns backup metadata.
    """
    p = pool or get_pool()
    config = p.get_config(device_key)
    client = p.get_client(device_key)

    with client.connect() as c:
        users = c.get_users()
        fingerprints = c.get_fingerprints()

    attendance: List[ZKAttendance] = []
    if include_attendance:
        attendance = _get_attendance_for_backup(device_key, p)

    record = BackupRecord(
        device_key=device_key,
        device_name=config.name,
        timestamp=datetime.now().isoformat(),
        users=users,
        fingerprints=fingerprints,
        attendance=attendance,
        user_count=len(users),
        fingerprint_count=len(fingerprints),
        attendance_count=len(attendance),
    )

    s3 = S3Client()
    s3_key = s3.upload_backup(device_key, record.model_dump())

    result = {
        "device": device_key,
        "device_name": config.name,
        "s3_key": s3_key,
        "user_count": len(users),
        "fingerprint_count": len(fingerprints),
        "attendance_count": len(attendance),
        "timestamp": record.timestamp,
    }
    logger.info(
        "Backup complete for %s: %d users, %d fingerprints, %d attendance -> %s",
        device_key,
        len(users),
        len(fingerprints),
        len(attendance),
        s3_key,
    )
    return result


def _get_attendance_for_backup(
    device_key: str,
    pool: DevicePool,
) -> List[ZKAttendance]:
    """Try cache first for attendance, fall back to device fetch."""
    from abcfood_fingerprint.core.cache import get_cache

    cached = get_cache().get_records_raw(device_key)
    if cached is not None:
        logger.info("Backup using cached attendance for %s: %d records", device_key, len(cached))
        return cached

    logger.info("Backup cache miss for %s, fetching from device", device_key)
    client = pool.get_client(device_key)
    with client.connect() as c:
        return c.get_attendance()


def list_backups(device_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """List available backups from S3."""
    s3 = S3Client()
    return s3.list_backups(device_key)


def restore_backup(
    s3_key: str,
    target_device: Optional[str] = None,
    dry_run: bool = False,
    pool: Optional[DevicePool] = None,
) -> Dict[str, Any]:
    """Restore users + fingerprints from an S3 backup to a device.

    If target_device is not specified, restores to the original device.
    """
    p = pool or get_pool()
    s3 = S3Client()
    data = s3.download_backup(s3_key)

    record = BackupRecord(**data)
    device_key = target_device or record.device_key

    result = {
        "s3_key": s3_key,
        "target_device": device_key,
        "user_count": record.user_count,
        "fingerprint_count": record.fingerprint_count,
        "dry_run": dry_run,
    }

    if dry_run:
        logger.info("Dry run restore from %s -> %s", s3_key, device_key)
        return result

    client = p.get_client(device_key)
    with client.connect() as c:
        # Restore users
        for user_data in record.users:
            user = ZKUser(**user_data) if isinstance(user_data, dict) else user_data
            c.set_user(
                uid=user.uid,
                name=user.name,
                privilege=user.privilege,
                password=user.password,
                user_id=user.user_id,
                card=user.card,
            )

        # Restore fingerprints
        for fp_data in record.fingerprints:
            fp = ZKFingerprint(**fp_data) if isinstance(fp_data, dict) else fp_data
            try:
                c.set_fingerprint(fp.uid, fp.finger_index, fp.template)
            except Exception as e:
                logger.warning(
                    "Failed to restore fingerprint uid=%d finger=%d: %s",
                    fp.uid,
                    fp.finger_index,
                    e,
                )

    logger.info(
        "Restored %d users and %d fingerprints to %s from %s",
        record.user_count,
        record.fingerprint_count,
        device_key,
        s3_key,
    )
    return result
