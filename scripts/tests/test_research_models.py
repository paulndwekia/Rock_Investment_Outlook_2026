from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from research_models import (
    calculate_correlation,
    calculate_index_performance,
    calculate_market_regime,
    calculate_market_regime_from_monthly,
    classify_market_regime,
    calculate_return_risk_statistics,
    calculate_rolling_risk,
    calculate_security_metrics,
    calculate_tbill_spread,
    calculate_yield_curve_slope,
    prepare_equity_panel,
    validate_model_outputs,
)


def _prices(values: list[float], security: str = "SCOM") -> pd.DataFrame:
    return pd.DataFrame({
        "Date": pd.date_range("2025-01-01", periods=len(values), freq="B"),
        "Security": security,
        "Price": values,
        "Volume": [1000.0] * len(values),
        "Net_Foreign_Flow": [100.0] * len(values),
    })


def test_prepare_equity_panel_removes_invalid_prices_and_deduplicates():
    frame = pd.DataFrame({
        "Date": ["2026-01-01", "2026-01-02", "2026-01-02", "bad-date", "2026-01-04", "2026-01-05"],
        "Security": ["SCOM", "SCOM", "SCOM", "SCOM", "SCOM", "SCOM"],
        "Price": [10, 11, 12, 13, 0, np.inf],
    })

    result = prepare_equity_panel(frame)

    assert len(result) == 2
    assert result["Date"].is_monotonic_increasing
    assert result["Price"].tolist() == [10.0, 12.0]
    assert result.iloc[1]["Raw_Daily_Return"] == pytest.approx(0.2)


def test_prepare_equity_panel_flags_spike_and_does_not_bridge_reversal():
    frame = _prices([10.0, 10.2, 10.1, 100.0, 10.3, 10.4])
    result = prepare_equity_panel(frame, max_abs_daily_return=2.0)

    assert bool(result.loc[3, "Return_Anomaly"])
    assert pd.isna(result.loc[3, "Risk_Return"])
    assert pd.isna(result.loc[4, "Risk_Return"])
    assert result.loc[5, "Risk_Return"] == pytest.approx(10.4 / 10.3 - 1)


def test_prepare_equity_panel_rejects_empty_or_non_positive_price_history():
    frame = pd.DataFrame({
        "Date": ["2026-01-01", "2026-01-02"],
        "Security": ["SCOM", "SCOM"],
        "Price": [0, -1],
    })
    with pytest.raises(ValueError, match="No valid positive-price"):
        prepare_equity_panel(frame)


def test_prepare_equity_panel_requires_finite_positive_threshold():
    frame = _prices([10, 11])
    with pytest.raises(ValueError, match="positive finite"):
        prepare_equity_panel(frame, max_abs_daily_return=float("inf"))


def test_security_metrics_use_only_valid_finite_risk_observations():
    values = [100.0]
    for i in range(1, 70):
        values.append(values[-1] * (1.001 if i % 2 else 0.999))
    prepared = prepare_equity_panel(_prices(values))
    metrics = calculate_security_metrics(prepared)
    row = metrics.iloc[0]

    assert row["Valid_Risk_Observations"] >= 30
    assert np.isfinite(row["Annualized_Volatility"])
    assert np.isfinite(row["Maximum_Drawdown"])
    assert -1.0 <= row["Maximum_Drawdown"] <= 0.0
    assert np.isfinite(row["Total_Return"])
    assert np.isfinite(row["Valid_Risk_Observations"])
    assert np.isfinite(row["Return_Anomaly_Count"])
    # CAGR is deliberately unavailable because this test history is shorter than one year.
    assert np.isnan(row["Annualized_Return"])


def test_security_metrics_withhold_full_period_return_if_anomaly_exists():
    values = [10.0 + i * 0.01 for i in range(40)]
    values[20] = 100.0
    values[21] = 10.21
    prepared = prepare_equity_panel(_prices(values))
    metrics = calculate_security_metrics(prepared)
    row = metrics.iloc[0]

    assert row["Return_Anomaly_Count"] >= 1
    assert np.isnan(row["Total_Return"])
    assert np.isnan(row["Annualized_Return"])


def test_security_metrics_respect_minimum_sample_size():
    prepared = prepare_equity_panel(_prices([10, 10.1, 10.2, 10.3]))
    metrics = calculate_security_metrics(prepared, min_risk_observations=30)
    assert np.isnan(metrics.iloc[0]["Annualized_Volatility"])
    assert np.isnan(metrics.iloc[0]["Maximum_Drawdown"])


