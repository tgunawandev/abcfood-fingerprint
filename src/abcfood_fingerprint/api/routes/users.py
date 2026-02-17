"""User management API routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from abcfood_fingerprint.api.deps import get_device_pool, verify_api_key
from abcfood_fingerprint.zk.pool import DevicePool

router = APIRouter(dependencies=[Depends(verify_api_key)])


class UserResponse(BaseModel):
    uid: int
    user_id: str
    name: str
    privilege: int
    card: int


class CreateUserRequest(BaseModel):
    uid: int
    name: str
    user_id: str = ""
    privilege: int = 0
    password: str = ""
    card: int = 0


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    user_id: Optional[str] = None
    privilege: Optional[int] = None
    card: Optional[int] = None


class SyncRequest(BaseModel):
    dry_run: bool = True


@router.get("/users/{device}")
def list_users(
    device: str,
    pool: DevicePool = Depends(get_device_pool),
):
    """List all users on a device."""
    from abcfood_fingerprint.core.user_sync import get_users

    try:
        users = get_users(device, pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{device}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return [
        UserResponse(
            uid=u.uid,
            user_id=u.user_id,
            name=u.name,
            privilege=u.privilege,
            card=u.card,
        )
        for u in sorted(users, key=lambda x: x.uid)
    ]


@router.post("/users/{device}")
def create_user(
    device: str,
    body: CreateUserRequest,
    pool: DevicePool = Depends(get_device_pool),
):
    """Create a user on a device."""
    from abcfood_fingerprint.core.user_sync import add_user

    try:
        add_user(
            device,
            uid=body.uid,
            name=body.name,
            user_id=body.user_id,
            privilege=body.privilege,
            password=body.password,
            card=body.card,
            pool=pool,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{device}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "message": f"User uid={body.uid} created on {device}"}


@router.put("/users/{device}/{user_id}")
def update_user(
    device: str,
    user_id: int,
    body: UpdateUserRequest,
    pool: DevicePool = Depends(get_device_pool),
):
    """Update a user on a device by UID."""
    from abcfood_fingerprint.core.user_sync import update_user as _update

    try:
        _update(
            device,
            uid=user_id,
            name=body.name,
            user_id=body.user_id,
            privilege=body.privilege,
            card=body.card,
            pool=pool,
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{device}' not found")
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "message": f"User uid={user_id} updated on {device}"}


@router.delete("/users/{device}/{user_id}")
def delete_user(
    device: str,
    user_id: int,
    pool: DevicePool = Depends(get_device_pool),
):
    """Delete a user from a device by UID."""
    from abcfood_fingerprint.core.user_sync import delete_user as _delete

    try:
        _delete(device, uid=user_id, pool=pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{device}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ok", "message": f"User uid={user_id} deleted from {device}"}


@router.post("/users/{device}/sync")
def sync_from_odoo(
    device: str,
    body: SyncRequest = SyncRequest(),
    pool: DevicePool = Depends(get_device_pool),
):
    """Sync users from Odoo HRIS to a device."""
    from abcfood_fingerprint.core.user_sync import sync_from_odoo as _sync

    try:
        result = _sync(device, dry_run=body.dry_run, pool=pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{device}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result
