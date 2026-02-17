"""Pydantic models for ZKTeco device data."""
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ZKUser(BaseModel):
    """User record from a ZKTeco device."""

    uid: int = Field(description="Internal UID on device")
    user_id: str = Field(description="User ID (maps to employee identification_id)")
    name: str = Field(default="", description="User display name")
    privilege: int = Field(default=0, description="Privilege level (0=user, 14=admin)")
    password: str = Field(default="", description="User password")
    group_id: str = Field(default="0", description="Group ID")
    card: int = Field(default=0, description="Card number")


class ZKAttendance(BaseModel):
    """Attendance record from a ZKTeco device."""

    uid: int = Field(description="Internal UID on device")
    user_id: str = Field(description="User ID")
    timestamp: datetime = Field(description="Punch timestamp")
    status: int = Field(default=0, description="Punch status (0=check-in, 1=check-out, etc.)")
    punch: int = Field(default=0, description="Punch type")


class ZKFingerprint(BaseModel):
    """Fingerprint template from a ZKTeco device."""

    uid: int = Field(description="Internal UID on device")
    user_id: str = Field(description="User ID")
    finger_index: int = Field(description="Finger index (0-9)")
    template: str = Field(description="Base64-encoded fingerprint template")
    valid: int = Field(default=1, description="Template validity flag")


class ZKDeviceInfo(BaseModel):
    """Device information from a ZKTeco device."""

    firmware_version: str = Field(default="")
    serial_number: str = Field(default="")
    platform: str = Field(default="")
    device_name: str = Field(default="")
    mac_address: str = Field(default="")
    user_count: int = Field(default=0)
    fp_count: int = Field(default=0)
    attendance_count: int = Field(default=0)
    device_time: Optional[datetime] = None


class DeviceConfig(BaseModel):
    """Device configuration from machines.yml."""

    name: str
    ip: str
    port: int = 4370
    password: int = 0
    model: str = ""
    serial: str = ""


class DeviceStatus(BaseModel):
    """Device status with health info."""

    key: str = Field(description="Device key from config (e.g., 'tmi')")
    config: DeviceConfig
    online: bool = False
    info: Optional[ZKDeviceInfo] = None
    error: Optional[str] = None
    last_check: Optional[datetime] = None


class BackupRecord(BaseModel):
    """A full device backup record."""

    device_key: str
    device_name: str
    timestamp: str
    users: List[ZKUser] = Field(default_factory=list)
    fingerprints: List[ZKFingerprint] = Field(default_factory=list)
    attendance: List[ZKAttendance] = Field(default_factory=list)
    user_count: int = 0
    fingerprint_count: int = 0
    attendance_count: int = 0
