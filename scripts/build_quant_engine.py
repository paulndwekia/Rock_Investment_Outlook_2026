from pathlib import Path
import sqlite3
import json
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

from research_models import (
    calculate_market_regime,
    classify_market_regime,
    calculate_rolling_risk,
    calculate_security_metrics,
    prepare_equity_panel,
    validate_model_outputs,
)


PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
DB = PROJECT / "database" / "rock_investment_intelligence.db"
OUT = PROJECT / "analysis"

OUT.mkdir(parents=True, exist_ok=True)

print("\n" + "=" * 80)
print("ROCK QUANTITATIVE ENGINE")
print("=" * 80)
print("Primary source: Rock Data Plus")

conn = sqlite3.connect(DB)

# ============================================================
# 1. LOAD THE CORRECTED NSE DATA
# ============================================================

print("\nLoading corrected NSE dataset...")

try:
    df = pd.read_sql_query(
        """
        SELECT
            Date,
            Security,
            "Price (KES)" AS Price,
            Volume,
            "Net Foreign Flow" AS Net_Foreign_Flow,
            "Change %" AS Change_Pct,
            Daily_Return,
            Log_Return
        FROM rock_nse_analysis
        ORDER BY Security, Date
        """,
        conn
    )

except Exception:
    print("rock_nse_analysis table not found.")
    print("Stopping rather than using an unverified fallback.")
    conn.close()
    raise

df["Date"] = pd.to_datetime(
    df["Date"],
    errors="coerce"
)

df["Price"] = pd.to_numeric(
    df["Price"],
    errors="coerce"
)

df["Volume"] = pd.to_numeric(
    df["Volume"],
    errors="coerce"
)

df["Net_Foreign_Flow"] = pd.to_numeric(
    df["Net_Foreign_Flow"],
    errors="coerce"
)

df["Change_Pct"] = pd.to_numeric(
    df["Change_Pct"],
    errors="coerce"
)

# Validate the price panel before any model uses it.
df = prepare_equity_panel(df)

print(
    f"✓ Valid positive-price rows: {len(df):,}"
)
print(
    f"✓ Security / benchmark series: {df['Security'].nunique():,}"
)
print(
    f"✓ Return anomalies flagged: {int(df['Return_Anomaly'].sum()):,}"
)

# ============================================================
# 2. SECURITY-LEVEL HISTORICAL METRICS
# ============================================================

print("\\nCalculating validated security metrics...")

metrics = calculate_security_metrics(
    df,
    min_risk_observations=30,
    annualisation_days=252,
)
metrics.to_csv(
    OUT / "security_metrics.csv",
    index=False
)

print(
    f"✓ Security metrics: {len(metrics):,} series"
)

# ============================================================
# 3. ROLLING RISK MEASURES
# ============================================================

rolling_df = calculate_rolling_risk(
    df,
    windows=(21, 63),
    annualisation_days=252,
)
rolling_df.to_csv(
    OUT / "rolling_risk.csv",
    index=False
)

rolling_21_valid = rolling_df[["Vol_21D"]].dropna()
rolling_63_valid = rolling_df[["Vol_63D"]].dropna()
rolling_21_gate = validate_model_outputs(
    rolling_21_valid,
    required_numeric=("Vol_21D",),
)
rolling_63_gate = validate_model_outputs(
    rolling_63_valid,
    required_numeric=("Vol_63D",),
)

# A market-regime summary is an equal-weighted sample proxy, not
# the official NSE index. A 12-month return is only emitted when
# all twelve consecutive calendar months are present.
market_regime = calculate_market_regime(df, months_required=12)
regime_classification = classify_market_regime(market_regime)
market_regime_monthly = market_regime.pop("monthly")
market_regime_monthly.to_csv(
    OUT / "market_regime_monthly.csv",
    index=False
)

risk_eligible = metrics[
    metrics["Valid_Risk_Observations"] >= 30
].copy()
risk_gate = validate_model_outputs(
    risk_eligible,
    required_numeric=("Annualized_Volatility", "Maximum_Drawdown"),
)

return_eligible = metrics[
    (metrics["Return_Anomaly_Count"] == 0)
    & (metrics["Observations"] >= 2)
].copy()
return_gate = validate_model_outputs(
    return_eligible,
    required_numeric=("Total_Return",),
)

model_validation = {
    "generated_at": datetime.now().isoformat(),
    "equity_risk_model": risk_gate,
    "full_period_return_model": return_gate,
    "market_regime_model": {
        "status": market_regime.get("status"),
        "classification": regime_classification,
        "months_available": market_regime.get("months_available", 0),
        "is_full_consecutive_12m": market_regime.get("is_full_consecutive_12m", False),
        "historical_return_12m_available": bool(
            np.isfinite(market_regime.get("historical_return_12m", np.nan))
        ),
    },
    "anomaly_policy": (
        "Returns beyond +/-200% are flagged; the flagged return and "
        "the immediately following return are excluded from risk "
        "calculations. Full-period return is withheld for any series "
        "with a flagged return."
    ),
}

