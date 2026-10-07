from pathlib import Path
from datetime import datetime
import hashlib
import json
import re
import sqlite3
import shutil
import traceback

import pandas as pd

# ============================================================
# ROCK INVESTMENT INTELLIGENCE
# PERMANENT MASTER DATABASE BUILDER
# ============================================================

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"

CANONICAL = PROJECT / "data" / "canonical"
ARCHIVE = PROJECT / "data" / "archive"
DATABASE = PROJECT / "database"
ANALYSIS = PROJECT / "analysis"
LOGS = PROJECT / "logs"

for folder in [
    CANONICAL,
    ARCHIVE,
    DATABASE,
    ANALYSIS,
    LOGS
]:
    folder.mkdir(parents=True, exist_ok=True)

DB_PATH = DATABASE / "rock_investment_intelligence.db"
LOG_PATH = LOGS / "database_build.log"

# ------------------------------------------------------------
# Logging
# ------------------------------------------------------------

def log(message):
    timestamp = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    line = f"{timestamp} | {message}"

    print(line)

    with LOG_PATH.open(
        "a",
        encoding="utf-8"
    ) as f:
        f.write(line + "\n")


# ------------------------------------------------------------
# Naming
# ------------------------------------------------------------

def clean_name(value):
    value = str(value).strip().lower()
    value = re.sub(
        r"[^a-zA-Z0-9_]+",
        "_",
        value
    )
    value = re.sub(
        r"_+",
        "_",
        value
    )
    return value.strip("_")[:100]


def unique_columns(columns):
    seen = {}
    result = []

    for col in columns:

        base = clean_name(col)

        if not base:
            base = "column"

        if base not in seen:
            seen[base] = 0
            result.append(base)

        else:
            seen[base] += 1
            result.append(
                f"{base}_{seen[base]}"
            )

    return result


# ------------------------------------------------------------
# File hashing
# ------------------------------------------------------------

def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b""
        ):
            h.update(chunk)

    return h.hexdigest()


# ------------------------------------------------------------
# Read files
# ------------------------------------------------------------

def read_csv_safely(path):

    attempts = [
        {"encoding": "utf-8-sig"},
        {"encoding": "utf-8"},
        {"encoding": "latin1"},
    ]

    errors = []

    for options in attempts:

        try:

            df = pd.read_csv(
                path,
                **options
            )

            return {
                "Data": df
            }

        except Exception as exc:

            errors.append(
                str(exc)
            )

    raise ValueError(
        "CSV could not be read: "
        + " | ".join(errors)
    )


def read_excel_safely(path):

    workbook = pd.ExcelFile(path)

    sheets = {}

    for sheet in workbook.sheet_names:

        try:

            df = pd.read_excel(
                path,
                sheet_name=sheet
            )

            sheets[str(sheet)] = df

        except Exception as exc:

            log(
                f"WARNING | Could not read "
                f"{path.name} / {sheet}: {exc}"
            )

    return sheets


def read_file(path):

    suffix = path.suffix.lower()

    if suffix == ".csv":
        return read_csv_safely(path)

    if suffix in [".xlsx", ".xls"]:
        return read_excel_safely(path)

    raise ValueError(
        f"Unsupported file type: {suffix}"
    )


# ------------------------------------------------------------
# Detect date column
# ------------------------------------------------------------

def find_date_column(df):

    candidates = []

    for column in df.columns:

        name = str(column).lower()

        score = 0

        if "date" in name:
            score += 5

        if "period" in name:
            score += 4

        if "time" in name:
            score += 2

        if "year" in name:
            score += 1

        if score:
            candidates.append(
                (score, column)
            )

    if not candidates:
        return None

    candidates.sort(
        reverse=True
    )

    return candidates[0][1]


# ------------------------------------------------------------
# Normalize values
# ------------------------------------------------------------

