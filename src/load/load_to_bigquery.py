"""
Loads raw Parquet files from GCS into BigQuery raw dataset tables.

Each taxi type gets its own table (raw.yellow_taxi_trips, raw.green_taxi_trips).
Tables are partitioned by pickup_datetime and clustered for cost-efficient queries.
Schema is inferred from the Parquet files — no hardcoded schema required.
"""

import os
import re

from google.cloud import bigquery
from google.cloud.exceptions import NotFound

from src.utils.gcp_client import get_bigquery_client
from src.utils.logger import get_logger

logger = get_logger(__name__)

_TRIP_URI_RE = re.compile(
    r"gs://.+/raw/(?P<taxi_type>yellow|green)/year=\d{4}/month=\d{2}/.+\.parquet"
)

TABLE_MAP = {
    "yellow": "yellow_taxi_trips",
    "green": "green_taxi_trips",
}

# Column name containing pickup time differs between yellow and green
PICKUP_COL = {
    "yellow": "tpep_pickup_datetime",
    "green": "lpep_pickup_datetime",
}


def _ensure_dataset(client: bigquery.Client, dataset_id: str, location: str) -> None:
    full_id = f"{client.project}.{dataset_id}"
    try:
        client.get_dataset(full_id)
    except NotFound:
        logger.info("Creating BigQuery dataset: %s", full_id)
        dataset = bigquery.Dataset(full_id)
        dataset.location = location
        client.create_dataset(dataset)


def _load_taxi_table(
    client: bigquery.Client,
    project_id: str,
    dataset_id: str,
    taxi_type: str,
    gcs_uris: list[str],
    location: str,
) -> None:
    table_id = f"{project_id}.{dataset_id}.{TABLE_MAP[taxi_type]}"
    pickup_col = PICKUP_COL[taxi_type]

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        # Partition by the pickup datetime column for efficient date-range queries
        time_partitioning=bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field=pickup_col,
        ),
        clustering_fields=["VendorID", "payment_type"],
        autodetect=True,
    )

    logger.info(
        "Loading %d file(s) into %s (partition: %s)",
        len(gcs_uris),
        table_id,
        pickup_col,
    )
    load_job = client.load_table_from_uri(gcs_uris, table_id, job_config=job_config)
    load_job.result()  # wait for completion
    logger.info("Load complete: %s rows → %s", load_job.output_rows, table_id)


def _load_zone_lookup(
    client: bigquery.Client,
    project_id: str,
    dataset_id: str,
    zone_uri: str,
    location: str,
) -> None:
    table_id = f"{project_id}.{dataset_id}.taxi_zones"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )

    logger.info("Loading taxi zone lookup → %s", table_id)
    load_job = client.load_table_from_uri(zone_uri, table_id, job_config=job_config)
    load_job.result()
    logger.info("Zone lookup load complete")


def load_to_bigquery(
    trip_uris: list[str],
    zone_uri: str,
    dataset_id: str,
    location: str = "US",
) -> None:
    """
    Load all trip Parquet files and the zone lookup CSV into BigQuery.

    trip_uris are grouped by taxi_type and loaded into separate tables.
    Existing rows are appended (idempotent: re-running without deduplication
    may create duplicates — use dbt staging to deduplicate if needed).
    """
    client = get_bigquery_client()
    project_id = client.project

    _ensure_dataset(client, dataset_id, location)

    # Group URIs by taxi type
    by_type: dict[str, list[str]] = {"yellow": [], "green": []}
    for uri in trip_uris:
        match = _TRIP_URI_RE.match(uri)
        if match:
            by_type[match.group("taxi_type")].append(uri)

    for taxi_type, uris in by_type.items():
        if uris:
            _load_taxi_table(client, project_id, dataset_id, taxi_type, uris, location)

    if zone_uri:
        _load_zone_lookup(client, project_id, dataset_id, zone_uri, location)
