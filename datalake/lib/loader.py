"""Loader — Optional Parquet archive to MinIO.

This module handles archiving extracted data as Parquet files to MinIO
for long-term storage. Bronze data lives in PostgreSQL for fast access;
Parquet in MinIO is the canonical archive.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "hmk-datalake")


def upload_parquet(file_path: str, object_name: str) -> bool:
    """Upload a Parquet file to MinIO. Returns True on success.

    Requires `minio` package to be installed.
    """
    try:
        from minio import Minio  # type: ignore[import-untyped]

        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False,
        )

        # Ensure bucket exists
        if not client.bucket_exists(MINIO_BUCKET):
            client.make_bucket(MINIO_BUCKET)

        client.fput_object(MINIO_BUCKET, object_name, file_path)
        logger.info("Uploaded %s → %s/%s", file_path, MINIO_BUCKET, object_name)
        return True

    except ImportError:
        logger.warning("minio package not installed, skipping Parquet archive")
        return False
    except Exception as exc:
        logger.error("Failed to upload %s: %s", file_path, exc)
        return False
