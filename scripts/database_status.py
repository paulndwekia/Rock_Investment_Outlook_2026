import sqlite3
from pathlib import Path
import pandas as pd

db = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026" / "database" / "rock_investment_intelligence.db"

conn = sqlite3.connect(db)

print("\nROCK DATABASE STATUS")
print("=" * 70)

datasets = pd.read_sql_query(
    """
    SELECT
        dataset_name,
        COUNT(*) AS observations,
        MIN(observed_date) AS first_date,
        MAX(observed_date) AS last_date
    FROM rock_observations
    GROUP BY dataset_name
    ORDER BY dataset_name
    """,
    conn
)

print(datasets.to_string(index=False))

print("\n" + "=" * 70)

total = conn.execute(
    "SELECT COUNT(*) FROM rock_observations"
).fetchone()[0]

sources = conn.execute(
    "SELECT COUNT(*) FROM source_files"
).fetchone()[0]

print(f"TOTAL OBSERVATIONS: {total:,}")
print(f"SOURCE FILES:       {sources:,}")
print(f"DATASETS:           {len(datasets):,}")

conn.close()
