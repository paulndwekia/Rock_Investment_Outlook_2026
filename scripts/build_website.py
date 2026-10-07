from pathlib import Path

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
WEBSITE = PROJECT / "website"

WEBSITE.mkdir(parents=True, exist_ok=True)

app = r'''
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# KENYA INVESTMENT INTELLIGENCE
# Rock Data Plus powered research platform
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "database" / "rock_investment_intelligence.db"

st.set_page_config(
    page_title="Kenya Investment Intelligence",
    page_icon="🇰🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------------------------------------
# Custom appearance
# ------------------------------------------------------------

st.markdown("""
<style>

.main {
    background: #0b1020;
}

.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

h1, h2, h3 {
    letter-spacing: 0.02em;
}

.hero {
    padding: 2rem 2.2rem;
    border-radius: 20px;
    background:
        linear-gradient(
            135deg,
            rgba(19, 34, 75, 0.98),
            rgba(39, 27, 65, 0.96)
        );
    border: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 1.5rem;
}

.hero-title {
    font-size: 2.6rem;
    font-weight: 800;
    margin-bottom: 0.4rem;
}

.hero-subtitle {
    font-size: 1.05rem;
    opacity: 0.80;
}

.source-pill {
    display: inline-block;
    margin-top: 1rem;
    padding: 0.4rem 0.8rem;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,0.12);
    font-size: 0.85rem;
}

.section {
    margin-top: 1.5rem;
    margin-bottom: 0.8rem;
}

.metric-card {
    padding: 1rem;
    border-radius: 16px;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.025);
}

.small-note {
    font-size: 0.82rem;
    opacity: 0.70;
}

</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Database loader
# ------------------------------------------------------------

@st.cache_data(ttl=300)
def load_market_data():

    conn = sqlite3.connect(DB)

    df = pd.read_sql_query(
        """
        SELECT
            Date,
            Security,
            "Price (KES)" AS Price,
            Volume,
            "Net Foreign Flow" AS Foreign_Flow,
            "Change %" AS Change_Pct
        FROM rock_nse_analysis
        ORDER BY Security, Date
        """,
        conn
    )

    conn.close()

    df["Date"] = pd.to_datetime(
        df["Date"],
        errors="coerce"
    )

    for col in [
        "Price",
        "Volume",
        "Foreign_Flow",
        "Change_Pct"
    ]:
        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        )

    df["Return"] = (
        df.groupby("Security")["Price"]
        .pct_change()
    )

    return df


@st.cache_data(ttl=300)
def load_database_summary():

    conn = sqlite3.connect(DB)

    data = pd.read_sql_query(
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

    conn.close()

    return data


df = load_market_data()
db_summary = load_database_summary()

if df.empty:
    st.error(
        "The Rock NSE dataset is empty. "
        "Run the database build first."
    )
    st.stop()

# ------------------------------------------------------------
# Header
# ------------------------------------------------------------

st.markdown("""
<div class="hero">

<div class="hero-title">
🇰🇪 Kenya Investment Intelligence
</div>

<div class="hero-subtitle">
Quantitative market research platform built around
Rock Data Plus observations.
</div>

<div class="source-pill">
PRIMARY SOURCE: ROCK DATA PLUS
</div>

</div>
""", unsafe_allow_html=True)

# ------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------

st.sidebar.title("Research Console")

page = st.sidebar.radio(
    "Navigate",
    [
        "Executive Dashboard",
        "Market Analytics",
        "Security Research",
        "Risk Analytics",
        "Fixed Income",
        "Macro Environment",
        "12-Month Outlook",
        "Data & Methodology"
    ]
)

st.sidebar.divider()

st.sidebar.caption(
    "The analytical dataset is sourced from Rock Data Plus. "
    "Derived metrics are calculated within this platform."
)

if st.sidebar.button("↻ Refresh data"):

    st.cache_data.clear()
    st.rerun()

# ------------------------------------------------------------
# Common metrics
# ------------------------------------------------------------

latest_date = df["Date"].max()
first_date = df["Date"].min()

latest = df[
    df["Date"] == latest_date
]

securities = df["Security"].nunique()
observations = len(df)

# ------------------------------------------------------------
# EXECUTIVE DASHBOARD
# ------------------------------------------------------------

if page == "Executive Dashboard":

    st.header("Executive Dashboard")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Securities / Series",
        f"{securities:,}"
    )

    c2.metric(
        "NSE Observations",
        f"{observations:,}"
    )

    c3.metric(
        "Historical Start",
        first_date.strftime("%d %b %Y")
    )

    c4.metric(
        "Latest Rock Observation",
        latest_date.strftime("%d %b %Y")
    )

    st.markdown(
        '<div class="section"><h3>Market Snapshot</h3></div>',
        unsafe_allow_html=True
    )

    # Aggregate market activity.
    daily = (
        df.groupby("Date")
        .agg(
            Total_Volume=("Volume", "sum"),
            Foreign_Flow=("Foreign_Flow", "sum"),
            Mean_Return=("Return", "mean"),
            Securities=("Security", "nunique")
        )
        .reset_index()
    )

    left, right = st.columns(2)

    with left:

        fig = px.line(
            daily,
            x="Date",
            y="Total_Volume",
            title="Reported Trading Volume"
        )

        fig.update_layout(
            template="plotly_dark",
            height=420
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with right:

        flow = daily.dropna(
            subset=["Foreign_Flow"]
        )

        fig = px.line(
            flow,
            x="Date",
            y="Foreign_Flow",
            title="Reported Net Foreign Flow"
        )

        fig.update_layout(
            template="plotly_dark",
            height=420
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.subheader(
        "Latest Market Observations"
    )

    st.dataframe(
        latest.sort_values(
            "Volume",
            ascending=False
        ).head(40),
        use_container_width=True
    )

# ------------------------------------------------------------
# MARKET ANALYTICS
# ------------------------------------------------------------

elif page == "Market Analytics":

    st.header("Market Analytics")

    monthly = (
        df.assign(
            Month=df["Date"]
            .dt.to_period("M")
            .astype(str)
        )
        .groupby(
            "Month",
            as_index=False
        )
        .agg(
            Average_Return=("Return", "mean"),
            Volume=("Volume", "sum"),
            Foreign_Flow=("Foreign_Flow", "sum"),
            Securities=("Security", "nunique")
        )
    )

    fig = px.line(
        monthly,
        x="Month",
        y="Average_Return",
        title="Average Monthly Security Return"
    )

    fig.update_layout(
        template="plotly_dark",
        height=480
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.subheader(
        "Monthly Market Activity"
    )

    st.dataframe(
        monthly.sort_values(
            "Month",
            ascending=False
        ),
        use_container_width=True
    )

# ------------------------------------------------------------
# SECURITY RESEARCH
# ------------------------------------------------------------

elif page == "Security Research":

    st.header("Security Research")

    securities_list = sorted(
        df["Security"]
        .dropna()
        .unique()
    )

    security = st.selectbox(
        "Select security",
        securities_list
    )

    x = df[
        df["Security"] == security
    ].sort_values("Date").copy()

    prices = x["Price"].dropna()
    returns = x["Return"].dropna()

    if len(prices) >= 2:

        total_return = (
            prices.iloc[-1] /
            prices.iloc[0]
            - 1
        )

        volatility = (
            returns.std() *
            np.sqrt(252)
            if len(returns) > 1
            else np.nan
        )

        wealth = (
            1 + returns
        ).cumprod()

        drawdown = (
            wealth /
            wealth.cummax()
            - 1
        )

        max_drawdown = (
            drawdown.min()
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Historical Return",
            f"{total_return:.2%}"
        )

        c2.metric(
            "Annualised Volatility",
            (
                "N/A"
                if pd.isna(volatility)
                else f"{volatility:.2%}"
            )
        )

        c3.metric(
            "Maximum Drawdown",
            f"{max_drawdown:.2%}"
        )

    fig = px.line(
        x,
        x="Date",
        y="Price",
        title=f"{security} — Rock historical price"
    )

    fig.update_layout(
        template="plotly_dark",
        height=500
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    fig2 = px.line(
        x,
        x="Date",
        y="Return",
        title=f"{security} — Daily return"
    )

    fig2.update_layout(
        template="plotly_dark",
        height=350
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

# ------------------------------------------------------------
# RISK ANALYTICS
# ------------------------------------------------------------

elif page == "Risk Analytics":

    st.header("Risk Analytics")

    results = []

    for security, g in df.groupby(
        "Security"
    ):

        r = g["Return"].dropna()

        if len(r) < 20:
            continue

        vol = (
            r.std() *
            np.sqrt(252)
        )

        wealth = (
            1 + r
        ).cumprod()

        drawdown = (
            wealth /
            wealth.cummax()
            - 1
        )

        results.append({
            "Security": security,
            "Annualised_Volatility": vol,
            "Maximum_Drawdown": drawdown.min(),
            "Observations": len(r)
        })

    risk = pd.DataFrame(results)

    fig = px.scatter(
        risk,
        x="Annualised_Volatility",
        y="Maximum_Drawdown",
        hover_name="Security",
        title="Historical Volatility vs Maximum Drawdown"
    )

    fig.update_layout(
        template="plotly_dark",
        height=520
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    st.dataframe(
        risk.sort_values(
            "Annualised_Volatility",
            ascending=False
        ),
        use_container_width=True
    )

# ------------------------------------------------------------
# FIXED INCOME
# ------------------------------------------------------------

elif page == "Fixed Income":

    st.header("Fixed Income")

    conn = sqlite3.connect(DB)

    fixed_tables = {}

    for name in [
        "treasury_bills",
        "nse_bond_index",
        "yield_curve",
        "public_debt"
    ]:

        try:

            q = pd.read_sql_query(
                """
                SELECT
                    dataset_name,
                    sheet_name,
                    row_json,
                    observed_date,
                    source_file
                FROM rock_observations
                WHERE dataset_name = ?
                """,
                conn,
                params=(name,)
            )

            fixed_tables[name] = q

        except Exception:
            fixed_tables[name] = pd.DataFrame()

    conn.close()

    tabs = st.tabs(
        [
            "Treasury Bills",
            "NSE Bond Index",
            "Yield Curve",
            "Public Debt"
        ]
    )

    for tab, name in zip(
        tabs,
        [
            "treasury_bills",
            "nse_bond_index",
            "yield_curve",
            "public_debt"
        ]
    ):

        with tab:

            data = fixed_tables[name]

            if data.empty:

                st.info(
                    f"No {name} observations found."
                )

            else:

                st.metric(
                    "Rock observations",
                    f"{len(data):,}"
                )

                st.dataframe(
                    data,
                    use_container_width=True
                )

    st.info(
        "The Yield Curve dataset is handled as a maturity/yield "
        "snapshot where no historical observation date is provided."
    )

# ------------------------------------------------------------
# MACRO ENVIRONMENT
# ------------------------------------------------------------

elif page == "Macro Environment":

    st.header("Macro Environment")

    macro = db_summary[
        db_summary["dataset_name"].isin(
            [
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
        )
    ].copy()

    st.subheader(
        "Rock datasets available to the research engine"
    )

    st.dataframe(
        macro,
        use_container_width=True
    )

    st.markdown(
        """
The macro layer is deliberately separated by dataset because
Rock data arrive at different frequencies and use different
measurements. The research engine does not assume that daily,
monthly, annual and snapshot observations are interchangeable.
"""
    )

# ------------------------------------------------------------
# 12-MONTH OUTLOOK
# ------------------------------------------------------------

elif page == "12-Month Outlook":

    st.header(
        "12-Month Investment Outlook"
    )

    st.warning(
        "This section separates historical Rock evidence from "
        "forward-looking scenarios. Historical performance is "
        "not a guarantee of future results."
    )

    st.subheader(
        "Evidence Base"
    )

    st.write(
        f"The current equity research dataset contains "
        f"{observations:,} observations across "
        f"{securities:,} securities/series, with observations "
        f"running from {first_date:%d %b %Y} to "
        f"{latest_date:%d %b %Y}."
    )

    st.subheader(
        "Scenario Framework"
    )

    c1, c2, c3 = st.columns(3)

    with c1:

        st.markdown("### Base Environment")

        st.write(
            "Assess whether market performance, realised risk, "
            "trading activity and benchmark behaviour remain "
            "broadly consistent with the observed regime."
        )

    with c2:

        st.markdown("### Supportive Scenario")

        st.write(
            "Monitor for improving market performance, "
            "supportive participation and stable or declining "
            "realised risk."
        )

    with c3:

        st.markdown("### Adverse Scenario")

        st.write(
            "Monitor for deteriorating performance, increasing "
            "volatility, deeper drawdowns and weakening activity."
        )

    st.subheader(
        "Variables to Monitor"
    )

    st.markdown(
        """
**Equities:** returns, volatility, drawdowns and trading volume.

**Market participation:** reported net foreign-flow behaviour.

**Fixed income:** Treasury Bills, bond-index observations and
the Rock yield-curve snapshot.

**Macro environment:** inflation, exchange rates, PMI,
liquidity, monetary conditions, reserves and other Rock
datasets where the observations support analysis.
"""
    )

# ------------------------------------------------------------
# DATA & METHODOLOGY
# ------------------------------------------------------------

elif page == "Data & Methodology":

    st.header(
        "Data & Methodology"
    )

    st.subheader(
        "Primary Data Source"
    )

    st.write(
        "Rock Data Plus"
    )

    st.subheader(
        "Data Architecture"
    )

    st.code(
        """
Rock Data Plus
      ↓
Curated Rock datasets
      ↓
SQLite database
      ↓
Quantitative research engine
      ↓
Interactive website
        """,
        language="text"
    )

    st.subheader(
        "Database Inventory"
    )

    st.dataframe(
        db_summary,
        use_container_width=True
    )

    st.subheader(
        "Important Data-Governance Notes"
    )

    st.markdown(
        """
- Raw Rock exports are preserved locally.
- Dataset-level provenance is recorded.
- Duplicate NSE observations were identified and removed
  before quantitative analysis.
- The NSE dataset contains 181,554 unique observations after
  removal of 8,855 exact duplicate records from the 190,409-row
  Rock export.
- The Rock Yield Curve file is a 32-row maturity/yield snapshot
  rather than a dated historical time series.
- Raw Rock data should not be redistributed publicly unless
  Rock Investment Bank's terms permit that use.
"""
    )

    st.subheader(
        "Data Refresh"
    )

    st.write(
        "The application reads from the SQLite database rather "
        "than hard-coded market figures. Future authorized Rock "
        "data updates can therefore extend the database without "
        "redesigning the website."
    )

st.divider()

st.caption(
    "Source: Rock Data Plus | "
    "Derived statistics calculated by the research engine."
)
'''

(WEBSITE / "app.py").write_text(
    app.strip(),
    encoding="utf-8"
)

print("Website created:")
print(WEBSITE / "app.py")

print("\nStarting website...")
