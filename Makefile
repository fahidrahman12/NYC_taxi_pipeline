.PHONY: install extract load-gcs load-bq pipeline \
        dbt-deps dbt-seed dbt-run dbt-test dbt-docs dbt-all \
        clean help

# ── Python env ────────────────────────────────────────────────────────────────
install:
	pip install -r requirements.txt

# ── ELT steps ─────────────────────────────────────────────────────────────────
extract:
	python scripts/run_pipeline.py --step extract

load-gcs:
	python scripts/run_pipeline.py --step load-gcs

load-bq:
	python scripts/run_pipeline.py --step load-bq

pipeline:
	python scripts/run_pipeline.py --step all

# ── dbt ───────────────────────────────────────────────────────────────────────
dbt-deps:
	cd dbt && dbt deps

dbt-seed:
	cd dbt && dbt seed

dbt-run:
	cd dbt && dbt run

dbt-test:
	cd dbt && dbt test

dbt-docs:
	cd dbt && dbt docs generate && dbt docs serve

dbt-all: dbt-deps dbt-seed dbt-run dbt-test

# ── Full end-to-end ───────────────────────────────────────────────────────────
all: pipeline dbt-all

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean:
	rm -rf data/tmp dbt/target dbt/logs dbt/dbt_packages

# ── Help ──────────────────────────────────────────────────────────────────────
help:
	@echo "Available targets:"
	@echo "  install     Install Python dependencies"
	@echo "  extract     Download Parquet files from TLC website"
	@echo "  load-gcs    Upload local files to GCS raw zone"
	@echo "  load-bq     Load GCS files into BigQuery raw dataset"
	@echo "  pipeline    Run extract + load-gcs + load-bq"
	@echo "  dbt-deps    Install dbt packages"
	@echo "  dbt-seed    Load seed CSV files into BigQuery"
	@echo "  dbt-run     Run all dbt models"
	@echo "  dbt-test    Run all dbt tests"
	@echo "  dbt-docs    Generate and serve dbt documentation"
	@echo "  dbt-all     deps + seed + run + test"
	@echo "  all         Full pipeline end-to-end"
	@echo "  clean       Remove local temp files and dbt artifacts"
