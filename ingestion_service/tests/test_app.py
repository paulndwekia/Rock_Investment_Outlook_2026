from datetime import datetime, timezone
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as api  # noqa: E402
from app import get_observations, verify_read_token  # noqa: E402


def test_read_token_accepts_valid_bearer_credentials(monkeypatch):
    monkeypatch.setenv("API_READ_TOKEN", "test-read-token")

    assert verify_read_token("Bearer test-read-token") is True


def test_read_token_accepts_case_insensitive_bearer_scheme(monkeypatch):
    monkeypatch.setenv("API_READ_TOKEN", "test-read-token")

    assert verify_read_token("bearer test-read-token") is True


@pytest.mark.parametrize(
    "authorization",
    [
        None,
        "",
        "test-read-token",
        "Basic test-read-token",
        "Bearer",
        "Bearer wrong-token",
        "Bearer test-read-token extra",
    ],
)
def test_read_token_rejects_missing_or_malformed_credentials(monkeypatch, authorization):
    monkeypatch.setenv("API_READ_TOKEN", "test-read-token")

    with pytest.raises(HTTPException) as error:
        verify_read_token(authorization)

    assert error.value.status_code == 401


def test_read_token_fails_closed_when_server_secret_is_missing(monkeypatch):
    monkeypatch.delenv("API_READ_TOKEN", raising=False)

    with pytest.raises(HTTPException) as error:
        verify_read_token("Bearer test-read-token")

    assert error.value.status_code == 503


def test_observation_query_is_scoped_and_returns_chronological_rows(monkeypatch):
    later = datetime(2026, 11, 18, tzinfo=timezone.utc)
    earlier = datetime(2026, 11, 17, tzinfo=timezone.utc)

    class FakeCursor:
        def fetchall(self):
            return [
                {
                    "observed_at": later,
                    "dataset": "NSE equities",
                    "series": "SCOM close",
                    "value": 21.5,
                    "unit": "KES",
                    "source_name": "Approved training feed",
                },
                {
                    "observed_at": earlier,
                    "dataset": "NSE equities",
                    "series": "SCOM close",
                    "value": 21.0,
                    "unit": "KES",
                    "source_name": "Approved training feed",
                },
            ]

    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def execute(self, query, params):
            assert "WHERE dataset = %s AND series = %s" in query
            assert params == ("NSE equities", "SCOM close", 50)
            return FakeCursor()

    monkeypatch.setattr(api, "connection", lambda: FakeConnection())

    result = get_observations(
        dataset="NSE equities",
        series_name="SCOM close",
        limit=50,
        _=True,
    )

    assert [row["observed_at"] for row in result] == [
        earlier.isoformat(),
        later.isoformat(),
    ]
    assert [row["value"] for row in result] == [21.0, 21.5]
