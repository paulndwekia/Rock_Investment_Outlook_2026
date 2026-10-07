from pathlib import Path
import pandas as pd
import re
import json
from datetime import datetime

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
INVENTORY = PROJECT / "data" / "processed" / "rock_data_inventory.csv"
OUT = PROJECT / "data" / "processed"

df = pd.read_csv(INVENTORY)

def base_name(name):
    name = str(name).lower()

    # Remove timestamps such as 2026-10-02 / 20261002
    name = re.sub(r'[_-]?20\d{2}[-_]?\d{2}[-_]?\d{2}', '', name)

    # Remove duplicate numbering
    name = re.sub(r'\s*\(\d+\)', '', name)

    # Remove extension
    name = re.sub(r'\.(xlsx|xls|csv)$', '', name)

    return re.sub(r'[_\s]+', '_', name).strip('_')

df["Dataset"] = df["file"].apply(base_name)

# Rank files:
# Excel is preferred over malformed CSV when both exist.
# Larger row count is preferred.
# Larger file size is a secondary signal.
df["Excel"] = df["type"].isin([".xlsx", ".xls"]).astype(int)

df = df.sort_values(
    ["Dataset", "Excel", "rows", "size_mb"],
    ascending=[True, False, False, False]
)

canonical = (
    df.groupby("Dataset", as_index=False)
      .first()
      .sort_values("Dataset")
)

canonical.to_csv(
    OUT / "rock_canonical_registry.csv",
    index=False
)

duplicates = df.merge(
    canonical[["Dataset", "file"]],
    on="Dataset",
    suffixes=("", "_canonical")
)

duplicates["Is_Canonical"] = (
    duplicates["file"] ==
    duplicates["file_canonical"]
)

duplicates.to_csv(
    OUT / "rock_file_registry.csv",
    index=False
)

summary = {
    "generated": datetime.now().isoformat(),
    "source": "Rock Data Plus",
    "files_seen": int(len(df)),
    "unique_dataset_groups": int(
        df["Dataset"].nunique()
    ),
    "canonical_files": int(
        len(canonical)
    ),
}

(OUT / "rock_registry_summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print("\n" + "=" * 70)
print("ROCK DATASET REGISTRY COMPLETE")
print("=" * 70)

print(f"\nFiles seen: {len(df):,}")
print(f"Unique dataset groups: {df['Dataset'].nunique():,}")
print(f"Canonical datasets: {len(canonical):,}")

print("\nCanonical datasets:")
print(
    canonical[
        [
            "Dataset",
            "file",
            "type",
            "rows",
            "columns",
            "date_min",
            "date_max"
        ]
    ].to_string(index=False)
)

print("\nSaved:")
print(OUT / "rock_canonical_registry.csv")
print(OUT / "rock_file_registry.csv")
print(OUT / "rock_registry_summary.json")
