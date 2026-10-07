from pathlib import Path
import pandas as pd
import re
import json
from datetime import datetime

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
INCOMING = PROJECT / "data" / "incoming"
PROCESSED = PROJECT / "data" / "processed"
CANONICAL = PROJECT / "data" / "canonical"

PROCESSED.mkdir(parents=True, exist_ok=True)
CANONICAL.mkdir(parents=True, exist_ok=True)

# ============================================================
# ONLY DATASETS WE HAVE DECIDED ARE RELEVANT TO THE CHALLENGE
# ============================================================

ALLOWED = {
    "nse_analysis",
    "nse_bond_index",
    "treasury_bills",
    "yield_curve",
    "public_debt",
    "liquidity_indicators",
    "monetary_policy_indicators",
    "exchange_rates",
    "inflation_data",
    "historical_pmi",
    "fuel_prices",
    "forex_reserves",
    "agriculture",
    "international_arrivals",
    "diaspora_remittances",
}

def normalize_dataset(filename):

    name = filename.lower()

    # Remove extension
    name = re.sub(r'\.(xlsx|xls|csv)$', '', name)

    # Remove export timestamps such as:
    # 2026-10-02
    # 20261002
    name = re.sub(
        r'[_-]?20\d{2}[-_]?\d{2}[-_]?\d{2}',
        '',
        name
    )

    # Remove NSE export timestamps such as _124449
    name = re.sub(
        r'_\d{6}$',
        '',
        name
    )

    # Remove duplicate numbering
    name = re.sub(
        r'\s*\(\d+\)',
        '',
        name
    )

    name = re.sub(
        r'[_-]+',
        '_',
        name
    ).strip('_')

    return name


def score_file(path):

    score = 0

    # Prefer Excel because some exported CSVs were malformed.
    if path.suffix.lower() == ".xlsx":
        score += 100

    elif path.suffix.lower() == ".xls":
        score += 80

    elif path.suffix.lower() == ".csv":
        score += 50

    # Larger file is generally preferable when duplicates exist.
    score += min(
        int(path.stat().st_size / 1024 / 1024),
        50
    )

    return score


files = []

for pattern in ["*.xlsx", "*.xls", "*.csv"]:

    files.extend(
        INCOMING.glob(pattern)
    )

print("\nROCK CHALLENGE DATA CURATION")
print("=" * 70)

groups = {}

for file in files:

    dataset = normalize_dataset(
        file.name
    )

    if dataset not in ALLOWED:
        print(
            f"  EXCLUDED: {file.name}"
        )
        continue

    groups.setdefault(
        dataset,
        []
    ).append(file)

print("\nRelevant dataset groups:")
print("-" * 70)

for dataset, group in sorted(
    groups.items()
):

    print(
        f"{dataset:30} "
        f"{len(group)} file(s)"
    )

# ============================================================
# SELECT ONE CANONICAL FILE PER DATASET
# ============================================================

registry = []

for dataset, group in sorted(
    groups.items()
):

    ranked = sorted(
        group,
        key=score_file,
        reverse=True
    )

    selected = ranked[0]

    destination = (
        CANONICAL /
        f"{dataset}{selected.suffix.lower()}"
    )

    # Copy canonical file.
    destination.write_bytes(
        selected.read_bytes()
    )

    # Basic metadata.
    rows = None
    columns = None
    sheet_names = []

    try:

        if selected.suffix.lower() == ".csv":

            df = pd.read_csv(
                selected,
                nrows=5000
            )

            rows = len(
                pd.read_csv(
                    selected,
                    usecols=[0]
                )
            )

            columns = len(
                df.columns
            )

            sheet_names = ["CSV"]

        else:

            xl = pd.ExcelFile(
                selected
            )

            sheet_names = xl.sheet_names

            total = 0

            for sheet in xl.sheet_names:

                try:
                    data = pd.read_excel(
                        selected,
                        sheet_name=sheet
                    )

                    total += len(data)

                except Exception:
                    pass

            rows = total

            first = pd.read_excel(
                selected,
                sheet_name=xl.sheet_names[0],
                nrows=5
            )

            columns = len(
                first.columns
            )

    except Exception as exc:

        print(
            f"  Warning reading "
            f"{selected.name}: {exc}"
        )

    registry.append({
        "dataset": dataset,
        "canonical_file": destination.name,
        "original_file": selected.name,
        "format": selected.suffix.lower(),
        "rows": rows,
        "columns": columns,
        "sheets": " | ".join(sheet_names),
        "alternatives": "; ".join(
            x.name for x in ranked[1:]
        )
    })

    print(
        f"  ✓ {dataset} "
        f"→ {destination.name}"
    )

registry_df = pd.DataFrame(
    registry
)

registry_path = (
    PROCESSED /
    "rock_challenge_registry.csv"
)

registry_df.to_csv(
    registry_path,
    index=False
)

summary = {
    "generated": datetime.now().isoformat(),
    "source": "Rock Data Plus",
    "allowed_dataset_count": len(ALLOWED),
    "canonical_dataset_count": len(registry),
    "excluded_dataset_count": sum(
        normalize_dataset(f.name) not in ALLOWED
        for f in files
    ),
    "canonical_folder": str(CANONICAL),
}

(
    PROCESSED /
    "rock_challenge_registry.json"
).write_text(
    json.dumps(
        summary,
        indent=2
    ),
    encoding="utf-8"
)

print("\n" + "=" * 70)
print("CURATION COMPLETE")
print("=" * 70)

print(
    f"\nCanonical datasets: {len(registry)}"
)

print(
    "\nCanonical folder:"
)
print(CANONICAL)

print(
    "\nRegistry:"
)
print(registry_path)

print("\n" + registry_df[
    [
        "dataset",
        "canonical_file",
        "format",
        "rows",
        "columns"
    ]
].to_string(index=False))
