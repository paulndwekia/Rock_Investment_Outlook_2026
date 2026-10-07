from pathlib import Path
import sqlite3
import json
import re
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
DB = PROJECT / "database" / "rock_investment_intelligence.db"
OUT = PROJECT / "analysis"

OUT.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("ROCK MULTI-ASSET RESEARCH ENGINE")
print("=" * 80)
print("Primary source: Rock Data Plus only")

conn = sqlite3.connect(DB)

# ------------------------------------------------------------
# Load generic Rock observations
# ------------------------------------------------------------

obs = pd.read_sql_query(
    """
    SELECT
        dataset_name,
        sheet_name,
        source_file,
        observed_date,
        row_json,
        imported_at
    FROM rock_observations
    ORDER BY dataset_name, observed_date
    """,
    conn
)

print(
    f"\nDatabase observations: {len(obs):,}"
)

# ------------------------------------------------------------
# Flatten Rock JSON rows
# ------------------------------------------------------------

records = []

for row in obs.itertuples(index=False):

    try:
        values = json.loads(row.row_json)
    except Exception:
        continue

    if not isinstance(values, dict):
        continue

    item = {
        "dataset": row.dataset_name,
        "sheet": row.sheet_name,
        "source_file": row.source_file,
        "observed_date": row.observed_date,
        "imported_at": row.imported_at
    }

    for key, value in values.items():
        item[str(key)] = value

    records.append(item)

flat = pd.DataFrame(records)

flat.to_parquet(
    OUT / "rock_flat_observations.parquet",
    index=False
)

flat.to_csv(
    OUT / "rock_flat_observations.csv",
    index=False
)

print(
    f"Flattened records: {len(flat):,}"
)

# ------------------------------------------------------------
# Identify date columns
# ------------------------------------------------------------

date_candidates = []

for column in flat.columns:

    if column in [
        "dataset",
        "sheet",
        "source_file",
        "imported_at",
        "row_json"
    ]:
        continue

    name = str(column).lower()

    score = 0

    if "date" in name:
        score += 5
    if "period" in name:
        score += 4
    if "month" in name:
        score += 3
    if "year" in name:
        score += 2
    if "time" in name:
        score += 2

    if score == 0:
        continue

    converted = pd.to_datetime(
        flat[column],
        errors="coerce"
    )

    valid = converted.notna().sum()

    if valid:
        date_candidates.append({
            "column": column,
            "score": score,
            "valid": int(valid),
            "min": str(converted.min()),
            "max": str(converted.max())
        })

date_table = pd.DataFrame(
    date_candidates
)

date_table.to_csv(
    OUT / "rock_date_field_inventory.csv",
    index=False
)

# ------------------------------------------------------------
# Identify numeric columns
# ------------------------------------------------------------

numeric_inventory = []

for column in flat.columns:

    if column in [
        "dataset",
        "sheet",
        "source_file",
        "imported_at"
    ]:
        continue

    numeric = pd.to_numeric(
        flat[column],
        errors="coerce"
    )

    valid = int(
        numeric.notna().sum()
    )

    if valid == 0:
        continue

    numeric_inventory.append({
        "column": column,
        "numeric_values": valid,
        "coverage": valid / len(flat)
        if len(flat)
        else 0
    })

numeric_table = pd.DataFrame(
    numeric_inventory
)

numeric_table.to_csv(
    OUT / "rock_numeric_field_inventory.csv",
    index=False
)

# ------------------------------------------------------------
# Dataset-level structural summary
# ------------------------------------------------------------

dataset_rows = []

for dataset, group in flat.groupby(
    "dataset"
):

    dataset_rows.append({
        "dataset": dataset,
        "rows": len(group),
        "sheets": group["sheet"].nunique(),
        "source_files": group["source_file"].nunique(),
        "first_observed_date":
            group["observed_date"].min(),
        "last_observed_date":
            group["observed_date"].max(),
        "columns":
            len(group.columns)
    })

dataset_summary = pd.DataFrame(
    dataset_rows
)

dataset_summary.to_csv(
    OUT / "rock_research_dataset_summary.csv",
    index=False
)

print("\nDATASET SUMMARY")
print("-" * 80)
print(
    dataset_summary.to_string(index=False)
)

# ------------------------------------------------------------
# Helper: find a numeric field by keywords
# ------------------------------------------------------------

