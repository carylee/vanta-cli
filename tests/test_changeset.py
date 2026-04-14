"""Tests for write interception in agent profile and changeset staging."""

import json

import pytest

from vanta_cli.changeset import (
    CHANGESET_FILE,
    load_changeset,
    save_changeset,
    stage_change,
    drop_change,
    clear_changeset,
)
from vanta_cli.client import VantaClient, WriteIntercepted
from vanta_cli.config import Settings


# -- Changeset file operations ------------------------------------------------


class TestChangesetFileOps:
    """Low-level changeset file read/write/modify."""

    def test_load_empty_changeset(self, monkeypatch, tmp_path):
        monkeypatch.setattr("vanta_cli.changeset.CHANGESET_FILE", tmp_path / "changeset.json")
        assert load_changeset() == []

    def test_stage_and_load(self, monkeypatch, tmp_path):
        cs_file = tmp_path / "changeset.json"
        monkeypatch.setattr("vanta_cli.changeset.CHANGESET_FILE", cs_file)

        entry = stage_change(
            method="POST",
            path="/vendors",
            body={"name": "Acme"},
            description="Create vendor: Acme",
        )
        assert entry["method"] == "POST"
        assert entry["path"] == "/vendors"
        assert entry["body"] == {"name": "Acme"}
        assert "id" in entry
        assert "timestamp" in entry

        changes = load_changeset()
        assert len(changes) == 1
        assert changes[0]["id"] == entry["id"]

    def test_stage_appends(self, monkeypatch, tmp_path):
        cs_file = tmp_path / "changeset.json"
        monkeypatch.setattr("vanta_cli.changeset.CHANGESET_FILE", cs_file)

        stage_change(method="POST", path="/vendors", body={"name": "A"})
        stage_change(method="DELETE", path="/vendors/123", body=None)

        changes = load_changeset()
        assert len(changes) == 2

    def test_drop_change(self, monkeypatch, tmp_path):
        cs_file = tmp_path / "changeset.json"
        monkeypatch.setattr("vanta_cli.changeset.CHANGESET_FILE", cs_file)

        e1 = stage_change(method="POST", path="/a", body={})
        e2 = stage_change(method="POST", path="/b", body={})

        dropped = drop_change(e1["id"])
        assert dropped is True
        changes = load_changeset()
        assert len(changes) == 1
        assert changes[0]["id"] == e2["id"]

    def test_drop_nonexistent_returns_false(self, monkeypatch, tmp_path):
        cs_file = tmp_path / "changeset.json"
        monkeypatch.setattr("vanta_cli.changeset.CHANGESET_FILE", cs_file)
        assert drop_change("nonexistent") is False

    def test_clear_changeset(self, monkeypatch, tmp_path):
        cs_file = tmp_path / "changeset.json"
        monkeypatch.setattr("vanta_cli.changeset.CHANGESET_FILE", cs_file)

        stage_change(method="POST", path="/a", body={})
        stage_change(method="POST", path="/b", body={})
        clear_changeset()

        assert load_changeset() == []


# -- Client write interception ------------------------------------------------


class TestWriteInterception:
    """In agent profile, write methods should stage instead of calling the API."""

    def _agent_client(self, monkeypatch, tmp_path):
        """Create a VantaClient in agent profile with fake token and temp changeset."""
        monkeypatch.setattr("vanta_cli.changeset.CHANGESET_FILE", tmp_path / "changeset.json")
        settings = Settings(
            client_id="vci_test",
            client_secret="vcs_test",
            organization="test-org",
            profile="agent",
        )
        client = VantaClient(settings=settings)
        client._token = "fake-token"  # Skip real auth
        return client

    def _default_client(self, monkeypatch, tmp_path):
        """Create a VantaClient in default profile."""
        settings = Settings(
            client_id="vci_test",
            client_secret="vcs_test",
            organization="test-org",
            profile="default",
        )
        client = VantaClient(settings=settings)
        client._token = "fake-token"
        return client

    def test_post_stages_in_agent_profile(self, monkeypatch, tmp_path):
        client = self._agent_client(monkeypatch, tmp_path)
        with pytest.raises(WriteIntercepted) as exc_info:
            client.post("/vendors", json={"name": "Acme"})

        assert exc_info.value.entry["method"] == "POST"
        assert exc_info.value.entry["path"] == "/vendors"

        changes = load_changeset()
        assert len(changes) == 1

    def test_patch_stages_in_agent_profile(self, monkeypatch, tmp_path):
        client = self._agent_client(monkeypatch, tmp_path)
        with pytest.raises(WriteIntercepted):
            client.patch("/vendors/123", json={"name": "New"})

        changes = load_changeset()
        assert len(changes) == 1
        assert changes[0]["method"] == "PATCH"

    def test_delete_stages_in_agent_profile(self, monkeypatch, tmp_path):
        client = self._agent_client(monkeypatch, tmp_path)
        with pytest.raises(WriteIntercepted):
            client.delete("/vendors/123")

        changes = load_changeset()
        assert len(changes) == 1
        assert changes[0]["method"] == "DELETE"

    def test_put_stages_in_agent_profile(self, monkeypatch, tmp_path):
        client = self._agent_client(monkeypatch, tmp_path)
        with pytest.raises(WriteIntercepted):
            client.put("/vendors/123", json={"name": "Acme"})

        changes = load_changeset()
        assert len(changes) == 1
        assert changes[0]["method"] == "PUT"

    def test_agent_profile_is_intercepted(self, monkeypatch, tmp_path):
        """Agent profile should flag writes as intercepted."""
        client = self._agent_client(monkeypatch, tmp_path)
        assert client._is_write_intercepted()

    def test_default_profile_not_intercepted(self, monkeypatch, tmp_path):
        """Default profile should NOT intercept writes."""
        client = self._default_client(monkeypatch, tmp_path)
        assert not client._is_write_intercepted()
