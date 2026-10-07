# Kenya Investment Intelligence

## A Kenyan Market Research, Risk and Investment Outlook Platform

**Kenya Investment Intelligence** is a quantitative research platform designed to bring Kenyan equity, macroeconomic, fixed-income and risk analysis into one interactive research environment.

The platform is built around a simple research workflow:

**Data → Market Regime → Equity Analysis → Risk → Fixed Income → Macro → Cross-Market Research → 12-Month Outlook**

It is intended for quantitative market research rather than simply displaying charts. Observed data is kept separate from derived statistics and forward-looking scenarios so that the research process remains transparent.

---

## 1. What the Website Does

The website acts as a research console for analysing the Kenyan investment environment.

Instead of studying equities, interest rates, macroeconomic indicators and risk measures separately, the platform connects them into one workflow.

The core questions are:

- What is happening in the Kenyan market?
- What market regime are we in?
- Which equities are performing and how much risk are they carrying?
- What is happening across Treasury Bills, the yield curve and government bonds?
- What macroeconomic conditions could affect Kenyan assets?
- How are macro variables historically related to the equity market?
- What evidence should support a 12-month investment view?

The platform is deliberately structured so that historical relationships are not presented as guaranteed forecasts.

---

# 2. Website Modules

## Command Center

The Command Center provides the high-level market view.

It is intended to give the user a quick understanding of the state of the research environment before moving into the detailed analytical modules.

Typical information includes market summaries, key quantitative indicators and the status of the underlying research data.

---

## Market Regime

The Market Regime module is used to interpret the broader market environment.

It brings together market behaviour and selected risk indicators to help distinguish between more constructive, balanced and defensive conditions.

The objective is not to predict the market with certainty, but to provide a structured regime interpretation based on observed evidence.

---

## Equity Lab

The Equity Lab focuses on the Kenyan equity sample.

It supports analysis of areas such as:

- historical prices
- returns
- volatility
- drawdowns
- performance comparisons
- trading observations
- security-level behaviour

The platform uses a cleaned analytical NSE dataset for research calculations while preserving the original Rock observations separately.

This distinction prevents analytical cleaning from silently rewriting the underlying source data.

---

## Risk Lab

The Risk Lab evaluates the risk characteristics of the equity sample.

It can be used to study:

- returns
- volatility
- maximum drawdown
- security-level risk
- historical stress behaviour
- portfolio-style risk diagnostics

Risk calculations use the cleaned analytical equity structure where appropriate.

Extreme observations are not automatically assumed to be errors. Data corrections are only applied where there is evidence that an observation is invalid or unsuitable for the intended analytical calculation.

---

## Fixed Income

The Fixed Income module covers the Kenyan government fixed-income environment.

It contains research areas for:

### Yield Curve
Analysis of maturity and yield structure, including the relationship between short and long yields.

### Treasury Bills
Analysis of Treasury Bill tenor and rate behaviour, including the 91-day and 364-day relationship.

### Bond Index
Analysis of observed government bond-index behaviour where the underlying dataset supports it.

### Public Debt
Presentation and analysis of the available public-debt observations.

Fixed-income evidence is used as part of the broader investment-outlook framework.

---

## Macro Radar

Macro Radar provides a central view of Kenyan macroeconomic observations.

The platform can work with datasets including:

- inflation
- diaspora remittances
- exchange rates
- foreign-exchange reserve reference data
- fuel prices
- historical PMI
- monetary-policy indicators
- public debt
- liquidity indicators

Where the source unit or interpretation is not sufficiently verified, the platform avoids inventing a unit or economic meaning.

### Important Forex Reserve Limitation

The available Rock series is a **Forex Reserve Threshold/reference series** rather than an actual reserve-balance series.

It must therefore not be interpreted as Kenya's actual foreign-exchange reserve balance.

---

## Cross-Market Research

Cross-Market Research studies historical relationships between Kenyan macro variables and the cleaned NSE equity sample.

The module calculates descriptive historical correlations using time-aligned observations.

These results are intended to answer questions such as:

> Which macro variables have historically moved with the equity sample?

Correlation is descriptive. It does **not** establish causation and does not guarantee future returns.

The platform also reports the number of matched observations so that users can see how much data supports each relationship.

---

## 12-Month Investment Outlook

The 12-Month Investment Outlook combines observed quantitative evidence with a forward-looking scenario framework.

The page separates:

### Observed Evidence
Examples include:

- recent historical equity return
- annualised monthly volatility
- maximum drawdown
- Treasury Bill spread
- short yield
- long yield
- yield-curve slope
- bond-index return
- latest inflation
- latest reported foreign flow

### Forward-Looking Scenarios

The framework uses three scenarios:

**Base — Balanced**

A central scenario based on the current evidence and the continuation of broadly similar conditions.

**Bull — Constructive**

A scenario supported by improving macro conditions, improving liquidity and sustained market risk appetite.

**Bear — Defensive**

A scenario associated with renewed inflation pressure, FX stress, tighter liquidity or persistent foreign outflows.

The scenario framework is deliberately presented as a decision framework rather than a guaranteed forecast.

---

## Data Governance

Data Governance explains where the research data comes from, how it is stored and how analytical datasets are separated from raw observations.

The current architecture is:

```text
ROCK DATA PLUS
      ↓
Curated Rock Exports
      ↓
SQLite Research Database
      ↓
Dataset-Specific Analytical Structures
      ↓
Quantitative Research Engine
      ↓
Interactive Research Platform
```

The governance layer is responsible for making the distinction between:

**Raw data**

Original stored observations retained for provenance.

**Analytical data**