# ============================================================
# 4. IDENTIFY ACTUAL ROCK BENCHMARK SERIES
# ============================================================

names = df["Security"].dropna().unique()

patterns = [
    "ALL SHARE",
    "NSE 20",
    "NSE 25",
    "BANKING SECTOR",
    "BOND TURNOVER",
    "BOND INDEX",
    "FTSE NSE"
]

benchmarks = []

for security in names:

    upper = str(security).upper()

    if any(
        pattern in upper
        for pattern in patterns
    ):
        benchmarks.append(
            security
        )

print("\nRock benchmark series detected:")

for b in benchmarks:
    print("  ✓", b)

benchmark_df = df[
    df["Security"].isin(benchmarks)
].copy()

benchmark_df.to_csv(
    OUT / "benchmark_data.csv",
    index=False
)

# ============================================================
# 5. BENCHMARK RETURN ANALYSIS
# ============================================================

benchmark_metrics = []

for security, g in benchmark_df.groupby(
    "Security"
):

    g = g.sort_values("Date")

    prices = g["Price"].dropna()

    if len(prices) < 2:
        continue

    total_return = (
        prices.iloc[-1] / prices.iloc[0] - 1
        if not g["Return_Anomaly"].fillna(False).any()
        else np.nan
    )

    returns = (
        g["Daily_Return"]
        .dropna()
    )

    volatility = np.nan

    if len(returns) > 1:
        volatility = (
            returns.std()
            * np.sqrt(252)
        )

    benchmark_metrics.append({
        "Benchmark": security,
        "Start_Date": g["Date"].min().date(),
        "End_Date": g["Date"].max().date(),
        "Observations": len(g),
        "Total_Return": total_return,
        "Return_Anomaly_Count": int(g["Return_Anomaly"].fillna(False).sum()),
        "Annualized_Volatility": volatility
    })

benchmark_metrics = pd.DataFrame(
    benchmark_metrics
)

benchmark_metrics.to_csv(
    OUT / "benchmark_metrics.csv",
    index=False
)

benchmark_eligible = benchmark_metrics[
    (benchmark_metrics["Observations"] >= 30)
    & benchmark_metrics["Total_Return"].notna()
    & benchmark_metrics["Annualized_Volatility"].notna()
].copy()
benchmark_return_gate = validate_model_outputs(
    benchmark_eligible,
    required_numeric=("Total_Return", "Annualized_Volatility"),
)

# ============================================================
# 6. BENCHMARK CORRELATION MATRIX
# ============================================================

print("\nCalculating benchmark correlations...")

if len(benchmarks) >= 2:

    pivot = (
        benchmark_df
        .pivot_table(
            index="Date",
            columns="Security",
            values="Daily_Return"
        )
    )

    correlation = pivot.corr(
        min_periods=30
    )

    correlation.to_csv(
        OUT / "benchmark_return_correlations.csv"
    )

else:

    correlation = pd.DataFrame()

# ============================================================
# 7. FOREIGN-FLOW RELATIONSHIP
# ============================================================

print("\nCalculating foreign-flow relationships...")

foreign_results = []

for security, g in df.groupby(
    "Security"
):

    x = g[
        [
            "Net_Foreign_Flow",
            "Daily_Return"
        ]
    ].dropna()

    if len(x) < 30:
        continue

    if x["Net_Foreign_Flow"].nunique() < 2:
        continue

    if x["Daily_Return"].nunique() < 2:
        continue

    try:

        corr, pvalue = pearsonr(
            x["Net_Foreign_Flow"],
            x["Daily_Return"]
        )

        foreign_results.append({
            "Security": security,
            "Observations": len(x),
            "Foreign_Flow_Return_Correlation": corr,
            "P_Value": pvalue
        })

    except Exception:
        pass

foreign_relationships = pd.DataFrame(
    foreign_results
)

foreign_relationships.to_csv(
    OUT / "foreign_flow_relationships.csv",
    index=False
)

foreign_eligible = foreign_relationships[
    foreign_relationships["Observations"] >= 30
].copy() if not foreign_relationships.empty else pd.DataFrame()
foreign_flow_gate = validate_model_outputs(
    foreign_eligible,
    required_numeric=("Foreign_Flow_Return_Correlation", "P_Value"),
)

# The release gate covers every implemented calculation stage. A model with
# insufficient observations remains incomplete; it is never marked green just
# because the script executed without an exception.
model_validation.update({
    "rolling_21d_model": rolling_21_gate,
    "rolling_63d_model": rolling_63_gate,
    "benchmark_return_model": benchmark_return_gate,
    "benchmark_correlation_model": {
        "status": (
            "passed"
            if (
                not correlation.empty
                and len(benchmarks) >= 2
                and np.isfinite(
                    correlation.where(
                        np.triu(np.ones(correlation.shape), k=1).astype(bool)
                    ).to_numpy(dtype=float)
                ).any()
            )
            else "incomplete"
        ),
        "benchmark_series": int(len(benchmarks)),
    },
    "foreign_flow_model": foreign_flow_gate,
})

