"""Tests that AsyncVantaService caps concurrent in-flight requests."""

import asyncio
import threading
import time

import pytest

from vanta_cli.tui.service import MAX_CONCURRENT_REQUESTS, AsyncVantaService


@pytest.mark.asyncio
async def test_run_sync_caps_concurrency(monkeypatch):
    service = AsyncVantaService()

    lock = threading.Lock()
    active = 0
    peak = 0

    def slow_call():
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        with lock:
            active -= 1

    # Fire far more calls than the gate allows; the peak observed inside the
    # worker threads must never exceed the cap.
    await asyncio.gather(*(service._run_sync(slow_call) for _ in range(20)))

    assert peak <= MAX_CONCURRENT_REQUESTS
    assert peak > 1  # sanity: calls really did overlap
