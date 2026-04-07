"""Async wrapper around VantaClient for use in the Textual TUI."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import partial
from typing import Any

from vanta_cli.client import VantaClient


@dataclass
class Page:
    """A single page of results from the API."""

    items: list[dict[str, Any]]
    next_cursor: str | None
    has_more: bool


class AsyncVantaService:
    """Wraps the synchronous VantaClient for async/threaded use in Textual."""

    def __init__(self) -> None:
        self._client = VantaClient()

    async def _run_sync(self, fn, *args, **kwargs):
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, partial(fn, *args, **kwargs))

    async def list_page(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        cursor: str | None = None,
        page_size: int = 100,
    ) -> Page:
        """Fetch a single page of results."""
        p = dict(params or {})
        p["pageSize"] = page_size
        if cursor:
            p["pageCursor"] = cursor

        data = await self._run_sync(self._client.get, path, params=p)
        results = data.get("results", {})

        if isinstance(results, dict):
            items = results.get("data", [])
            page_info = results.get("pageInfo", {})
        else:
            items = results
            page_info = data.get("pageInfo", {})

        has_more = page_info.get("hasNextPage", False)
        next_cursor = page_info.get("endCursor") if has_more else None
        return Page(items=items, next_cursor=next_cursor, has_more=has_more)

    async def get(self, path: str) -> dict[str, Any]:
        """Fetch a single resource."""
        data = await self._run_sync(self._client.get, path)
        return data.get("results", data)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        """POST to an endpoint."""
        data = await self._run_sync(self._client.post, path, json=json)
        return data if data else {}