required_gates = [
    risk_gate,
    return_gate,
    rolling_21_gate,
    rolling_63_gate,
    benchmark_return_gate,
    foreign_flow_gate,
]
all_gates_passed = all(gate.get("status") == "passed" for gate in required_gates)
model_validation["overall_status"] = (
    "passed"
    if (
        all_gates_passed
        and market_regime.get("status") == "ok"
        and market_regime.get("is_full_consecutive_12m", False)
        and regime_classification.get("status") == "ok"
        and model_validation["benchmark_correlation_model"]["status"] == "passed"
    )
    else "incomplete"
)

(OUT / "model_validation.json").write_text(
    json.dumps(model_validation, indent=2, default=str),
    encoding="utf-8",
)

print("Model validation:", model_validation["overall_status"])
for model_name, gate in model_validation.items():
    if model_name.endswith("_model") or model_name in {
        "equity_risk_model", "full_period_return_model"
    }:
        if isinstance(gate, dict):
            print(f"  {model_name}: {gate.get('status', gate.get('overall_status', 'not evaluated'))}")

# ============================================================
# 8. MARKET-WIDE DAILY SNAPSHOT
# ============================================================

market_daily = (
    df.groupby("Date")
    .agg(
        Securities_Observed=(
            "Security",
            "nunique"
        ),
        Total_Volume=(
            "Volume",
            "sum"
        ),
        Total_Foreign_Flow=(
            "Net_Foreign_Flow",
            "sum"
        ),
        Mean_Return=(
            "Daily_Return",
            "mean"
        ),
        Median_Return=(
            "Daily_Return",
            "median"
        )
    )
    .reset_index()
)

market_daily.to_csv(
    OUT / "market_daily_snapshot.csv",
    index=False
)

# ============================================================
# 9. CURRENT / LATEST OBSERVATIONS
# ============================================================

latest_date = df["Date"].max()

latest = df[
    df["Date"] == latest_date
].copy()

latest.to_csv(
    OUT / "latest_market_snapshot.csv",
    index=False
)

# ============================================================
# 10. DATASET INVENTORY FROM DATABASE
# ============================================================

dataset_summary = pd.read_sql_query(
    """
    SELECT
        dataset_name,
        COUNT(*) AS observations,
        MIN(observed_date) AS first_observation,
        MAX(observed_date) AS last_observation
    FROM rock_observations
    GROUP BY dataset_name
    ORDER BY dataset_name
    """,
    conn
)

dataset_summary.to_csv(
    OUT / "database_dataset_summary.csv",
    index=False
)

# ============================================================
# 11. RESEARCH SUMMARY
# ============================================================

research = {
    "generated_at": datetime.now().isoformat(),
    "source": "Rock Data Plus",
    "external_market_data_used": False,
    "nse_rows": int(len(df)),
    "securities_or_series": int(
        df["Security"].nunique()
    ),
    "nse_start": str(
        df["Date"].min().date()
    ),
    "nse_end": str(
        df["Date"].max().date()
    ),
    "benchmark_series": [
        str(x) for x in benchmarks
    ],
    "model_validation": model_validation,
    "market_regime": {
        "status": market_regime.get("status"),
        "classification": regime_classification,
        "historical_return_12m": market_regime.get("historical_return_12m"),
        "annualised_monthly_volatility": market_regime.get("annualised_monthly_volatility"),
        "maximum_drawdown_12m": market_regime.get("maximum_drawdown_12m"),
        "months_available": market_regime.get("months_available", 0),
        "is_full_consecutive_12m": market_regime.get("is_full_consecutive_12m", False),
    },
    "outputs": [
        "security_metrics.csv",
        "rolling_risk.csv",
        "market_regime_monthly.csv",
        "model_validation.json",
        "benchmark_data.csv",
        "benchmark_metrics.csv",
        "benchmark_return_correlations.csv",
        "foreign_flow_relationships.csv",
        "market_daily_snapshot.csv",
        "latest_market_snapshot.csv",
        "database_dataset_summary.csv"
    ]
}

(
    OUT / "quant_engine_manifest.json"
).write_text(
    json.dumps(
        research,
        indent=2
    ),
    encoding="utf-8"
)

conn.close()

print("\n" + "=" * 80)
print("QUANTITATIVE ENGINE COMPLETE")
print("=" * 80)

print("\nCreated:")
print("  ✓ security_metrics.csv")
print("  ✓ rolling_risk.csv")
print("  ✓ benchmark_data.csv")
print("  ✓ benchmark_metrics.csv")
print("  ✓ benchmark_return_correlations.csv")
print("  ✓ foreign_flow_relationships.csv")
print("  ✓ market_daily_snapshot.csv")
print("  ✓ latest_market_snapshot.csv")
print("  ✓ database_dataset_summary.csv")
print("  ✓ quant_engine_manifest.json")

print("\nAll calculations use Rock Data Plus observations.")
