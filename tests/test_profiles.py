"""Tests for multi-profile auth: profile-aware config and token caching."""

import json
import os
import time

import pytest

from vanta_cli.config import (
    CACHE_DIR,
    Settings,
    get_token,
    PROFILES,
)


class TestProfileConfig:
    """Settings should load the profile from env var and expose scope/cache info."""

    def test_default_profile_when_unset(self, monkeypatch):
        monkeypatch.delenv("VANTA_PROFILE", raising=False)
        monkeypatch.setenv("VANTA_OAUTH_CLIENT_ID", "vci_test")
        monkeypatch.setenv("VANTA_OAUTH_CLIENT_SECRET", "vcs_test")
        settings = Settings.load()
        assert settings.profile == "default"

    def test_agent_profile_from_env(self, monkeypatch):
        monkeypatch.setenv("VANTA_PROFILE", "agent")
        monkeypatch.setenv("VANTA_OAUTH_CLIENT_ID", "vci_test")
        monkeypatch.setenv("VANTA_OAUTH_CLIENT_SECRET", "vcs_test")
        settings = Settings.load()
        assert settings.profile == "agent"

    def test_explicit_profile_overrides_env(self, monkeypatch):
        monkeypatch.setenv("VANTA_PROFILE", "agent")
        monkeypatch.setenv("VANTA_OAUTH_CLIENT_ID", "vci_test")
        monkeypatch.setenv("VANTA_OAUTH_CLIENT_SECRET", "vcs_test")
        settings = Settings.load(profile="default")
        assert settings.profile == "default"

    def test_invalid_profile_raises(self, monkeypatch):
        monkeypatch.setenv("VANTA_PROFILE", "nonexistent")
        monkeypatch.setenv("VANTA_OAUTH_CLIENT_ID", "vci_test")
        monkeypatch.setenv("VANTA_OAUTH_CLIENT_SECRET", "vcs_test")
        with pytest.raises(SystemExit, match="Unknown profile"):
            Settings.load()


class TestProfileScopes:
    """Each profile should map to the correct OAuth scope."""

    def test_default_profile_has_read_write_scope(self):
        assert "read" in PROFILES["default"]["scope"]
        assert "write" in PROFILES["default"]["scope"]

    def test_agent_profile_has_read_only_scope(self):
        assert "read" in PROFILES["agent"]["scope"]
        assert "write" not in PROFILES["agent"]["scope"]


class TestProfileTokenCache:
    """Each profile should use a separate token cache file."""

    def test_default_profile_cache_file(self):
        assert PROFILES["default"]["cache_file"] == "token.json"

    def test_agent_profile_cache_file(self):
        assert PROFILES["agent"]["cache_file"] == "token-agent.json"

    def test_get_token_uses_profile_scope(self, monkeypatch, tmp_path):
        """get_token should request the scope matching the profile."""
        captured = {}

        def fake_post(url, json=None, **kwargs):
            captured.update(json or {})

            class FakeResp:
                status_code = 200
                def raise_for_status(self): pass
                def json(self): return {"access_token": "tok", "expires_in": 3600}

            return FakeResp()

        import httpx
        monkeypatch.setattr(httpx, "post", fake_post)
        # Use a temp cache dir to avoid polluting real cache
        monkeypatch.setattr("vanta_cli.config.CACHE_DIR", tmp_path)

        settings = Settings(
            client_id="vci_test",
            client_secret="vcs_test",
            organization="test-org",
            profile="agent",
        )
        get_token(settings)
        assert captured["scope"] == PROFILES["agent"]["scope"]

    def test_get_token_caches_per_profile(self, monkeypatch, tmp_path):
        """Agent and default profiles should not share a cache file."""
        call_count = 0

        def fake_post(url, json=None, **kwargs):
            nonlocal call_count
            call_count += 1

            class FakeResp:
                status_code = 200
                def raise_for_status(self): pass
                def json(self_inner):
                    return {"access_token": f"tok-{call_count}", "expires_in": 3600}

            return FakeResp()

        import httpx
        monkeypatch.setattr(httpx, "post", fake_post)
        monkeypatch.setattr("vanta_cli.config.CACHE_DIR", tmp_path)

        agent_settings = Settings(
            client_id="vci_test", client_secret="vcs_test",
            organization="test-org", profile="agent",
        )
        default_settings = Settings(
            client_id="vci_test", client_secret="vcs_test",
            organization="test-org", profile="default",
        )

        tok1 = get_token(agent_settings)
        tok2 = get_token(default_settings)

        # Should be different tokens (two separate HTTP calls)
        assert tok1 != tok2
        assert call_count == 2

        # Cache files should exist for each profile
        assert (tmp_path / "token-agent.json").exists()
        assert (tmp_path / "token.json").exists()