def test_rolling_risk_respects_full_window_and_never_emits_infinity():
    prepared = prepare_equity_panel(_prices([10 + i * 0.1 for i in range(80)]))
    rolling = calculate_rolling_risk(prepared, windows=(5, 10))

    assert rolling["Vol_5D"].iloc[:5].isna().all()
    assert rolling["Vol_10D"].iloc[:10].isna().all()
    finite = rolling[["Vol_5D", "Vol_10D"]].to_numpy(dtype=float)
    assert not np.isinf(finite).any()


def test_market_regime_compounds_exactly_twelve_consecutive_months():
    dates = pd.date_range("2025-01-01", periods=12, freq="MS")
    prepared = pd.DataFrame({
        "Date": dates,
        "Security": ["SCOM"] * len(dates),
        "Price": [100 + i for i in range(len(dates))],
        "Risk_Return": [0.01] * len(dates),
    })

    result = calculate_market_regime(prepared)
    assert result["status"] == "ok"
    assert result["is_full_consecutive_12m"] is True
    assert result["historical_return_12m"] == pytest.approx((1.01 ** 12) - 1)


def test_market_regime_does_not_claim_twelve_month_return_with_short_history():
    prepared = pd.DataFrame({
        "Date": pd.date_range("2026-01-01", periods=6, freq="MS"),
        "Security": ["SCOM"] * 6,
        "Price": [100, 101, 102, 103, 104, 105],
        "Risk_Return": [0.01] * 6,
    })
    result = calculate_market_regime(prepared)
    assert result["status"] == "ok"
    assert result["is_full_consecutive_12m"] is False
    assert np.isnan(result["historical_return_12m"])


def test_correlation_returns_known_result_and_p_value():
    x = pd.Series(np.arange(40, dtype=float))
    y = pd.Series(np.arange(40, dtype=float) * 3 + 2)
    result = calculate_correlation(x, y, min_observations=30)

    assert result["status"] == "ok"
    assert result["observations"] == 40
    assert result["correlation"] == pytest.approx(1.0)
    assert result["p_value"] < 1e-10


def test_correlation_refuses_insufficient_or_constant_series():
    short = calculate_correlation(pd.Series([1, 2, 3]), pd.Series([3, 2, 1]), min_observations=10)
    constant = calculate_correlation(pd.Series([1] * 30), pd.Series(range(30)), min_observations=10)

    assert short["status"] == "insufficient_observations"
    assert constant["status"] == "constant_series"
    assert np.isnan(constant["correlation"])


def test_tbill_spread_requires_same_observation_date():
    bills = pd.DataFrame({
        "Date": ["2026-01-01", "2026-01-01", "2026-02-01"],
        "Tenor": ["91-Day", "364-Day", "91-Day"],
        "Rate (%)": [8.0, 8.25, 8.5],
    })
    result = calculate_tbill_spread(bills)

    assert result["status"] == "ok"
    assert pd.Timestamp(result["date"]) == pd.Timestamp("2026-01-01")
    assert result["spread_percentage_points"] == pytest.approx(0.25)


def test_tbill_spread_returns_unavailable_when_no_common_date():
    bills = pd.DataFrame({
        "Date": ["2026-01-01", "2026-02-01"],
        "Tenor": ["91-Day", "364-Day"],
        "Rate (%)": [8.0, 8.5],
    })
    result = calculate_tbill_spread(bills)
    assert result["status"] == "unavailable"


def test_yield_curve_slope_orders_maturities_numerically():
    curve = pd.DataFrame({
        "Maturity": ["10 Years", "91 Day", "30 Years", "1 Year"],
        "Yield (%)": [13.0, 8.0, 14.0, 9.0],
    })
    result = calculate_yield_curve_slope(curve)

    assert result["status"] == "ok"
    assert result["short_maturity"] == "91 Day"
    assert result["long_maturity"] == "30 Years"
    assert result["slope_percentage_points"] == pytest.approx(6.0)


def test_yield_curve_does_not_make_slope_from_one_point():
    curve = pd.DataFrame({"Maturity": ["10 Years"], "Yield (%)": [13.0]})
    assert calculate_yield_curve_slope(curve)["status"] == "unavailable"


