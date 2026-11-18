from pathlib import Path
import sys

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import verify_read_token  # noqa: E402


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
