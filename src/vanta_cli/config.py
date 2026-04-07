from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv

TOKEN_CACHE_DIR = Path.home() / ".cache" / "vanta-cli"
TOKEN_CACHE_FILE = TOKEN_CACHE_DIR / "token.json"
TOKEN_URL = "https://api.vanta.com/oauth/token"
# Refresh token 60s before actual expiry
TOKEN_EXPIRY_BUFFER = 60


@dataclass
class Settings:
    client_id: str
    client_secret: str
    organization: str

    @classmethod
    def load(cls) -> Settings:
        load_dotenv()
        client_id = os.environ.get("VANTA_OAUTH_CLIENT_ID", "")
        client_secret = os.environ.get("VANTA_OAUTH_CLIENT_SECRET", "")
        organization = os.environ.get("VANTA_ORGANIZATION", "")
        if not client_id or not client_secret:
            raise SystemExit(
                "Missing VANTA_OAUTH_CLIENT_ID or VANTA_OAUTH_CLIENT_SECRET. "
                "Set them in .env or as environment variables."
            )
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            organization=organization,
        )


def get_token(settings: Settings, scope: str = "vanta-api.all:read vanta-api.all:write") -> str:
    """Get a valid OAuth token, using cache if available."""
    cached = _load_cached_token()
    if cached:
        return cached

    resp = httpx.post(
        TOKEN_URL,
        json={
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "scope": scope,
            "grant_type": "client_credentials",
        },
    )
    resp.raise_for_status()
    data = resp.json()

    token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    _save_cached_token(token, expires_in)
    return token


def _load_cached_token() -> str | None:
    if not TOKEN_CACHE_FILE.exists():
        return None
    try:
        data = json.loads(TOKEN_CACHE_FILE.read_text())
        if data.get("expires_at", 0) > time.time() + TOKEN_EXPIRY_BUFFER:
            return data["access_token"]
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _save_cached_token(token: str, expires_in: int) -> None:
    TOKEN_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE_FILE.write_text(
        json.dumps(
            {
                "access_token": token,
                "expires_at": time.time() + expires_in,
            }
        )
    )
