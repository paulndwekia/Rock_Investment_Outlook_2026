from pathlib import Path
import json
import numpy as np
import pandas as pd

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
ANALYSIS = PROJECT / "analysis"

print("=" * 90)
print("KENYA INVESTMENT INTELLIGENCE — QUANTITATIVE OUTLOOK ENGINE")
print("=" * 90)


def read_csv(name):

    path = ANALYSIS / name

    if not path.exists():

        print(f"  - {name}: NOT FOUND")
        return pd.DataFrame()

    try:

        df = pd.read_csv(
            path,
            low_memory=False
        )

        print(
            f"  ✓ {name}: {len(df):,} rows"
        )

        return df

    except Exception as exc:

        print(
            f"  ! {name}: {exc}"
        )

        return pd.DataFrame()


def numeric(series):

    return pd.to_numeric(
        series.astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("KES", "", regex=False)
        .str.replace("KSh", "", regex=False),
        errors="coerce"
    )


metrics = {}

# ============================================================
# EQUITIES
# ============================================================

print("\n[1] EQUITY MARKET")

equity = read_csv(
    "nse_analysis.csv"
)

if equity.empty:

    # fall back to the repaired/derived market snapshot
    equity = read_csv(
        "market_daily_snapshot.csv"
    )

if not equity.empty:

    if "Date" in equity.columns:

        equity["Date"] = pd.to_datetime(
            equity["Date"],
            errors="coerce"
        )

    price_col = None

    for candidate in [
        "Price (KES)",
        "Price",
        "price",
        "Index Value"
    ]:

        if candidate in equity.columns:

            price_col = candidate
            break

    if price_col:

        equity[price_col] = numeric(
            equity[price_col]
        )

        equity = equity.dropna(
            subset=[price_col]
        )

        if not equity.empty:

            metrics["equity"] = {
                "observations": int(len(equity)),
                "latest_price": float(
                    equity[price_col].iloc[-1]
                ),
                "minimum": float(
                    equity[price_col].min()
                ),
                "maximum": float(
                    equity[price_col].max()
                )
            }


# ============================================================
# MARKET RETURNS / RISK
# ============================================================

print("\n[2] MARKET RISK")

risk = read_csv(
    "security_metrics.csv"
)

if not risk.empty:

    numeric_cols = []

    for col in risk.columns:

        converted = pd.to_numeric(
            risk[col],
            errors="coerce"
        )

        if converted.notna().sum() > 0:

            risk[col] = converted
            numeric_cols.append(col)

    metrics["risk"] = {
        "numeric_fields": numeric_cols
    }

    for field in [
        "annualised_volatility",
        "Annualised_Volatility",
        "volatility",
        "max_drawdown",
        "Maximum_Drawdown"
    ]:

        if field in risk.columns:

            series = risk[field].dropna()

            if not series.empty:

                metrics["risk"][
                    field
                ] = float(series.iloc[-1])


# ============================================================
# TREASURY BILLS
# ============================================================

print("\n[3] TREASURY BILLS")

tb = read_csv(
    "clean_treasury_bills.csv"
)

if not tb.empty:

    tb["Date"] = pd.to_datetime(
        tb["Date"],
        errors="coerce"
    )

    tb["Rate (%)"] = numeric(
        tb["Rate (%)"]
    )

    tb = tb.dropna(
        subset=[
            "Date",
            "Rate (%)"
        ]
    )

    if not tb.empty:

        latest_date = tb["Date"].max()

        latest = tb[
            tb["Date"] == latest_date
        ].copy()

        metrics["treasury_bills"] = {
            "latest_date": latest_date.strftime(
                "%Y-%m-%d"
            ),
            "latest_rates": {}
        }

        for _, row in latest.iterrows():

            tenor = str(
                row["Tenor"]
            )

            metrics["treasury_bills"][
                "latest_rates"
            ][tenor] = float(
                row["Rate (%)"]
            )

        # 91D / 364D spread where available
        rates = {
            str(r["Tenor"]): float(r["Rate (%)"])
            for _, r in latest.iterrows()
        }

        if (
            "91-Day" in rates
            and
            "364-Day" in rates
        ):

            metrics["treasury_bills"][
                "91d_364d_spread"
            ] = rates["364-Day"] - rates["91-Day"]


# ============================================================
# YIELD CURVE
# ============================================================

print("\n[4] YIELD CURVE")

curve = read_csv(
    "clean_yield_curve.csv"
)

if not curve.empty:

    curve["Yield (%)"] = numeric(
        curve["Yield (%)"]
    )

    curve = curve.dropna(
        subset=["Yield (%)"]
    )

    curve["Maturity"] = (
        curve["Maturity"]
        .astype(str)
        .str.strip()
    )

    order = {
        "1 Year": 1,
        "2 Years": 2,
        "3 Years": 3,
        "5 Years": 5,
        "10 Years": 10,
        "20 Years": 20,
        "30 Years": 30
    }

    curve["_years"] = (
        curve["Maturity"].map(order)
    )

    curve = curve.dropna(
        subset=["_years"]
    )

    if not curve.empty:

        curve = curve.sort_values(
            "_years"
        )

        metrics["yield_curve"] = {
            "points": int(len(curve))
        }

        if len(curve) >= 2:

            short = curve.iloc[0]
            long = curve.iloc[-1]

            metrics["yield_curve"][
                "short_maturity"
            ] = short["Maturity"]

            metrics["yield_curve"][
                "short_yield"
            ] = float(short["Yield (%)"])

            metrics["yield_curve"][
                "long_maturity"
            ] = long["Maturity"]

            metrics["yield_curve"][
                "long_yield"
            ] = float(long["Yield (%)"])

            metrics["yield_curve"][
                "long_short_spread"
            ] = float(
                long["Yield (%)"]
                -
                short["Yield (%)"]
            )


