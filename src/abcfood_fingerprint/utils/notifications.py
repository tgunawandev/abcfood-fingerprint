"""Notification helpers for Telegram and Mattermost."""
from __future__ import annotations

import logging
from typing import Optional

import requests

from abcfood_fingerprint.config import get_settings

logger = logging.getLogger(__name__)

SERVICE_NAME = "FINGERPRINT-SVC"


def send_telegram_message(message: str) -> bool:
    """Send a message via Telegram bot."""
    settings = get_settings()
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        logger.debug("Telegram not configured, skipping notification")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={
                "chat_id": settings.TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Failed to send Telegram message: %s", e)
        return False


def send_mattermost_message(message: str) -> bool:
    """Send a message via Mattermost webhook."""
    settings = get_settings()
    if not settings.MATTERMOST_WEBHOOK_URL:
        return False

    try:
        resp = requests.post(
            settings.MATTERMOST_WEBHOOK_URL,
            json={"text": message},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error("Failed to send Mattermost message: %s", e)
        return False


def notify_backup_success(device: str, users: int, fingerprints: int, s3_key: str) -> None:
    """Notify about successful backup."""
    msg = (
        f"<b>{SERVICE_NAME} - Backup OK</b>\n"
        f"Device: {device}\n"
        f"Users: {users}, Fingerprints: {fingerprints}\n"
        f"S3: {s3_key}"
    )
    send_telegram_message(msg)


def notify_error(operation: str, error: str) -> None:
    """Notify about an error."""
    msg = f"<b>{SERVICE_NAME} - ERROR</b>\nOperation: {operation}\nError: {error}"
    send_telegram_message(msg)
