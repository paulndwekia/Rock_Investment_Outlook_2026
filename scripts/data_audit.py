from pathlib import Path
import sqlite3
import pandas as pd
import json

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"

DB = (
    PROJECT /
    "database" /
    "rock_investment_intelligence.db"
)

CANONICAL = (
    PROJECT /
    "data" /
    "canonical"
)

OUT = (
    PROJECT /
    "analysis"
)

OUT.mkdir(parents=True, exist_ok=True)

print("\n" + "=" * 80)
print("ROCK DATA INTEGRITY AUDIT")
print("=" * 80)

conn = sqlite3.connect(DB)

# ------------------------------------------------------------
# Database dataset summary
# ------------------------------------------------------------

db_summary = pd.read_sql_query(
    """
    SELECT
        dataset_name,
        COUNT(*) AS database_rows,
        MIN(observed_date) AS database_first_date,
        MAX(observed_date) AS database_last_date
    FROM rock_observations
    GROUP BY dataset_name
    ORDER BY dataset_name
    """,
    conn
)

print("\nDATABASE SUMMARY")
print("-" * 80)
print(db_summary.to_string(index=False))

# ------------------------------------------------------------
# Source file information
# ------------------------------------------------------------

sources = pd.read_sql_query(
    """
    SELECT
        dataset_name,
        file_name,
        file_size_bytes,
        imported_at
    FROM source_files
    ORDER BY dataset_name
    """,
    conn
)

print("\nSOURCE FILES")
print("-" * 80)
print(sources.to_string(index=False))

# ------------------------------------------------------------
# Database duplicate check
# ------------------------------------------------------------

duplicates = pd.read_sql_query(
    """
    SELECT
        dataset_name,
        COUNT(*) AS total_rows,
        COUNT(DISTINCT row_hash) AS unique_row_hashes
    FROM rock_observations
    GROUP BY dataset_name
    """,
    conn
)

duplicates["duplicate_rows"] = (
    duplicates["total_rows"]
    -
    duplicates["unique_row_hashes"]
)

print("\nDATABASE DUPLICATE CHECK")
print("-" * 80)
print(duplicates.to_string(index=False))

# ------------------------------------------------------------
# Canonical file inspection
# ------------------------------------------------------------

file_results = []

for file in sorted(CANONICAL.iterdir()):

    if file.suffix.lower() not in [
        ".xlsx",
        ".xls",
        ".csv"
    ]:
        continue

    print("\n" + "-" * 80)
    print("FILE:", file.name)

    try:

        if file.suffix.lower() == ".csv":

            data = pd.read_csv(
                file,
                low_memory=False
            )

            sheets = {
                "CSV": data
            }

        else:

            excel = pd.ExcelFile(file)

            print(
                "Sheets:",
                excel.sheet_names
            )

            sheets = {}

            for sheet in excel.sheet_names:

                try:

                    sheets[sheet] = pd.read_excel(
                        file,
                        sheet_name=sheet
                    )

                except Exception as exc:

                    print(
                        f"  Sheet {sheet} ERROR: {exc}"
                    )

        total_rows = 0

        for sheet_name, data in sheets.items():

            total_rows += len(data)

            print(
                f"\n  SHEET: {sheet_name}"
            )

            print(
                f"  Rows: {len(data):,}"
            )

            print(
                f"  Columns: {len(data.columns)}"
            )

            print(
                "  Columns:"
            )

            for column in data.columns:
                print(
                    f"     - {column}"
                )

            # Identify possible date-like columns.
            possible_dates = []

            for column in data.columns:

                name = str(column).lower()

                if any(
                    keyword in name
                    for keyword in [
                        "date",
                        "time",
                        "period",
                        "month",
                        "year"
                    ]
                ):

                    converted = pd.to_datetime(
                        data[column],
                        errors="coerce"
                    )

                    valid = converted.dropna()

                    if len(valid):

                        possible_dates.append({
                            "column": str(column),
                            "valid_values": len(valid),
                            "date_min": str(valid.min()),
                            "date_max": str(valid.max())
                        })

            if possible_dates:

                print(
                    "  Date candidates:"
                )

                for item in possible_dates:

                    print(
                        f"     {item['column']} | "
                        f"{item['date_min']} → "
                        f"{item['date_max']} | "
                        f"{item['valid_values']:,} valid"
                    )

            else:

                print(
                    "  Date candidates: NONE DETECTED"
                )

            file_results.append({
                "file": file.name,
                "sheet": sheet_name,
                "rows": len(data),
                "columns": len(data.columns),
                "column_names": " | ".join(
                    map(str, data.columns)
                ),
                "date_candidates": json.dumps(
                    possible_dates
                )
            })

        print(
            f"\n  TOTAL FILE ROWS: {total_rows:,}"
        )

    except Exception as exc:

        print(
            "  FILE ERROR:",
            exc
        )

# ------------------------------------------------------------
# Compare database with source files
# ------------------------------------------------------------

file_summary = pd.DataFrame(
    file_results
)

file_summary.to_csv(
    OUT /
    "rock_source_audit.csv",
    index=False
)

db_summary.to_csv(
    OUT /
    "rock_database_audit.csv",
    index=False
)

duplicates.to_csv(
    OUT /
    "rock_duplicate_audit.csv",
    index=False
)

# ------------------------------------------------------------
# Final audit report
# ------------------------------------------------------------

audit = {
    "generated": pd.Timestamp.now().isoformat(),
    "database_total_observations": int(
        db_summary["database_rows"].sum()
    ),
    "database_dataset_count": int(
        len(db_summary)
    ),
    "source_file_count": int(
        len(sources)
    ),
    "datasets_without_database_dates": (
        db_summary[
            db_summary["database_first_date"].isna()
        ]["dataset_name"]
        .tolist()
    ),
    "datasets_with_possible_duplicate_rows": (
        duplicates[
            duplicates["duplicate_rows"] > 0
        ]["dataset_name"]
        .tolist()
    ),
    "source_audit_file": str(
        OUT / "rock_source_audit.csv"
    )
}

(
    OUT /
    "rock_data_integrity_audit.json"
).write_text(
    json.dumps(
        audit,
        indent=2
    ),
    encoding="utf-8"
)

print("\n" + "=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)

print(
    "\nSaved:"
)

print(
    OUT /
    "rock_source_audit.csv"
)

print(
    OUT /
    "rock_database_audit.csv"
)

print(
    OUT /
    "rock_duplicate_audit.csv"
)

print(
    OUT /
    "rock_data_integrity_audit.json"
)

print("\nIMPORTANT:")
print(
    "Do NOT build the quantitative engine until we "
    "review this audit."
)

conn.close()
