"""Device management API routes."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from abcfood_fingerprint.api.deps import get_device_pool, verify_api_key
from abcfood_fingerprint.zk.pool import DevicePool

router = APIRouter(dependencies=[Depends(verify_api_key)])


class DeviceResponse(BaseModel):
    key: str
    name: str
    ip: str
    port: int
    model: str
    serial: str
    online: bool
    error: Optional[str] = None


class DeviceInfoResponse(BaseModel):
    key: str
    name: str
    ip: str
    port: int
    model: str
    serial: str
    firmware_version: str = ""
    device_serial: str = ""
    platform: str = ""
    device_name: str = ""
    mac_address: str = ""
    user_count: int = 0
    fp_count: int = 0
    attendance_count: int = 0
    device_time: Optional[str] = None


class TimeResponse(BaseModel):
    device_time: Optional[str] = None
    system_time: str


@router.get("/devices")
def list_devices(pool: DevicePool = Depends(get_device_pool)):
    """List all configured devices with online status."""
    from abcfood_fingerprint.core.device_manager import get_all_device_statuses

    statuses = get_all_device_statuses(pool)
    return [
        DeviceResponse(
            key=s.key,
            name=s.config.name,
            ip=s.config.ip,
            port=s.config.port,
            model=s.config.model,
            serial=s.config.serial,
            online=s.online,
            error=s.error,
        )
        for s in statuses
    ]


@router.get("/devices/{name}")
def get_device(name: str, pool: DevicePool = Depends(get_device_pool)):
    """Get detailed device information."""
    from abcfood_fingerprint.core.device_manager import get_device_status

    try:
        status = get_device_status(name, pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{name}' not found")

    if not status.online:
        raise HTTPException(status_code=503, detail=f"Device '{name}' is offline: {status.error}")

    info = status.info
    return DeviceInfoResponse(
        key=status.key,
        name=status.config.name,
        ip=status.config.ip,
        port=status.config.port,
        model=status.config.model,
        serial=status.config.serial,
        firmware_version=info.firmware_version if info else "",
        device_serial=info.serial_number if info else "",
        platform=info.platform if info else "",
        device_name=info.device_name if info else "",
        mac_address=info.mac_address if info else "",
        user_count=info.user_count if info else 0,
        fp_count=info.fp_count if info else 0,
        attendance_count=info.attendance_count if info else 0,
        device_time=str(info.device_time) if info and info.device_time else None,
    )


@router.post("/devices/{name}/restart")
def restart_device(name: str, pool: DevicePool = Depends(get_device_pool)):
    """Restart a device."""
    from abcfood_fingerprint.core.device_manager import restart_device as _restart

    try:
        _restart(name, pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "message": f"Device {name} restarted"}


@router.get("/devices/{name}/time")
def get_device_time(name: str, pool: DevicePool = Depends(get_device_pool)):
    """Get device time."""
    from abcfood_fingerprint.core.device_manager import get_device_time as _get_time

    try:
        dt = _get_time(name, pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return TimeResponse(
        device_time=str(dt) if dt else None,
        system_time=datetime.now().isoformat(),
    )


@router.put("/devices/{name}/time")
def sync_device_time(name: str, pool: DevicePool = Depends(get_device_pool)):
    """Sync device time to system time."""
    from abcfood_fingerprint.core.device_manager import sync_device_time as _sync_time

    try:
        _sync_time(name, pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "message": f"Time synced on device {name}"}
