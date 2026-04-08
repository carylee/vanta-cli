from __future__ import annotations

import json
import os
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

import httpx
import platformdirs
import tomli_w
from dotenv import load_dotenv

APP_NAME = "vanta-cli"
CACHE_DIR = Path(platformdirs.user_cache_dir(APP_NAME))
CONFIG_DIR = Path(platformdirs.user_config_dir(APP_NAME))
CONFIG_FILE = CONFIG_DIR / "config.toml"
TOKEN_CACHE_FILE = CACHE_DIR / "token.json"
TOKEN_URL = "https://api.vanta.com/oauth/token"
TOKEN_EXPIRY_BUFFER = 60

PROFILES: dict[str, dict[str, str]] = {
    "default": {
        "scope": "vanta-api.all:read vanta-api.all:write",
        "cache_file": "token.json",
    },
    "agent": {
        "scope": "vanta-api.all:read",
        "cache_file": "token-agent.json",
    },
}


@dataclass
class UserConfig:
    """User identity stored in config.toml."""

    user_id: str | None = None
    email: str | None = None
    display_name: str | None = None


def load_user_config() -> UserConfig:
    """Load user config from config.toml, returning defaults if missing."""
    if not CONFIG_FILE.exists():
        return UserConfig()
    try:
        with CONFIG_FILE.open("rb") as f:
            data = tomllib.load(f)
        user = data.get("user", {})
        return UserConfig(
            user_id=user.get("id"),
            email=user.get("email"),
            display_name=user.get("display_name"),
        )
    except (tomllib.TOMLDecodeError, KeyError):
        return UserConfig()


def save_user_config(config: UserConfig) -> Path:
    """Save user config to config.toml. Returns the config file path."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if CONFIG_FILE.exists():
        try:
            with CONFIG_FILE.open("rb") as f:
                data = tomllib.load(f)
        except tomllib.TOMLDecodeError:
            data = {}
    user: dict = {}
    if config.user_id:
        user["id"] = config.user_id
    if config.email:
        user["email"] = config.email
    if config.display_name:
        user["display_name"] = config.display_name
    data["user"] = user
    with CONFIG_FILE.open("wb") as f:
        tomli_w.dump(data, f)
    return CONFIG_FILE


@dataclass
class Settings:
    client_id: str
    client_secret: str
    organization: str
    user_id: str | None = None
    profile: str = "default"

    @classmethod
    def load(cls, profile: str | None = None) -> Settings:
        load_dotenv()
        client_id = os.environ.get("VANTA_OAUTH_CLIENT_ID", "")
        client_secret = os.environ.get("VANTA_OAUTH_CLIENT_SECRET", "")
        organization = os.environ.get("VANTA_ORGANIZATION", "")
        if not client_id or not client_secret:
            raise SystemExit(
                "Missing VANTA_OAUTH_CLIENT_ID or VANTA_OAUTH_CLIENT_SECRET. "
                "Set them in .env or as environment variables."
            )
        resolved_profile = profile or os.environ.get("VANTA_PROFILE", "default")
        if resolved_profile not in PROFILES:
            raise SystemExit(
                f"Unknown profile '{resolved_profile}'. "
                f"Valid profiles: {', '.join(PROFILES)}"
            )
        user_config = load_user_config()
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            organization=organization,
            user_id=user_config.user_id,
            profile=resolved_profile,
        )


def get_token(settings: Settings) -> str:
    """Get a valid OAuth token, using cache if available. Scope and cache file are determined by profile."""
    profile_info = PROFILES[settings.profile]
    cache_file = CACHE_DIR / profile_info["cache_file"]

    cached = _load_cached_token(cache_file)
    if cached:
        return cached

    resp = httpx.post(
        TOKEN_URL,
        json={
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "scope": profile_info["scope"],
            "grant_type": "client_credentials",
        },
    )
    resp.raise_for_status()
    data = resp.json()

    token = data["access_token"]
    expires_in = data.get("expires_in", 3600)
    _save_cached_token(token, expires_in, cache_file)
    return token


def _load_cached_token(cache_file: Path) -> str | None:
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text())
        if data.get("expires_at", 0) > time.time() + TOKEN_EXPIRY_BUFFER:
            return data["access_token"]
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _save_cached_token(token: str, expires_in: int, cache_file: Path) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(
        json.dumps(
            {
                "access_token": token,
                "expires_at": time.time() + expires_in,
            }
        )
    )
