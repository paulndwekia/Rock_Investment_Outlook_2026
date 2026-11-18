"""Import an approved Rock Data Plus or other licensed CSV/XLSX export.

Canonical fields: observed_at, series, value
Optional fields: unit, source_reference

Export layouts vary by dataset. Use the column-mapping options rather than
assuming that every Rock Data Plus workbook has the same column names.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

import psycopg
from openpyxl import load_workbook


def parse_args():
    parser = argparse.ArgumentParser(description="Import an approved financial research CSV or XLSX export.")
    parser.add_argument("--file", required=True, type=Path, help="CSV or .xlsx file downloaded from an authorised source.")
    parser.add_argument("--dataset", required=True, help="Dataset label, e.g. NSE equities.")
    parser.add_argument("--source", required=True, help="Source label, e.g. Rock Data Plus.")
    parser.add_argument("--approval-reference", required=True, help="Internal permission/licence reference. Never put credentials here.")
    parser.add_argument("--approved-for-display", action="store_true", help="Confirm the source owner permits this dataset to be displayed.")
    parser.add_argument("--sheet", help="Worksheet name for an .xlsx workbook. Defaults to the active sheet.")
    parser.add_argument("--date-column", default="observed_at", help="Column containing the observation date/time.")
    parser.add_argument("--series-column", default="series", help="Column containing the security or indicator name.")
    parser.add_argument("--value-column", default="value", help="Column containing the numeric observation.")
    parser.add_argument("--unit-column", default="unit", help="Optional unit column; pass an empty value to skip it.")
    parser.add_argument("--source-reference-column", default="source_reference", help="Optional source reference column; pass an empty value to skip it.")
    return parser.parse_args()


def json_safe(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def open_source_rows(path: Path, sheet_name: str | None):
    """Return the headers and a streaming iterator of (line_number, row_dict)."""
    suffix = path.suffix.casefold()
    if suffix == ".csv":
        if sheet_name:
            raise ValueError("--sheet can only be used with an .xlsx workbook.")
        stream = path.open("r", encoding="utf-8-sig", newline="")
        reader = csv.reader(stream)
        headers = next(reader, None)
        if not headers:
            stream.close()
            raise ValueError("The CSV file is empty or has no header row.")

        def csv_rows():
            try:
                for line_number, values in enumerate(reader, start=2):
                    yield line_number, {
                        headers[index]: values[index] if index < len(values) else None
                        for index in range(len(headers))
                    }
            finally:
                stream.close()

        return headers, csv_rows()

    if suffix == ".xlsx":
        workbook = load_workbook(path, read_only=True, data_only=True)
        try:
            worksheet = workbook[sheet_name] if sheet_name else workbook.active
        except KeyError as exc:
            workbook.close()
            raise ValueError(f"Worksheet not found: {sheet_name}") from exc

        rows = worksheet.iter_rows(values_only=True)
        header_values = next(rows, None)
        if not header_values:
            workbook.close()
            raise ValueError("The selected worksheet is empty or has no header row.")
        headers = [str(value).strip() if value is not None else "" for value in header_values]

        def workbook_rows():
            try:
                for line_number, values in enumerate(rows, start=2):
                    yield line_number, {
                        headers[index]: values[index] if index < len(values) else None
                        for index in range(len(headers))
                        if headers[index]
                    }
            finally:
                workbook.close()

        return headers, workbook_rows()

    raise ValueError("Unsupported file type. Use .csv or .xlsx.")


def resolve_column(headers, requested_name: str, required: bool = True):
    if not requested_name.strip():
        if required:
            raise ValueError("A required column mapping cannot be blank.")
        return None

    matches = [
        header for header in headers
        if header is not None and str(header).strip().casefold() == requested_name.strip().casefold()
    ]
    if len(matches) > 1:
        raise ValueError(f"Column name is ambiguous in the source file: {requested_name}")
    if not matches:
        if required:
            available = ", ".join(str(item) for item in headers if item is not None and str(item).strip())
            raise ValueError(f"Required column '{requested_name}' was not found. Available columns: {available}")
        return None
    return matches[0]


def parse_observed_at(raw_value):
    if isinstance(raw_value, datetime):
        observed = raw_value
    elif isinstance(raw_value, date):
        observed = datetime.combine(raw_value, time.min)
    else:
        text = str(raw_value).strip()
        observed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    return observed


def parse_numeric_value(raw_value):
    if raw_value is None or isinstance(raw_value, bool):
        raise ValueError("missing or invalid numeric value")
    text = str(raw_value).replace(",", "").strip()
    value = float(Decimal(text))
    if not math.isfinite(value):
        raise ValueError("non-finite numeric value")
    return value


def main():
    args = parse_args()
    if not args.approved_for_display:
        raise SystemExit("Import stopped: confirm display permission with --approved-for-display.")
    if not args.approval_reference.strip():
        raise SystemExit("Import stopped: an approval reference is required.")
    if not args.dataset.strip() or not args.source.strip():
        raise SystemExit("Dataset and source labels cannot be blank.")

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set.")
    if not args.file.is_file():
        raise SystemExit(f"Source file not found: {args.file}")

    file_bytes = args.file.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    try:
        headers, rows = open_source_rows(args.file, args.sheet)
        date_column = resolve_column(headers, args.date_column)
        series_column = resolve_column(headers, args.series_column)
        value_column = resolve_column(headers, args.value_column)
        unit_column = resolve_column(headers, args.unit_column, required=False)
        source_reference_column = resolve_column(headers, args.source_reference_column, required=False)
    except (ValueError, OSError) as exc:
        raise SystemExit(f"Import stopped: {exc}") from exc

    accepted = duplicates = rejected = 0
    with psycopg.connect(dsn) as conn:
        for line_number, row in rows:
            try:
                observed = parse_observed_at(row.get(date_column))
                series = str(row.get(series_column) or "").strip()
                if not series:
                    raise ValueError("empty series")
                value = parse_numeric_value(row.get(value_column))
                unit_raw = row.get(unit_column) if unit_column else None
                unit = str(unit_raw).strip() if unit_raw is not None and str(unit_raw).strip() else None
                reference_raw = row.get(source_reference_column) if source_reference_column else None
                source_reference = str(reference_raw).strip() if reference_raw is not None and str(reference_raw).strip() else args.approval_reference.strip()
                raw = {str(key): json_safe(item) for key, item in row.items()}

                canonical = json.dumps({
                    "dataset": args.dataset.strip(),
                    "series": series,
                    "observed_at": observed.isoformat(),
                    "value": value,
                    "unit": unit or "",
                    "source": args.source.strip(),
                    "raw": raw
                }, sort_keys=True, separators=(",", ":"))
                digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

                result = conn.execute("""
                    INSERT INTO market_observations
                    (dataset, series, observed_at, value, unit, source_name, source_reference, row_hash, raw_record)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (row_hash) DO NOTHING
                    RETURNING id
                """, (
                    args.dataset.strip(), series, observed, value, unit,
                    args.source.strip(), source_reference, digest, json.dumps(raw)
                )).fetchone()

                if result:
                    accepted += 1
                else:
                    duplicates += 1
            except (ValueError, InvalidOperation, TypeError, KeyError, OverflowError):
                rejected += 1
                print(f"Rejected source row {line_number}: invalid date, series or numeric value.")

        conn.execute("""
            INSERT INTO ingestion_runs
            (dataset, source_name, source_reference, accepted_rows, duplicate_rows, rejected_rows, file_sha256)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            args.dataset.strip(), args.source.strip(), args.approval_reference.strip(),
            accepted, duplicates, rejected, file_hash
        ))

    print(f"Import complete — accepted: {accepted}; duplicates: {duplicates}; rejected: {rejected}")


if __name__ == "__main__":
    main()
