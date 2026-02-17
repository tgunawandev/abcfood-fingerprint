"""User synchronization between Odoo and ZKTeco devices."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from abcfood_fingerprint.config import get_settings
from abcfood_fingerprint.zk.models import ZKUser
from abcfood_fingerprint.zk.pool import DevicePool, get_pool

logger = logging.getLogger(__name__)


def get_users(
    device_key: str,
    pool: Optional[DevicePool] = None,
) -> List[ZKUser]:
    """Get all users from a device."""
    p = pool or get_pool()
    client = p.get_client(device_key)
    with client.connect() as c:
        return c.get_users()


def get_user(
    device_key: str,
    user_id: str,
    pool: Optional[DevicePool] = None,
) -> Optional[ZKUser]:
    """Get a specific user by user_id from a device."""
    users = get_users(device_key, pool)
    for u in users:
        if u.user_id == user_id:
            return u
    return None


def add_user(
    device_key: str,
    uid: int,
    name: str,
    user_id: str = "",
    privilege: int = 0,
    password: str = "",
    card: int = 0,
    pool: Optional[DevicePool] = None,
) -> None:
    """Add a user to a device."""
    p = pool or get_pool()
    client = p.get_client(device_key)
    with client.connect() as c:
        c.set_user(
            uid=uid,
            name=name,
            privilege=privilege,
            password=password,
            user_id=user_id,
            card=card,
        )
    logger.info("Added user uid=%d name=%s to device %s", uid, name, device_key)


def update_user(
    device_key: str,
    uid: int,
    name: Optional[str] = None,
    user_id: Optional[str] = None,
    privilege: Optional[int] = None,
    card: Optional[int] = None,
    pool: Optional[DevicePool] = None,
) -> None:
    """Update an existing user on a device."""
    p = pool or get_pool()
    users = get_users(device_key, p)

    existing = None
    for u in users:
        if u.uid == uid:
            existing = u
            break
    if not existing:
        raise ValueError(f"User uid={uid} not found on device {device_key}")

    client = p.get_client(device_key)
    with client.connect() as c:
        c.set_user(
            uid=uid,
            name=name if name is not None else existing.name,
            privilege=privilege if privilege is not None else existing.privilege,
            password=existing.password,
            user_id=user_id if user_id is not None else existing.user_id,
            card=card if card is not None else existing.card,
        )
    logger.info("Updated user uid=%d on device %s", uid, device_key)


def delete_user(
    device_key: str,
    uid: int,
    pool: Optional[DevicePool] = None,
) -> None:
    """Delete a user from a device."""
    p = pool or get_pool()
    client = p.get_client(device_key)
    with client.connect() as c:
        c.delete_user(uid)
    logger.info("Deleted user uid=%d from device %s", uid, device_key)


def _fetch_odoo_employees() -> List[Dict[str, Any]]:
    """Fetch employees from Odoo with identification_id set."""
    import odoorpc

    settings = get_settings()
    odoo = odoorpc.ODOO(
        settings.ODOO_HOST,
        protocol=settings.ODOO_PROTOCOL,
        port=settings.ODOO_PORT,
    )
    odoo.login(settings.ODOO_DB, settings.ODOO_USER, settings.ODOO_PASSWORD)

    Employee = odoo.env["hr.employee"]
    ids = Employee.search([("identification_id", "!=", False)])
    employees = Employee.read(ids, ["name", "identification_id"])
    logger.info("Fetched %d employees from Odoo with identification_id", len(employees))
    return employees


def sync_from_odoo(
    device_key: str,
    dry_run: bool = False,
    pool: Optional[DevicePool] = None,
) -> Dict[str, Any]:
    """Sync users from Odoo to a device.

    Maps Odoo hr.employee.identification_id -> device user_id.
    Returns summary of operations.
    """
    p = pool or get_pool()
    employees = _fetch_odoo_employees()
    device_users = get_users(device_key, p)

    # Build lookup by user_id
    existing = {u.user_id: u for u in device_users}

    to_add = []
    to_update = []
    unchanged = []

    for emp in employees:
        eid = str(emp["identification_id"]).strip()
        name = emp["name"][:24]  # ZKTeco name limit

        if eid in existing:
            user = existing[eid]
            if user.name != name:
                to_update.append({"uid": user.uid, "user_id": eid, "name": name})
            else:
                unchanged.append(eid)
        else:
            # Find next available UID
            max_uid = max((u.uid for u in device_users), default=0)
            new_uid = max_uid + 1 + len(to_add)
            to_add.append({"uid": new_uid, "user_id": eid, "name": name})

    result = {
        "device": device_key,
        "odoo_employees": len(employees),
        "device_users": len(device_users),
        "to_add": len(to_add),
        "to_update": len(to_update),
        "unchanged": len(unchanged),
        "dry_run": dry_run,
        "details_add": to_add,
        "details_update": to_update,
    }

    if dry_run:
        logger.info("Dry run - no changes applied to device %s", device_key)
        return result

    client = p.get_client(device_key)
    with client.connect() as c:
        for u in to_add:
            c.set_user(uid=u["uid"], name=u["name"], user_id=u["user_id"])
        for u in to_update:
            c.set_user(uid=u["uid"], name=u["name"], user_id=u["user_id"])

    logger.info(
        "Synced device %s: %d added, %d updated, %d unchanged",
        device_key,
        len(to_add),
        len(to_update),
        len(unchanged),
    )
    return result