def find_numeric_field(
    group,
    keywords
):

    candidates = []

    for column in group.columns:

        if column in [
            "dataset",
            "sheet",
            "source_file",
            "imported_at",
            "observed_date"
        ]:
            continue

        name = str(column).lower()

        if not any(
            keyword in name
            for keyword in keywords
        ):
            continue

        values = pd.to_numeric(
            group[column],
            errors="coerce"
        )

        valid = values.notna().sum()

        if valid:
            candidates.append(
                (
                    valid,
                    column
                )
            )

    if not candidates:
        return None

    return sorted(
        candidates,
        reverse=True
    )[0][1]

# ------------------------------------------------------------
# Create standard monthly macro dataset
# ------------------------------------------------------------

macro_datasets = [
    "inflation_data",
    "exchange_rates",
    "historical_pmi",
    "fuel_prices",
    "liquidity_indicators",
    "monetary_policy_indicators",
    "forex_reserves",
    "public_debt",
    "diaspora_remittances",
    "international_arrivals",
    "agriculture"
]

macro_frames = []

for dataset in macro_datasets:

    g = flat[
        flat["dataset"] == dataset
    ].copy()

    if g.empty:
        continue

    # Prefer explicit date fields from the generic
    # observed_date column when available.
    g["Date"] = pd.to_datetime(
        g["observed_date"],
        errors="coerce"
    )

    # If generic date is absent, search the row fields.
    if g["Date"].notna().sum() == 0:

        date_candidates_local = []

        for column in g.columns:

            name = str(column).lower()

            if any(
                x in name
                for x in [
                    "date",
                    "period",
                    "month",
                    "year"
                ]
            ):

                converted = pd.to_datetime(
                    g[column],
                    errors="coerce"
                )

                valid = converted.notna().sum()

                if valid:
                    date_candidates_local.append(
                        (
                            valid,
                            column,
                            converted
                        )
                    )

        if date_candidates_local:

            _, _, converted = max(
                date_candidates_local,
                key=lambda x: x[0]
            )

            g["Date"] = converted

    g = g[
        g["Date"].notna()
    ].copy()

    if g.empty:
        continue

    g["Month"] = (
        g["Date"]
        .dt.to_period("M")
        .astype(str)
    )

    # Select a useful numeric measure automatically.
    value_field = find_numeric_field(
        g,
        [
            "price",
            "rate",
            "yield",
            "value",
            "index",
            "inflation",
            "percentage",
            "percent",
            "amount",
            "reserve",
            "liquidity",
            "pmi"
        ]
    )

    if value_field is None:
        continue

    g["Value"] = pd.to_numeric(
        g[value_field],
        errors="coerce"
    )

    monthly = (
        g.dropna(
            subset=["Value"]
        )
        .groupby("Month", as_index=False)
        .agg(
            Value=("Value", "mean")
        )
    )

    monthly["Dataset"] = dataset
    monthly["Measure"] = value_field

    macro_frames.append(
        monthly
    )

if macro_frames:

    macro = pd.concat(
        macro_frames,
        ignore_index=True
    )

else:

    macro = pd.DataFrame(
        columns=[
            "Month",
            "Value",
            "Dataset",
            "Measure"
        ]
    )

macro.to_csv(
    OUT / "rock_macro_monthly.csv",
    index=False
)

# ------------------------------------------------------------
# Treasury Bills
# ------------------------------------------------------------

t_bill = flat[
    flat["dataset"] == "treasury_bills"
].copy()

if not t_bill.empty:

    t_bill.to_csv(
        OUT / "rock_treasury_bills_research.csv",
        index=False
    )

# ------------------------------------------------------------
# NSE Bond Index
# ------------------------------------------------------------

bond_index = flat[
    flat["dataset"] == "nse_bond_index"
].copy()

if not bond_index.empty:

    bond_index.to_csv(
        OUT / "rock_bond_index_research.csv",
        index=False
    )

# ------------------------------------------------------------
# Yield curve snapshot
# ------------------------------------------------------------

yield_curve = flat[
    flat["dataset"] == "yield_curve"
].copy()

if not yield_curve.empty:

    yield_curve.to_csv(
        OUT / "rock_yield_curve_snapshot.csv",
        index=False
    )

# ------------------------------------------------------------
# NSE monthly market series
# ------------------------------------------------------------

nse = flat[
    flat["dataset"] == "nse_analysis"
].copy()

