from datetime import date, datetime, timezone
from pathlib import Path
import sys

import pytest
from openpyxl import Workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from import_csv import (  # noqa: E402
    open_source_rows,
    parse_numeric_value,
    parse_observed_at,
    resolve_column,
    sha256_file,
)


def test_parse_observed_at_adds_utc_to_naive_timestamp():
    result = parse_observed_at("2026-11-17T09:30:00")
    assert result.tzinfo == timezone.utc
    assert result.isoformat() == "2026-11-17T09:30:00+00:00"


def test_parse_observed_at_preserves_explicit_timezone():
    result = parse_observed_at("2026-11-17T09:30:00+03:00")
    assert result.utcoffset().total_seconds() == 3 * 60 * 60


def test_parse_observed_at_accepts_excel_date_values():
    result = parse_observed_at(date(2026, 11, 17))
    assert result == datetime(2026, 11, 17, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,234.56", 1234.56),
        (100, 100.0),
        (DecimalLike("0.075"), 0.075),
    ],
)
def test_parse_numeric_value_accepts_finite_values(raw, expected):
    assert parse_numeric_value(raw) == pytest.approx(expected)


class DecimalLike(str):
    """String stand-in for a decimal-formatted spreadsheet cell."""


@pytest.mark.parametrize("raw", [None, True, "NaN", "Infinity", "-Infinity", "not-a-number"])
def test_parse_numeric_value_rejects_invalid_or_non_finite_values(raw):
    with pytest.raises((ValueError, Exception)):
        parse_numeric_value(raw)


def test_resolve_column_uses_trimmed_case_insensitive_names():
    assert resolve_column([" Date ", "Security", "Close"], "date") == " Date "


def test_resolve_column_rejects_ambiguous_names():
    with pytest.raises(ValueError, match="ambiguous"):
        resolve_column(["Date", " date "], "date")


def test_resolve_optional_column_can_be_absent():
    assert resolve_column(["Date", "Security"], "unit", required=False) is None


def test_open_source_rows_reads_csv_and_streams_records(tmp_path):
    source = tmp_path / "market.csv"
    source.write_text(
        "Date,Security,Close\n2026-11-17,SCOM,21.50\n",
        encoding="utf-8",
    )

    headers, rows = open_source_rows(source, None)
    records = list(rows)

    assert headers == ["Date", "Security", "Close"]
    assert records == [(2, {"Date": "2026-11-17", "Security": "SCOM", "Close": "21.50"})]
    assert parse_numeric_value(records[0][1]["Close"]) == pytest.approx(21.5)


def test_open_source_rows_reads_selected_xlsx_worksheet(tmp_path):
    source = tmp_path / "market.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Daily"
    sheet.append(["Date", "Security", "Close"])
    sheet.append([date(2026, 11, 17), "SCOM", 21.5])
    workbook.save(source)

    headers, rows = open_source_rows(source, "Daily")
    records = list(rows)

    assert headers == ["Date", "Security", "Close"]
    assert len(records) == 1
    assert records[0][0] == 2
    assert records[0][1]["Security"] == "SCOM"
    assert parse_observed_at(records[0][1]["Date"]).date() == date(2026, 11, 17)
    assert parse_numeric_value(records[0][1]["Close"]) == pytest.approx(21.5)


def test_open_source_rows_rejects_missing_worksheet(tmp_path):
    source = tmp_path / "market.xlsx"
    workbook = Workbook()
    workbook.save(source)

    with pytest.raises(ValueError, match="Worksheet not found"):
        open_source_rows(source, "Missing")


def test_sha256_file_reads_complete_file(tmp_path):
    source = tmp_path / "source.csv"
    source.write_bytes(b"one,two\n1,2\n")
    assert sha256_file(source) == "c1ab2d5c4f1d2c2f9e1239a6d341b88c1720e3b62ab3e18b843e980fdfd3e5a0"
