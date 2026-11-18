"""Import an authorised Rock Data Plus (or other licensed) CSV export.

Required CSV columns: observed_at, series, value
Optional columns: unit, source_reference
The import refuses to run without an explicit approval reference.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
import psycopg

def parse_args():
    parser = argparse.ArgumentParser(description="Import an approved financial research CSV.")
    parser.add_argument("--file", required=True, type=Path)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--approval-reference", required=True, help="Internal permission/licence reference. Do not use credentials.")
    parser.add_argument("--approved-for-display", action="store_true", help="Confirm the source owner permits this dataset to be displayed.")
    return parser.parse_args()

def main():
    args = parse_args()
    if not args.approved_for_display:
        raise SystemExit("Import stopped: confirm display permission with --approved-for-display.")
    if not args.approval_reference.strip():
        raise SystemExit("Import stopped: an approval reference is required.")
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is not set.")
    if not args.file.is_file():
        raise SystemExit(f"CSV file not found: {args.file}")

    file_bytes = args.file.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    text = file_bytes.decode("utf-8-sig")
    reader = csv.DictReader(text.splitlines())
    required = {"observed_at", "series", "value"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise SystemExit("CSV must contain observed_at, series and value columns.")

    accepted = duplicates = rejected = 0
    with psycopg.connect(dsn) as conn:
        for line_number, row in enumerate(reader, start=2):
            try:
                observed = datetime.fromisoformat(row["observed_at"].strip().replace("Z", "+00:00"))
                if observed.tzinfo is None:
                    observed = observed.replace(tzinfo=timezone.utc)
                series = row["series"].strip()
                if not series:
                    raise ValueError("empty series")
                value = float(Decimal(row["value"].replace(",", "").strip()))
                if not math.isfinite(value):
                    raise ValueError("non-finite numeric value")
                raw = {key: (val or "").strip() for key, val in row.items()}
                canonical = json.dumps({
                    "dataset": args.dataset, "series": series,
                    "observed_at": observed.isoformat(), "value": value,
                    "unit": raw.get("unit", ""), "source": args.source,
                    "raw": raw
                }, sort_keys=True, separators=(",", ":"))
                digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                result = conn.execute("""
                    INSERT INTO market_observations
                    (dataset, series, observed_at, value, unit, source_name, source_reference, row_hash, raw_record)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (row_hash) DO NOTHING
                    RETURNING id
                """, (args.dataset, series, observed, value, raw.get("unit") or None,
                      args.source, raw.get("source_reference") or args.approval_reference,
                      digest, json.dumps(raw))).fetchone()
                if result:
                    accepted += 1
                else:
                    duplicates += 1
            except (ValueError, InvalidOperation, TypeError, KeyError):
                rejected += 1
                print(f"Rejected CSV row {line_number}: invalid date, series or numeric value.")

        conn.execute("""
            INSERT INTO ingestion_runs
            (dataset, source_name, source_reference, accepted_rows, duplicate_rows, rejected_rows, file_sha256)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (args.dataset, args.source, args.approval_reference, accepted, duplicates, rejected, file_hash))
    print(f"Import complete — accepted: {accepted}; duplicates: {duplicates}; rejected: {rejected}")

if __name__ == "__main__":
    main()
