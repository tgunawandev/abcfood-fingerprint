"""APScheduler BackgroundScheduler with job definitions."""
from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler

from abcfood_fingerprint.config import get_settings
from abcfood_fingerprint.core.cache import get_cache
from abcfood_fingerprint.utils.notifications import notify_backup_success, notify_error
from abcfood_fingerprint.zk.pool import get_pool

logger = logging.getLogger(__name__)


# -- Job functions (run in thread-pool) --


def _job_refresh_cache(device_key: str) -> None:
    """Refresh attendance cache for a single device."""
    try:
        cache = get_cache()
        count = cache.refresh(device_key)
        logger.info("Scheduled cache refresh for %s: %d records", device_key, count)
    except Exception as exc:
        logger.error("Scheduled cache refresh failed for %s: %s", device_key, exc)


def _job_daily_backup(device_key: str) -> None:
    """Run daily backup (users + fingerprints + attendance) for a device."""
    from abcfood_fingerprint.core.backup import run_backup

    try:
        result = run_backup(device_key, include_attendance=True)
        logger.info("Scheduled backup complete for %s: %s", device_key, result["s3_key"])
        notify_backup_success(
            device=device_key,
            users=result["user_count"],
            fingerprints=result["fingerprint_count"],
            s3_key=result["s3_key"],
            attendance=result.get("attendance_count", 0),
        )
    except Exception as exc:
        logger.error("Scheduled backup failed for %s: %s", device_key, exc)
        notify_error("scheduled_backup", f"{device_key}: {exc}")


def _job_cleanup_old_backups() -> None:
    """Delete backups older than retention period."""
    from abcfood_fingerprint.storage.s3 import S3Client

    settings = get_settings()
    try:
        s3 = S3Client()
        deleted = s3.cleanup_old_backups(settings.BACKUP_RETENTION_DAYS)
        logger.info("Cleanup: deleted %d old backups", deleted)
    except Exception as exc:
        logger.error("Cleanup failed: %s", exc)
        notify_error("cleanup_old_backups", str(exc))


# -- Scheduler lifecycle --


_scheduler: Optional[BackgroundScheduler] = None


def start_scheduler() -> BackgroundScheduler:
    """Create, configure, and start the background scheduler.

    Registers:
      - Cache refresh per device (every N minutes, staggered)
      - Daily backup per device (cron, staggered by 5 min)
      - Daily cleanup of old backups
    """
    global _scheduler

    settings = get_settings()
    pool = get_pool()
    device_keys = pool.device_keys()

    scheduler = BackgroundScheduler(
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 3600,
        },
    )

    # Cache refresh jobs (staggered by 1 minute)
    for i, key in enumerate(device_keys):
        # Interval job — first run happens after the interval.
        # We use next_run_time trick below to trigger immediate first run.
        scheduler.add_job(
            _job_refresh_cache,
            "interval",
            args=[key],
            minutes=settings.CACHE_REFRESH_MINUTES,
            id=f"cache_refresh_{key}",
            name=f"Cache refresh: {key}",
            # Stagger start by 1 minute per device
            next_run_time=_staggered_start(seconds=i * 60),
        )
        logger.info(
            "Scheduled cache refresh for %s every %d min (offset %ds)",
            key,
            settings.CACHE_REFRESH_MINUTES,
            i * 60,
        )

    # Daily backup jobs (staggered by 5 minutes)
    for i, key in enumerate(device_keys):
        minute = settings.BACKUP_MINUTE_UTC + (i * 5)
        scheduler.add_job(
            _job_daily_backup,
            "cron",
            args=[key],
            hour=settings.BACKUP_HOUR_UTC,
            minute=minute,
            id=f"daily_backup_{key}",
            name=f"Daily backup: {key}",
        )
        logger.info(
            "Scheduled daily backup for %s at %02d:%02d UTC",
            key,
            settings.BACKUP_HOUR_UTC,
            minute,
        )

    # Cleanup old backups (1 hour after backups)
    scheduler.add_job(
        _job_cleanup_old_backups,
        "cron",
        hour=settings.BACKUP_HOUR_UTC + 1,
        minute=0,
        id="cleanup_old_backups",
        name="Cleanup old backups",
    )
    logger.info(
        "Scheduled cleanup at %02d:00 UTC (retention=%d days)",
        settings.BACKUP_HOUR_UTC + 1,
        settings.BACKUP_RETENTION_DAYS,
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))
    return scheduler


def stop_scheduler() -> None:
    """Shut down the scheduler gracefully."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
    _scheduler = None


def get_scheduler() -> Optional[BackgroundScheduler]:
    """Return the current scheduler instance (may be None)."""
    return _scheduler


def _staggered_start(seconds: int) -> "datetime":
    """Return a datetime ``seconds`` from now for staggered first runs."""
    from datetime import datetime, timedelta

    return datetime.now() + timedelta(seconds=seconds)
