"""Configuration settings for abcfood-fingerprint."""
from __future__ import annotations

import os
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Device config
    ZK_MACHINES_CONFIG: str = "config/machines.yml"

    # API Server
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_KEY: str = "change-me-in-production"
    API_CORS_ORIGINS: str = "https://odoo-hris.abcfood.app"

    # S3 Backup (Hetzner)
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET: str = "hz-abcfood-fingerprint"
    S3_ENDPOINT: str = "https://nbg1.your-objectstorage.com"
    S3_REGION: str = "nbg1"

    # Odoo HRIS (for user sync)
    ODOO_HOST: str = "odoo-hris.abcfood.app"
    ODOO_PORT: int = 443
    ODOO_PROTOCOL: str = "jsonrpc+ssl"
    ODOO_DB: str = "hris_db"
    ODOO_USER: str = "admin"
    ODOO_PASSWORD: str = "change-me"

    # Cloudflared
    CLOUDFLARE_TUNNEL_TOKEN: str = ""

    # Notifications
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    MATTERMOST_WEBHOOK_URL: str = ""

    # Scheduler & Cache
    SCHEDULER_ENABLED: bool = True
    CACHE_REFRESH_MINUTES: int = 5
    BACKUP_HOUR_UTC: int = 17
    BACKUP_MINUTE_UTC: int = 0

    # General
    ENVIRONMENT: str = "production"
    LOG_LEVEL: str = "INFO"
    BACKUP_RETENTION_DAYS: int = 90

    model_config = SettingsConfigDict(
        env_file=[".env.local", ".env"],
        case_sensitive=True,
        extra="allow",
    )

    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [o.strip() for o in self.API_CORS_ORIGINS.split(",") if o.strip()]


# Lazy-loaded singleton
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get application settings (lazy loaded)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
