"""
Uploads local files to GCS, organising them under an immutable raw zone:

  raw/{taxi_type}/year={YYYY}/month={MM}/{filename}
  raw/taxi_zones/taxi_zone_lookup.csv
"""

import os
import re
from pathlib import Path

from google.cloud import storage

from src.utils.gcp_client import get_storage_client
from src.utils.logger import get_logger

logger = get_logger(__name__)

_TRIP_FILE_RE = re.compile(
    r"(?P<taxi_type>yellow|green)_tripdata_(?P<year>\d{4})-(?P<month>\d{2})\.parquet"
)


def _ensure_bucket(client: storage.Client, bucket_name: str, location: str) -> storage.Bucket:
    bucket = client.lookup_bucket(bucket_name)
    if bucket is None:
        logger.info("Creating GCS bucket: %s in %s", bucket_name, location)
        bucket = client.create_bucket(bucket_name, location=location)
    return bucket


def _gcs_path_for_trip_file(filename: str, raw_prefix: str) -> str | None:
    match = _TRIP_FILE_RE.match(filename)
    if not match:
        return None
    taxi_type = match.group("taxi_type")
    year = match.group("year")
    month = match.group("month")
    return f"{raw_prefix}/{taxi_type}/year={year}/month={month}/{filename}"


def upload_trip_files(
    local_paths: list[Path],
    bucket_name: str,
    raw_prefix: str = "raw",
    location: str = "US",
) -> list[str]:
    """
    Upload Parquet trip files to GCS.
    Returns list of gs:// URIs for each uploaded blob.
    """
    client = get_storage_client()
    bucket = _ensure_bucket(client, bucket_name, location)
    uris: list[str] = []

    for local_path in local_paths:
        gcs_path = _gcs_path_for_trip_file(local_path.name, raw_prefix)
        if gcs_path is None:
            logger.warning("Unrecognised filename format, skipping: %s", local_path.name)
            continue

        blob = bucket.blob(gcs_path)
        if blob.exists():
            logger.info("Already in GCS, skipping: %s", gcs_path)
        else:
            logger.info("Uploading %s → gs://%s/%s", local_path.name, bucket_name, gcs_path)
            blob.upload_from_filename(str(local_path))

        uri = f"gs://{bucket_name}/{gcs_path}"
        uris.append(uri)

    return uris


def upload_zone_lookup(
    local_path: Path,
    bucket_name: str,
    raw_prefix: str = "raw",
    location: str = "US",
) -> str:
    client = get_storage_client()
    bucket = _ensure_bucket(client, bucket_name, location)

    gcs_path = f"{raw_prefix}/taxi_zones/{local_path.name}"
    blob = bucket.blob(gcs_path)

    if blob.exists():
        logger.info("Already in GCS, skipping: %s", gcs_path)
    else:
        logger.info("Uploading %s → gs://%s/%s", local_path.name, bucket_name, gcs_path)
        blob.upload_from_filename(str(local_path))

    return f"gs://{bucket_name}/{gcs_path}"
