"""FastAPI application factory."""
from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from abcfood_fingerprint import __version__
from abcfood_fingerprint.api.middleware import RequestLoggingMiddleware
from abcfood_fingerprint.api.routes import attendance, backup, devices, fingerprints, users
from abcfood_fingerprint.config import get_settings


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="ABCFood Fingerprint API",
        description="ZKTeco middleware REST API for fingerprint device management",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Logging
    app.add_middleware(RequestLoggingMiddleware)

    # Routes
    app.include_router(devices.router, prefix="/api/v1", tags=["Devices"])
    app.include_router(attendance.router, prefix="/api/v1", tags=["Attendance"])
    app.include_router(users.router, prefix="/api/v1", tags=["Users"])
    app.include_router(fingerprints.router, prefix="/api/v1", tags=["Fingerprints"])
    app.include_router(backup.router, prefix="/api/v1", tags=["Backup"])

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "abcfood-fingerprint",
            "version": __version__,
            "timestamp": datetime.now().isoformat(),
        }

    @app.get("/metrics")
    async def metrics():
        from abcfood_fingerprint.zk.pool import get_pool

        pool = get_pool()
        device_count = len(pool.device_keys())
        return {
            "service": "abcfood-fingerprint",
            "version": __version__,
            "devices_configured": device_count,
            "timestamp": datetime.now().isoformat(),
        }

    return app