def normalize_dataframe(df):

    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()

    # Standardize column names.
    df.columns = unique_columns(
        df.columns
    )

    # Remove completely empty rows/columns.
    df = df.dropna(
        how="all"
    )

    df = df.dropna(
        axis=1,
        how="all"
    )

    # Remove common export artefacts.
    for column in df.columns:

        if df[column].dtype == "object":

            df[column] = (
                df[column]
                .astype(str)
                .str.strip()
                .replace({
                    "nan": pd.NA,
                    "None": pd.NA,
                    "NaN": pd.NA,
                    "-": pd.NA,
                    "—": pd.NA,
                })
            )

    # Detect date.
    date_column = find_date_column(
        df
    )

    if date_column:

        converted = pd.to_datetime(
            df[date_column],
            errors="coerce"
        )

        # Only replace if a meaningful number of
        # values successfully parse.
        if converted.notna().sum() > 0:
            df[date_column] = converted

    # Try numeric conversion where appropriate.
    for column in df.columns:

        if column == date_column:
            continue

        if df[column].dtype != "object":
            continue

        original = df[column]

        candidate = (
            original
            .astype(str)
            .str.replace(",", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.replace("KES", "", regex=False)
            .str.replace("KSh", "", regex=False)
            .str.strip()
        )

        numeric = pd.to_numeric(
            candidate,
            errors="coerce"
        )

        valid_original = (
            original.notna()
        ).sum()

        valid_numeric = (
            numeric.notna()
        ).sum()

        if (
            valid_original > 0
            and
            valid_numeric / valid_original >= 0.80
        ):
            df[column] = numeric

    # Exact duplicate rows.
    df = df.drop_duplicates()

    return df.reset_index(
        drop=True
    )


# ------------------------------------------------------------
# Row hashing
# ------------------------------------------------------------

def row_hash(
    dataset,
    source_file,
    values
):

    payload = {
        "dataset": dataset,
        "source_file": source_file,
        "values": values
    }

    raw = json.dumps(
        payload,
        sort_keys=True,
        default=str
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


# ------------------------------------------------------------
# Database initialization
# ------------------------------------------------------------

def init_database(conn):

    conn.executescript("""
    PRAGMA journal_mode=WAL;

    CREATE TABLE IF NOT EXISTS datasets (
        dataset_id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_name TEXT NOT NULL UNIQUE,
        source TEXT NOT NULL,
        description TEXT,
        latest_imported_at TEXT,
        row_count INTEGER DEFAULT 0,
        column_count INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS source_files (
        source_file_id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_name TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_hash TEXT NOT NULL UNIQUE,
        file_size_bytes INTEGER,
        imported_at TEXT NOT NULL,
        archived_path TEXT,
        status TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dataset_sheets (
        sheet_id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_name TEXT NOT NULL,
        sheet_name TEXT,
        row_count INTEGER,
        column_count INTEGER,
        date_column TEXT,
        date_min TEXT,
        date_max TEXT,
        imported_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS rock_observations (
        observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
        dataset_name TEXT NOT NULL,
        sheet_name TEXT,
        source_file TEXT NOT NULL,
        source_hash TEXT NOT NULL,
        row_hash TEXT NOT NULL UNIQUE,
        observed_date TEXT,
        row_json TEXT NOT NULL,
        imported_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_rock_obs_dataset
        ON rock_observations(dataset_name);

    CREATE INDEX IF NOT EXISTS idx_rock_obs_date
        ON rock_observations(observed_date);

    CREATE TABLE IF NOT EXISTS data_dictionary (
        dataset_name TEXT,
        column_name TEXT,
        dtype TEXT,
        non_null_count INTEGER,
        example_value TEXT,
        PRIMARY KEY(dataset_name, column_name)
    );

    CREATE TABLE IF NOT EXISTS build_history (
        build_id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        finished_at TEXT NOT NULL,
        files_seen INTEGER,
        files_imported INTEGER,
        rows_seen INTEGER,
        rows_added INTEGER,
        rows_skipped INTEGER,
        status TEXT
    );
    """)

    conn.commit()


# ------------------------------------------------------------
# Create dataset-specific SQL table
# ------------------------------------------------------------

def write_dataset_table(
    conn,
    table_name,
    df,
    source_file,
    source_hash,
    imported_at
):

    # Never allow dangerous SQL names.
    table_name = (
        "rock_"
        + clean_name(table_name)
    )

    work = df.copy()

    # Add provenance columns.
    work["_source_file"] = source_file
    work["_source_hash"] = source_hash
    work["_imported_at"] = imported_at

    # SQLite/Pandas table.
    work.to_sql(
        table_name,
        conn,
        if_exists="append",
        index=False
    )

    return table_name


# ------------------------------------------------------------
# Update metadata
# ------------------------------------------------------------

def update_metadata(
    conn,
    dataset,
    sheet_name,
    df,
    source_file,
    source_hash,
    imported_at
):

    date_column = find_date_column(
        df
    )

    date_min = None
    date_max = None

    if date_column:

        dates = pd.to_datetime(
            df[date_column],
            errors="coerce"
        ).dropna()

        if not dates.empty:

            date_min = str(
                dates.min().date()
            )

            date_max = str(
                dates.max().date()
            )

    conn.execute(
        """
        INSERT OR REPLACE INTO dataset_sheets
        (
            dataset_name,
            sheet_name,
            row_count,
            column_count,
            date_column,
            date_min,
            date_max,
            imported_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dataset,
            sheet_name,
            len(df),
            len(df.columns),
            str(date_column)
            if date_column else None,
            date_min,
            date_max,
            imported_at
        )
    )

    for column in df.columns:

        non_null = int(
            df[column].notna().sum()
        )

        example = None

        values = (
            df[column]
            .dropna()
            .astype(str)
        )

        if len(values):
            example = values.iloc[0][:200]

        conn.execute(
            """
            INSERT OR REPLACE INTO data_dictionary
            (
                dataset_name,
                column_name,
                dtype,
                non_null_count,
                example_value
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                dataset,
                str(column),
                str(df[column].dtype),
                non_null,
                example
            )
        )


# ------------------------------------------------------------
# Process one sheet
# ------------------------------------------------------------

def process_sheet(
    conn,
    dataset,
    sheet_name,
    df,
    source_file,
    source_hash,
    imported_at
):

    df = normalize_dataframe(
        df
    )

    if df.empty:

        log(
            f"SKIP | {dataset} / "
            f"{sheet_name} is empty"
        )

        return 0, 0

    # Dataset-specific table.
    table_name = (
        dataset
        if sheet_name.lower() == "data"
        else f"{dataset}_{sheet_name}"
    )

    table_name = clean_name(
        table_name
    )

    # Add row metadata.
    rows_seen = len(df)
    rows_added = 0

    update_metadata(
        conn,
        dataset,
        sheet_name,
        df,
        source_file,
        source_hash,
        imported_at
    )

    # Insert into generic observations.
    for record in df.to_dict(
        orient="records"
    ):

        cleaned = {}

        for key, value in record.items():

            if pd.isna(value):
                cleaned[str(key)] = None
            elif hasattr(value, "isoformat"):
                cleaned[str(key)] = value.isoformat()
            else:
                cleaned[str(key)] = value

        observed_date = None

        date_column = find_date_column(
            df
        )

        if date_column:

            value = cleaned.get(
                str(date_column)
            )

            if value:
                observed_date = str(
                    value
                )

        rhash = row_hash(
            dataset,
            source_file + "|" + sheet_name,
            cleaned
        )

        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO rock_observations
            (
                dataset_name,
                sheet_name,
                source_file,
                source_hash,
                row_hash,
                observed_date,
                row_json,
                imported_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dataset,
                sheet_name,
                source_file,
                source_hash,
                rhash,
                observed_date,
                json.dumps(
                    cleaned,
                    default=str
                ),
                imported_at
            )
        )

        if cursor.rowcount > 0:
            rows_added += 1

    # Also create/queryable dataset table.
    # We don't rebuild it when an identical file has already
    # been imported; source-level deduplication handles that.
    try:

        write_dataset_table(
            conn,
            table_name,
            df,
            source_file,
            source_hash,
            imported_at
        )

    except Exception as exc:

        log(
            f"WARNING | Could not create "
            f"dataset table {table_name}: {exc}"
        )

    return rows_seen, rows_added


# ------------------------------------------------------------
# Process source file
# ------------------------------------------------------------

def process_file(
    conn,
    path,
    imported_at
):

    dataset = clean_name(
        path.stem
    )

    source_file = path.name
    source_hash = sha256(path)

    # Don't import the exact same file twice.
    existing = conn.execute(
        """
        SELECT source_file_id
        FROM source_files
        WHERE file_hash = ?
        """,
        (source_hash,)
    ).fetchone()

    if existing:

        log(
            f"SKIP | Already imported: "
            f"{source_file}"
        )

        return 0, 0, False

    log(
        f"IMPORT | {source_file}"
    )

    sheets = read_file(
        path
    )

    total_seen = 0
    total_added = 0

    for sheet_name, df in sheets.items():

        seen, added = process_sheet(
            conn,
            dataset,
            sheet_name,
            df,
            source_file,
            source_hash,
            imported_at
        )

        total_seen += seen
        total_added += added

    # Dataset metadata.
    total_rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM rock_observations
        WHERE dataset_name = ?
        """,
        (dataset,)
    ).fetchone()[0]

    conn.execute(
        """
        INSERT INTO datasets
        (
            dataset_name,
            source,
            description,
            latest_imported_at,
            row_count,
            column_count
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(dataset_name)
        DO UPDATE SET
            latest_imported_at = excluded.latest_imported_at,
            row_count = excluded.row_count
        """,
        (
            dataset,
            "Rock Data Plus",
            f"Canonical Rock Data Plus dataset: {dataset}",
            imported_at,
            total_rows,
            0
        )
    )

    archive_destination = (
        ARCHIVE /
        f"{datetime.now():%Y%m%d_%H%M%S}_"
        f"{source_file}"
    )

    try:

        shutil.copy2(
            path,
            archive_destination
        )

    except Exception as exc:

        log(
            f"WARNING | Archive failed for "
            f"{source_file}: {exc}"
        )

    conn.execute(
        """
        INSERT INTO source_files
        (
            dataset_name,
            file_name,
            file_hash,
            file_size_bytes,
            imported_at,
            archived_path,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dataset,
            source_file,
            source_hash,
            path.stat().st_size,
            imported_at,
            str(archive_destination),
            "imported"
        )
    )

    conn.commit()

    log(
        f"DONE | {source_file} | "
        f"rows seen={total_seen:,} | "
        f"new rows={total_added:,}"
    )

    return total_seen, total_added, True


# ------------------------------------------------------------
# Build analytics-ready summary views
# ------------------------------------------------------------

def create_views(conn):

    conn.executescript("""
    DROP VIEW IF EXISTS v_rock_database_summary;

    CREATE VIEW v_rock_database_summary AS
    SELECT
        dataset_name,
        COUNT(*) AS observations,
        MIN(observed_date) AS earliest_observation,
        MAX(observed_date) AS latest_observation
    FROM rock_observations
    GROUP BY dataset_name;

    DROP VIEW IF EXISTS v_rock_source_summary;

    CREATE VIEW v_rock_source_summary AS
    SELECT
        dataset_name,
        COUNT(*) AS source_files,
        MAX(imported_at) AS latest_import
    FROM source_files
    GROUP BY dataset_name;
    """)

    conn.commit()


# ------------------------------------------------------------
# Export data catalogue
# ------------------------------------------------------------

def export_catalogue(conn):

    summary = pd.read_sql_query(
        """
        SELECT *
        FROM v_rock_database_summary
        ORDER BY dataset_name
        """,
        conn
    )

    summary.to_csv(
        ANALYSIS /
        "rock_database_summary.csv",
        index=False
    )

    dictionary = pd.read_sql_query(
        """
        SELECT *
        FROM data_dictionary
        ORDER BY dataset_name, column_name
        """,
        conn
    )

    dictionary.to_csv(
        ANALYSIS /
        "rock_data_dictionary.csv",
        index=False
    )

    sources = pd.read_sql_query(
        """
        SELECT *
        FROM source_files
        ORDER BY imported_at
        """,
        conn
    )

    sources.to_csv(
        ANALYSIS /
        "rock_source_register.csv",
        index=False
    )

    return summary


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():

    started = datetime.now()

    log("=" * 70)
    log("ROCK INVESTMENT INTELLIGENCE — DATABASE BUILD")
    log("=" * 70)

    if not CANONICAL.exists():

        raise FileNotFoundError(
            f"Canonical folder not found: {CANONICAL}"
        )

    files = sorted(
        [
            p
            for p in CANONICAL.iterdir()
            if p.is_file()
            and p.suffix.lower()
            in [".xlsx", ".xls", ".csv"]
        ]
    )

    if not files:

        raise FileNotFoundError(
            "No canonical Rock datasets found."
        )

    log(
        f"Canonical input files: {len(files)}"
    )

    conn = sqlite3.connect(
        DB_PATH
    )

    init_database(
        conn
    )

    total_seen = 0
    total_added = 0
    imported = 0

    for path in files:

        try:

            seen, added, did_import = process_file(
                conn,
                path,
                datetime.now().isoformat()
            )

            total_seen += seen
            total_added += added

            if did_import:
                imported += 1

        except Exception as exc:

            log(
                f"ERROR | {path.name}: {exc}"
            )

            log(
                traceback.format_exc()
            )

    create_views(
        conn
    )

    summary = export_catalogue(
        conn
    )

    finished = datetime.now()

    # Overall database statistics.
    observation_count = conn.execute(
        "SELECT COUNT(*) FROM rock_observations"
    ).fetchone()[0]

    dataset_count = conn.execute(
        "SELECT COUNT(DISTINCT dataset_name) "
        "FROM rock_observations"
    ).fetchone()[0]

    source_count = conn.execute(
        "SELECT COUNT(*) FROM source_files"
    ).fetchone()[0]

    conn.execute(
        """
        INSERT INTO build_history
        (
            started_at,
            finished_at,
            files_seen,
            files_imported,
            rows_seen,
            rows_added,
            rows_skipped,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            started.isoformat(),
            finished.isoformat(),
            len(files),
            imported,
            total_seen,
            total_added,
            total_seen - total_added,
            "completed"
        )
    )

    conn.commit()
    conn.close()

    # Write build manifest.
    manifest = {
        "project": "Rock Investment Intelligence",
        "primary_source": "Rock Data Plus",
        "external_market_data_used": False,
        "database": str(DB_PATH),
        "build_started": started.isoformat(),
        "build_finished": finished.isoformat(),
        "canonical_files_seen": len(files),
        "files_imported_this_run": imported,
        "rows_seen_this_run": total_seen,
        "new_rows_added_this_run": total_added,
        "total_database_observations": observation_count,
        "total_datasets": dataset_count,
        "source_files_registered": source_count
    }

    (
        ANALYSIS /
        "rock_database_manifest.json"
    ).write_text(
        json.dumps(
            manifest,
            indent=2
        ),
        encoding="utf-8"
    )

    log("")
    log("=" * 70)
    log("DATABASE BUILD COMPLETE")
    log("=" * 70)

    log(
        f"Datasets in database: {dataset_count:,}"
    )

    log(
        f"Total observations: {observation_count:,}"
    )

    log(
        f"Source files registered: {source_count:,}"
    )

    log(
        f"New observations added this run: "
        f"{total_added:,}"
    )

    log("")
    log(
        f"Database: {DB_PATH}"
    )

    log(
        f"Catalogue: "
        f"{ANALYSIS / 'rock_database_summary.csv'}"
    )

    log(
        f"Dictionary: "
        f"{ANALYSIS / 'rock_data_dictionary.csv'}"
    )

    log(
        f"Source register: "
        f"{ANALYSIS / 'rock_source_register.csv'}"
    )

    log(
        f"Manifest: "
        f"{ANALYSIS / 'rock_database_manifest.json'}"
    )

    log("")
    log(
        "The database is now ready to become the "
        "single data source for the website and "
        "quantitative engine."
    )


if __name__ == "__main__":
    main()