def test_release_gate_rejects_non_finite_required_model_outputs():
    frame = pd.DataFrame({"volatility": [0.2, 0.3], "drawdown": [-0.1, np.inf]})
    result = validate_model_outputs(frame, required_numeric=("volatility", "drawdown"))
    assert result["status"] == "failed"
    assert result["non_finite"] == ["drawdown"]


def test_release_gate_rejects_missing_required_model_outputs():
    frame = pd.DataFrame({"volatility": [0.2, 0.3]})
    result = validate_model_outputs(frame, required_numeric=("volatility", "drawdown"))
    assert result["status"] == "failed"
    assert result["missing_columns"] == ["drawdown"]


def test_contiguous_drawdown_does_not_bridge_missing_return_gaps():
    result = calculate_return_risk_statistics(
        pd.Series([0.5, np.nan, -0.2] + [0.1] * 29),
        min_risk_observations=30,
    )

    assert result["status"] == "ok"
    # The post-gap loss starts a new segment; it must not be measured
    # against the pre-gap peak.
    assert result["maximum_drawdown"] == pytest.approx(0.0)


def test_tbill_spread_parses_percentage_strings_and_same_date_rates():
    bills = pd.DataFrame({
        "Date": ["2026-01-05", "2026-01-05", "2026-01-12", "2026-01-12"],
        "Tenor": ["91-Day", "364-Day", "91-Day", "364-Day"],
        "Rate (%)": ["8.50%", "8.75%", "8.60%", "8.90%"],
    })
    result = calculate_tbill_spread(bills)

    assert result["status"] == "ok"
    assert pd.Timestamp(result["date"]) == pd.Timestamp("2026-01-12")
    assert result["91_day_rate"] == pytest.approx(8.6)
    assert result["364_day_rate"] == pytest.approx(8.9)
    assert result["spread_percentage_points"] == pytest.approx(0.3)


def test_bond_index_performance_uses_levels_to_calculate_sample_return():
    frame = pd.DataFrame({
        "Date": ["2025-01-01", "2025-12-31"],
        "Index Value": [1000.0, 1125.0],
    })
    result = calculate_index_performance(frame)

    assert result["status"] == "ok"
    assert result["latest_index_value"] == pytest.approx(1125.0)
    assert result["sample_return"] == pytest.approx(0.125)
    assert result["sample_return"] != result["latest_index_value"]


def test_market_regime_classifies_constructive_observed_trend_without_forecast_claim():
    result = classify_market_regime({
        "is_full_consecutive_12m": True,
        "historical_return_12m": 0.12,
        "positive_month_share": 0.67,
    })
    assert result["status"] == "ok"
    assert result["signal"] == "constructive"
    assert result["is_forecast"] is False


def test_market_regime_classifies_defensive_and_mixed_trends():
    defensive = classify_market_regime({
        "is_full_consecutive_12m": True,
        "historical_return_12m": -0.1,
        "positive_month_share": 0.4,
    })
    mixed = classify_market_regime({
        "is_full_consecutive_12m": True,
        "historical_return_12m": 0.1,
        "positive_month_share": 0.4,
    })
    assert defensive["signal"] == "defensive"
    assert mixed["signal"] == "mixed"


def test_market_regime_classification_is_unavailable_without_twelve_consecutive_months():
    result = classify_market_regime({
        "is_full_consecutive_12m": False,
        "historical_return_12m": np.nan,
        "positive_month_share": np.nan,
    })
    assert result["status"] == "insufficient_history"
    assert result["signal"] == "unavailable"


def test_monthly_regime_summary_calculates_full_twelve_month_return():
    frame = pd.DataFrame({
        "Month": pd.period_range("2025-01", periods=12, freq="M").astype(str),
        "Market_Return": [0.01] * 12,
    })
    result = calculate_market_regime_from_monthly(frame)
    assert result["status"] == "passed"
    assert result["is_full_consecutive_12m"] is True
    assert result["historical_return_12m"] == pytest.approx((1.01 ** 12) - 1)
    assert result["maximum_drawdown_12m"] == pytest.approx(0.0)


def test_monthly_regime_summary_withholds_gapped_monthly_history():
    months = list(pd.period_range("2025-01", periods=12, freq="M").astype(str))
    months.pop(5)
    frame = pd.DataFrame({"Month": months, "Market_Return": [0.01] * len(months)})
    result = calculate_market_regime_from_monthly(frame)
    assert result["status"] == "incomplete"
    assert result["is_full_consecutive_12m"] is False
    assert np.isnan(result["historical_return_12m"])
