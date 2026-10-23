"""Shared fixtures. The socket guard blocks every connection that isn't to loopback.

Tests that need the real network must be marked `@pytest.mark.live` and run with `-m live`.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Iterator
from typing import Any

import pytest

_real_connect = socket.socket.connect
_real_connect_ex = socket.socket.connect_ex
_real_getaddrinfo = socket.getaddrinfo

LOCAL_NAMES = {"localhost", "testserver"}


class BlockedNetworkError(RuntimeError):
    pass


def _is_local_host(host: object) -> bool:
    if isinstance(host, bytes):
        host = host.decode()
    if not isinstance(host, str):
        return False
    if host in LOCAL_NAMES:
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False


def _check_address(sock: socket.socket, address: Any) -> None:
    if sock.family == getattr(socket, "AF_UNIX", None):
        return
    host = address[0] if isinstance(address, tuple) else address
    if not _is_local_host(host):
        raise BlockedNetworkError(f"Test tried to connect to {host!r}; only loopback is allowed")


def _guarded_connect(self: socket.socket, address: Any) -> None:
    _check_address(self, address)
    _real_connect(self, address)


def _guarded_connect_ex(self: socket.socket, address: Any) -> int:
    _check_address(self, address)
    return _real_connect_ex(self, address)


def _guarded_getaddrinfo(host: Any, *args: Any, **kwargs: Any) -> Any:
    if host is not None and not _is_local_host(host):
        raise BlockedNetworkError(f"Test tried to resolve {host!r}; only loopback is allowed")
    return _real_getaddrinfo(host, *args, **kwargs)


@pytest.fixture(autouse=True)
def socket_guard(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    if request.node.get_closest_marker("live") is None:
        monkeypatch.setattr(socket.socket, "connect", _guarded_connect)
        monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect_ex)
        monkeypatch.setattr(socket, "getaddrinfo", _guarded_getaddrinfo)
    yield


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Keep the developer's .env and shell variables out of tests."""
    from seculayer_demo.config import get_settings

    monkeypatch.setenv("OPENAI_API_KEY", "")
    for name in (
        "SECULAYER_MODE",
        "SECULAYER_HOST",
        "SECULAYER_PORT",
        "SECULAYER_TOKEN_BUDGET",
        "SECULAYER_CLASSIFIER_DIR",
    ):
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
