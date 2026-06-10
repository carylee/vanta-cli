"""Tests for VantaClient 401 token refresh and 429 rate-limit backoff."""

import httpx
import pytest

from vanta_cli.client import RATE_LIMIT_BACKOFF, VantaClient
from vanta_cli.config import Settings


@pytest.fixture
def slept(monkeypatch):
    """Records (and skips) every retry sleep so tests can assert on the delays."""
    delays: list[float] = []
    monkeypatch.setattr("vanta_cli.client.time.sleep", delays.append)
    return delays


@pytest.fixture
def client(monkeypatch, slept):
    """A VantaClient with a stubbed token and instant sleeps."""
    settings = Settings(client_id="id", client_secret="secret", organization="org")
    c = VantaClient(settings=settings)
    monkeypatch.setattr(c, "_ensure_token", lambda: "test-token")
    return c


def _install(client: VantaClient, handler) -> None:
    client._http = httpx.Client(
        base_url="https://api.vanta.com/v1",
        transport=httpx.MockTransport(handler),
    )


def test_retries_on_429_then_succeeds(client):
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if len(calls) < 3:
            return httpx.Response(429, headers={"Retry-After": "1"})
        return httpx.Response(200, json={"ok": True})

    _install(client, handler)
    assert client.get("/tests") == {"ok": True}
    assert len(calls) == 3  # two 429s, then success


def test_gives_up_after_max_retries(client):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    _install(client, handler)
    with pytest.raises(httpx.HTTPStatusError):
        client.get("/tests")


def test_respects_retry_after_header(client, slept):
    responses = [
        httpx.Response(429, headers={"Retry-After": "5"}),
        httpx.Response(200, json={}),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    _install(client, handler)
    client.get("/tests")
    assert slept == [5.0]


def test_falls_back_to_backoff_without_header(client, slept):
    responses = [httpx.Response(429), httpx.Response(429), httpx.Response(200, json={})]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    _install(client, handler)
    client.get("/tests")
    assert slept == [RATE_LIMIT_BACKOFF[0], RATE_LIMIT_BACKOFF[1]]
