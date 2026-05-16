# NYC Taxi ELT Pipeline

End-to-end ELT pipeline for the [NYC TLC Trip Record dataset](https://www.nyc.gov/site/tlc/about/tlc-trip-record-data.page), built with Python, Google Cloud Storage, BigQuery, and dbt.

## Architecture

```
TLC Website (Parquet)
        │
        ▼
   [Extract]  ─── Python + requests
        │
        ▼
 GCS Raw Zone  ──  Immutable Parquet files
        │            raw/{taxi_type}/year={Y}/month={M}/
        ▼
  BigQuery Raw  ──  nyc_taxi_raw.yellow_taxi_trips
        │            nyc_taxi_raw.green_taxi_trips
        │            nyc_taxi_raw.taxi_zones
        ▼
  dbt Staging  ──  nyc_taxi_staging.stg_yellow_taxi  (views)
        │            nyc_taxi_staging.stg_green_taxi
        │            nyc_taxi_staging.stg_taxi_zones
        ▼
   dbt Marts   ──  nyc_taxi_marts.fact_trips          (tables)
                    nyc_taxi_marts.dim_zones
                    nyc_taxi_marts.dim_payment_types
```

## Prerequisites

- Python 3.11+
- A GCP project with BigQuery and GCS APIs enabled
- A GCP service account with:
  - `roles/storage.admin` (or narrower bucket-level permissions)
  - `roles/bigquery.dataEditor` + `roles/bigquery.jobUser`
- dbt CLI (`pip install dbt-bigquery`)

## Quick Start

### 1. Clone and install

```bash
git clone <repo-url>
cd NYC_taxi_pipeline
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your GCP project ID, bucket name, and credentials path
```

### 3. Configure dbt

```bash
cp dbt/profiles.yml.example ~/.dbt/profiles.yml
# Edit ~/.dbt/profiles.yml — the env vars from .env are picked up automatically
```

### 4. Run the pipeline

```bash
# Full ELT pipeline (download → GCS → BigQuery)
make pipeline

# Then run dbt transformations
make dbt-all
```

Or step by step:

```bash
make extract      # Download Parquet files to data/tmp/
make load-gcs     # Upload to GCS raw zone
make load-bq      # Load into BigQuery raw tables
make dbt-deps     # Install dbt packages
make dbt-seed     # Load payment_types and rate_codes seed data
make dbt-run      # Build staging views + marts tables
make dbt-test     # Run all schema tests and custom tests
make dbt-docs     # Generate and serve dbt documentation
```

### 5. Configure what to ingest

Edit `config/config.yaml` to change which taxi types, years, and months to download:

```yaml
pipeline:
  taxi_types: [yellow, green]
  years: [2024]
  months: [1, 2, 3]
```

## Project Structure

```
NYC_taxi_pipeline/
├── config/
│   └── config.yaml          # Ingest scope (taxi types, years, months)
├── src/
│   ├── extract/
│   │   └── download_data.py # Download Parquet files from TLC website
│   ├── load/
│   │   ├── upload_to_gcs.py # Upload raw files to GCS
│   │   └── load_to_bigquery.py # Load GCS → BigQuery raw tables
│   └── utils/
│       ├── gcp_client.py    # GCS + BigQuery client factories
│       └── logger.py        # Structured logging
├── scripts/
│   └── run_pipeline.py      # CLI orchestrator (click)
├── dbt/
│   ├── dbt_project.yml
│   ├── packages.yml
│   ├── profiles.yml.example
│   ├── macros/
│   │   └── generate_schema_name.sql  # Routes models to correct BQ datasets
│   ├── seeds/
│   │   ├── payment_types.csv
│   │   └── rate_codes.csv
│   ├── models/
│   │   ├── staging/         # Views — clean and standardise raw data
│   │   │   ├── _sources.yml
│   │   │   ├── _schema.yml
│   │   │   ├── stg_yellow_taxi.sql
│   │   │   ├── stg_green_taxi.sql
│   │   │   └── stg_taxi_zones.sql
│   │   └── marts/           # Tables — analysis-ready fact + dimension models
│   │       ├── _schema.yml
│   │       ├── fact_trips.sql
│   │       ├── dim_zones.sql
│   │       └── dim_payment_types.sql
│   └── tests/
│       ├── assert_positive_trip_duration.sql
│       └── assert_fare_not_exceeds_total.sql
├── .env.example
├── .gitignore
├── Makefile
└── requirements.txt
```

## dbt Data Model

### Staging (views in `nyc_taxi_staging`)

| Model | Description |
|---|---|
| `stg_yellow_taxi` | Yellow taxi trips — columns cast, renamed to snake_case, invalid rows filtered |
| `stg_green_taxi` | Green taxi trips — same contract as yellow; `trip_type` added, `airport_fee` nulled |
| `stg_taxi_zones` | TLC zone lookup — LocationID → borough + zone name |

### Marts (tables in `nyc_taxi_marts`)

| Model | Description |
|---|---|
| `fact_trips` | All trips (yellow + green unioned). Surrogate key, derived duration + date fields. Partitioned by `pickup_date`, clustered on `taxi_type`, `payment_type_id`, `pickup_location_id` |
| `dim_zones` | Zone dimension with surrogate key |
| `dim_payment_types` | Payment type dimension from seed data |

## dbt Tests

- **Schema tests** (`not_null`, `unique`, `accepted_values`, `relationships`) on all key columns
- **Custom data tests** asserting business rules:
  - Every trip has a positive duration
  - Fare amount never exceeds total amount

## Reproducibility

All GCP configuration is injected via environment variables — no credentials are hardcoded. Any GCP account with the required IAM roles can run this pipeline against their own project.
