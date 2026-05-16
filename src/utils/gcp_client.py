import os

from google.cloud import bigquery, storage
from google.oauth2 import service_account


def get_storage_client() -> storage.Client:
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    project_id = os.environ["GCP_PROJECT_ID"]

    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path
        )
        return storage.Client(project=project_id, credentials=credentials)

    # Fall back to application default credentials (e.g. gcloud auth)
    return storage.Client(project=project_id)


def get_bigquery_client() -> bigquery.Client:
    credentials_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    project_id = os.environ["GCP_PROJECT_ID"]

    if credentials_path:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(project=project_id, credentials=credentials)

    return bigquery.Client(project=project_id)
