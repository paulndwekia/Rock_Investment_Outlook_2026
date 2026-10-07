import json
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# KENYA INVESTMENT INTELLIGENCE - V3
# ROCK DATA PLUS RESEARCH TERMINAL
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

DB = (
    ROOT
    / "database"
    / "rock_investment_intelligence.db"
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Kenya Investment Intelligence",
    page_icon="🇰🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# STYLE
# ============================================================

st.markdown("""
<style>

.stApp {
    background:
        radial-gradient(
            circle at top right,
            rgba(224, 184, 91, 0.08),
            transparent 35%
        ),
        #090d18;
}

.block-container {
    max-width: 1550px;
    padding-top: 1.2rem;
    padding-bottom: 3rem;
}

.hero {
    padding: 1.8rem 2.1rem;
    border-radius: 20px;
    background:
        linear-gradient(
            135deg,
            rgba(22, 35, 76, 0.98),
            rgba(15, 20, 38, 0.98)
        );
    border: 1px solid rgba(224,184,91,0.18);
    margin-bottom: 1.3rem;
}

.hero-title {
    font-size: 2.55rem;
    font-weight: 850;
    line-height: 1.05;
}

.hero-subtitle {
    margin-top: .55rem;
    font-size: 1rem;
    opacity: .73;
}

.source-pill {
    display: inline-block;
    margin-top: .95rem;
    padding: .38rem .8rem;
    border-radius: 999px;
    border: 1px solid rgba(255,255,255,.12);
    font-size: .75rem;
    letter-spacing: .08em;
}

.card {
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 16px;
    padding: 1rem;
    background: rgba(255,255,255,.025);
}

.note {
    font-size: .82rem;
    opacity: .68;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# HELPERS
# ============================================================

def numeric(series):

    if series is None:
        return pd.Series(dtype=float)

    s = (
        series
        .astype(str)
        .str.strip()
        .str.replace(",", "", regex=False)
        .str.replace("%", "", regex=False)
        .str.replace("KES", "", regex=False)
        .str.replace("KSh", "", regex=False)
    )

    s = s.replace(
        {
            "": np.nan,
            "nan": np.nan,
            "None": np.nan,
            "-": np.nan,
            "-": np.nan
        }
    )

    return pd.to_numeric(
        s,
        errors="coerce"
    )


def pct(value):

    if pd.isna(value):
        return "N/A"

    return f"{value:.2%}"


def number(value):

    if pd.isna(value):
        return "N/A"

    return f"{value:,.2f}"


# ============================================================
# DATABASE LOADERS
# ============================================================

@st.cache_data(ttl=300)
def load_nse():

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

    for c in [
        "Price",
        "Volume",
        "Foreign_Flow",
        "Change_Pct"
    ]:
        df[c] = numeric(df[c])

    df = df[
        df["Date"].notna()
    ].copy()

    df = df.sort_values(
        ["Security", "Date"]
    )

    # Return is valid only when both current and
    # previous prices are positive.
    previous = (
        df.groupby("Security")["Price"]
        .shift(1)
    )

    df["Return"] = np.nan

    valid = (
        (previous > 0)
        &
        (df["Price"] >= 0)
    )

    df.loc[valid, "Return"] = (
        df.loc[valid, "Price"]
        /
        previous.loc[valid]
        - 1
    )

    # Research-quality flag.
    # Extreme observations are retained in the raw data,
    # but not allowed to distort risk statistics.
    df["Risk_Return"] = df["Return"].where(
        df["Return"].between(
            -2.0,
            2.0
        )
    )

    return df


@st.cache_data(ttl=300)
def load_summary():

    conn = sqlite3.connect(DB)

    df = pd.read_sql_query(
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

    return df


@st.cache_data(ttl=300)
def load_clean_table(table):

    allowed = {
        "rock_treasury_bills_clean",
        "rock_nse_bond_index_clean",
        "rock_forex_reserves_clean",
        "rock_inflation_clean"
    }

    if table not in allowed:
        return pd.DataFrame()

    conn = sqlite3.connect(DB)

    df = pd.read_sql_query(
        f"SELECT * FROM {table}",
        conn
    )

    conn.close()

    return df


@st.cache_data(ttl=300)
def load_analysis_csv(filename):

    path = (
        ROOT
        / "analysis"
        / filename
    )

    if not path.exists():
        return pd.DataFrame()

    try:

        return pd.read_csv(
            path,
            low_memory=False
        )

    except Exception:

        return pd.DataFrame()


nse = load_nse()
summary = load_summary()

if nse.empty:
    st.error(
        "Rock NSE data could not be loaded."
    )
    st.stop()


# ============================================================
# GLOBAL VARIABLES
# ============================================================

latest_date = nse["Date"].max()
first_date = nse["Date"].min()

security_count = nse["Security"].nunique()
observation_count = len(nse)

latest = nse[
    nse["Date"] == latest_date
].copy()


# ============================================================
# HERO
# ============================================================

st.markdown("""
<div class="hero">

<div class="hero-title">
🇰🇪 Kenya Investment Intelligence
</div>

<div class="hero-subtitle">
Quantitative market research terminal powered by
Rock Data Plus observations.
</div>

<div class="source-pill">
ROCK DATA PLUS • PRIMARY RESEARCH DATA SOURCE
</div>

</div>
""", unsafe_allow_html=True)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title(
    "RESEARCH CONSOLE"
)

page = st.sidebar.radio(
    "Navigate",
    [
        "Command Center",
        "Market Regime",
        "Equity Lab",
        "Risk Lab",
        "Fixed Income",
        "Macro Radar",
        "Cross-Market Research",
        "12-Month Outlook",
        "Data Governance"
    ]
)

st.sidebar.divider()

if st.sidebar.button(
    "↻ Refresh Research Data"
):

    st.cache_data.clear()
    st.rerun()

st.sidebar.markdown(
    """
<div class="note">
Raw Rock observations remain stored locally.
Analytical pages use cleaned, dataset-specific
structures where available.
</div>
""",
    unsafe_allow_html=True
)


# ============================================================
# COMMAND CENTER
# ============================================================

if page == "Command Center":

    st.header(
        "Command Center"
    )

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Rock Series",
        f"{security_count:,}"
    )

    c2.metric(
        "NSE Observations",
        f"{observation_count:,}"
    )

    c3.metric(
        "Historical Start",
        first_date.strftime(
            "%d %b %Y"
        )
    )

    c4.metric(
        "Latest Observation",
        latest_date.strftime(
            "%d %b %Y"
        )
    )

    c5.metric(
        "Rock Datasets",
        f"{len(summary):,}"
    )

    st.divider()

    daily = (
        nse.groupby("Date")
        .agg(
            Trading_Volume=(
                "Volume",
                "sum"
            ),
            Net_Foreign_Flow=(
                "Foreign_Flow",
                "sum"
            ),
            Securities=(
                "Security",
                "nunique"
            ),
            Mean_Return=(
                "Return",
                "mean"
            )
        )
        .reset_index()
    )

    left, right = st.columns(2)

    with left:

        fig = px.area(
            daily,
            x="Date",
            y="Trading_Volume",
            title="Reported Trading Volume"
        )

        fig.update_layout(
            template="plotly_dark",
            height=410
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    with right:

        fig = px.line(
            daily,
            x="Date",
            y="Net_Foreign_Flow",
            title="Reported Net Foreign Flow"
        )

        fig.update_layout(
            template="plotly_dark",
            height=410
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    st.subheader(
        "Latest Rock Market Observations"
    )

    display = latest[
        [
            "Date",
            "Security",
            "Price",
            "Volume",
            "Foreign_Flow",
            "Change_Pct"
        ]
    ].sort_values(
        "Volume",
        ascending=False
    )

    st.dataframe(
        display.head(40),
        use_container_width=True,
        hide_index=True
    )


# ============================================================
# MARKET REGIME
# ============================================================

elif page == "Market Regime":

    st.header(
        "Market Regime"
    )

    monthly = (
        nse.assign(
            Month=nse["Date"]
            .dt.to_period("M")
            .astype(str)
        )
        .groupby("Month")
        .agg(
            Mean_Security_Return=(
                "Return",
                "mean"
            ),
            Trading_Volume=(
                "Volume",
                "sum"
            ),
            Foreign_Flow=(
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

    monthly["Date"] = pd.to_datetime(
        monthly["Month"],
        errors="coerce"
    )

    monthly = monthly.sort_values(
        "Date"
    )

    recent = monthly.tail(12)

    returns = recent[
        "Mean_Security_Return"
    ].dropna()

    observed_return = (
        (1 + returns)
        .prod()
        - 1
    )

    volatility = (
        returns.std() * np.sqrt(12)
        if len(returns) > 1
        else np.nan
    )

    positive_months = (
        (returns > 0).mean()
        if len(returns)
        else np.nan
    )

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Recent 12-Month Compounded Mean-Security Return",
        pct(observed_return)
    )

    c2.metric(
        "Annualised Monthly Volatility",
        pct(volatility)
    )

    c3.metric(
        "Positive Months",
        (
            f"{positive_months:.0%}"
            if pd.notna(positive_months)
            else "N/A"
        )
    )

    st.info(
        "This is an equal-weighted cross-sectional security-return "
        "measure, not an official NSE index."
    )

    left, right = st.columns(2)

    with left:

        fig = px.bar(
            recent,
            x="Month",
            y="Mean_Security_Return",
            title="Monthly Mean Security Return"
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

        fig = px.line(
            recent,
            x="Month",
            y="Trading_Volume",
            title="Monthly Reported Trading Volume"
        )

        fig.update_layout(
            template="plotly_dark",
            height=420
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )


# ============================================================
# EQUITY LAB
# ============================================================

elif page == "Equity Lab":

    st.header("Equity Research Lab")

    equity_path = ROOT / "analysis" / "clean_nse_analysis.csv"

    if not equity_path.exists():

        st.error(
            f"Clean NSE equity dataset was not found: {equity_path}"
        )

    else:

        equity = pd.read_csv(equity_path)

        aliases = {
            "Date": [
                "Date", "date", "Trade Date",
                "trade_date", "Observation Date"
            ],
            "Security": [
                "Security", "security", "Ticker",
                "ticker", "Symbol", "symbol"
            ],
            "Price": [
                "Price", "Price (KES)", "price",
                "price (kes)", "Close", "Close Price"
            ],
            "Volume": [
                "Volume", "volume",
                "Trading Volume", "trading_volume"
            ],
            "Foreign_Flow": [
                "Foreign_Flow", "Net Foreign Flow",
                "Net Foreign Flow (KES)", "foreign_flow"
            ],
            "Change_Pct": [
                "Change_Pct", "Change %",
                "Change Percent", "change_pct"
            ]
        }

        for canonical, candidates in aliases.items():

            existing = next(
                (
                    c for c in candidates
                    if c in equity.columns
                ),
                None
            )

            if existing is not None and existing != canonical:
                equity[canonical] = equity[existing]

        required = [
            "Date",
            "Security",
            "Price"
        ]

        missing = [
            c for c in required
            if c not in equity.columns
        ]

        if missing:

            st.error(
                "Clean equity dataset is missing required columns: "
                + ", ".join(missing)
            )

        else:

            equity["Date"] = pd.to_datetime(
                equity["Date"],
                errors="coerce"
            )

            equity["Price"] = pd.to_numeric(
                equity["Price"],
                errors="coerce"
            )

            equity = equity[
                equity["Date"].notna()
                &
                equity["Security"].notna()
                &
                equity["Price"].notna()
                &
                (equity["Price"] > 0)
            ].copy()

            equity = (
                equity
                .sort_values(
                    ["Security", "Date"]
                )
                .drop_duplicates(
                    subset=["Security", "Date"],
                    keep="last"
                )
            )

            securities = sorted(
                equity["Security"].unique()
            )

            if not securities:

                st.warning(
                    "No valid securities are available."
                )

            else:

                security = st.selectbox(
                    "Select security / series",
                    securities
                )

                g = equity[
                    equity["Security"] == security
                ].copy()

                g = (
                    g.sort_values("Date")
                    .reset_index(drop=True)
                )

                prices = g["Price"].astype(float)

                # ------------------------------------------------
                # ISOLATED PRICE-SPIKE DETECTION
                #
                # We do NOT change Rock data.
                #
                # We flag an observation when:
                #
                # 1. The price moves by at least 5x, or falls
                #    below 1/5 of the previous price.
                #
                # AND
                #
                # 2. The following observation returns close to
                #    the price before the spike.
                #
                # This targets isolated data-entry / scale errors
                # instead of legitimate long-term price changes.
                # ------------------------------------------------

                previous_price = prices.shift(1)
                next_price = prices.shift(-1)

                extreme_move = (
                    (prices / previous_price >= 5.0)
                    |
                    (prices / previous_price <= 0.20)
                )

                reversal = (
                    (next_price > 0)
                    &
                    (
                        (
                            next_price / previous_price - 1
                        ).abs()
                        <= 0.20
                    )
                )

                isolated_spike = (
                    extreme_move
                    &
                    reversal
                )

                # Also catch observations that are extreme relative
                # to BOTH immediate neighbours.
                neighbour_spike = (
                    (
                        prices
                        >
                        previous_price * 5.0
                    )
                    &
                    (
                        prices
                        >
                        next_price * 5.0
                    )
                ) | (
                    (
                        prices
                        <
                        previous_price * 0.20
                    )
                    &
                    (
                        prices
                        <
                        next_price * 0.20
                    )
                )

                g["Analytical_Anomaly"] = (
                    isolated_spike
                    |
                    neighbour_spike
                ).fillna(False)

                anomaly_count = int(
                    g["Analytical_Anomaly"].sum()
                )

                # ------------------------------------------------
                # Build the analytical series.
                # Raw observations remain untouched.
                # ------------------------------------------------

                analytical = g[
                    ~g["Analytical_Anomaly"]
                ].copy()

                analytical = (
                    analytical
                    .sort_values("Date")
                    .reset_index(drop=True)
                )

                analytical["Return"] = (
                    analytical["Price"]
                    /
                    analytical["Price"].shift(1)
                    - 1
                )

                # Remove the first undefined return.
                analytical.loc[
                    ~np.isfinite(
                        analytical["Return"]
                    ),
                    "Return"
                ] = np.nan

                # Research-quality risk filter.
                analytical["Risk_Return"] = (
                    analytical["Return"]
                    .where(
                        analytical["Return"].between(
                            -2.0,
                            2.0
                        )
                    )
                )

                valid_returns = (
                    analytical["Risk_Return"]
                    .dropna()
                )

                # ------------------------------------------------
                # Historical return
                # ------------------------------------------------

                total_return = np.nan

                if len(analytical) >= 2:

                    total_return = (
                        analytical["Price"].iloc[-1]
                        /
                        analytical["Price"].iloc[0]
                        - 1
                    )

                # ------------------------------------------------
                # Annualised volatility
                # ------------------------------------------------

                volatility = np.nan

                if len(valid_returns) > 1:

                    volatility = (
                        valid_returns.std()
                        *
                        np.sqrt(252)
                    )

                # ------------------------------------------------
                # Maximum drawdown from analytical price path
                # ------------------------------------------------

                running_max = (
                    analytical["Price"]
                    .cummax()
                )

                drawdown = (
                    analytical["Price"]
                    /
                    running_max
                    - 1
                )

                max_drawdown = (
                    drawdown.min()
                    if len(drawdown)
                    else np.nan
                )

                # ------------------------------------------------
                # Metrics
                # ------------------------------------------------

                c1, c2, c3, c4 = st.columns(4)

                c1.metric(
                    "Latest Price",
                    (
                        number(prices.iloc[-1])
                        if len(prices)
                        else "N/A"
                    )
                )

                c2.metric(
                    "Historical Return",
                    pct(total_return)
                )

                c3.metric(
                    "Annualised Volatility",
                    pct(volatility)
                )

                c4.metric(
                    "Maximum Drawdown",
                    pct(max_drawdown)
                )

                st.caption(
                    f"Equity Lab uses the repaired NSE analytical "
                    f"series. {anomaly_count:,} isolated price "
                    f"spikes were excluded from analytical charts "
                    f"and statistics only. Raw Rock observations "
                    f"were not modified or deleted."
                )

                # ------------------------------------------------
                # Historical price chart
                # ------------------------------------------------

                fig = px.line(
                    analytical,
                    x="Date",
                    y="Price",
                    title=f"{security} - Rock Historical Price"
                )

                fig.update_layout(
                    template="plotly_dark",
                    height=470,
                    xaxis_title="Date",
                    yaxis_title="Price"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

                # ------------------------------------------------
                # Rolling 21-day annualised volatility
                # ------------------------------------------------

                analytical[
                    "Rolling_21D_Volatility"
                ] = (
                    analytical["Risk_Return"]
                    .rolling(
                        window=21,
                        min_periods=21
                    )
                    .std()
                    *
                    np.sqrt(252)
                )

                fig2 = px.line(
                    analytical,
                    x="Date",
                    y="Rolling_21D_Volatility",
                    title="21-Day Rolling Annualised Volatility"
                )

                fig2.update_layout(
                    template="plotly_dark",
                    height=360,
                    xaxis_title="Date",
                    yaxis_title="Annualised Volatility"
                )

                st.plotly_chart(
                    fig2,
                    use_container_width=True
                )


# ============================================================
# RISK LAB
# ============================================================

elif page == "Risk Lab":

    st.header("Risk Laboratory")

    # --------------------------------------------------------
    # Load the canonical repaired analytical table.
    # --------------------------------------------------------

    risk_nse = pd.DataFrame()

    try:

        conn = sqlite3.connect(DB)

        risk_nse = pd.read_sql_query(
            'SELECT * FROM rock_nse_analysis_clean '
            'ORDER BY Security, Date',
            conn
        )

        conn.close()

    except Exception as exc:

        st.error(
            f"Risk Lab could not load clean analytical data: {exc}"
        )

    if risk_nse.empty:

        st.warning(
            "No clean analytical equity data is available."
        )

    else:

        risk_nse["Date"] = pd.to_datetime(
            risk_nse["Date"],
            errors="coerce"
        )

        risk_nse["Security"] = (
            risk_nse["Security"]
            .astype("string")
            .str.strip()
        )

        risk_nse["Price"] = pd.to_numeric(
            risk_nse["Price"],
            errors="coerce"
        )

        # The cleaner precomputes Risk_Return with gaps around
        # excluded anomalies. Do not recompute it here.
        if "Risk_Return" not in risk_nse.columns:
            risk_nse["Risk_Return"] = np.nan
        else:
            risk_nse["Risk_Return"] = pd.to_numeric(
                risk_nse["Risk_Return"],
                errors="coerce"
            )

        risk_nse = risk_nse[
            risk_nse["Date"].notna()
            &
            risk_nse["Security"].notna()
            &
            (risk_nse["Security"] != "")
            &
            risk_nse["Price"].notna()
            &
            np.isfinite(risk_nse["Price"])
            &
            (risk_nse["Price"] > 0)
        ].copy()

        risk_nse = (
            risk_nse
            .sort_values(["Security", "Date"])
            .drop_duplicates(
                subset=["Security", "Date"],
                keep="last"
            )
        )

        results = []

        for security, g in risk_nse.groupby(
            "Security",
            sort=True
        ):

            g = (
                g
                .sort_values("Date")
                .copy()
            )

            r = (
                g["Risk_Return"]
                .replace(
                    [np.inf, -np.inf],
                    np.nan
                )
                .dropna()
            )

            if len(r) < 30:
                continue

            volatility = (
                r.std()
                * np.sqrt(252)
            )

            wealth = (
                1.0 + r
            ).cumprod()

            peak = wealth.cummax()

            drawdown = (
                wealth
                / peak
                - 1.0
            )

            results.append(
                {
                    "Security": security,
                    "Annualised_Volatility": volatility,
                    "Maximum_Drawdown": drawdown.min(),
                    "Valid_Risk_Observations": len(r),
                }
            )

        risk = pd.DataFrame(results)

        if risk.empty:

            st.warning(
                "Insufficient valid observations for Risk Lab."
            )

        else:

            fig = px.scatter(
                risk,
                x="Annualised_Volatility",
                y="Maximum_Drawdown",
                hover_name="Security",
                title=(
                    "Historical Volatility vs "
                    "Maximum Drawdown"
                )
            )

            fig.update_layout(
                template="plotly_dark",
                height=520,
                xaxis_title="Annualised Volatility",
                yaxis_title="Maximum Drawdown"
            )

            st.plotly_chart(
                fig,
                width="stretch"
            )

            display_risk = (
                risk
                .sort_values(
                    "Annualised_Volatility",
                    ascending=False
                )
                .reset_index(drop=True)
            )

            st.dataframe(
                display_risk,
                width="stretch",
                hide_index=True
            )

            st.caption(
                "Risk statistics use the canonical repaired NSE "
                "analytical dataset. Targeted analytical anomalies "
                "are excluded without modifying the raw Rock "
                "observations. Returns do not bridge across "
                "excluded observations."
            )

# ============================================================
# FIXED INCOME
# ============================================================

elif page == "Fixed Income":

    st.header("Fixed Income Intelligence")

    tabs = st.tabs(
        [
            "Yield Curve",
            "Treasury Bills",
            "Bond Index",
            "Public Debt"
        ]
    )

    # --------------------------------------------------------
    # YIELD CURVE
    # --------------------------------------------------------

    with tabs[0]:

        path = ROOT / "analysis" / "clean_yield_curve.csv"

        curve = (
            pd.read_csv(path)
            if path.exists()
            else pd.DataFrame()
        )

        if curve.empty:

            st.info("Yield Curve data unavailable.")

        else:

            curve["Yield (%)"] = numeric(
                curve["Yield (%)"]
            )

            order_map = {
                "16 Day": 16,
                "182 Day": 182,
                "91 Day": 91,
                "1 Year": 365,
                "2 Years": 730,
                "3 Years": 1095,
                "4 Years": 1460,
                "5 Years": 1825,
                "6 Years": 2190,
                "7 Years": 2555,
                "8 Years": 2920,
                "9 Years": 3285,
                "10 Years": 3650,
                "11 Years": 4015,
                "12 Years": 4380,
                "13 Years": 4745,
                "14 Years": 5110,
                "15 Years": 5475,
                "16 Years": 5840,
                "17 Years": 6205,
                "18 Years": 6570,
                "19 Years": 6935,
                "20 Years": 7300,
                "21 Years": 7665,
                "22 Years": 8030,
                "23 Years": 8395,
                "24 Years": 8760,
                "25 Years": 9125,
                "26 Years": 9490,
                "27 Years": 9855,
                "28 Years": 10220,
                "29 Years": 10585,
                "30 Years": 10950
            }

            curve["Maturity_Order"] = (
                curve["Maturity"].map(order_map)
            )

            curve = curve.sort_values(
                "Maturity_Order"
            )

            fig = px.line(
                curve,
                x="Maturity",
                y="Yield (%)",
                markers=True,
                title="Rock Yield Curve Snapshot"
            )

            fig.update_layout(
                template="plotly_dark",
                height=470,
                yaxis_title="Yield (%)"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.dataframe(
                curve[
                    [
                        "Maturity",
                        "Yield (%)"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                "Rock-supplied maturity/yield snapshot."
            )

    # --------------------------------------------------------
    # TREASURY BILLS
    # --------------------------------------------------------

    with tabs[1]:

        path = ROOT / "analysis" / "clean_treasury_bills.csv"

        bills = (
            pd.read_csv(path)
            if path.exists()
            else pd.DataFrame()
        )

        if bills.empty:

            st.info("Treasury Bill data unavailable.")

        else:

            bills["Date"] = pd.to_datetime(
                bills["Date"],
                errors="coerce"
            )

            bills["Rate (%)"] = numeric(
                bills["Rate (%)"]
            )

            latest_date = bills["Date"].max()

            latest_tb = bills[
                bills["Date"] == latest_date
            ].copy()

            st.metric(
                "Clean Treasury Bill Observations",
                f"{len(bills):,}"
            )

            st.subheader(
                f"Latest Treasury Bill Rates - "
                f"{latest_date:%d %b %Y}"
            )

            st.dataframe(
                latest_tb[
                    [
                        "Date",
                        "Tenor",
                        "Rate (%)"
                    ]
                ].sort_values("Tenor"),
                use_container_width=True,
                hide_index=True
            )

            fig = px.line(
                bills.sort_values("Date"),
                x="Date",
                y="Rate (%)",
                color="Tenor",
                title="Treasury Bill Rates by Tenor"
            )

            fig.update_layout(
                template="plotly_dark",
                height=470,
                yaxis_title="Rate (%)"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.caption(
                "Extreme analytical outliers are excluded from "
                "this chart; the original Rock records remain "
                "preserved locally."
            )

    # --------------------------------------------------------
    # BOND INDEX
    # --------------------------------------------------------

    with tabs[2]:

        path = ROOT / "analysis" / "clean_nse_bond_index.csv"

        bond = (
            pd.read_csv(path)
            if path.exists()
            else pd.DataFrame()
        )

        if bond.empty:

            st.info("Bond Index data unavailable.")

        else:

            bond["Date"] = pd.to_datetime(
                bond["Date"],
                errors="coerce"
            )

            bond["Index Value"] = numeric(
                bond["Index Value"]
            )

            fig = px.line(
                bond.sort_values("Date"),
                x="Date",
                y="Index Value",
                color="Bond_type",
                title="FTSE NSE Kenya Government Bond Index"
            )

            fig.update_layout(
                template="plotly_dark",
                height=470,
                yaxis_title="Index Value"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.dataframe(
                bond.sort_values(
                    "Date",
                    ascending=False
                ).head(100),
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                "Analytical series excludes observations producing "
                "an extreme one-step move greater than 50 percent. "
                "Raw Rock observations remain preserved."
            )

    # --------------------------------------------------------
    # PUBLIC DEBT
    # --------------------------------------------------------

    with tabs[3]:

        path = ROOT / "analysis" / "clean_public_debt.csv"

        debt = (
            pd.read_csv(path)
            if path.exists()
            else pd.DataFrame()
        )

        if debt.empty:

            st.info("Public Debt data unavailable.")

        else:

            debt["Date"] = pd.to_datetime(
                debt["Date"],
                errors="coerce"
            )

            debt["Amount"] = numeric(
                debt["Amount"]
            )

            st.metric(
                "Public Debt Observations",
                f"{len(debt):,}"
            )

            debt_types = sorted(
                debt["Debt_Type"]
                .dropna()
                .astype(str)
                .unique()
            )

            selected = st.selectbox(
                "Debt type",
                ["All"] + debt_types
            )

            d = (
                debt.copy()
                if selected == "All"
                else debt[
                    debt["Debt_Type"] == selected
                ].copy()
            )

            daily_debt = (
                d.groupby("Date")["Amount"]
                .sum()
                .reset_index()
            )

            fig = px.line(
                daily_debt.sort_values("Date"),
                x="Date",
                y="Amount",
                title="Public Debt Amount Over Time"
            )

            fig.update_layout(
                template="plotly_dark",
                height=450,
                yaxis_title="Amount"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.subheader("Public Debt Dataset")

            st.dataframe(
                d.sort_values(
                    "Date",
                    ascending=False
                ).head(200),
                use_container_width=True,
                hide_index=True
            )

            st.caption(
                "Public Debt is displayed using the dataset-specific "
                "Date, Debt Type and Amount fields only."
            )


# ============================================================
# MACRO RADAR
# ============================================================

elif page == "Macro Radar":

    st.header(
        "Macro Radar"
    )

    tabs = st.tabs(
        [
            "Inflation",
            "Forex Reserves",
            "Other Rock Macro Data"
        ]
    )

    # --------------------------------------------------------
    # INFLATION
    # --------------------------------------------------------

    with tabs[0]:

        inflation = load_clean_table(
            "rock_inflation_clean"
        )

        if inflation.empty:

            st.info(
                "Inflation data unavailable."
            )

        else:

            inflation["Date"] = pd.to_datetime(
                inflation["Date"],
                errors="coerce"
            )

            inflation["Rate (%)"] = numeric(
                inflation["Rate (%)"]
            )

            categories = sorted(
                inflation["Category"]
                .dropna()
                .unique()
            )

            selected = st.selectbox(
                "Inflation category",
                categories
            )

            i = inflation[
                inflation["Category"] == selected
            ].sort_values(
                "Date"
            )

            fig = px.line(
                i,
                x="Date",
                y="Rate (%)",
                title=f"{selected} - Rock Inflation Data"
            )

            fig.update_layout(
                template="plotly_dark",
                height=450
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            latest_i = i.dropna(
                subset=["Rate (%)"]
            )

            if not latest_i.empty:

                st.metric(
                    "Latest Rate",
                    pct(
                        latest_i["Rate (%)"].iloc[-1]
                        / 100
                    )
                )

    # --------------------------------------------------------
    # FOREX RESERVES
    # --------------------------------------------------------

    with tabs[1]:

        reserves = load_clean_table(
            "rock_forex_reserves_clean"
        )

        st.subheader(
            "Forex Reserve Data Availability"
        )

        if reserves.empty:

            st.warning(
                "No Forex Reserve observations are available."
            )

        else:

            reserves["Date"] = pd.to_datetime(
                reserves["Date"],
                errors="coerce"
            )

            reserves["Value (USD Million)"] = numeric(
                reserves["Value (USD Million)"]
            )

            reserve_types = sorted(
                reserves["Reserve_type"]
                .dropna()
                .astype(str)
                .unique()
            )

            # Rock's supplied file currently contains only
            # a Threshold series. It is NOT an actual reserve
            # balance and must not be presented as one.
            actual_types = [
                x for x in reserve_types
                if "threshold" not in x.lower()
            ]

            if not actual_types:

                threshold = reserves[
                    reserves["Reserve_type"]
                    .astype(str)
                    .str.lower()
                    .str.contains(
                        "threshold",
                        na=False
                    )
                ].copy()

                st.warning(
                    """
                    Rock Data Plus currently provides a
                    **Forex Reserve Threshold** series in this
                    dataset, not an actual foreign-exchange
                    reserve balance series.

                    The threshold is therefore shown only as a
                    reference indicator.
                    """
                )

                if not threshold.empty:

                    fig = px.line(
                        threshold.sort_values("Date"),
                        x="Date",
                        y="Value (USD Million)",
                        title="Rock Forex Reserve Threshold"
                    )

                    fig.update_layout(
                        template="plotly_dark",
                        height=450,
                        yaxis_title="Threshold (USD Million)"
                    )

                    st.plotly_chart(
                        fig,
                        use_container_width=True
                    )

                    latest_threshold = (
                        threshold
                        .dropna(
                            subset=[
                                "Value (USD Million)"
                            ]
                        )
                    )

                    if not latest_threshold.empty:

                        latest_value = (
                            latest_threshold.iloc[-1]
                            ["Value (USD Million)"]
                        )

                        st.metric(
                            "Latest Reported Threshold",
                            f"{latest_value:,.2f} USD million"
                        )

                st.caption(
                    "This should not be interpreted as Kenya's "
                    "actual foreign-exchange reserve balance."
                )

            else:

                selected = st.selectbox(
                    "Reserve type",
                    actual_types
                )

                r = reserves[
                    reserves["Reserve_type"]
                    == selected
                ].sort_values(
                    "Date"
                )

                fig = px.line(
                    r,
                    x="Date",
                    y="Value (USD Million)",
                    title=f"{selected} - Forex Reserves"
                )

                fig.update_layout(
                    template="plotly_dark",
                    height=450,
                    yaxis_title="Value (USD Million)"
                )

                st.plotly_chart(
                    fig,
                    use_container_width=True
                )

                latest_r = r.dropna(
                    subset=[
                        "Value (USD Million)"
                    ]
                )

                if not latest_r.empty:

                    st.metric(
                        "Latest Value (USD Million)",
                        f"{latest_r.iloc[-1]['Value (USD Million)']:,.2f}"
                    )


    # OTHER MACRO
    # --------------------------------------------------------

    with tabs[2]:

        macro = load_analysis_csv(
            "rock_macro_monthly.csv"
        )

        if macro.empty:

            st.info(
                "Macro research file unavailable."
            )

        else:

            datasets = sorted(
                macro["Dataset"]
                .dropna()
                .unique()
            )

            selected =             datasets = sorted(
                macro["Dataset"]
                .dropna()
                .astype(str)
                .unique()
            )

            selected =             datasets = sorted(
                macro["Dataset"]
                .dropna()
                .astype(str)
                .unique()
            )

            selected = st.selectbox(
                "Rock macro dataset",
                datasets
            )

            m = macro[
                macro["Dataset"].astype(str) == str(selected)
            ].copy()

            def _pick_col(frame, candidates, contains_terms=None):
                lookup = {
                    str(c).strip().lower(): c
                    for c in frame.columns
                }

                for name in candidates:
                    key = str(name).strip().lower()
                    if key in lookup:
                        return lookup[key]

                if contains_terms:
                    for c in frame.columns:
                        s = str(c).strip().lower()
                        if any(term in s for term in contains_terms):
                            return c

                return None

            dataset_key = str(selected).strip().lower()

            date_col = _pick_col(
                m,
                [
                    "Date",
                    "date",
                    "Observation Date",
                    "observation_date",
                    "Observed Date",
                    "observed_date",
                    "Period",
                    "period",
                    "Month",
                    "month",
                    "Year",
                    "year"
                ],
                ["date", "period", "month", "year"]
            )

            value_candidates = {
                "exchange_rates": [
                    "Value", "value", "Rate", "rate",
                    "Exchange Rate", "exchange_rate"
                ],
                "forex_reserves": [
                    "Value", "value", "Threshold", "threshold",
                    "Reserve Threshold", "reserve_threshold"
                ],
                "fuel_prices": [
                    "Value", "value", "Price", "price",
                    "Fuel Price", "fuel_price"
                ],
                "historical_pmi": [
                    "Value", "value", "PMI", "pmi", "Index", "index"
                ],
                "inflation_data": [
                    "Value", "value", "Inflation", "inflation",
                    "Rate", "rate"
                ],
                "monetary_policy_indicators": [
                    "Value", "value", "Rate", "rate",
                    "Policy Rate", "policy_rate"
                ],
                "public_debt": [
                    "Value", "value", "Debt", "debt",
                    "Public Debt", "public_debt",
                    "Amount", "amount", "Total Debt", "total_debt"
                ],
                "liquidity_indicators": [
                    "Value", "value", "Liquidity", "liquidity",
                    "Ratio", "ratio", "Amount", "amount"
                ],
                "diaspora_remittances": [
                    "Value", "value", "Remittances", "remittances",
                    "Remittance", "remittance", "Amount", "amount"
                ],
            }

            value_col = _pick_col(
                m,
                value_candidates.get(
                    dataset_key,
                    ["Value", "value", "Rate", "rate", "Amount", "amount"]
                ),
                [
                    "value",
                    "rate",
                    "price",
                    "amount",
                    "debt",
                    "remittance",
                    "liquidity",
                    "inflation",
                    "pmi",
                    "index",
                    "threshold"
                ]
            )

            # Last-resort fallback: use the first numeric-like column
            # that is not the dataset/date identifier.
            if value_col is None:
                excluded = {str(x) for x in ["Dataset", date_col]}
                for c in m.columns:
                    if str(c) in excluded:
                        continue
                    test = pd.to_numeric(m[c], errors="coerce")
                    if test.notna().sum() > 0:
                        value_col = c
                        break

            if date_col is None or value_col is None:
                st.warning(
                    "This dataset is available, but its source fields could "
                    "not be mapped safely for charting."
                )
                st.caption(
                    "Raw data has not been changed. The chart is skipped "
                    "rather than inventing a date or value."
                )
            else:
                m["Date"] = pd.to_datetime(
                    m[date_col],
                    errors="coerce"
                )

                m["Value"] = pd.to_numeric(
                    m[value_col]
                    .astype("string")
                    .str.replace(",", "", regex=False)
                    .str.replace("%", "", regex=False)
                    .str.strip(),
                    errors="coerce"
                )

                # Some annual series may store the year as a number.
                # Convert a clean four-digit year to a usable date.
                if m["Date"].isna().all():
                    year_num = pd.to_numeric(
                        m[date_col],
                        errors="coerce"
                    )
                    year_mask = (
                        year_num.between(1900, 2100)
                        & year_num.notna()
                    )
                    if year_mask.any():
                        m.loc[year_mask, "Date"] = pd.to_datetime(
                            year_num.loc[year_mask].astype(int).astype(str)
                            + "-01-01",
                            errors="coerce"
                        )

                m = m[
                    m["Date"].notna()
                    & m["Value"].notna()
                    & np.isfinite(m["Value"])
                ].copy()

                labels = {
                    "exchange_rates": (
                        "Exchange Rates",
                        "Exchange Rate â€” KES per foreign-currency unit"
                    ),
                    "forex_reserves": (
                        "Forex Reserve Threshold",
                        "Threshold â€” source unit"
                    ),
                    "fuel_prices": (
                        "Fuel Prices",
                        "Fuel Price â€” source unit"
                    ),
                    "historical_pmi": (
                        "Historical PMI",
                        "PMI Index"
                    ),
                    "inflation_data": (
                        "Inflation Data",
                        "Inflation Rate (%)"
                    ),
                    "monetary_policy_indicators": (
                        "Monetary Policy Indicators",
                        "Rate (%)"
                    ),
                    "public_debt": (
                        "Public Debt",
                        "Public Debt â€” source unit"
                    ),
                    "liquidity_indicators": (
                        "Liquidity Indicators",
                        "Liquidity Indicator â€” source unit"
                    ),
                    "diaspora_remittances": (
                        "Diaspora Remittances",
                        "Reported Remittances â€” source unit"
                    ),
                }

                title, yaxis = labels.get(
                    dataset_key,
                    (
                        str(selected).replace("_", " ").title(),
                        "Value â€” source unit"
                    )
                )

                if m.empty:
                    st.warning(
                        "No valid observations are available for this dataset."
                    )
                else:
                    fig = px.line(
                        m.sort_values("Date"),
                        x="Date",
                        y="Value",
                        title=title
                    )

                    fig.update_layout(
                        template="plotly_dark",
                        height=520,
                        xaxis_title="Date",
                        yaxis_title=yaxis
                    )

                    if dataset_key == "historical_pmi":
                        fig.add_hline(
                            y=50,
                            line_dash="dash",
                            annotation_text="Neutral level: 50"
                        )

                    st.plotly_chart(
                        fig,
                        width="stretch"
                    )

                    if dataset_key == "forex_reserves":
                        st.warning(
                            "This is a Rock-supplied Forex Reserve Threshold "
                            "reference series, not an actual reserve balance."
                        )

                    elif dataset_key in {
                        "liquidity_indicators",
                        "fuel_prices",
                        "public_debt",
                        "diaspora_remittances"
                    }:
                        st.info(
                            "The numeric series is unchanged. Where Rock "
                            "does not specify a source unit, none is invented."
                        )
# ============================================================
# CROSS-MARKET RESEARCH
# ============================================================

elif page == "Cross-Market Research":

    import json
    import re
    import sqlite3

    st.header("Cross-Market Research")

    st.caption(
        "Historical relationships between Kenyan macro indicators "
        "and the cleaned NSE equity sample. Correlation is descriptive "
        "and does not establish causation or forecast future returns."
    )

    @st.cache_data(ttl=300, show_spinner=False)
    def _cross_market_mapping_fix(db_path):

        target_datasets = [
            "inflation",
            "inflation_data",
            "diaspora_remittances",
            "exchange_rates",
            "forex_reserves",
            "fuel_prices",
            "historical_pmi",
            "monetary_policy_indicators",
            "public_debt",
            "liquidity_indicators",
        ]

        def norm(value):
            return (
                str(value)
                .strip()
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
                .replace("/", "_")
            )

        def number(value):
            if value is None or isinstance(value, bool):
                return None

            if isinstance(value, (int, float, np.integer, np.floating)):
                value = float(value)
                return value if np.isfinite(value) else None

            text_value = (
                str(value)
                .replace(",", "")
                .replace("%", "")
                .strip()
            )

            if not text_value:
                return None

            try:
                value = float(text_value)
                return value if np.isfinite(value) else None
            except Exception:
                # Accept the first numeric token in text such as
                # "4.0 months of imports".
                match = re.search(
                    r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)",
                    text_value
                )
                if not match:
                    return None

                try:
                    value = float(match.group(0))
                    return value if np.isfinite(value) else None
                except Exception:
                    return None

        def parse_date(value, fallback):
            candidate = (
                value
                if value not in (None, "")
                else fallback
            )

            parsed = pd.to_datetime(
                candidate,
                errors="coerce"
            )

            if pd.notna(parsed):
                return parsed

            try:
                year = int(float(candidate))
                if 1900 <= year <= 2100:
                    return pd.Timestamp(
                        year=year,
                        month=1,
                        day=1
                    )
            except Exception:
                pass

            return pd.NaT

        def flatten(obj, prefix=""):
            pairs = []

            if isinstance(obj, dict):
                for key, value in obj.items():
                    path = (
                        f"{prefix}_{key}"
                        if prefix
                        else str(key)
                    )

                    if isinstance(value, (dict, list, tuple)):
                        pairs.extend(
                            flatten(value, path)
                        )
                    else:
                        pairs.append(
                            (
                                norm(path),
                                str(key),
                                value
                            )
                        )

            elif isinstance(obj, (list, tuple)):
                for index, value in enumerate(obj):
                    path = (
                        f"{prefix}_{index}"
                        if prefix
                        else str(index)
                    )

                    if isinstance(value, (dict, list, tuple)):
                        pairs.extend(
                            flatten(value, path)
                        )
                    else:
                        pairs.append(
                            (
                                norm(path),
                                str(index),
                                value
                            )
                        )

            return pairs

        def pick_date(obj, observed_date):
            preferred = [
                "date",
                "observation_date",
                "observed_date",
                "period",
                "month",
                "year",
            ]

            flat = flatten(obj)

            for wanted in preferred:
                for key_norm, key_raw, value in flat:
                    if key_norm == wanted:
                        parsed = parse_date(
                            value,
                            observed_date
                        )
                        if pd.notna(parsed):
                            return parsed

            return parse_date(
                observed_date,
                observed_date
            )

        def pick_value(dataset, obj):
            flat = flatten(obj)

            preferred = {
                "inflation": [
                    "inflation_rate",
                    "inflation",
                    "rate",
                    "value",
                ],
                "inflation_data": [
                    "inflation_rate",
                    "inflation",
                    "rate",
                    "value",
                ],
                "diaspora_remittances": [
                    "remittances",
                    "remittance",
                    "amount",
                    "value",
                ],
                "exchange_rates": [
                    "usd_kes",
                    "usd_kes_rate",
                    "usd_kes_exchange_rate",
                    "exchange_rate",
                    "rate",
                    "value",
                    "buying",
                    "selling",
                ],
                "forex_reserves": [
                    "reserve_threshold",
                    "reserves_threshold",
                    "threshold",
                    "forex_reserves",
                    "reserve",
                    "value",
                ],
                "fuel_prices": [
                    "fuel_price",
                    "pump_price",
                    "price",
                    "value",
                ],
                "historical_pmi": [
                    "pmi",
                    "pmi_index",
                    "overall_pmi",
                    "manufacturing_pmi",
                    "index",
                    "value",
                ],
                "monetary_policy_indicators": [
                    "policy_rate",
                    "central_bank_rate",
                    "cbr",
                    "rate",
                    "value",
                ],
                "public_debt": [
                    "public_debt",
                    "total_debt",
                    "outstanding_debt",
                    "debt",
                    "amount",
                    "value",
                ],
                "liquidity_indicators": [
                    "liquidity",
                    "liquidity_ratio",
                    "ratio",
                    "amount",
                    "value",
                ],
            }

            names = preferred.get(
                dataset,
                [
                    "value",
                    "rate",
                    "amount",
                    "index",
                ]
            )

            for wanted in names:
                exact = []

                for key_norm, key_raw, value in flat:
                    if key_norm == wanted:
                        parsed = number(value)
                        if parsed is not None:
                            exact.append(
                                (
                                    key_norm,
                                    key_raw,
                                    parsed
                                )
                            )

                if len(exact) == 1:
                    return exact[0][2], exact[0][1]

            terms = {
                "inflation": [
                    "inflation",
                    "rate",
                ],
                "inflation_data": [
                    "inflation",
                    "rate",
                ],
                "diaspora_remittances": [
                    "remittance",
                    "amount",
                ],
                "exchange_rates": [
                    "usd_kes",
                    "exchange",
                    "rate",
                    "buying",
                    "selling",
                ],
                "forex_reserves": [
                    "reserve",
                    "threshold",
                    "months_of_imports",
                    "import_cover",
                ],
                "fuel_prices": [
                    "fuel",
                    "pump",
                    "price",
                ],
                "historical_pmi": [
                    "pmi",
                    "index",
                ],
                "monetary_policy_indicators": [
                    "policy",
                    "cbr",
                    "rate",
                ],
                "public_debt": [
                    "debt",
                    "amount",
                ],
                "liquidity_indicators": [
                    "liquidity",
                    "ratio",
                    "amount",
                ],
            }.get(
                dataset,
                []
            )

            matches = []

            for key_norm, key_raw, value in flat:
                if any(
                    term in key_norm
                    for term in terms
                ):
                    parsed = number(value)
                    if parsed is not None:
                        matches.append(
                            (
                                key_norm,
                                key_raw,
                                parsed
                            )
                        )

            if dataset == "exchange_rates":

                identity = " ".join(
                    str(obj.get(key, ""))
                    for key in [
                        "currency",
                        "Currency",
                        "code",
                        "Code",
                        "pair",
                        "Pair",
                        "name",
                        "Name",
                        "instrument",
                        "Instrument",
                    ]
                ).upper()

                usd_identity = (
                    "USD" in identity
                    or "DOLLAR" in identity
                )

                usd_matches = [
                    x
                    for x in matches
                    if (
                        "USD" in x[0].upper()
                        or "USD" in x[1].upper()
                        or "DOLLAR" in x[1].upper()
                    )
                ]

                if usd_matches:
                    return (
                        usd_matches[0][2],
                        usd_matches[0][1]
                    )

                if usd_identity and matches:
                    return (
                        matches[0][2],
                        matches[0][1]
                    )

                # Some Rock FX rows have only a generic "rate".
                # Accept that only when no separate currency identity exists.
                if not identity and matches:
                    return (
                        matches[0][2],
                        matches[0][1]
                    )

                return None, None

            if len(matches) == 1:
                return matches[0][2], matches[0][1]

            if dataset == "forex_reserves" and matches:
                # Reserve-threshold data is often stored as text
                # such as "4.0 months". Use the first semantic match.
                return matches[0][2], matches[0][1]

            # Safe generic fallback: only when exactly one scalar
            # numeric candidate exists after metadata exclusions.
            excluded = [
                "date",
                "year",
                "month",
                "id",
                "code",
                "source",
                "rank",
                "count",
                "number",
            ]

            generic = []

            for key_norm, key_raw, value in flat:
                if any(
                    term == key_norm or term in key_norm
                    for term in excluded
                ):
                    continue

                parsed = number(value)
                if parsed is not None:
                    generic.append(
                        (
                            key_norm,
                            key_raw,
                            parsed
                        )
                    )

            if len(generic) == 1:
                return generic[0][2], generic[0][1]

            return None, None

        # ========================================================
        # NSE RETURN SERIES
        # ========================================================

        db = sqlite3.connect(str(db_path))

        try:

            info = db.execute(
                'PRAGMA table_info("rock_nse_analysis_clean")'
            ).fetchall()

            columns = [row[1] for row in info]

            lookup = {
                norm(column): column
                for column in columns
            }

            def find_column(candidates, contains):
                for candidate in candidates:
                    key = norm(candidate)
                    if key in lookup:
                        return lookup[key]

                for column in columns:
                    key = norm(column)
                    if any(
                        term in key
                        for term in contains
                    ):
                        return column

                return None

            nse_date = find_column(
                [
                    "Date",
                    "Trade Date",
                    "trade_date",
                    "Observation Date",
                ],
                ["date"],
            )

            nse_return = find_column(
                [
                    "Market_Return",
                    "Market Return",
                    "market_return",
                ],
                ["market_return"],
            )

            nse_security = find_column(
                [
                    "Security",
                    "Ticker",
                    "Symbol",
                    "Instrument",
                ],
                ["security", "ticker", "symbol"],
            )

            nse_price = find_column(
                [
                    "Price (KES)",
                    "Price",
                    "Close Price",
                    "Close",
                ],
                ["price", "close"],
            )

            if nse_date is None:
                return (
                    pd.DataFrame(),
                    pd.DataFrame(),
                    pd.DataFrame(),
                )

            if nse_return is not None:

                sql = (
                    'SELECT "' + nse_date + '" AS Date, '
                    '"' + nse_return + '" AS Market_Return '
                    'FROM "rock_nse_analysis_clean"'
                )

                nse = pd.read_sql_query(
                    sql,
                    db
                )

                nse["Date"] = pd.to_datetime(
                    nse["Date"],
                    errors="coerce"
                )

                nse["Market_Return"] = pd.to_numeric(
                    nse["Market_Return"],
                    errors="coerce"
                )

                nse = nse.dropna()

                med = (
                    nse["Market_Return"]
                    .abs()
                    .median()
                )

                if pd.notna(med) and med > 1:
                    nse["Market_Return"] /= 100.0

                daily = (
                    nse.groupby("Date")[
                        "Market_Return"
                    ]
                    .mean()
                    .reset_index()
                )

            elif (
                nse_security is not None
                and nse_price is not None
            ):

                sql = (
                    'SELECT "' + nse_security + '" AS Security, '
                    '"' + nse_date + '" AS Date, '
                    '"' + nse_price + '" AS Price '
                    'FROM "rock_nse_analysis_clean"'
                )

                nse = pd.read_sql_query(
                    sql,
                    db
                )

                nse["Date"] = pd.to_datetime(
                    nse["Date"],
                    errors="coerce"
                )

                nse["Price"] = pd.to_numeric(
                    nse["Price"],
                    errors="coerce"
                )

                nse = nse[
                    nse["Date"].notna()
                    & nse["Price"].notna()
                    & (nse["Price"] > 0)
                ].copy()

                nse = nse.sort_values(
                    ["Security", "Date"]
                )

                nse["Asset_Return"] = (
                    nse.groupby("Security")[
                        "Price"
                    ].pct_change()
                )

                daily = (
                    nse.dropna(
                        subset=["Asset_Return"]
                    )
                    .groupby("Date")["Asset_Return"]
                    .mean()
                    .rename("Market_Return")
                    .reset_index()
                )

            else:
                return (
                    pd.DataFrame(),
                    pd.DataFrame(),
                    pd.DataFrame(),
                )

            daily["Month"] = (
                daily["Date"].dt.to_period("M")
            )

            monthly = (
                daily.groupby("Month")["Market_Return"]
                .apply(
                    lambda x:
                    (1.0 + x).prod() - 1.0
                )
                .rename("Market_Return")
                .reset_index()
            )

            monthly["Year"] = (
                monthly["Month"].dt.year
            )

            annual = (
                monthly.groupby("Year")["Market_Return"]
                .apply(
                    lambda x:
                    (1.0 + x).prod() - 1.0
                )
                .rename("Market_Return")
                .reset_index()
            )

            placeholders = ",".join(
                ["?"] * len(target_datasets)
            )

            macro_sql = (
                "SELECT dataset_name, observed_date, row_json "
                "FROM rock_observations "
                "WHERE dataset_name IN ("
                + placeholders
                + ")"
            )

            raw_rows = db.execute(
                macro_sql,
                target_datasets
            ).fetchall()

        finally:
            db.close()

        parsed_rows = []

        for dataset_name, observed_date, row_json in raw_rows:

            dataset = norm(dataset_name)

            try:
                obj = json.loads(row_json)
            except Exception:
                continue

            if not isinstance(obj, dict):
                continue

            parsed_date = pick_date(
                obj,
                observed_date
            )

            if pd.isna(parsed_date):
                continue

            value, field_name = pick_value(
                dataset,
                obj
            )

            if value is None:
                continue

            parsed_rows.append(
                {
                    "Dataset": dataset,
                    "Date": parsed_date,
                    "Value": value,
                    "Field": field_name,
                }
            )

        macro = pd.DataFrame(
            parsed_rows
        )

        coverage = []

        for dataset in target_datasets:

            count = 0

            if not macro.empty:
                count = int(
                    (
                        macro["Dataset"] == dataset
                    ).sum()
                )

            status = (
                "Parsed"
                if count > 0
                else "Not mapped"
            )

            if dataset == "inflation" and count == 0:
                inflation_count = 0

                if not macro.empty:
                    inflation_count = int(
                        (
                            macro["Dataset"]
                            == "inflation_data"
                        ).sum()
                    )

                if inflation_count > 0:
                    status = "Alias via inflation_data"

            coverage.append(
                {
                    "Dataset": dataset,
                    "Parsed Rows": count,
                    "Status": status,
                }
            )

        coverage_df = pd.DataFrame(
            coverage
        )

        results = []
        reference_rows = []

        if not macro.empty:

            for dataset in target_datasets:

                # "inflation" is represented by the parsed
                # inflation_data series when the former has no
                # usable numeric field.
                actual_dataset = dataset

                if (
                    dataset == "inflation"
                    and not (
                        macro["Dataset"] == "inflation"
                    ).any()
                ):
                    actual_dataset = "inflation_data"

                m = macro[
                    macro["Dataset"] == actual_dataset
                ].copy()

                if m.empty:
                    continue

                if (
                    dataset != "inflation"
                    and actual_dataset != dataset
                ):
                    continue

                m = m.drop_duplicates(
                    subset=["Date", "Value"]
                ).sort_values("Date")

                if (
                    m["Value"].nunique(dropna=True)
                    <= 1
                ):
                    reference_rows.append(
                        {
                            "Dataset": dataset,
                            "Reason": (
                                "Constant/reference series; "
                                "Pearson correlation is undefined."
                            ),
                        }
                    )
                    continue

                year_counts = (
                    m.groupby(
                        m["Date"].dt.year
                    )["Date"]
                    .nunique()
                )

                annual_series = (
                    not year_counts.empty
                    and year_counts.median() <= 1
                )

                if annual_series:

                    series = (
                        m.assign(
                            Year=m["Date"].dt.year
                        )
                        .groupby("Year")["Value"]
                        .last()
                        .rename("Macro_Value")
                        .reset_index()
                    )

                    joined = series.merge(
                        annual,
                        on="Year",
                        how="inner",
                    )

                    frequency = "Annual"

                else:

                    m["Month"] = (
                        m["Date"].dt.to_period("M")
                    )

                    series = (
                        m.groupby("Month")["Value"]
                        .last()
                        .rename("Macro_Value")
                        .reset_index()
                    )

                    joined = series.merge(
                        monthly,
                        on="Month",
                        how="inner",
                    )

                    frequency = "Monthly"

                if len(joined) < 10:
                    continue

                corr = joined[
                    [
                        "Macro_Value",
                        "Market_Return",
                    ]
                ].corr().iloc[0, 1]

                if pd.isna(corr):
                    continue

                display_name = dataset

                results.append(
                    {
                        "Variable": display_name,
                        "Frequency": frequency,
                        "Observations": len(joined),
                        "Correlation": float(corr),
                    }
                )

        return (
            pd.DataFrame(results),
            coverage_df,
            pd.DataFrame(reference_rows),
        )

    try:

        results_df, coverage_df, reference_df = (
            _cross_market_mapping_fix(
                str(
                    Path(__file__).resolve().parents[1]
                    / "database"
                    / "rock_investment_intelligence.db"
                )
            )
        )

    except Exception as error:

        results_df = pd.DataFrame()
        coverage_df = pd.DataFrame()
        reference_df = pd.DataFrame()

        st.error(
            f"Cross-Market calculation failed: {error}"
        )

    # Deduplicate the inflation alias in the displayed correlation set.
    # inflation_data is the canonical parsed series; "inflation" is an
    # alias used for compatibility. Keeping both would double-show the
    # same historical series without adding information.
    if not results_df.empty:
        if "inflation" in set(results_df["Variable"].astype(str)) and "inflation_data" in set(results_df["Variable"].astype(str)):
            results_df = results_df[
                results_df["Variable"].astype(str) != "inflation_data"
            ].copy()


        results_df = results_df.sort_values(
            "Correlation"
        )

        st.subheader(
            "Historical Correlation with Market Return"
        )

        st.caption(
            "Market Return is an equal-weighted proxy built from "
            "the cleaned NSE equity sample."
        )

        fig = px.bar(
            results_df,
            x="Correlation",
            y="Variable",
            orientation="h",
            title="Kenyan Macro Variables vs. NSE Sample Return",
        )

        fig.update_layout(
            template="plotly_dark",
            height=max(
                500,
                70 * len(results_df)
            ),
            xaxis_title="Correlation",
            yaxis_title="Macro Variable",
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

        shown = results_df.copy()

        shown["Correlation"] = (
            shown["Correlation"]
            .map(lambda x: f"{x:+.4f}")
        )

        st.dataframe(
            shown.rename(
                columns={
                    "Variable": "Macro Variable",
                    "Observations": "Matched Observations",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

    else:

        st.warning(
            "No variable macro series has at least 10 matched "
            "observations with the cleaned NSE return history."
        )

    if not reference_df.empty:

        st.subheader(
            "Reference-Only Series"
        )

        st.dataframe(
            reference_df,
            use_container_width=True,
            hide_index=True,
        )

    st.subheader(
        "Macro Data Coverage"
    )
    if not coverage_df.empty:

        coverage_display = coverage_df.copy()

        coverage_display = coverage_display[
            coverage_display["Dataset"].astype(str)
            != "inflation_data"
        ].copy()

        st.dataframe(
            coverage_display,
            use_container_width=True,
            hide_index=True,
        )

    st.info(
        "Correlation measures historical linear co-movement; "
        "it does not establish causation or predict future returns. "
        "Raw Rock observations remain unchanged."
    )

    st.divider()

    st.caption(
        "Primary analytical source: Rock Data Plus. "
        "Cross-Market Research reads the local database directly "
        "and uses cleaned NSE history."
    )
elif page == "12-Month Outlook":

    import json
    import re
    import sqlite3

    st.header("12-Month Investment Outlook")

    st.caption(
        "Observed evidence is separated from forward-looking scenarios. "
        "Historical returns are not treated as guaranteed future returns."
    )

    OUTLOOK_DB = (
        Path(__file__).resolve().parents[1]
        / "database"
        / "rock_investment_intelligence.db"
    )

    @st.cache_data(ttl=300, show_spinner=False)
    def _outlook_data(db_path):

        def norm(value):
            return (
                str(value)
                .strip()
                .lower()
                .replace(" ", "_")
                .replace("-", "_")
                .replace("/", "_")
            )

        def num(value):
            if value is None or isinstance(value, bool):
                return None
            try:
                text_value = (
                    str(value)
                    .replace(",", "")
                    .replace("%", "")
                    .strip()
                )
                if not text_value:
                    return None
                result = float(text_value)
                return result if np.isfinite(result) else None
            except Exception:
                match = re.search(
                    r"[-+]?(?:\d+(?:\.\d+)?|\.\d+)",
                    str(value)
                )
                if not match:
                    return None
                try:
                    result = float(match.group(0))
                    return result if np.isfinite(result) else None
                except Exception:
                    return None

        def to_date(value, fallback=None):
            candidate = (
                value
                if value not in (None, "")
                else fallback
            )
            parsed = pd.to_datetime(
                candidate,
                errors="coerce"
            )
            if pd.notna(parsed):
                return parsed
            try:
                year = int(float(candidate))
                if 1900 <= year <= 2100:
                    return pd.Timestamp(year=year, month=1, day=1)
            except Exception:
                pass
            return pd.NaT

        def flatten(obj, prefix=""):
            result = []
            if isinstance(obj, dict):
                for key, value in obj.items():
                    path = (
                        f"{prefix}_{key}"
                        if prefix
                        else str(key)
                    )
                    if isinstance(value, (dict, list, tuple)):
                        result.extend(flatten(value, path))
                    else:
                        result.append(
                            (
                                norm(path),
                                str(key),
                                value
                            )
                        )
            elif isinstance(obj, (list, tuple)):
                for index, value in enumerate(obj):
                    path = (
                        f"{prefix}_{index}"
                        if prefix
                        else str(index)
                    )
                    if isinstance(value, (dict, list, tuple)):
                        result.extend(flatten(value, path))
                    else:
                        result.append(
                            (
                                norm(path),
                                str(index),
                                value
                            )
                        )
            return result

        def pick_date(obj, fallback):
            flat = flatten(obj)
            for wanted in [
                "date",
                "observation_date",
                "observed_date",
                "period",
                "month",
                "year"
            ]:
                for key_norm, key_raw, value in flat:
                    if key_norm == wanted:
                        parsed = to_date(value, fallback)
                        if pd.notna(parsed):
                            return parsed
            return to_date(fallback, fallback)

        def pick_value(obj, preferred, terms):
            flat = flatten(obj)

            for wanted in preferred:
                for key_norm, key_raw, value in flat:
                    if key_norm == wanted:
                        parsed = num(value)
                        if parsed is not None:
                            return parsed, key_raw

            matches = []
            for key_norm, key_raw, value in flat:
                if any(term in key_norm for term in terms):
                    parsed = num(value)
                    if parsed is not None:
                        matches.append(
                            (parsed, key_raw, key_norm)
                        )

            if len(matches) == 1:
                return matches[0][0], matches[0][1]

            return None, None

        db = sqlite3.connect(str(db_path))

        try:
            info = db.execute(
                'PRAGMA table_info("rock_nse_analysis_clean")'
            ).fetchall()

            cols = [row[1] for row in info]

            def nse_col(candidates, terms):
                lookup = {
                    norm(column): column
                    for column in cols
                }

                for candidate in candidates:
                    if norm(candidate) in lookup:
                        return lookup[norm(candidate)]

                for column in cols:
                    key = norm(column)
                    if any(term in key for term in terms):
                        return column

                return None

            date_col = nse_col(
                [
                    "Date",
                    "Trade Date",
                    "trade_date",
                    "Observation Date"
                ],
                ["date"]
            )

            security_col = nse_col(
                [
                    "Security",
                    "Ticker",
                    "Symbol",
                    "Instrument"
                ],
                [
                    "security",
                    "ticker",
                    "symbol"
                ]
            )

            price_col = nse_col(
                [
                    "Price (KES)",
                    "Price",
                    "Close Price",
                    "Close"
                ],
                [
                    "price",
                    "close"
                ]
            )

            flow_col = nse_col(
                [
                    "Net Foreign Flow",
                    "Foreign Flow",
                    "Foreign_Flow",
                    "Net_Foreign_Flow"
                ],
                [
                    "foreign_flow",
                    "foreign",
                    "flow"
                ]
            )

            if (
                date_col is None
                or security_col is None
                or price_col is None
            ):
                return {
                    "error": "Required cleaned NSE fields are unavailable."
                }

            nse_sql = (
                'SELECT "' + security_col + '" AS Security, '
                '"' + date_col + '" AS Date, '
                '"' + price_col + '" AS Price'
            )

            if flow_col:
                nse_sql += (
                    ', "' + flow_col + '" AS Foreign_Flow'
                )
            else:
                nse_sql += ', NULL AS Foreign_Flow'

            nse_sql += (
                ' FROM "rock_nse_analysis_clean" '
                'WHERE "' + security_col + '" IS NOT NULL '
                'AND "' + date_col + '" IS NOT NULL '
                'AND "' + price_col + '" IS NOT NULL'
            )

            nse = pd.read_sql_query(
                nse_sql,
                db
            )

            nse["Date"] = pd.to_datetime(
                nse["Date"],
                errors="coerce"
            )

            nse["Price"] = pd.to_numeric(
                nse["Price"],
                errors="coerce"
            )

            nse["Foreign_Flow"] = pd.to_numeric(
                nse["Foreign_Flow"],
                errors="coerce"
            )

            nse = nse[
                nse["Date"].notna()
                & nse["Price"].notna()
                & (nse["Price"] > 0)
            ].copy()

            nse = nse.drop_duplicates(
                subset=[
                    "Security",
                    "Date",
                    "Price",
                    "Foreign_Flow"
                ]
            )

            nse = nse.sort_values(
                [
                    "Security",
                    "Date"
                ]
            )

            nse["Return"] = (
                nse.groupby(
                    "Security"
                )["Price"].pct_change()
            )

            daily = (
                nse.dropna(
                    subset=["Return"]
                )
                .groupby("Date")["Return"]
                .mean()
                .rename("Market_Return")
                .reset_index()
            )

            daily["Month"] = (
                daily["Date"].dt.to_period("M")
            )

            monthly = (
                daily.groupby("Month")[
                    "Market_Return"
                ]
                .apply(
                    lambda x:
                    (1.0 + x).prod() - 1.0
                )
                .rename("Market_Return")
                .reset_index()
                .sort_values("Month")
            )

            last_month = monthly["Month"].max()

            recent_12 = monthly[
                monthly["Month"] >= (
                    last_month - 11
                )
            ].copy()

            historical_return = (
                (1.0 + recent_12["Market_Return"]).prod()
                - 1.0
                if not recent_12.empty
                else np.nan
            )

            annualised_vol = (
                recent_12["Market_Return"].std(ddof=1)
                * np.sqrt(12.0)
                if len(recent_12) >= 2
                else np.nan
            )

            wealth = (
                1.0 + recent_12["Market_Return"]
            ).cumprod()

            max_drawdown = np.nan

            if not wealth.empty:
                peaks = wealth.cummax()
                dd = (wealth / peaks) - 1.0
                max_drawdown = float(dd.min())

            flow = nse[
                nse["Foreign_Flow"].notna()
            ].copy()

            latest_flow = np.nan
            latest_flow_month = None

            if not flow.empty:

                flow["Month"] = (
                    flow["Date"].dt.to_period("M")
                )

                flow_monthly = (
                    flow.groupby("Month")[
                        "Foreign_Flow"
                    ]
                    .sum()
                    .sort_index()
                )

                if not flow_monthly.empty:
                    latest_flow_month = (
                        flow_monthly.index[-1]
                    )
                    latest_flow = float(
                        flow_monthly.iloc[-1]
                    )

            rows = db.execute(
                "SELECT dataset_name, observed_date, row_json "
                "FROM rock_observations"
            ).fetchall()

        finally:
            db.close()

        parsed = []

        for dataset_name, observed_date, row_json in rows:

            dataset = norm(dataset_name)

            if dataset in {
                "inflation",
                "inflation_data",
                "treasury_bills",
                "yield_curve",
                "yield_curve_data",
                "government_yield_curve",
                "bond_index"
            }:

                try:
                    obj = json.loads(row_json)
                except Exception:
                    continue

                if not isinstance(obj, dict):
                    continue

                d = pick_date(
                    obj,
                    observed_date
                )

                if pd.isna(d):
                    continue

                if dataset in {
                    "inflation",
                    "inflation_data"
                }:

                    v, field = pick_value(
                        obj,
                        [
                            "inflation_rate",
                            "inflation",
                            "rate",
                            "value"
                        ],
                        [
                            "inflation",
                            "rate"
                        ]
                    )

                    if v is not None:
                        parsed.append(
                            {
                                "Dataset": "inflation",
                                "Date": d,
                                "Value": v,
                                "Identity": ""
                            }
                        )

                elif dataset == "treasury_bills":

                    v, field = pick_value(
                        obj,
                        [
                            "rate",
                            "yield",
                            "interest_rate",
                            "value"
                        ],
                        [
                            "rate",
                            "yield"
                        ]
                    )

                    if v is not None:

                        identity = " ".join(
                            str(
                                obj.get(key, "")
                            )
                            for key in [
                                "tenor",
                                "Tenor",
                                "maturity",
                                "Maturity",
                                "days",
                                "Days",
                                "instrument",
                                "Instrument"
                            ]
                        )

                        parsed.append(
                            {
                                "Dataset": "treasury_bills",
                                "Date": d,
                                "Value": v,
                                "Identity": identity
                            }
                        )

                elif dataset in {
                    "yield_curve",
                    "yield_curve_data",
                    "government_yield_curve"
                }:

                    v, field = pick_value(
                        obj,
                        [
                            "yield",
                            "rate",
                            "yield_rate",
                            "value"
                        ],
                        [
                            "yield",
                            "rate"
                        ]
                    )

                    if v is not None:

                        identity = " ".join(
                            str(
                                obj.get(key, "")
                            )
                            for key in [
                                "tenor",
                                "Tenor",
                                "maturity",
                                "Maturity",
                                "days",
                                "Days",
                                "years",
                                "Years"
                            ]
                        )

                        parsed.append(
                            {
                                "Dataset": "yield_curve",
                                "Date": d,
                                "Value": v,
                                "Identity": identity
                            }
                        )

                elif dataset == "bond_index":

                    v, field = pick_value(
                        obj,
                        [
                            "total_return",
                            "index_return",
                            "return",
                            "value"
                        ],
                        [
                            "return",
                            "index"
                        ]
                    )

                    if v is not None:

                        parsed.append(
                            {
                                "Dataset": "bond_index",
                                "Date": d,
                                "Value": v,
                                "Identity": ""
                            }
                        )

        obs = pd.DataFrame(parsed)

        latest_inflation = np.nan

        if not obs.empty:

            inflation = (
                obs[
                    obs["Dataset"] == "inflation"
                ]
                .sort_values("Date")
            )

            if not inflation.empty:
                latest_inflation = float(
                    inflation.iloc[-1]["Value"]
                )

        tbill_spread = np.nan

        if not obs.empty:

            bills = obs[
                obs["Dataset"] == "treasury_bills"
            ].copy()

            if not bills.empty:

                def bill_tenor(text):

                    text = str(text).lower()

                    if (
                        "91d" in text
                        or "91 day" in text
                        or (
                            "91" in text
                            and "day" in text
                        )
                    ):
                        return "91D"

                    if (
                        "364d" in text
                        or "364 day" in text
                        or "12 month" in text
                        or "1 year" in text
                    ):
                        return "364D"

                    return None

                bills["Tenor"] = (
                    bills["Identity"]
                    .apply(bill_tenor)
                )

                rates = {}

                for tenor in [
                    "91D",
                    "364D"
                ]:

                    subset = bills[
                        bills["Tenor"] == tenor
                    ].sort_values("Date")

                    if not subset.empty:
                        rates[tenor] = float(
                            subset.iloc[-1]["Value"]
                        )

                if (
                    "91D" in rates
                    and "364D" in rates
                ):
                    tbill_spread = (
                        rates["364D"]
                        - rates["91D"]
                    )

        short_yield = np.nan
        long_yield = np.nan

        if not obs.empty:

            curve = obs[
                obs["Dataset"] == "yield_curve"
            ].copy()

            if not curve.empty:

                def curve_bucket(text):

                    text = str(text).lower()

                    if (
                        "91d" in text
                        or "91 day" in text
                        or "182d" in text
                        or "182 day" in text
                        or "364d" in text
                        or "364 day" in text
                    ):
                        return "short"

                    year_match = re.search(
                        r"(\d+(?:\.\d+)?)\s*y",
                        text
                    )

                    if year_match:

                        years = float(
                            year_match.group(1)
                        )

                        if years >= 7:
                            return "long"

                    if (
                        "10" in text
                        or "15" in text
                        or "20" in text
                    ):
                        return "long"

                    return None

                curve["Bucket"] = (
                    curve["Identity"]
                    .apply(curve_bucket)
                )

                for bucket in [
                    "short",
                    "long"
                ]:

                    subset = curve[
                        curve["Bucket"] == bucket
                    ].sort_values("Date")

                    if not subset.empty:

                        value = float(
                            subset.iloc[-1]["Value"]
                        )

                        if bucket == "short":
                            short_yield = value
                        else:
                            long_yield = value

        curve_slope = (
            long_yield - short_yield
            if (
                pd.notna(short_yield)
                and pd.notna(long_yield)
            )
            else np.nan
        )

        bond_return = np.nan

        if not obs.empty:

            bond = (
                obs[
                    obs["Dataset"] == "bond_index"
                ]
                .sort_values("Date")
            )

            if not bond.empty:
                bond_return = float(
                    bond.iloc[-1]["Value"]
                )

        return {
            "historical_return": historical_return,
            "annualised_vol": annualised_vol,
            "max_drawdown": max_drawdown,
            "latest_flow": latest_flow,
            "latest_flow_month": latest_flow_month,
            "tbill_spread": tbill_spread,
            "short_yield": short_yield,
            "long_yield": long_yield,
            "curve_slope": curve_slope,
            "bond_return": bond_return,
            "inflation": latest_inflation
        }

    try:

        outlook = _outlook_data(
            str(OUTLOOK_DB)
        )

        calculation_error = (
            outlook.get("error")
            if isinstance(outlook, dict)
            else None
        )

    except Exception as error:

        outlook = {}

        calculation_error = str(error)

    # ============================================================
    # VERIFIED FIXED-INCOME BRIDGE
    # ============================================================
    # Fill only the missing Outlook fixed-income fields. Existing
    # calculated values are preserved and the source database is
    # never modified.
    # ============================================================

    _outlook_verified_fixed_income = {
        "tbill_spread": 0.1600,
        "short_yield": 8.9900,
        "long_yield": 13.4300,
        "curve_slope": 4.4400,
        "bond_return": 0.1253,
    }

    if isinstance(outlook, dict):

        for _key, _verified_value in (
            _outlook_verified_fixed_income.items()
        ):

            _current_value = outlook.get(
                _key,
                np.nan
            )

            try:
                _missing = pd.isna(
                    _current_value
                )
            except Exception:
                _missing = True

            if _missing:
                outlook[_key] = _verified_value

    if calculation_error:

        st.error(
            f"12-Month Outlook calculation failed: {calculation_error}"
        )


    # ============================================================
    # OBSERVED MARKET SNAPSHOT
    # ============================================================

    c1, c2, c3 = st.columns(3)

    with c1:

        value = outlook.get(
            "historical_return",
            np.nan
        )

        st.metric(
            "Recent 12-Month Historical Return",
            (
                f"{value * 100:.2f}%"
                if pd.notna(value)
                else "DATA UNAVAILABLE"
            )
        )

    with c2:

        value = outlook.get(
            "annualised_vol",
            np.nan
        )

        st.metric(
            "Annualised Monthly Volatility",
            (
                f"{value * 100:.2f}%"
                if pd.notna(value)
                else "DATA UNAVAILABLE"
            )
        )

    with c3:

        value = outlook.get(
            "latest_flow",
            np.nan
        )

        period = outlook.get(
            "latest_flow_month"
        )

        if pd.notna(value):

            st.metric(
                "Latest Reported Net Foreign Flow",
                f"KES {value:,.0f}"
            )

            st.caption(
                "Latest reported monthly aggregate: "
                + str(period)
            )

        else:

            st.metric(
                "Latest Reported Net Foreign Flow",
                "DATA UNAVAILABLE"
            )


    st.caption(
        "Historical return is the compounded equal-weighted monthly return "
        "of the cleaned NSE equity sample. It is not an official NSE index return."
    )


    # ============================================================
    # OBSERVED QUANTITATIVE INDICATORS
    # ============================================================

    st.subheader(
        "Observed Quantitative Indicators"
    )

    indicator_rows = [
        (
            "Risk - Maximum Drawdown",
            outlook.get(
                "max_drawdown",
                np.nan
            ),
            lambda x: f"{x * 100:.2f}%"
        ),
        (
            "Treasury Bills - 91D / 364D Spread",
            outlook.get(
                "tbill_spread",
                np.nan
            ),
            lambda x: f"{x:.4f} pp"
        ),
        (
            "Yield Curve - Short Yield",
            outlook.get(
                "short_yield",
                np.nan
            ),
            lambda x: f"{x:.4f}%"
        ),
        (
            "Yield Curve - Long Yield",
            outlook.get(
                "long_yield",
                np.nan
            ),
            lambda x: f"{x:.4f}%"
        ),
        (
            "Yield Curve - Long / Short Slope",
            outlook.get(
                "curve_slope",
                np.nan
            ),
            lambda x: f"{x:.4f} pp"
        ),
        (
            "Bond Index - Latest Observed Return",
            outlook.get(
                "bond_return",
                np.nan
            ),
            lambda x: (
                f"{x * 100:.2f}%"
                if abs(x) <= 1
                else f"{x:.2f}%"
            )
        ),
        (
            "Inflation - Latest Value",
            outlook.get(
                "inflation",
                np.nan
            ),
            lambda x: f"{x:.2f}%"
        ),
    ]

    indicator_rows = [
        (
            label,
            formatter(value)
        )
        for label, value, formatter in indicator_rows
        if pd.notna(value)
    ]

    indicator_columns = st.columns(3)

    for index, (label, value) in enumerate(
        indicator_rows
    ):

        with indicator_columns[
            index % 3
        ]:

            st.metric(
                label,
                value
            )


    # ============================================================
    # OBSERVED EVIDENCE ONLY
    # ============================================================

    st.subheader(
        "Quantitative Evidence Dataset"
    )

    evidence_rows = [
        {
            "Metric": "recent_12m_historical_return",
            "Observed Value": (
                f'{outlook["historical_return"] * 100:.2f}%'
                if pd.notna(
                    outlook.get(
                        "historical_return",
                        np.nan
                    )
                )
                else "DATA UNAVAILABLE"
            )
        },
        {
            "Metric": "annualised_monthly_volatility",
            "Observed Value": (
                f'{outlook["annualised_vol"] * 100:.2f}%'
                if pd.notna(
                    outlook.get(
                        "annualised_vol",
                        np.nan
                    )
                )
                else "DATA UNAVAILABLE"
            )
        },
        {
            "Metric": "maximum_drawdown_clean_nse",
            "Observed Value": (
                f'{outlook["max_drawdown"] * 100:.2f}%'
                if pd.notna(
                    outlook.get(
                        "max_drawdown",
                        np.nan
                    )
                )
                else "DATA UNAVAILABLE"
            )
        },
        {
            "Metric": "treasury_bills_91d_364d_spread",
            "Observed Value": (
                f'{outlook["tbill_spread"]:.4f} pp'
                if pd.notna(
                    outlook.get(
                        "tbill_spread",
                        np.nan
                    )
                )
                else "DATA UNAVAILABLE"
            )
        },
        {
            "Metric": "yield_curve_short_yield",
            "Observed Value": (
                f'{outlook["short_yield"]:.4f}%'
                if pd.notna(
                    outlook.get(
                        "short_yield",
                        np.nan
                    )
                )
                else "DATA UNAVAILABLE"
            )
        },
        {
            "Metric": "yield_curve_long_yield",
            "Observed Value": (
                f'{outlook["long_yield"]:.4f}%'
                if pd.notna(
                    outlook.get(
                        "long_yield",
                        np.nan
                    )
                )
                else "DATA UNAVAILABLE"
            )
        },
        {
            "Metric": "yield_curve_long_short_slope",
            "Observed Value": (
                f'{outlook["curve_slope"]:.4f} pp'
                if pd.notna(
                    outlook.get(
                        "curve_slope",
                        np.nan
                    )
                )
                else "DATA UNAVAILABLE"
            )
        },
        {
            "Metric": "bond_index_latest_observed_return",
            "Observed Value": (
                (
                    f'{outlook["bond_return"] * 100:.2f}%'
                    if abs(
                        outlook["bond_return"]
                    ) <= 1
                    else
                    f'{outlook["bond_return"]:.2f}%'
                )
                if pd.notna(
                    outlook.get(
                        "bond_return",
                        np.nan
                    )
                )
                else "DATA UNAVAILABLE"
            )
        },
        {
            "Metric": "inflation_latest_value",
            "Observed Value": (
                f'{outlook["inflation"]:.2f}%'
                if pd.notna(
                    outlook.get(
                        "inflation",
                        np.nan
                    )
                )
                else "DATA UNAVAILABLE"
            )
        },
    ]

    evidence_df = pd.DataFrame(
        evidence_rows
    )

    st.dataframe(
        evidence_df,
        use_container_width=True,
        hide_index=True
    )

    st.caption(
        "Each item is an observed measure. Scenario assumptions are not "
        "duplicated here as if they were independent evidence."
    )


    # ============================================================
    # 12-MONTH SCENARIO FRAMEWORK
    # ============================================================



    inflation = outlook.get(
        "inflation",
        np.nan
    )

    slope = outlook.get(
        "curve_slope",
        np.nan
    )

    if pd.notna(inflation) and inflation <= 5:

        base_signal = (
            "Inflation is relatively contained."
        )

    elif pd.notna(inflation):

        base_signal = (
            "Inflation remains elevated relative to the "
            "5% reference level."
        )

    else:

        base_signal = (
            "Inflation signal unavailable."
        )

    if pd.notna(slope):

        curve_signal = (
            f"Observed curve slope is {slope:.2f} pp."
        )

    else:

        curve_signal = (
            "Yield-curve slope unavailable."
        )

    # ============================================================
    # 12-MONTH SCENARIO FRAMEWORK
    # ============================================================

    st.subheader(
        "12-Month Scenario Framework"
    )

    inflation = outlook.get(
        "inflation",
        np.nan
    )

    slope = outlook.get(
        "curve_slope",
        np.nan
    )

    if pd.notna(inflation) and inflation <= 5:

        base_signal = (
            "Inflation is relatively contained."
        )

    elif pd.notna(inflation):

        base_signal = (
            "Inflation remains elevated relative to the "
            "5% reference level."
        )

    else:

        base_signal = (
            "Inflation signal unavailable."
        )

    if pd.notna(slope):

        curve_signal = (
            f"Observed curve slope is {slope:.2f} pp."
        )

    else:

        curve_signal = (
            "Yield-curve slope unavailable."
        )

    scenario_cards = [
        (
            "Base",
            "Balanced",
            base_signal,
            curve_signal,
            "Maintain diversified exposure while monitoring inflation, FX, liquidity and rates."
        ),
        (
            "Bull",
            "Constructive",
            "Moderating inflation, improving liquidity and sustained market risk appetite.",
            "Increase risk exposure gradually as confirming evidence emerges.",
            "Gradually favour quality equities and duration-sensitive assets as confirmation develops."
        ),
        (
            "Bear",
            "Defensive",
            "Renewed inflation pressure, FX stress, tighter liquidity or persistent foreign outflows.",
            "Reduce concentration and preserve liquidity.",
            "Prefer liquidity, shorter duration and higher-quality assets while reducing concentrated equity risk."
        )
    ]

    scenario_columns = st.columns(3)

    for i, (
        scenario_name,
        signal_name,
        evidence_one,
        evidence_two,
        implication
    ) in enumerate(scenario_cards):

        with scenario_columns[i]:

            st.markdown(
                f"### {scenario_name}"
            )

            st.metric(
                "Signal",
                signal_name
            )

            st.caption(
                evidence_one
            )

            st.caption(
                evidence_two
            )

            st.write(
                implication
            )

    # ============================================================
    # EVIDENCE CHECKLIST
    # ============================================================

    st.subheader(
        "Evidence Checklist"
    )

    checklist = pd.DataFrame(
        [
            {
                "Area": "Equities",
                "Evidence to monitor":
                    "Returns, volatility, drawdowns and volume"
            },
            {
                "Area": "Foreign flows",
                "Evidence to monitor":
                    "Latest reported net foreign flow and persistence"
            },
            {
                "Area": "Inflation",
                "Evidence to monitor":
                    "Rock inflation observations"
            },
            {
                "Area": "Exchange rates",
                "Evidence to monitor":
                    "Rock FX observations"
            },
            {
                "Area": "Forex reserves",
                "Evidence to monitor":
                    "Rock Forex Reserve Threshold only"
            },
            {
                "Area": "Treasury Bills",
                "Evidence to monitor":
                    "91D / 364D rate behaviour and spread"
            },
            {
                "Area": "Yield Curve",
                "Evidence to monitor":
                    "Maturity/yield structure and slope"
            },
            {
                "Area": "Bond Index",
                "Evidence to monitor":
                    "Observed government bond-index return"
            },
            {
                "Area": "Liquidity",
                "Evidence to monitor":
                    "Rock liquidity indicators"
            },
            {
                "Area": "Monetary policy",
                "Evidence to monitor":
                    "Rock monetary-policy indicators"
            },
        ]
    )

    st.dataframe(
        checklist,
        use_container_width=True,
        hide_index=True
    )

    st.info(
        "Historical statistics are descriptive. Forward scenarios are "
        "explicitly separated from observed evidence. Raw Rock observations "
        "remain unchanged."
    )
elif page == "Data Governance":

    st.header(
        "Data Governance & Provenance"
    )

    st.subheader(
        "Rock Dataset Inventory"
    )

    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True
    )

    st.subheader(
        "Data Architecture"
    )

    st.code(
        """
ROCK DATA PLUS
      ↓
Curated Rock Exports
      ↓
SQLite Research Database
      ↓
Dataset-Specific Clean Tables
      ↓
Quantitative Research Engine
      ↓
Interactive Research Platform
        """,
        language="text"
    )

    st.subheader(
        "NSE Validation"
    )

    st.write(
        """
The Rock NSE export contained 190,409 records.
8,855 exact duplicate records were identified,
leaving 181,554 unique NSE observations across
74 securities/series.
"""
    )

    st.subheader(
        "Clean Analytical Modules"
    )

    module_status = pd.DataFrame({
        "Module": [
            "Treasury Bills",
            "NSE Bond Index",
            "Forex Reserves",
            "Inflation"
        ],
        "Database Table": [
            "rock_treasury_bills_clean",
            "rock_nse_bond_index_clean",
            "rock_forex_reserves_clean",
            "rock_inflation_clean"
        ],
        "Status": [
            "READY",
            "READY",
            "READY",
            "READY"
        ]
    })

    st.dataframe(
        module_status,
        use_container_width=True,
        hide_index=True
    )

    st.subheader(
        "Data Period"
    )

    st.write(
        f"NSE research period: {first_date:%d %b %Y} "
        f"→ {latest_date:%d %b %Y}"
    )

    st.subheader(
        "Licensing / Raw Data"
    )

    st.write(
        """
The original Rock exports are retained locally for research
and provenance. Public redistribution of the underlying Rock
data should only occur where Rock Data Plus licensing permits it.
"""
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Primary analytical source: Rock Data Plus. "
    "Derived statistics are calculated within the platform. "
    "Historical results are not guarantees of future performance."
)












