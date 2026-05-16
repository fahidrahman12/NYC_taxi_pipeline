"""
Downloads NYC TLC trip record Parquet files and the taxi zone lookup CSV
to a local temporary directory before they are uploaded to GCS.
"""

import os
from pathlib import Path

import requests
from tqdm import tqdm

from src.utils.logger import get_logger

logger = get_logger(__name__)

TLC_BASE_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data"
ZONE_LOOKUP_URL = "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv"

TAXI_FILE_TEMPLATES = {
    "yellow": "yellow_tripdata_{year}-{month:02d}.parquet",
    "green": "green_tripdata_{year}-{month:02d}.parquet",
}


def _download_file(url: str, dest: Path, chunk_size: int = 8 * 1024 * 1024) -> Path:
    """Stream-download *url* to *dest*, skipping if the file already exists."""
    if dest.exists():
        logger.info("Already downloaded, skipping: %s", dest.name)
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading %s → %s", url, dest)

    with requests.get(url, stream=True, timeout=120) as response:
        response.raise_for_status()
        total = int(response.headers.get("content-length", 0))

        with open(dest, "wb") as fh, tqdm(
            total=total,
            unit="B",
            unit_scale=True,
            unit_divisor=1024,
            desc=dest.name,
            leave=False,
        ) as bar:
            for chunk in response.iter_content(chunk_size=chunk_size):
                fh.write(chunk)
                bar.update(len(chunk))

    return dest


def download_taxi_data(
    taxi_types: list[str],
    years: list[int],
    months: list[int],
    tmp_dir: str = "data/tmp",
) -> list[Path]:
    """
    Download trip record Parquet files for each combination of
    taxi_type × year × month.  Returns list of local file paths.
    """
    downloaded: list[Path] = []

    for taxi_type in taxi_types:
        template = TAXI_FILE_TEMPLATES[taxi_type]

        for year in years:
            for month in months:
                filename = template.format(year=year, month=month)
                url = f"{TLC_BASE_URL}/{filename}"
                dest = Path(tmp_dir) / taxi_type / filename

                try:
                    path = _download_file(url, dest)
                    downloaded.append(path)
                except requests.HTTPError as exc:
                    # Some year/month combinations don't exist yet — log and continue
                    logger.warning("Skipping %s: %s", filename, exc)

    return downloaded


def download_zone_lookup(tmp_dir: str = "data/tmp") -> Path:
    """Download the taxi zone lookup CSV."""
    dest = Path(tmp_dir) / "taxi_zone_lookup.csv"
    return _download_file(ZONE_LOOKUP_URL, dest)
