"""Settings: defaults, the loopback-only host rule, and the key kept secret."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from seculayer_demo.config import Settings, is_loopback


def test_defaults() -> None:
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.mode == "replay"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8765
    assert settings.token_budget == 1_500_000
    assert settings.has_api_key is False


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost", "127.0.0.2"])
def test_loopback_hosts_allowed(host: str) -> None:
    assert is_loopback(host)
    assert Settings(_env_file=None, SECULAYER_HOST=host).host == host  # type: ignore[call-arg]


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.20", "example.com", ""])
def test_non_loopback_hosts_rejected(host: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, SECULAYER_HOST=host)  # type: ignore[call-arg]


def test_key_is_not_in_repr() -> None:
    key = "sk-test-not-a-real-key-0123456789"
    settings = Settings(_env_file=None, OPENAI_API_KEY=key)  # type: ignore[call-arg]
    assert settings.has_api_key
    assert key not in repr(settings)
    assert key not in str(settings.model_dump())


def test_blank_key_means_no_key() -> None:
    assert not Settings(_env_file=None, OPENAI_API_KEY="   ").has_api_key  # type: ignore[call-arg]
