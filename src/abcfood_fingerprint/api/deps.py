"""FastAPI dependencies - auth, device pool injection."""
from __future__ import annotations

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from abcfood_fingerprint.config import get_settings
from abcfood_fingerprint.zk.pool import DevicePool, get_pool

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key from X-API-Key header."""
    settings = get_settings()
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return api_key


def get_device_pool() -> DevicePool:
    """Dependency to get the device pool."""
    return get_pool()
