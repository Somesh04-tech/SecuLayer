"""The socket guard in conftest.py blocks non-loopback connections in every test."""

from __future__ import annotations

import socket

import pytest

from tests.conftest import BlockedNetworkError


def test_outbound_connection_is_blocked() -> None:
    with (
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock,
        pytest.raises(BlockedNetworkError),
    ):
        sock.connect(("93.184.216.34", 443))


def test_outbound_dns_is_blocked() -> None:
    with pytest.raises(BlockedNetworkError):
        socket.getaddrinfo("api.openai.com", 443)


def test_loopback_is_allowed() -> None:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
            client.connect(server.getsockname())
