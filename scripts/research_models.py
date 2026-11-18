"""Validated, reusable quantitative calculations for Kenya Investment Intelligence.

These functions are deliberately pure: they do not read project files, mutate input
frames, or substitute fallback values when an input series is missing.
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import pearsonr


def _finite_numeric(values: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(values, errors="coerce")
    return numeric.where(np.isfinite(numeric))


def prepare_equity_panel(
    frame: pd.DataFrame,
    *,
    date_col: str = "Date",
    security_col: str = "Security",
    price_col: str = "Price",
    max_abs_daily_return: float = 2.0,
) -> pd.DataFrame:
    """Clean price inputs and calculate gap-aware daily returns.

    Price rows with invalid dates, names, non-finite values or non-positive prices
    are excluded. Duplicate security/date rows keep the last source row.
    Returns larger than the configured limit are flagged; both the flagged return
    and the immediately following return are excluded from risk calculations so
    an isolated bad price cannot create a false reversal return.
    """
    if not np.isfinite(max_abs_daily_return) or max_abs_daily_return <= 0:
        raise ValueError("max_abs_daily_return must be a positive finite number")

    required = {date_col, security_col, price_col}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required equity columns: {sorted(missing)}")

    data = frame.copy()
    data["Date"] = pd.to_datetime(data[date_col], errors="coerce", utc=True).dt.tz_convert(None)
    data["Security"] = data[security_col].astype("string").str.strip()
    data["Price"] = _finite_numeric(data[price_col])

    for column in ("Volume", "Net_Foreign_Flow", "Change_Pct"):
        if column in data.columns:
            data[column] = _finite_numeric(data[column])
        else:
            data[column] = np.nan

    data = data[
        data["Date"].notna()
        & data["Security"].notna()
        & data["Security"].ne("")
        & data["Price"].notna()
        & data["Price"].gt(0)
    ].copy()

    if data.empty:
        raise ValueError("No valid positive-price equity observations remain")

    data = (
        data.sort_values(["Security", "Date"], kind="stable")
        .drop_duplicates(["Security", "Date"], keep="last")
        .reset_index(drop=True)
    )

    raw_returns = data.groupby("Security", sort=False)["Price"].pct_change(fill_method=None)
    anomaly = raw_returns.abs().gt(max_abs_daily_return).fillna(False)
    prior_anomaly = anomaly.groupby(data["Security"], sort=False).shift(1).fillna(False).astype(bool)
    excluded = anomaly | prior_anomaly

    data["Raw_Daily_Return"] = raw_returns
    data["Return_Anomaly"] = anomaly
    data["Risk_Return"] = raw_returns.mask(excluded)
    data["Daily_Return"] = data["Risk_Return"]
    data["Log_Return"] = np.log1p(data["Daily_Return"].where(data["Daily_Return"].gt(-1)))

    return data


def _maximum_drawdown_by_contiguous_segment(returns: pd.Series) -> float:
    """Calculate the worst peak-to-trough loss without bridging missing returns."""
    values = _finite_numeric(returns).reset_index(drop=True)
    valid = values.notna()
    if not valid.any():
        return float("nan")

    segment_id = (~valid).cumsum()
    drawdowns: list[float] = []
    for _, segment in values[valid].groupby(segment_id[valid]):
        wealth = (1.0 + segment).cumprod()
        drawdown = wealth / wealth.cummax() - 1.0
        if not drawdown.empty:
            drawdowns.append(float(drawdown.min()))

    return min(drawdowns) if drawdowns else float("nan")


def calculate_security_metrics(
    prepared: pd.DataFrame,
    *,
    min_risk_observations: int = 30,
    annualisation_days: int = 252,
) -> pd.DataFrame:
    """Calculate auditable security-level return and risk measures."""
    if min_risk_observations < 2:
        raise ValueError("min_risk_observations must be at least 2")
    if annualisation_days <= 0:
        raise ValueError("annualisation_days must be positive")

    rows: list[dict[str, Any]] = []
    for security, group in prepared.groupby("Security", sort=True):
        group = group.sort_values("Date")
        prices = _finite_numeric(group["Price"]).dropna()
        returns = _finite_numeric(group["Risk_Return"]).dropna()
        anomaly_count = int(group["Return_Anomaly"].fillna(False).sum())
        enough_returns = len(returns) >= min_risk_observations
        clean_full_path = anomaly_count == 0 and len(prices) >= 2

        first_price = float(prices.iloc[0]) if not prices.empty else float("nan")
        last_price = float(prices.iloc[-1]) if not prices.empty else float("nan")
        total_return = (
            last_price / first_price - 1.0
            if clean_full_path and first_price > 0
            else float("nan")
        )

        elapsed_days = (
            (group["Date"].max() - group["Date"].min()).days
            if len(group) >= 2
            else 0
        )
        annualised_return = (
            (last_price / first_price) ** (365.25 / elapsed_days) - 1.0
            if clean_full_path and elapsed_days >= 365 and first_price > 0
            else float("nan")
        )

        volatility = (
            float(returns.std(ddof=1) * np.sqrt(annualisation_days))
            if enough_returns
            else float("nan")
        )
        max_drawdown = (
            _maximum_drawdown_by_contiguous_segment(group["Risk_Return"])
            if enough_returns
            else float("nan")
        )
        positive_days = float((returns > 0).mean()) if enough_returns else float("nan")

        volume = _finite_numeric(group["Volume"]).dropna()
        foreign_flow = _finite_numeric(group["Net_Foreign_Flow"]).dropna()

        rows.append({
            "Security": security,
            "Start_Date": group["Date"].min().date(),
            "End_Date": group["Date"].max().date(),
            "Observations": int(len(group)),
            "Valid_Risk_Observations": int(len(returns)),
            "Return_Anomaly_Count": anomaly_count,
            "First_Price": first_price,
            "Last_Price": last_price,
            "Total_Return": total_return,
            "Annualized_Return": annualised_return,
            "Annualized_Volatility": volatility,
            "Maximum_Drawdown": max_drawdown,
            "Average_Volume": float(volume.mean()) if not volume.empty else float("nan"),
            "Total_Net_Foreign_Flow": float(foreign_flow.sum()) if not foreign_flow.empty else float("nan"),
            "Positive_Return_Days": positive_days,
        })

    result = pd.DataFrame(rows)
    numeric_columns = result.select_dtypes(include=[np.number]).columns
    if not result.empty and not np.isfinite(result[numeric_columns].to_numpy(dtype=float)).all():
        raise ArithmeticError("Non-finite values detected in security metrics")
    return result


def calculate_rolling_risk(
    prepared: pd.DataFrame,
    *,
    windows: tuple[int, ...] = (21, 63),
    annualisation_days: int = 252,
) -> pd.DataFrame:
    """Return rolling annualised volatility for each security."""
    if not windows or any(window < 2 for window in windows):
        raise ValueError("Rolling windows must contain integers of at least 2")
    if annualisation_days <= 0:
        raise ValueError("annualisation_days must be positive")

    frames: list[pd.DataFrame] = []
    for _, group in prepared.groupby("Security", sort=True):
        group = group.sort_values("Date").copy()
        returns = _finite_numeric(group["Risk_Return"])
        for window in windows:
            group[f"Vol_{window}D"] = (
                returns.rolling(window=window, min_periods=window).std(ddof=1)
                * np.sqrt(annualisation_days)
            )
        frames.append(group[["Date", "Security", "Price", "Risk_Return", *[f"Vol_{w}D" for w in windows]]])

    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def calculate_market_regime(
    prepared: pd.DataFrame,
    *,
    months_required: int = 12,
) -> dict[str, Any]:
    """Summarise equal-weighted monthly security returns; not an official index."""
    daily = (
        prepared.dropna(subset=["Risk_Return"])
        .groupby("Date")["Risk_Return"]
        .mean()
        .sort_index()
    )
    if daily.empty:
        return {
            "status": "unavailable",
            "reason": "No valid daily security returns",
            "monthly": pd.DataFrame(),
        }

    daily_frame = daily.rename("Market_Return").reset_index()
    daily_frame["Month"] = daily_frame["Date"].dt.to_period("M")
    monthly = (
        daily_frame.groupby("Month")["Market_Return"]
        .apply(lambda values: float((1.0 + values).prod() - 1.0))
        .rename("Market_Return")
        .reset_index()
        .sort_values("Month")
    )

    recent = monthly.tail(months_required).copy()
    consecutive = (
        len(recent) == months_required
        and all(
            (recent["Month"].iloc[i] - recent["Month"].iloc[i - 1]) == 1
            for i in range(1, len(recent))
        )
    )
    return_series = _finite_numeric(recent["Market_Return"])
    return {
        "status": "ok" if len(recent) >= 2 else "insufficient_history",
        "monthly": monthly,
        "months_available": int(len(recent)),
        "historical_return_12m": (
            float((1.0 + return_series).prod() - 1.0)
            if consecutive
            else float("nan")
        ),
        "annualised_monthly_volatility": (
            float(return_series.std(ddof=1) * np.sqrt(12.0))
            if len(return_series) >= 2
            else float("nan")
        ),
        "positive_month_share": (
            float((return_series > 0).mean())
            if len(return_series) >= 2
            else float("nan")
        ),
        "is_full_consecutive_12m": bool(consecutive),
        "definition": "Equal-weighted cross-sectional security-return proxy; not an official NSE index.",
    }


def calculate_correlation(
    left: pd.Series,
    right: pd.Series,
    *,
    min_observations: int = 30,
) -> dict[str, Any]:
    """Pearson correlation with explicit coverage and degeneracy checks."""
    if min_observations < 3:
        raise ValueError("min_observations must be at least 3")
    pair = pd.DataFrame({
        "left": _finite_numeric(left).reset_index(drop=True),
        "right": _finite_numeric(right).reset_index(drop=True),
    }).dropna()
    count = int(len(pair))
    if count < min_observations:
        return {"status": "insufficient_observations", "observations": count, "correlation": float("nan"), "p_value": float("nan")}
    if pair["left"].nunique() < 2 or pair["right"].nunique() < 2:
        return {"status": "constant_series", "observations": count, "correlation": float("nan"), "p_value": float("nan")}
    correlation, p_value = pearsonr(pair["left"], pair["right"])
    return {
        "status": "ok",
        "observations": count,
        "correlation": float(correlation),
        "p_value": float(p_value),
    }


def _tenor_key(value: Any) -> str | None:
    text = str(value).strip().lower().replace(" ", "").replace("-", "")
    if text in {"91day", "91days", "91d"}:
        return "91-Day"
    if text in {"364day", "364days", "364d", "12month", "1year"}:
        return "364-Day"
    return None


def calculate_tbill_spread(
    bills: pd.DataFrame,
    *,
    date_col: str = "Date",
    tenor_col: str = "Tenor",
    rate_col: str = "Rate (%)",
) -> dict[str, Any]:
    """Calculate 364D minus 91D only on a date where both rates are present."""
    if not {date_col, tenor_col, rate_col}.issubset(bills.columns):
        return {"status": "unavailable", "reason": "Required Treasury-bill fields are missing"}
    data = bills[[date_col, tenor_col, rate_col]].copy()
    data["Date"] = pd.to_datetime(data[date_col], errors="coerce")
    data["Rate"] = _finite_numeric(data[rate_col])
    data["Tenor_Key"] = data[tenor_col].map(_tenor_key)
    data = data.dropna(subset=["Date", "Rate", "Tenor_Key"])
    pivot = data.pivot_table(index="Date", columns="Tenor_Key", values="Rate", aggfunc="last")
    if not {"91-Day", "364-Day"}.issubset(pivot.columns):
        return {"status": "unavailable", "reason": "91-Day and 364-Day rates are not both available"}
    matched = pivot.dropna(subset=["91-Day", "364-Day"])
    if matched.empty:
        return {"status": "unavailable", "reason": "No common observation date for both tenors"}
    date = matched.index.max()
    short_rate = float(matched.loc[date, "91-Day"])
    long_rate = float(matched.loc[date, "364-Day"])
    return {
        "status": "ok",
        "date": date,
        "91_day_rate": short_rate,
        "364_day_rate": long_rate,
        "spread_percentage_points": long_rate - short_rate,
    }


def _maturity_years(value: Any) -> float | None:
    text = str(value).strip().lower()
    day_match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:day|days|d)", text)
    year_match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(?:year|years|yr|yrs|y)", text)
    if day_match:
        return float(day_match.group(1)) / 365.0
    if year_match:
        return float(year_match.group(1))
    return None


def calculate_yield_curve_slope(
    curve: pd.DataFrame,
    *,
    maturity_col: str = "Maturity",
    yield_col: str = "Yield (%)",
) -> dict[str, Any]:
    """Calculate long-minus-short slope from valid maturity/yield pairs."""
    if not {maturity_col, yield_col}.issubset(curve.columns):
        return {"status": "unavailable", "reason": "Required maturity/yield fields are missing"}
    data = curve[[maturity_col, yield_col]].copy()
    data["Maturity_Years"] = data[maturity_col].map(_maturity_years)
    data["Yield"] = _finite_numeric(data[yield_col])
    data = data.dropna(subset=["Maturity_Years", "Yield"]).drop_duplicates("Maturity_Years", keep="last")
    if len(data) < 2:
        return {"status": "unavailable", "reason": "At least two distinct valid maturities are required"}
    data = data.sort_values("Maturity_Years")
    short = data.iloc[0]
    long = data.iloc[-1]
    return {
        "status": "ok",
        "short_maturity": str(short[maturity_col]),
        "short_yield": float(short["Yield"]),
        "long_maturity": str(long[maturity_col]),
        "long_yield": float(long["Yield"]),
        "slope_percentage_points": float(long["Yield"] - short["Yield"]),
        "points": int(len(data)),
    }


def validate_model_outputs(frame: pd.DataFrame, *, required_numeric: tuple[str, ...]) -> dict[str, Any]:
    """Generic release gate: fail if required model outputs are absent/non-finite."""
    missing = [column for column in required_numeric if column not in frame.columns]
    if missing:
        return {"status": "failed", "missing_columns": missing, "non_finite": []}
    non_finite = []
    for column in required_numeric:
        values = pd.to_numeric(frame[column], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            non_finite.append(column)
    return {
        "status": "passed" if not non_finite else "failed",
        "missing_columns": [],
        "non_finite": non_finite,
        "rows": int(len(frame)),
    }
