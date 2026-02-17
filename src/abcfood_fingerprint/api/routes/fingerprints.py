"""Fingerprint template API routes."""
from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from abcfood_fingerprint.api.deps import get_device_pool, verify_api_key
from abcfood_fingerprint.zk.pool import DevicePool

router = APIRouter(dependencies=[Depends(verify_api_key)])


class FingerprintResponse(BaseModel):
    uid: int
    user_id: str
    finger_index: int
    template: str


class FingerprintCountResponse(BaseModel):
    device: str
    count: int
    users_with_fingerprints: int


@router.get("/fingerprints/{device}/{user_id}")
def get_user_fingerprints(
    device: str,
    user_id: str,
    pool: DevicePool = Depends(get_device_pool),
):
    """Get fingerprint templates for a specific user."""
    from abcfood_fingerprint.core.fingerprint import get_fingerprints

    try:
        templates = get_fingerprints(device, user_id=user_id, pool=pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{device}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        FingerprintResponse(
            uid=t.uid,
            user_id=t.user_id,
            finger_index=t.finger_index,
            template=t.template,
        )
        for t in templates
    ]


@router.get("/fingerprints/{device}/count")
def count_fingerprints(
    device: str,
    pool: DevicePool = Depends(get_device_pool),
):
    """Count fingerprint templates on a device."""
    from abcfood_fingerprint.core.fingerprint import count_fingerprints as _count
    from abcfood_fingerprint.core.fingerprint import get_fingerprint_summary

    try:
        total = _count(device, pool)
        summary = get_fingerprint_summary(device, pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{device}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return FingerprintCountResponse(
        device=device,
        count=total,
        users_with_fingerprints=len(summary),
    )
