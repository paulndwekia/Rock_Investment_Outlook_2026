from pathlib import Path
import sqlite3
import json
import warnings
from datetime import datetime

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

warnings.filterwarnings("ignore")

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

# Recalculate daily returns safely.
df = df.sort_values(
    ["Security", "Date"]
).reset_index(drop=True)

df["Daily_Return"] = (
    df.groupby("Security")["Price"]
    .pct_change()
)

# Log return only where mathematically defined.
valid = df["Daily_Return"] > -1

df["Log_Return"] = np.nan

df.loc[valid, "Log_Return"] = np.log1p(
    df.loc[valid, "Daily_Return"]
)

print(
    f"✓ Rows: {len(df):,}"
)

print(
    f"✓ Securities/series: "
    f"{df['Security'].nunique():,}"
)

print(
    f"✓ Date range: "
    f"{df['Date'].min().date()} → "
    f"{df['Date'].max().date()}"
)

# ============================================================
# 2. SECURITY-LEVEL HISTORICAL METRICS
# ============================================================

print("\nCalculating security metrics...")

metrics = []

for security, g in df.groupby("Security"):

    g = g.sort_values("Date")

    prices = g["Price"].dropna()
    returns = g["Daily_Return"].dropna()

    if len(prices) < 2:
        continue

    start_price = prices.iloc[0]
    end_price = prices.iloc[-1]

    total_return = (
        end_price / start_price - 1
        if start_price > 0
        else np.nan
    )

    days = (
        g["Date"].max() - g["Date"].min()
    ).days

    annualized_return = np.nan

    if (
        days > 365
        and start_price > 0
    ):
        annualized_return = (
            (end_price / start_price)
            ** (365 / days)
            - 1
        )

    annualized_volatility = np.nan

    if len(returns) > 1:
        annualized_volatility = (
            returns.std()
            * np.sqrt(252)
        )

    # Wealth index from simple returns.
    wealth = (
        1 + returns
    ).cumprod()

    drawdown = (
        wealth / wealth.cummax()
        - 1
    )

    max_drawdown = (
        drawdown.min()
        if len(drawdown)
        else np.nan
    )

    average_volume = (
        g["Volume"].mean()
    )

    total_foreign_flow = (
        g["Net_Foreign_Flow"]
        .sum(min_count=1)
    )

    positive_days = (
        (returns > 0).mean()
        if len(returns)
        else np.nan
    )

    metrics.append({
        "Security": security,
        "Start_Date": g["Date"].min().date(),
        "End_Date": g["Date"].max().date(),
        "Observations": len(g),
        "First_Price": start_price,
        "Last_Price": end_price,
        "Total_Return": total_return,
        "Annualized_Return": annualized_return,
        "Annualized_Volatility": annualized_volatility,
        "Maximum_Drawdown": max_drawdown,
        "Average_Volume": average_volume,
        "Total_Net_Foreign_Flow": total_foreign_flow,
        "Positive_Return_Days": positive_days
    })

metrics = pd.DataFrame(metrics)

metrics.to_csv(
    OUT / "security_metrics.csv",
    index=False
)

print(
    f"✓ Security metrics: "
    f"{len(metrics):,} series"
)

# ============================================================
# 3. ROLLING RISK MEASURES
# ============================================================

rolling = []

for security, g in df.groupby("Security"):

    g = g.sort_values("Date").copy()

    g["Vol_21D"] = (
        g["Daily_Return"]
        .rolling(21)
        .std()
        * np.sqrt(252)
    )

    g["Vol_63D"] = (
        g["Daily_Return"]
        .rolling(63)
        .std()
        * np.sqrt(252)
    )

    rolling.append(
        g[
            [
                "Date",
                "Security",
                "Price",
                "Daily_Return",
                "Vol_21D",
                "Vol_63D"
            ]
        ]
    )

rolling_df = pd.concat(
    rolling,
    ignore_index=True
)

rolling_df.to_csv(
    OUT / "rolling_risk.csv",
    index=False
)

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
        prices.iloc[-1] /
        prices.iloc[0]
        - 1
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
        "Annualized_Volatility": volatility
    })

benchmark_metrics = pd.DataFrame(
    benchmark_metrics
)

benchmark_metrics.to_csv(
    OUT / "benchmark_metrics.csv",
    index=False
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
    "outputs": [
        "security_metrics.csv",
        "rolling_risk.csv",
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