# ============================================================
# BOND INDEX
# ============================================================

print("\n[5] GOVERNMENT BOND INDEX")

bond = read_csv(
    "clean_nse_bond_index.csv"
)

if not bond.empty:

    bond["Date"] = pd.to_datetime(
        bond["Date"],
        errors="coerce"
    )

    bond["Index Value"] = numeric(
        bond["Index Value"]
    )

    bond = bond.dropna(
        subset=[
            "Date",
            "Index Value"
        ]
    )

    if not bond.empty:

        bond = bond.sort_values(
            "Date"
        )

        values = bond[
            "Index Value"
        ]

        latest = float(
            values.iloc[-1]
        )

        first = float(
            values.iloc[0]
        )

        total_return = (
            latest / first
        ) - 1

        metrics["bond_index"] = {
            "observations": int(len(bond)),
            "latest_value": latest,
            "total_sample_return": float(
                total_return
            )
        }


# ============================================================
# INFLATION
# ============================================================

print("\n[6] INFLATION")

inflation = read_csv(
    "clean_inflation.csv"
)

if not inflation.empty:

    date_col = None

    for candidate in [
        "Date",
        "date"
    ]:

        if candidate in inflation.columns:

            date_col = candidate
            break

    value_col = None

    for candidate in [
        "Rate (%)",
        "rate",
        "value"
    ]:

        if candidate in inflation.columns:

            value_col = candidate
            break

    if date_col and value_col:

        inflation[date_col] = pd.to_datetime(
            inflation[date_col],
            errors="coerce"
        )

        inflation[value_col] = numeric(
            inflation[value_col]
        )

        inflation = inflation.dropna(
            subset=[
                date_col,
                value_col
            ]
        )

        if not inflation.empty:

            inflation = inflation.sort_values(
                date_col
            )

            latest = inflation.iloc[-1]

            metrics["inflation"] = {
                "latest_date": latest[
                    date_col
                ].strftime("%Y-%m-%d"),
                "latest_value": float(
                    latest[value_col]
                )
            }


# ============================================================
# FOREIGN FLOWS
# ============================================================

print("\n[7] FOREIGN FLOWS")

flows = read_csv(
    "foreign_flow_relationships.csv"
)

if not flows.empty:

    numeric_cols = []

    for col in flows.columns:

        converted = pd.to_numeric(
            flows[col],
            errors="coerce"
        )

        if converted.notna().sum() > 0:

            numeric_cols.append(
                col
            )

    metrics["foreign_flows"] = {
        "numeric_fields": numeric_cols
    }


# ============================================================
# SCENARIO INPUTS
# ============================================================

print("\n[8] SCENARIO FRAMEWORK")

scenario = {}

# These are analytical reference bands,
# not predictions or guaranteed returns.

if "risk" in metrics:

    vol = (
        metrics["risk"]
        .get("annualised_volatility")
        or
        metrics["risk"]
        .get("Annualised_Volatility")
        or
        metrics["risk"]
        .get("volatility")
    )

    if vol is not None:

        scenario["observed_volatility"] = vol

if "yield_curve" in metrics:

    scenario["curve_slope"] = metrics[
        "yield_curve"
    ].get(
        "long_short_spread"
    )

if "treasury_bills" in metrics:

    scenario["tbill_91d_364d_spread"] = metrics[
        "treasury_bills"
    ].get(
        "91d_364d_spread"
    )

if "inflation" in metrics:

    scenario["latest_inflation"] = metrics[
        "inflation"
    ].get(
        "latest_value"
    )

metrics["scenario_framework"] = scenario


# ============================================================
# SAVE RESULTS
# ============================================================

json_path = (
    ANALYSIS
    / "outlook_quant_metrics.json"
)

with open(
    json_path,
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        metrics,
        f,
        indent=2
    )

rows = []

for section, values in metrics.items():

    if not isinstance(
        values,
        dict
    ):

        continue

    for key, value in values.items():

        if isinstance(
            value,
            dict
        ):

            continue

        rows.append(
            {
                "section": section,
                "metric": key,
                "value": value
            }
        )

table = pd.DataFrame(
    rows
)

csv_path = (
    ANALYSIS
    / "outlook_quant_metrics.csv"
)

table.to_csv(
    csv_path,
    index=False,
    encoding="utf-8-sig"
)

print("\n" + "=" * 90)
print("QUANTITATIVE OUTLOOK ENGINE COMPLETE")
print("=" * 90)

print("\nCreated:")

print(
    f"  ✓ {json_path}"
)

print(
    f"  ✓ {csv_path}"
)

print("\nAvailable sections:")

for section in metrics:

    print(
        f"  ✓ {section}"
    )
