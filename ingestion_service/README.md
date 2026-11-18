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
$env:API_READ_TOKEN = "GENERATE_A_LONG_RANDOM_TOKEN"
$env:ALLOWED_ORIGINS = "https://YOUR-DASHBOARD.vercel.app"
uvicorn app:app --host 0.0.0.0 --port 8000
```

Keep the database URL and API token in the hosting provider's secret environment settings. Do not commit real credentials or place them in `NEXT_PUBLIC_*` variables.

## Import an authorised Rock Data Plus export

Rock Investment Bank publicly describes Rock Data Plus as a free financial-data repository and has stated that users can download data in Excel/CSV formats. This importer supports `.csv` and `.xlsx` files. A downloadable file is not, by itself, confirmation that the data may be republished on a public website. Confirm the relevant display, attribution and redistribution terms before importing anything for public display.

1. Sign in to Rock Data Plus and download the dataset you need in CSV or Excel format.
2. Keep the original export in private local storage. Do not commit the export to this public Git repository.
3. Inspect the column headings and choose the observation date, series/security identifier and numeric value columns. The exact headings can vary by dataset.
4. If the workbook is a wide table with several separate metric columns, reshape it into long format first: one row per observation, with one date, one series, one value and an optional unit.
5. Import only after the source owner has confirmed that the selected data may be displayed by this platform.

The preferred canonical columns are:

```csv
observed_at,series,value,unit,source_reference
```

A header-only template is available at `examples/observation_template.csv`. You can also map the actual column names in a CSV or Excel workbook. For example, the column names below are illustrative only; replace them with the exact headings in your export:

```powershell
$env:DATABASE_URL = "YOUR_POSTGRES_CONNECTION_STRING"

# CSV export
python import_csv.py --file ".\approved_export.csv" --dataset "NSE equities" --source "Rock Data Plus" --approval-reference "YOUR_APPROVAL_REFERENCE" --approved-for-display --date-column "Date" --series-column "Security" --value-column "Closing Price" --unit-column "Unit"

# Excel export (select the actual worksheet and column headings)
python import_csv.py --file ".\approved_export.xlsx" --sheet "Sheet1" --dataset "NSE equities" --source "Rock Data Plus" --approval-reference "YOUR_APPROVAL_REFERENCE" --approved-for-display --date-column "Date" --series-column "Security" --value-column "Closing Price" --unit-column "Unit"
```

Optional mappings:
- `--date-column`, `--series-column` and `--value-column` identify the required fields.
- `--unit-column` and `--source-reference-column` identify optional fields. Pass an empty string to skip either optional mapping.
- `--sheet` selects a worksheet in an `.xlsx` workbook; by default the active worksheet is used.

The importer validates dates and finite numeric values, records rejected rows, hashes observations to prevent duplicate imports, and writes an audit record for each run. The `--approved-for-display` flag is a deliberate safeguard; it does not obtain or verify permission on your behalf.

## API

- `GET /health`
- `GET /v1/overview`
- `GET /v1/series/{dataset}/{series_name}?limit=500`

The API is read-only. Restrict network access where possible and use TLS in production. Configure `ALLOWED_ORIGINS` to the dashboard origin.

## Important limitations

- The importer currently expects a long-format observation table. Do not assume every Rock Data Plus workbook has the same structure.
- If you provide a sample export with permission to process it, a dataset-specific normalizer can be added without guessing column meanings.
- Do not automate authenticated browser access or scrape the portal unless Rock Investment Bank has explicitly authorised that method.
