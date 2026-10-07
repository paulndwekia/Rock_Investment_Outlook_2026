from pathlib import Path
from datetime import datetime
import sqlite3
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"

DB = PROJECT / "database" / "rock_investment_intelligence.db"
ANALYSIS = PROJECT / "analysis"
REPORT = PROJECT / "report"
CHARTS = REPORT / "charts"

CHARTS.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("ROCK INVESTMENT RESEARCH & REPORT ENGINE")
print("=" * 80)

conn = sqlite3.connect(DB)

# ============================================================
# LOAD DATA
# ============================================================

nse = pd.read_sql_query(
    """
    SELECT
        Date,
        Security,
        "Price (KES)" AS Price,
        Volume,
        "Net Foreign Flow" AS Foreign_Flow
    FROM rock_nse_analysis
    """,
    conn
)

nse["Date"] = pd.to_datetime(
    nse["Date"],
    errors="coerce"
)

for col in [
    "Price",
    "Volume",
    "Foreign_Flow"
]:

    nse[col] = pd.to_numeric(
        nse[col],
        errors="coerce"
    )

nse = nse.dropna(
    subset=["Date"]
)

nse = nse.sort_values(
    ["Security", "Date"]
)

nse["Return"] = (
    nse.groupby("Security")["Price"]
    .pct_change()
)

print(
    f"\nNSE observations: {len(nse):,}"
)

print(
    f"Securities/series: "
    f"{nse['Security'].nunique():,}"
)

# ============================================================
# MARKET-WIDE DAILY DATA
# ============================================================

daily = (
    nse.groupby("Date")
    .agg(
        Mean_Return=("Return", "mean"),
        Median_Return=("Return", "median"),
        Total_Volume=("Volume", "sum"),
        Foreign_Flow=("Foreign_Flow", "sum"),
        Securities=("Security", "nunique")
    )
    .reset_index()
)

# Breadth.
breadth = (
    nse.assign(
        Up=nse["Return"] > 0,
        Down=nse["Return"] < 0
    )
    .groupby("Date")
    .agg(
        Advancing=("Up", "sum"),
        Declining=("Down", "sum")
    )
    .reset_index()
)

daily = daily.merge(
    breadth,
    on="Date",
    how="left"
)

daily["Breadth"] = (
    daily["Advancing"]
    /
    (
        daily["Advancing"]
        +
        daily["Declining"]
    )
)

# ============================================================
# MONTHLY MARKET SERIES
# ============================================================

nse["Month"] = (
    nse["Date"]
    .dt.to_period("M")
    .astype(str)
)

monthly = (
    nse.groupby(
        ["Month", "Security"],
        as_index=False
    )
    .agg(
        Mean_Price=("Price", "mean"),
        Volume=("Volume", "sum"),
        Foreign_Flow=("Foreign_Flow", "sum")
    )
)

monthly = monthly.sort_values(
    ["Security", "Month"]
)

monthly["Monthly_Return"] = (
    monthly.groupby("Security")
    ["Mean_Price"]
    .pct_change()
)

market_monthly = (
    monthly.groupby("Month")
    .agg(
        Market_Return=(
            "Monthly_Return",
            "mean"
        ),
        Market_Volume=(
            "Volume",
            "sum"
        ),
        Market_Foreign_Flow=(
            "Foreign_Flow",
            "sum"
        ),
        Securities=(
            "Security",
            "nunique"
        )
    )
    .reset_index()
)

market_monthly.to_csv(
    ANALYSIS /
    "final_market_monthly.csv",
    index=False
)

# ============================================================
# SECURITY RISK / RETURN
# ============================================================

security_stats = []

for security, g in nse.groupby(
    "Security"
):

    g = g.sort_values("Date")

    prices = g["Price"].dropna()
    returns = g["Return"].dropna()

    if len(prices) < 2:
        continue

    total_return = (
        prices.iloc[-1]
        /
        prices.iloc[0]
        - 1
    )

    volatility = np.nan

    if len(returns) > 1:
        volatility = (
            returns.std()
            *
            np.sqrt(252)
        )

    wealth = (
        1 + returns
    ).cumprod()

    drawdown = (
        wealth /
        wealth.cummax()
        - 1
    )

    security_stats.append({
        "Security": security,
        "Observations": len(g),
        "Total_Return": total_return,
        "Annualised_Volatility": volatility,
        "Maximum_Drawdown": (
            drawdown.min()
            if len(drawdown)
            else np.nan
        ),
        "Average_Volume": g["Volume"].mean(),
        "Foreign_Flow": g["Foreign_Flow"].sum(
            min_count=1
        )
    })

stats = pd.DataFrame(
    security_stats
)

stats.to_csv(
    ANALYSIS /
    "final_security_statistics.csv",
    index=False
)

# ============================================================
# CHART 1 — MARKET RETURN
# ============================================================

m = market_monthly.copy()

m["Date"] = pd.to_datetime(
    m["Month"],
    errors="coerce"
)

m = m.sort_values("Date")

plt.figure(
    figsize=(11, 5)
)

