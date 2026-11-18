# Research data service

This service exposes a read-only API over approved research observations. Imports are performed by a controlled command-line job, not by an unauthenticated public upload endpoint.

## Required environment

- `DATABASE_URL`: PostgreSQL connection string.

## Prepare the database

Run `schema.sql` against the target PostgreSQL database using an administrator connection.

## Run the API

```powershell
cd ingestion_service
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL = "YOUR_POSTGRES_CONNECTION_STRING"
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Import an authorised CSV export

The CSV must contain `observed_at,series,value`; `unit` and `source_reference` are optional.

```powershell
$env:DATABASE_URL = "YOUR_POSTGRES_CONNECTION_STRING"
python import_csv.py --file ".\approved_export.csv" --dataset "NSE equities" --source "Rock Data Plus" --approval-reference "INTERNAL-LICENCE-REF" --approved-for-display
```

The approval flag is a deliberate safeguard. Only import records that the source owner permits this platform to display. Keep source exports and licensed raw data in private storage, never in the public Git repository.

## API

- `GET /health`
- `GET /v1/overview`
- `GET /v1/series/{dataset}/{series_name}?limit=500`

The API is read-only. Restrict network access where possible and use TLS in production. Configure `ALLOWED_ORIGINS` to the dashboard origin.
