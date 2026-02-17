"""Backup API routes."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from abcfood_fingerprint.api.deps import get_device_pool, verify_api_key
from abcfood_fingerprint.zk.pool import DevicePool

router = APIRouter(dependencies=[Depends(verify_api_key)])


class RestoreRequest(BaseModel):
    target_device: Optional[str] = None
    dry_run: bool = True


@router.post("/backup/{device}")
def trigger_backup(
    device: str,
    pool: DevicePool = Depends(get_device_pool),
):
    """Trigger a full backup of a device to S3."""
    from abcfood_fingerprint.core.backup import run_backup

    try:
        result = run_backup(device, pool)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device '{device}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result


@router.get("/backup/list")
def list_backups(
    device: Optional[str] = Query(None, description="Filter by device key"),
):
    """List available backups in S3."""
    from abcfood_fingerprint.core.backup import list_backups as _list

    try:
        return _list(device)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backup/restore/{backup_id:path}")
def restore_backup(
    backup_id: str,
    body: RestoreRequest = RestoreRequest(),
    pool: DevicePool = Depends(get_device_pool),
):
    """Restore a backup from S3 to a device."""
    from abcfood_fingerprint.core.backup import restore_backup as _restore

    try:
        result = _restore(
            backup_id,
            target_device=body.target_device,
            dry_run=body.dry_run,
            pool=pool,
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return result
