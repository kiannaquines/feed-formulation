import pytest

from core.config import _get_secret


@pytest.mark.parametrize("value", ["", "short", "replace-with-a-long-random-secret"])
def test_secret_rejects_missing_placeholder_and_short_values(monkeypatch, value):
    monkeypatch.setenv("TEST_SECRET", value)

    with pytest.raises(ValueError, match="openssl rand -hex 32"):
        _get_secret("TEST_SECRET")


def test_secret_accepts_openssl_length_value(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "a" * 64)

    assert _get_secret("TEST_SECRET") == "a" * 64