if not nse.empty:

    nse["Date"] = pd.to_datetime(
        nse["observed_date"],
        errors="coerce"
    )

    nse["Price"] = pd.to_numeric(
        nse.get("Price (KES)"),
        errors="coerce"
    )

    nse["Volume"] = pd.to_numeric(
        nse.get("Volume"),
        errors="coerce"
    )

    nse["Foreign_Flow"] = pd.to_numeric(
        nse.get("Net Foreign Flow"),
        errors="coerce"
    )

    # Monthly mean price by security.
    monthly_nse = (
        nse.dropna(
            subset=["Date"]
        )
        .assign(
            Month=lambda x:
                x["Date"]
                .dt.to_period("M")
                .astype(str)
        )
        .groupby(
            ["Month", "Security"],
            as_index=False
        )
        .agg(
            Mean_Price=("Price", "mean"),
            Total_Volume=("Volume", "sum"),
            Foreign_Flow=("Foreign_Flow", "sum")
        )
    )

    monthly_nse.to_csv(
        OUT /
        "rock_nse_monthly_market.csv",
        index=False
    )

    # Security monthly returns.
    monthly_nse = monthly_nse.sort_values(
        ["Security", "Month"]
    )

    monthly_nse["Monthly_Return"] = (
        monthly_nse
        .groupby("Security")
        ["Mean_Price"]
        .pct_change()
    )

    monthly_nse.to_csv(
        OUT /
        "rock_nse_monthly_returns.csv",
        index=False
    )

# ------------------------------------------------------------
# Cross-dataset correlations
# ------------------------------------------------------------

if not macro.empty and not nse.empty:

    # Aggregate NSE to one market-wide monthly series.
    market = (
        monthly_nse
        .groupby("Month", as_index=False)
        .agg(
            Market_Return=(
                "Monthly_Return",
                "mean"
            ),
            Market_Volume=(
                "Total_Volume",
                "sum"
            ),
            Market_Foreign_Flow=(
                "Foreign_Flow",
                "sum"
            )
        )
    )

    macro_pivot = (
        macro
        .pivot_table(
            index="Month",
            columns="Dataset",
            values="Value",
            aggfunc="mean"
        )
        .reset_index()
    )

    merged = market.merge(
        macro_pivot,
        on="Month",
        how="inner"
    )

    merged.to_csv(
        OUT /
        "rock_market_macro_merged.csv",
        index=False
    )

    correlations = []

    numeric_cols = [
        c
        for c in merged.columns
        if c != "Month"
        and pd.api.types.is_numeric_dtype(
            merged[c]
        )
    ]

    for column in numeric_cols:

        if column == "Market_Return":
            continue

        pair = merged[
            [
                "Market_Return",
                column
            ]
        ].dropna()

        if len(pair) < 12:
            continue

        corr = pair.corr().iloc[0, 1]

        correlations.append({
            "Market_Variable":
                column,
            "Observations":
                len(pair),
            "Pearson_Correlation":
                corr
        })

    corr_df = pd.DataFrame(
        correlations
    )

    corr_df.to_csv(
        OUT /
        "rock_market_macro_correlations.csv",
        index=False
    )

else:

    merged = pd.DataFrame()
    corr_df = pd.DataFrame()

# ------------------------------------------------------------
# Research engine manifest
# ------------------------------------------------------------

manifest = {
    "generated_at":
        pd.Timestamp.now().isoformat(),

    "primary_source":
        "Rock Data Plus",

    "external_market_data_used":
        False,

    "database":
        str(DB),

    "database_observations":
        int(len(obs)),

    "flattened_observations":
        int(len(flat)),

    "datasets_available":
        sorted(
            flat["dataset"]
            .dropna()
            .unique()
            .tolist()
        ),

    "outputs": [
        "rock_flat_observations.parquet",
        "rock_flat_observations.csv",
        "rock_date_field_inventory.csv",
        "rock_numeric_field_inventory.csv",
        "rock_research_dataset_summary.csv",
        "rock_macro_monthly.csv",
        "rock_treasury_bills_research.csv",
        "rock_bond_index_research.csv",
        "rock_yield_curve_snapshot.csv",
        "rock_nse_monthly_market.csv",
        "rock_nse_monthly_returns.csv",
        "rock_market_macro_merged.csv",
        "rock_market_macro_correlations.csv"
    ]
}

(
    OUT /
    "rock_research_engine_manifest.json"
).write_text(
    json.dumps(
        manifest,
        indent=2
    ),
    encoding="utf-8"
)

conn.close()

print("\n" + "=" * 80)
print("MULTI-ASSET RESEARCH ENGINE COMPLETE")
print("=" * 80)

print("\nCreated:")
for output in manifest["outputs"]:
    print("  ✓", output)

print(
    "\nNext stage: professional interactive website."
)
print(
    "The website will read these Rock-derived outputs "
    "rather than hard-coded numbers."
)