Cleaned or dataset-specific structures used for calculations.

**Derived statistics**

Values calculated by the platform from the available observations.

**Scenarios**

Forward-looking interpretations that are kept separate from observed historical evidence.

---

# 3. Data Validation Philosophy

The platform follows a conservative data-validation approach.

### Raw data is preserved

The raw observation store is not rewritten merely to make a chart look better.

### Cleaning is analytical

When cleaning is necessary, the cleaned structure is separated from the raw observations.

### Missing information is disclosed

The platform uses states such as `DATA REQUIRED`, `DATA UNAVAILABLE` or `REVIEW` instead of inventing values.

### Extreme observations are investigated

Large movements are not automatically deleted. An observation is changed only when there is sufficient evidence that it is inappropriate for the intended analysis.

### Provenance matters

The platform retains dataset and observation lineage so that research results can be traced back to the underlying data structure.

---

# 4. Research Methodology

The website is designed around standard quantitative-finance and market-research concepts.

### Returns

Historical returns are calculated from the available cleaned equity observations.

### Volatility

Historical volatility is used to describe variability in observed returns.

### Drawdown

Drawdown measures the decline from a previous observed peak.

### Correlation

Pearson correlation is used for descriptive historical co-movement where sufficient matched observations exist.

### Yield-Curve Analysis

The fixed-income module compares yields across maturities and calculates the long-short curve slope where the necessary observations are available.

### Scenario Analysis

The 12-month outlook separates measured historical evidence from conditional forward-looking scenarios.

The platform does not treat historical return as a guaranteed forecast.

---

# 5. Data Sources

The primary analytical data source for the current platform is **Rock Data Plus**.

The local research database stores the available Rock observations and the platform derives its analytical measures from the relevant local structures.

The project is intended for research use subject to the applicable licensing and data-use restrictions.

Redistribution of underlying proprietary data should only occur where the relevant licence permits it.

---

# 6. Technology Stack

The current website is built primarily with:

- **Python**
- **Streamlit**
- **Pandas**
- **NumPy**
- **SQLite**
- **Plotly**

Python is used for data processing and quantitative calculations.

SQLite provides the local research-data layer.

Streamlit provides the interactive research interface.

Plotly is used for interactive analytical visualisations.

---

# 7. Project Structure

A simplified project structure is:

```text
Rock_Investment_Outlook_2026/
│
├── database/
│   └── rock_investment_intelligence.db
│
├── website/
│   └── app.py
│
├── analysis/
│   └── analytical outputs and research reports
│
├── scripts/
│   ├── build_database.py
│   ├── build_website.py
│   ├── build_quant_engine.py
│   ├── build_outlook.py
│   ├── connect_outlook.py
│   ├── data_audit.py
│   ├── data_collector.py
│   ├── data_curator.py
│   ├── data_inventory.py
│   ├── data_registry.py
│   ├── database_status.py
│   ├── equity_data_prep.py
│   ├── research_engine.py
│   ├── schema_audit.py
│   └── report_engine.py
│
└── README.md
```

The `scripts` directory contains active project tooling. Historical repair and temporary scripts are intentionally kept out of the active workflow.

---

# 8. Running the Website

From the project root:

```powershell
streamlit run website\app.py
```

The application should then be available through the local Streamlit address displayed in the terminal, normally:

```text
http://localhost:8501
```

---

# 9. Intended Research Workflow

A typical research session can follow this sequence:

```text
Command Center
      ↓
Market Regime
      ↓
Equity Lab
      ↓
Risk Lab
      ↓
Fixed Income
      ↓
Macro Radar
      ↓
Cross-Market Research
      ↓
12-Month Investment Outlook
      ↓
Data Governance
```

This creates a research chain from market observations to an investment view.

---

# 10. What the Platform Is Not

The website is not designed to claim certainty about future market performance.

In particular:

- historical correlation is not causation;
- historical performance is not a guaranteed future return;
- scenario analysis is conditional;
- reference-only data should not be interpreted beyond its documented meaning;
- missing data should not be replaced with fabricated estimates.

These limitations are part of the research methodology rather than an afterthought.

---

# 11. Kenya-Focused Investment Intelligence

The purpose of the platform is to make quantitative research more relevant to the Kenyan investment environment.

Rather than relying on a generic global-market dashboard, the platform is structured around Kenyan evidence such as:

- NSE equities
- Treasury Bills
- government bond and yield information
- inflation
- exchange rates
- liquidity
- monetary policy
- public debt
- diaspora remittances
- fuel prices
- foreign flows
- Kenyan macro-market relationships

This creates a foundation for studying how Kenya's macroeconomic environment can interact with local asset markets.

---

# 12. Future Development

Potential future development areas include:

- scheduled data ingestion
- additional validated government-bond data
- historical-data backfills
- portfolio-position integration
- instrument-specific historical risk analysis
- stronger workspace authorization
- audit logging
- rate limiting
- richer research reports
- additional scenario analytics

New features should preserve the separation between source data, analytical transformations and forward-looking assumptions.

---

# 13. Academic / Project Context

The platform is intended to demonstrate how quantitative methods, programming and financial-market research can be combined to build a practical Kenyan investment-research system.

It is particularly relevant to areas such as:

- Computational Mathematics
- Financial Engineering
- Quantitative Finance
- Econometrics
- Risk Management
- Investment Research
- Data Analytics

---

# 14. Author

**Kenya Investment Intelligence**

Quantitative research platform focused on the Kenyan investment market.

Developed as a practical research and quantitative-analytics project with an emphasis on Kenyan market data, financial modelling, risk analysis and investment decision support.