plt.plot(
    m["Date"],
    m["Market_Return"]
)

plt.axhline(
    0,
    linewidth=1
)

plt.title(
    "Rock Data Plus — Average Monthly Market Return"
)

plt.xlabel(
    "Date"
)

plt.ylabel(
    "Average monthly return"
)

plt.tight_layout()

plt.savefig(
    CHARTS /
    "01_market_returns.png",
    dpi=180
)

plt.close()

# ============================================================
# CHART 2 — MARKET VOLUME
# ============================================================

plt.figure(
    figsize=(11, 5)
)

plt.plot(
    m["Date"],
    m["Market_Volume"]
)

plt.title(
    "Rock Data Plus — Monthly Trading Volume"
)

plt.xlabel(
    "Date"
)

plt.ylabel(
    "Reported volume"
)

plt.tight_layout()

plt.savefig(
    CHARTS /
    "02_market_volume.png",
    dpi=180
)

plt.close()

# ============================================================
# CHART 3 — FOREIGN FLOWS
# ============================================================

plt.figure(
    figsize=(11, 5)
)

plt.plot(
    m["Date"],
    m["Market_Foreign_Flow"]
)

plt.axhline(
    0,
    linewidth=1
)

plt.title(
    "Rock Data Plus — Reported Net Foreign Flow"
)

plt.xlabel(
    "Date"
)

plt.ylabel(
    "Net foreign flow"
)

plt.tight_layout()

plt.savefig(
    CHARTS /
    "03_foreign_flows.png",
    dpi=180
)

plt.close()

# ============================================================
# CHART 4 — RISK / RETURN
# ============================================================

valid_stats = stats.dropna(
    subset=[
        "Total_Return",
        "Annualised_Volatility"
    ]
)

plt.figure(
    figsize=(10, 7)
)

plt.scatter(
    valid_stats["Annualised_Volatility"],
    valid_stats["Total_Return"]
)

for _, row in valid_stats.nlargest(
    10,
    "Total_Return"
).iterrows():

    plt.annotate(
        str(row["Security"])[:20],
        (
            row["Annualised_Volatility"],
            row["Total_Return"]
        ),
        fontsize=7
    )

plt.axhline(
    0,
    linewidth=1
)

plt.title(
    "Rock Data Plus — Historical Risk / Return"
)

plt.xlabel(
    "Annualised volatility"
)

plt.ylabel(
    "Historical total return"
)

plt.tight_layout()

plt.savefig(
    CHARTS /
    "04_risk_return.png",
    dpi=180
)

plt.close()

# ============================================================
# RECENT MARKET CONDITIONS
# ============================================================

recent = m.tail(12).copy()

recent_return = (
    (1 + recent["Market_Return"].dropna())
    .prod()
    - 1
)

recent_volatility = (
    recent["Market_Return"]
    .dropna()
    .std()
    *
    np.sqrt(12)
)

recent_volume = (
    recent["Market_Volume"]
    .mean()
)

recent_flow = (
    recent["Market_Foreign_Flow"]
    .sum(
        min_count=1
    )
)

positive_months = (
    (
        recent["Market_Return"]
        .dropna()
        > 0
    )
    .mean()
)

# ============================================================
# TOP / BOTTOM HISTORICAL OBSERVATIONS
# ============================================================

top = (
    stats
    .dropna(
        subset=["Total_Return"]
    )
    .sort_values(
        "Total_Return",
        ascending=False
    )
    .head(10)
)

high_risk = (
    stats
    .dropna(
        subset=[
            "Annualised_Volatility"
        ]
    )
    .sort_values(
        "Annualised_Volatility",
        ascending=False
    )
    .head(10)
)

# ============================================================
# DATABASE INVENTORY
# ============================================================

