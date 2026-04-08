from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx

from vanta_cli.changeset import stage_change
from vanta_cli.config import Settings, get_token

BASE_URL = "https://api.vanta.com/v1"


class WriteIntercepted(Exception):
    """Raised when a write is staged instead of executed (agent profile)."""

    def __init__(self, entry: dict) -> None:
        self.entry = entry
        super().__init__(
            f"Change staged ({entry['id']}): {entry['method']} {entry['path']}"
        )


class VantaClient:
    def __init__(self, settings: Settings | None = None) -> None:
        if settings is None:
            # Use the global settings from the CLI if available, else load fresh
            from vanta_cli.main import _settings
            settings = _settings if _settings is not None else Settings.load()
        self._settings = settings
        self._token: str | None = None
        self._http = httpx.Client(base_url=BASE_URL, timeout=30.0)

    def _ensure_token(self) -> str:
        if self._token is None:
            self._token = get_token(self._settings)
        return self._token

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._ensure_token()}"}

    def _is_write_intercepted(self) -> bool:
        """Check if writes should be staged instead of executed."""
        return self._settings.profile == "agent"

    def _intercept_write(self, method: str, path: str, body: dict | None = None) -> None:
        """Stage a write operation and raise WriteIntercepted."""
        entry = stage_change(method=method, path=path, body=body)
        raise WriteIntercepted(entry)

    def _handle_response(self, resp: httpx.Response) -> Any:
        if resp.status_code == 401:
            raise SystemExit(
                "Authentication failed (401). Check your VANTA_OAUTH_CLIENT_ID "
                "and VANTA_OAUTH_CLIENT_SECRET in .env"
            )
        if resp.status_code == 403:
            raise SystemExit(
                "Forbidden (403). Your API credentials may not have the required scope."
            )
        resp.raise_for_status()
        if resp.status_code == 204:
            return {}
        return resp.json()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        resp = self._http.get(path, headers=self._headers(), params=params)
        return self._handle_response(resp)

    def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        if self._is_write_intercepted():
            self._intercept_write("POST", path, json)
        resp = self._http.post(path, headers=self._headers(), json=json)
        return self._handle_response(resp)

    def patch(self, path: str, json: dict[str, Any] | None = None) -> Any:
        if self._is_write_intercepted():
            self._intercept_write("PATCH", path, json)
        resp = self._http.patch(path, headers=self._headers(), json=json)
        return self._handle_response(resp)

    def delete(self, path: str) -> Any:
        if self._is_write_intercepted():
            self._intercept_write("DELETE", path, None)
        resp = self._http.delete(path, headers=self._headers())
        return self._handle_response(resp)

    def put(self, path: str, json: dict[str, Any] | None = None) -> Any:
        if self._is_write_intercepted():
            self._intercept_write("PUT", path, json)
        resp = self._http.put(path, headers=self._headers(), json=json)
        return self._handle_response(resp)

    def upload(
        self,
        path: str,
        file_path: Path,
        fields: dict[str, str] | None = None,
    ) -> Any:
        """POST multipart/form-data with a file upload."""
        files = {"file": (file_path.name, file_path.open("rb"))}
        data = fields or {}
        resp = self._http.post(path, headers=self._headers(), files=files, data=data)
        return self._handle_response(resp)

    def download(self, path: str, dest: Path) -> Path:
        """GET binary content and save to a file."""
        with self._http.stream("GET", path, headers=self._headers()) as resp:
            resp.raise_for_status()
            with dest.open("wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
        return dest

    def download_url(self, url: str, dest: Path) -> Path:
        """Download from an arbitrary URL (e.g. pre-signed S3) and save to a file."""
        with httpx.stream("GET", url, timeout=60.0) as resp:
            resp.raise_for_status()
            with dest.open("wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
        return dest

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Iterate over all items from a paginated endpoint."""
        params = dict(params or {})
        params.setdefault("pageSize", 100)
        count = 0
        while True:
            data = self.get(path, params=params)
            results = data.get("results", {})
            # Handle both {"results": {"data": [...]}} and {"results": [...]}
            if isinstance(results, dict):
                items = results.get("data", [])
                page_info = results.get("pageInfo", {})
            else:
                items = results
                page_info = data.get("pageInfo", {})

            for item in items:
                yield item
                count += 1
                if limit and count >= limit:
                    return

            if not page_info.get("hasNextPage", False):
                break
            params["pageCursor"] = page_info["endCursor"]
