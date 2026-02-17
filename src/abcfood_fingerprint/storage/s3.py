"""Hetzner S3-compatible storage operations."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError

from abcfood_fingerprint.config import get_settings

logger = logging.getLogger(__name__)


class S3Client:
    """Client for Hetzner S3-compatible object storage."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = boto3.client(
            "s3",
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            endpoint_url=settings.S3_ENDPOINT,
            region_name=settings.S3_REGION,
        )
        self.bucket = settings.S3_BUCKET

    def upload_backup(self, device_key: str, data: Dict[str, Any]) -> str:
        """Upload a backup JSON to S3.

        Returns the S3 key of the uploaded backup.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        s3_key = f"backups/{device_key}/{timestamp}.json"

        body = json.dumps(data, default=str, indent=2)
        self.client.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=body.encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Uploaded backup to s3://%s/%s", self.bucket, s3_key)
        return s3_key

    def download_backup(self, s3_key: str) -> Dict[str, Any]:
        """Download a backup JSON from S3."""
        response = self.client.get_object(Bucket=self.bucket, Key=s3_key)
        body = response["Body"].read().decode("utf-8")
        logger.info("Downloaded backup from s3://%s/%s", self.bucket, s3_key)
        return json.loads(body)

    def list_backups(self, device_key: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available backups, optionally filtered by device."""
        prefix = f"backups/{device_key}/" if device_key else "backups/"

        backups = []
        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                if key.endswith(".json"):
                    parts = key.replace("backups/", "").split("/")
                    backups.append(
                        {
                            "key": key,
                            "device": parts[0] if len(parts) > 1 else "unknown",
                            "filename": parts[-1],
                            "size": obj["Size"],
                            "last_modified": obj["LastModified"].isoformat(),
                        }
                    )

        backups.sort(key=lambda x: x["last_modified"], reverse=True)
        logger.info("Found %d backups (prefix=%s)", len(backups), prefix)
        return backups

    def delete_backup(self, s3_key: str) -> None:
        """Delete a backup from S3."""
        self.client.delete_object(Bucket=self.bucket, Key=s3_key)
        logger.info("Deleted backup s3://%s/%s", self.bucket, s3_key)

    def cleanup_old_backups(self, retention_days: int = 90) -> int:
        """Delete backups older than retention_days. Returns count deleted."""
        cutoff = datetime.now() - timedelta(days=retention_days)
        deleted = 0

        paginator = self.client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix="backups/"):
            for obj in page.get("Contents", []):
                if obj["LastModified"].replace(tzinfo=None) < cutoff:
                    self.client.delete_object(Bucket=self.bucket, Key=obj["Key"])
                    deleted += 1

        logger.info("Cleaned up %d old backups (retention=%d days)", deleted, retention_days)
        return deleted

    def test_connection(self) -> bool:
        """Test S3 connectivity."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
            return True
        except ClientError:
            return False
