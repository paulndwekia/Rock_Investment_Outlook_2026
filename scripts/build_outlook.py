"""Build transparent quantitative outlook inputs from validated analysis outputs.

This module summarises calculated observations. It does not manufacture missing
market data or convert a descriptive scenario framework into a forecast.
"""
from __future__ import annotations

from pathlib import Path
import json
from typing import Any

import numpy as np
import pandas as pd

from research_models import (
    calculate_market_regime_from_monthly,
    calculate_index_performance,
    calculate_tbill_spread,
    calculate_yield_curve_slope,
)

PROJECT = Path.home() / "Desktop" / "Rock_Investment_Outlook_2026"
ANALYSIS = PROJECT / "analysis"

print("=" * 90)
print("KENYA INVESTMENT INTELLIGENCE — QUANTITATIVE OUTLOOK ENGINE")
print("=" * 90)


def read_csv(name: str) -> pd.DataFrame:
    path = ANALYSIS / name
    if not path.exists():
        print(f"  - {name}: NOT FOUND")
        return pd.DataFrame()
    try:
        frame = pd.read_csv(path, low_memory=False)
        print(f"  ✓ {name}: {len(frame):,} rows")
        return frame
    except Exception as exc:
        print(f"  ! {name}: {exc}")
        return pd.DataFrame()


def numeric(values: pd.Series) -> pd.Series:
    if values.dtype == object or pd.api.types.is_string_dtype(values.dtype):
        values = (
            values.astype("string")
            .str.strip()
            .str.replace(",", "", regex=False)
            .str.replace("%", "", regex=False)
            .str.replace("KES", "", regex=False)
            .str.replace("KSh", "", regex=False)
        )
    result = pd.to_numeric(values, errors="coerce")
    return result.where(np.isfinite(result))


def calculate_market_regime_from_monthly_input(frame: pd.DataFrame) -> dict[str, Any]:
    """Delegate to the shared tested market-regime summariser."""
    return calculate_market_regime_from_monthly(frame)


