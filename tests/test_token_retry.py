"""Tests for OAuth token endpoint 429 backoff and client-side fetch serialization."""

import threading
import time

import httpx
import pytest

from vanta_cli import config
from vanta_cli.client import VantaClient
from vanta_cli.config import TOKEN_RETRY_BACKOFF, TOKEN_URL, Settings, get_token

_REQUEST = httpx.Request("POST", TOKEN_URL)


def _resp(status: int, *, headers=None, json=None) -> httpx.Response:
    """Build a Response with a request attached so raise_for_status works."""
    return httpx.Response(status, headers=headers, json=json, request=_REQUEST)


@pytest.fixture
def settings():
    return Settings(client_id="id", client_secret="secret", organization="org")


@pytest.fixture(autouse=True)
def no_token_cache(monkeypatch, tmp_path):
    """Point the token cache at an empty dir so get_token always fetches."""
    monkeypatch.setattr(config, "CACHE_DIR", tmp_path)


@pytest.fixture
def slept(monkeypatch):
    delays: list[float] = []
    monkeypatch.setattr("vanta_cli.config.time.sleep", delays.append)
    return delays


def test_token_retries_on_429_then_succeeds(monkeypatch, settings, slept):
    responses = [
        _resp(429, headers={"Retry-After": "2"}),
        _resp(429),
        _resp(200, json={"access_token": "tok", "expires_in": 3600}),
    ]

    def fake_post(url, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr("vanta_cli.config.httpx.post", fake_post)

    assert get_token(settings) == "tok"
    # First wait honors Retry-After (2s); second falls back to backoff[1].
    assert slept == [2.0, TOKEN_RETRY_BACKOFF[1]]


def test_token_gives_up_after_max_retries(monkeypatch, settings, slept):
    def fake_post(url, **kwargs):
        return _resp(429)

    monkeypatch.setattr("vanta_cli.config.httpx.post", fake_post)

    with pytest.raises(httpx.HTTPStatusError):
        get_token(settings)


def test_concurrent_ensure_token_fetches_once(monkeypatch, settings):
    """A cold-cache stampede must result in exactly one token fetch."""
    client = VantaClient(settings=settings)
    calls = []

    def fake_get_token(_settings):
        calls.append(1)
        time.sleep(0.02)  # widen the race window
        return "tok"

    monkeypatch.setattr("vanta_cli.client.get_token", fake_get_token)

    results = []
    threads = [
        threading.Thread(target=lambda: results.append(client._ensure_token()))
        for _ in range(8)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == ["tok"] * 8
    assert len(calls) == 1  # only one thread actually hit the endpoint