inventory = pd.read_sql_query(
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

# ============================================================
# REPORT
# ============================================================

report = f"""
# KENYA INVESTMENT OUTLOOK 2026

## Rock Data Plus Quantitative Research

**Primary data source:** Rock Data Plus  
**Generated:** {datetime.now():%d %B %Y}

---

## 1. Executive Summary

This research platform analyses Kenyan market and economic
observations obtained from Rock Data Plus.

The current NSE research dataset contains **{len(nse):,} observations
across {nse["Security"].nunique():,} securities/series**.

The available historical NSE observations run from
**{nse["Date"].min():%d %b %Y} to {nse["Date"].max():%d %b %Y}**.

The analysis combines market performance, trading activity,
foreign-flow observations, historical risk, fixed-income
information and selected Rock macroeconomic datasets.

No external market-data source is used in the quantitative
research dataset.

---

## 2. Recent Historical Market Environment

Over the latest 12 monthly observations available in the
research dataset:

**Observed cumulative market return:** {recent_return:.2%}

**Annualised volatility of monthly market returns:** {recent_volatility:.2%}

**Average monthly reported volume:** {recent_volume:,.2f}

**Cumulative reported net foreign flow:** {recent_flow:,.2f}

**Share of positive months:** {positive_months:.1%}

These are historical measurements rather than guarantees of
future performance.

---

## 3. Historical Risk and Return

The security-level analysis calculates:

- Historical total return
- Annualised volatility
- Maximum drawdown
- Average reported trading volume
- Aggregate reported net foreign flow

### Highest historical total returns in the available sample

"""

for _, row in top.iterrows():

    report += (
        f"- **{row['Security']}** — "
        f"total return {row['Total_Return']:.2%}; "
        f"annualised volatility "
        f"{row['Annualised_Volatility']:.2%}.\n"
    )

report += """

### Highest historical realised volatility

"""

for _, row in high_risk.iterrows():

    report += (
        f"- **{row['Security']}** — "
        f"annualised volatility "
        f"{row['Annualised_Volatility']:.2%}; "
        f"maximum drawdown "
        f"{row['Maximum_Drawdown']:.2%}.\n"
    )

report += """

---

## 4. Cross-Market Research Framework

The platform compares market behaviour with the Rock datasets
available in the database, including:

- Exchange rates
- Inflation
- Historical PMI
- Fuel prices
- Liquidity indicators
- Monetary policy indicators
- Foreign reserves
- Public debt
- Treasury Bills
- NSE Bond Index
- Yield Curve
- Diaspora remittances
- International arrivals
- Agriculture

Where different datasets have different frequencies, they are
kept at their appropriate frequency rather than being treated
as identical daily observations.

---

## 5. 12-Month Outlook Framework

The forward-looking analysis distinguishes historical evidence
from scenarios.

### Base scenario

The baseline case is defined by the continuation of market
conditions broadly consistent with the observed historical
regime, subject to changes in volatility, liquidity, trading
activity, foreign flows and macroeconomic indicators.

### Supportive scenario

A more supportive environment would be characterised by
improving market performance and participation while realised
risk remains comparatively contained.

### Adverse scenario

A weaker environment would be characterised by deteriorating
performance, increasing realised volatility, deeper drawdowns
and weakening participation.

The scenarios are analytical frameworks and are not guarantees
of future investment performance.

---

## 6. Data Governance

The analysis uses Rock Data Plus as the primary and sole
market-data source.

The project preserves provenance through:

- Source file records
- Source hashes
- Import timestamps
- Database records
- Dataset-level metadata
- Duplicate control

The NSE export initially contained 190,409 records.
After identification of 8,855 exact duplicate records,
181,554 unique observations were retained for research.

Raw Rock datasets should not be redistributed publicly
unless Rock Data Plus licensing terms permit that use.

---

## 7. Interactive Platform

The accompanying Kenya Investment Intelligence platform
provides interactive exploration of the underlying Rock
observations and derived quantitative analytics.

The website should be used alongside this report to inspect
individual securities, risk measures, market activity,
fixed-income data and macroeconomic observations.

---

## 8. Charts

The report package contains:

- Market return history
- Trading volume history
- Net foreign-flow history
- Historical risk/return map

"""
for chart in [
    "01_market_returns.png",
    "02_market_volume.png",
    "03_foreign_flows.png",
    "04_risk_return.png"
]:

    report += f"- `{chart}`\n"

report_path = (
    REPORT /
    "Rock_Investment_Outlook_2026_Report.md"
)

report_path.write_text(
    report.strip(),
    encoding="utf-8"
)

# ============================================================
# JSON RESEARCH PACKAGE
# ============================================================

package = {
    "generated_at":
        datetime.now().isoformat(),

    "source":
        "Rock Data Plus",

    "external_market_data_used":
        False,

    "nse_observations":
        int(len(nse)),

    "nse_series":
        int(nse["Security"].nunique()),

    "nse_start":
        str(nse["Date"].min().date()),

    "nse_end":
        str(nse["Date"].max().date()),

    "recent_12_month_return":
        float(recent_return),

    "recent_12_month_annualised_volatility":
        float(recent_volatility)
        if pd.notna(recent_volatility)
        else None,

    "recent_positive_month_share":
        float(positive_months),

    "recent_foreign_flow":
        float(recent_flow)
        if pd.notna(recent_flow)
        else None,

    "top_historical_series":
        top[
            [
                "Security",
                "Total_Return",
                "Annualised_Volatility",
                "Maximum_Drawdown"
            ]
        ].to_dict(
            orient="records"
        ),

    "datasets":
        inventory.to_dict(
            orient="records"
        ),

    "charts":
        [
            str(
                CHARTS / x
            )
            for x in [
                "01_market_returns.png",
                "02_market_volume.png",
                "03_foreign_flows.png",
                "04_risk_return.png"
            ]
        ],

    "report":
        str(report_path)
}

(
    REPORT /
    "research_package.json"
).write_text(
    json.dumps(
        package,
        indent=2
    ),
    encoding="utf-8"
)

conn.close()

print("\n" + "=" * 80)
print("RESEARCH & REPORT ENGINE COMPLETE")
print("=" * 80)

print("\nReport:")
print(report_path)

print("\nCharts:")
print(CHARTS)

print("\nResearch package:")
print(REPORT / "research_package.json")

print("\nAll quantitative inputs are Rock Data Plus observations.")
