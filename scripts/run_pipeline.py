"""
Entry point for the NYC Taxi ELT pipeline.

Usage:
    python scripts/run_pipeline.py [--step extract|load-gcs|load-bq|all]

Steps:
    extract   – Download Parquet files from TLC website to data/tmp/
    load-gcs  – Upload local files to GCS raw zone
    load-bq   – Load GCS Parquet files into BigQuery raw dataset
    all       – Run all three steps end-to-end (default)

After load-bq, run dbt from the dbt/ directory:
    cd dbt && dbt run && dbt test
"""

import os
import sys
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extract.download_data import download_taxi_data, download_zone_lookup
from src.load.load_to_bigquery import load_to_bigquery
from src.load.upload_to_gcs import upload_trip_files, upload_zone_lookup
from src.utils.logger import get_logger

logger = get_logger("pipeline")


def load_config(config_path: str = "config/config.yaml") -> dict:
    with open(config_path) as fh:
        return yaml.safe_load(fh)


def require_env(key: str) -> str:
    value = os.environ.get(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' is not set. "
            "Copy .env.example → .env and fill in your values."
        )
    return value


@click.command()
@click.option(
    "--step",
    default="all",
    type=click.Choice(["extract", "load-gcs", "load-bq", "all"], case_sensitive=False),
    show_default=True,
    help="Pipeline step to run.",
)
@click.option(
    "--config",
    default="config/config.yaml",
    show_default=True,
    help="Path to config YAML.",
)
def main(step: str, config: str) -> None:
    load_dotenv()

    cfg = load_config(config)

    taxi_types = cfg["pipeline"]["taxi_types"]
    years = cfg["pipeline"]["years"]
    months = cfg["pipeline"]["months"]
    tmp_dir = cfg["local"]["tmp_dir"]
    raw_prefix = cfg["gcs"]["raw_prefix"]

    # ------------------------------------------------------------------ extract
    if step in ("extract", "all"):
        logger.info("=== STEP 1: EXTRACT ===")
        trip_files = download_taxi_data(taxi_types, years, months, tmp_dir)
        zone_file = download_zone_lookup(tmp_dir)
        logger.info("Downloaded %d trip file(s)", len(trip_files))
    else:
        # Reconstruct paths for subsequent steps without re-downloading
        from src.extract.download_data import TAXI_FILE_TEMPLATES

        trip_files = []
        for taxi_type in taxi_types:
            template = TAXI_FILE_TEMPLATES[taxi_type]
            for year in years:
                for month in months:
                    filename = template.format(year=year, month=month)
                    path = Path(tmp_dir) / taxi_type / filename
                    if path.exists():
                        trip_files.append(path)
        zone_file = Path(tmp_dir) / "taxi_zone_lookup.csv"

    # --------------------------------------------------------------- load-gcs
    if step in ("load-gcs", "all"):
        logger.info("=== STEP 2: LOAD TO GCS ===")
        bucket_name = require_env("GCS_BUCKET_NAME")
        location = os.environ.get("GCP_REGION", "US")

        trip_uris = upload_trip_files(trip_files, bucket_name, raw_prefix, location)
        zone_uri = upload_zone_lookup(zone_file, bucket_name, raw_prefix, location)
        logger.info("Uploaded %d trip file(s) to GCS", len(trip_uris))
    else:
        # Rebuild URIs from env so load-bq can run standalone
        bucket_name = os.environ.get("GCS_BUCKET_NAME", "")
        trip_uris = []
        zone_uri = ""

    # ---------------------------------------------------------------- load-bq
    if step in ("load-bq", "all"):
        logger.info("=== STEP 3: LOAD TO BIGQUERY ===")
        dataset_id = require_env("BQ_DATASET_RAW")
        location = os.environ.get("GCP_REGION", "US")

        if not trip_uris:
            raise RuntimeError(
                "No GCS URIs available. Run with --step all or provide load-gcs output."
            )

        load_to_bigquery(trip_uris, zone_uri, dataset_id, location)
        logger.info("BigQuery load complete")

    logger.info("=== PIPELINE COMPLETE ===")
    logger.info("Next step: cd dbt && dbt deps && dbt run && dbt test")


if __name__ == "__main__":
    main()