def sanitise(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitise(item) for item in value]
    if isinstance(value, (pd.Timestamp, pd.Period)):
        return str(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


metrics: dict[str, Any] = {}

# ---------------------------------------------------------------------------
# 1. Market regime: use the same equal-weighted daily cross-sectional proxy
#    that the validated quantitative engine generated.
# ---------------------------------------------------------------------------
print("\n[1] MARKET REGIME")
regime_monthly = read_csv("market_regime_monthly.csv")
market_regime = calculate_market_regime_from_monthly_input(regime_monthly)
metrics["market_regime"] = market_regime

# ---------------------------------------------------------------------------
# 2. Cross-sectional equity risk: summarise eligible securities, never the
#    last arbitrary row in the CSV.
# ---------------------------------------------------------------------------
print("\n[2] EQUITY RISK DISTRIBUTION")
risk = read_csv("security_metrics.csv")
if not risk.empty:
    expected = {
        "Annualized_Volatility",
        "Maximum_Drawdown",
        "Valid_Risk_Observations",
        "Return_Anomaly_Count",
    }
    if expected.issubset(risk.columns):
        volatility = numeric(risk["Annualized_Volatility"])
        drawdown = numeric(risk["Maximum_Drawdown"])
        risk_observations = numeric(risk["Valid_Risk_Observations"])
        anomaly_counts = numeric(risk["Return_Anomaly_Count"]).fillna(0)

        eligible = (
            risk_observations.ge(30)
            & volatility.notna()
            & drawdown.notna()
            & volatility.map(np.isfinite)
            & drawdown.map(np.isfinite)
        )
        vol_eligible = volatility[eligible]
        dd_eligible = drawdown[eligible]

        metrics["risk"] = {
            "status": "passed" if int(eligible.sum()) > 0 else "incomplete",
            "eligible_securities": int(eligible.sum()),
            "securities_with_anomalies": int(anomaly_counts.gt(0).sum()),
            "median_annualised_volatility": float(vol_eligible.median()) if not vol_eligible.empty else None,
            "p90_annualised_volatility": float(vol_eligible.quantile(0.90)) if not vol_eligible.empty else None,
            "median_maximum_drawdown": float(dd_eligible.median()) if not dd_eligible.empty else None,
            "worst_security_maximum_drawdown": float(dd_eligible.min()) if not dd_eligible.empty else None,
        }
    else:
        metrics["risk"] = {
            "status": "unavailable",
            "reason": f"Security metrics missing columns: {sorted(expected.difference(risk.columns))}",
        }
else:
    metrics["risk"] = {"status": "unavailable", "reason": "security_metrics.csv is missing or empty"}

# ---------------------------------------------------------------------------
# 3. Treasury bills: compare the 91-day and 364-day observations on the same
#    latest common date.
# ---------------------------------------------------------------------------
print("\n[3] TREASURY BILLS")
bills = read_csv("clean_treasury_bills.csv")
tbill_result = calculate_tbill_spread(bills)
metrics["treasury_bills"] = {
    "status": tbill_result["status"],
    "latest_common_date": tbill_result.get("date"),
    "91_day_rate": tbill_result.get("91_day_rate"),
    "364_day_rate": tbill_result.get("364_day_rate"),
    "91d_364d_spread": tbill_result.get("spread_percentage_points"),
    "reason": tbill_result.get("reason"),
}

# ---------------------------------------------------------------------------
# 4. Yield curve: sort maturities by their numeric tenor, not string order.
# ---------------------------------------------------------------------------
print("\n[4] YIELD CURVE")
curve = read_csv("clean_yield_curve.csv")
curve_result = calculate_yield_curve_slope(curve)
metrics["yield_curve"] = {
    "status": curve_result["status"],
    "points": curve_result.get("points"),
    "short_maturity": curve_result.get("short_maturity"),
    "short_yield": curve_result.get("short_yield"),
    "long_maturity": curve_result.get("long_maturity"),
    "long_yield": curve_result.get("long_yield"),
    "long_short_spread": curve_result.get("slope_percentage_points"),
    "reason": curve_result.get("reason"),
}

# ---------------------------------------------------------------------------
# 5. Bond index: calculate a return from index levels, not from the latest
#    index level itself.
# ---------------------------------------------------------------------------
print("\n[5] GOVERNMENT BOND INDEX")
bond = read_csv("clean_nse_bond_index.csv")
bond_result = calculate_index_performance(bond)
metrics["bond_index"] = {
    "status": bond_result["status"],
    "observations": bond_result.get("observations"),
    "first_date": bond_result.get("first_date"),
    "last_date": bond_result.get("last_date"),
    "first_index_value": bond_result.get("first_index_value"),
    "latest_index_value": bond_result.get("latest_index_value"),
    "total_sample_return": bond_result.get("sample_return"),
    "reason": bond_result.get("reason"),
}

# ---------------------------------------------------------------------------
# 6. Inflation: retain the latest actual dated rate.
# ---------------------------------------------------------------------------
print("\n[6] INFLATION")
inflation = read_csv("clean_inflation.csv")
if not inflation.empty and {"Date", "Rate (%)"}.issubset(inflation.columns):
    inflation["Date"] = pd.to_datetime(inflation["Date"], errors="coerce")
    inflation["Rate (%)"] = numeric(inflation["Rate (%)"])
    inflation = inflation.dropna(subset=["Date", "Rate (%)"]).sort_values("Date")
    if not inflation.empty:
        latest = inflation.iloc[-1]
        metrics["inflation"] = {
            "status": "passed",
            "latest_date": latest["Date"].strftime("%Y-%m-%d"),
            "latest_value": float(latest["Rate (%)"]),
        }
    else:
        metrics["inflation"] = {"status": "unavailable", "reason": "No valid dated inflation observations"}
else:
    metrics["inflation"] = {"status": "unavailable", "reason": "Required inflation fields are missing"}

# ---------------------------------------------------------------------------
# 7. Foreign-flow relationships: aggregate the valid cross-sectional estimates.
# ---------------------------------------------------------------------------
print("\n[7] FOREIGN-FLOW RELATIONSHIPS")
flows = read_csv("foreign_flow_relationships.csv")
if not flows.empty and {"Foreign_Flow_Return_Correlation", "P_Value"}.issubset(flows.columns):
    correlation = numeric(flows["Foreign_Flow_Return_Correlation"]).dropna()
    p_values = numeric(flows["P_Value"]).dropna()
    metrics["foreign_flows"] = {
        "status": "passed" if not correlation.empty else "unavailable",
        "securities_with_valid_estimates": int(len(correlation)),
        "median_correlation": float(correlation.median()) if not correlation.empty else None,
        "median_p_value": float(p_values.median()) if not p_values.empty else None,
    }
else:
    metrics["foreign_flows"] = {"status": "unavailable", "reason": "No valid foreign-flow relationship estimates"}

# ---------------------------------------------------------------------------
# 8. Scenario inputs: observed references only, never forecasts.
# ---------------------------------------------------------------------------
print("\n[8] SCENARIO MONITORING INPUTS")
metrics["scenario_framework"] = {
    "is_forecast": False,
    "probabilities_available": False,
    "observed_volatility": metrics["risk"].get("median_annualised_volatility"),
    "curve_slope": metrics["yield_curve"].get("long_short_spread"),
    "tbill_91d_364d_spread": metrics["treasury_bills"].get("91d_364d_spread"),
    "latest_inflation": metrics["inflation"].get("latest_value"),
    "note": "Descriptive monitoring inputs only. The Bull/Base/Bear cards are not statistical forecasts or trained prediction models.",
}

# Include the quant-engine release gate where available.
validation_path = ANALYSIS / "model_validation.json"
if validation_path.exists():
    try:
        metrics["model_validation"] = json.loads(validation_path.read_text(encoding="utf-8"))
    except Exception as exc:
        metrics["model_validation"] = {"overall_status": "unavailable", "reason": str(exc)}
else:
    metrics["model_validation"] = {"overall_status": "not_run", "reason": "Run build_quant_engine.py first"}

# Final machine-readable status: no success status if any upstream
# quantitative-engine gate or required data section is incomplete.
required_sections = (
    "market_regime",
    "risk",
    "treasury_bills",
    "yield_curve",
    "bond_index",
    "inflation",
    "model_validation",
)
section_status = {
    "market_regime": metrics["market_regime"].get("status") == "passed",
    "risk": metrics["risk"].get("status") == "passed",
    "treasury_bills": metrics["treasury_bills"].get("status") == "ok",
    "yield_curve": metrics["yield_curve"].get("status") == "ok",
    "bond_index": metrics["bond_index"].get("status") == "ok",
    "inflation": metrics["inflation"].get("status") == "passed",
    "model_validation": metrics["model_validation"].get("overall_status") == "passed",
}
metrics["overall_status"] = "passed" if all(section_status.values()) else "incomplete"
metrics["incomplete_sections"] = [
    section for section in required_sections if not section_status[section]
]

# ---------------------------------------------------------------------------
# Save JSON and flat CSV without NaN/Infinity literals.
# ---------------------------------------------------------------------------
json_path = ANALYSIS / "outlook_quant_metrics.json"
clean_metrics = sanitise(metrics)
json_path.write_text(
    json.dumps(clean_metrics, indent=2, allow_nan=False),
    encoding="utf-8",
)

rows: list[dict[str, Any]] = []
for section, values in clean_metrics.items():
    if not isinstance(values, dict):
        rows.append({"section": "summary", "metric": section, "value": values})
        continue
    for key, value in values.items():
        if isinstance(value, dict):
            continue
        rows.append({"section": section, "metric": key, "value": value})

csv_path = ANALYSIS / "outlook_quant_metrics.csv"
pd.DataFrame(rows).to_csv(csv_path, index=False, encoding="utf-8-sig")

print("\n" + "=" * 90)
print("QUANTITATIVE OUTLOOK ENGINE COMPLETE")
print("=" * 90)
print("Overall status:", metrics["overall_status"])
print("Incomplete sections:", metrics["incomplete_sections"] or "None")
print("Created:", json_path)
print("Created:", csv_path)
