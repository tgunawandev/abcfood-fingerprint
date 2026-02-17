"""Attendance API routes."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from abcfood_fingerprint.api.deps import get_device_pool, verify_api_key
from abcfood_fingerprint.zk.pool import DevicePool

router = APIRouter(dependencies=[Depends(verify_api_key)])


class AttendanceRecord(BaseModel):
    user_id: str
    timestamp: str
    status: int
    punch: int


class AttendanceCountResponse(BaseModel):
    device: str
    count: int


@router.get("/attendance/{device}")
def get_attendance(
    device: str,
    date_from: Optional[str] = Query(None, alias="from", description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, alias="to", description="End date YYYY-MM-DD"),
    pool: DevicePool = Depends(get_device_pool),
):
    """Get attendance records from a device with optional date filtering."""
    from abcfood_fingerprint.core.attendance import get_attendance as _get

    dt_from = datetime.strptime(date_from, "%Y-%m-%d") if date_from else None
    dt_to = (
        datetime.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        if date_to
        else None
    )

    try:
        records = _get(device, dt_from, dt_to, pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{device}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        AttendanceRecord(
            user_id=r.user_id,
            timestamp=r.timestamp.isoformat(),
            status=r.status,
            punch=r.punch,
        )
        for r in records
    ]


@router.get("/attendance/{device}/count")
def count_attendance(
    device: str,
    pool: DevicePool = Depends(get_device_pool),
):
    """Count attendance records on a device."""
    from abcfood_fingerprint.core.attendance import count_attendance as _count

    try:
        count = _count(device, pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{device}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return AttendanceCountResponse(device=device, count=count)
