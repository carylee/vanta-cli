"""Tests for the TUI changeset review screen."""

import json

import pytest
from textual.app import App
from textual.widgets import DataTable, Static

from vanta_cli.tui.screens.changeset import ChangesetScreen


# -- Helpers ------------------------------------------------------------------

SAMPLE_CHANGES = [
    {
        "id": "abc123",
        "timestamp": "2026-04-08T12:00:00+00:00",
        "method": "POST",
        "path": "/vendors",
        "body": {"name": "Acme Corp", "websiteUrl": "acme.com"},
        "description": "Create vendor",
    },
    {
        "id": "def456",
        "timestamp": "2026-04-08T12:01:00+00:00",
        "method": "PATCH",
        "path": "/vendors/123",
        "body": {"name": "Updated"},
        "description": "Update vendor",
    },
    {
        "id": "ghi789",
        "timestamp": "2026-04-08T12:02:00+00:00",
        "method": "DELETE",
        "path": "/vendors/456",
        "body": None,
        "description": "Delete vendor",
    },
]


def write_changeset(tmp_path, changes=None):
    cs_file = tmp_path / "changeset.json"
    cs_file.write_text(json.dumps(SAMPLE_CHANGES if changes is None else changes))
    return cs_file


class ChangesetApp(App):
    def __init__(self, changeset_file, apply_fn=None):
        super().__init__()
        self._changeset_file = changeset_file
        self._apply_fn = apply_fn

    def on_mount(self) -> None:
        screen = ChangesetScreen(
            changeset_file=self._changeset_file,
            apply_fn=self._apply_fn,
        )
        self.push_screen(screen)


def get_screen(app: App) -> ChangesetScreen:
    screen = app.screen
    if isinstance(screen, ChangesetScreen):
        return screen
    for s in reversed(app.screen_stack):
        if isinstance(s, ChangesetScreen):
            return s
    raise AssertionError("No ChangesetScreen found")


def get_status_text(screen) -> str:
    status = screen.query_one("#status-bar", Static)
    return str(status.render())


# -- Tests --------------------------------------------------------------------


class TestChangesetScreenLoads:
    """Screen should display changeset entries in a table."""

    @pytest.mark.asyncio
    async def test_shows_all_entries(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            table = screen.query_one("#changeset-table", DataTable)
            assert table.row_count == 3

    @pytest.mark.asyncio
    async def test_empty_changeset_has_no_data(self, tmp_path):
        cs_file = write_changeset(tmp_path, [])
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            # The screen loads from its own file, verify the data list is empty
            assert screen._read_file() == []


class TestChangesetDrop:
    """d drops the selected change, D clears all."""

    @pytest.mark.asyncio
    async def test_d_drops_selected(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            # Cursor is on first row (abc123)
            await pilot.press("d")
            await pilot.pause()
            table = screen.query_one("#changeset-table", DataTable)
            assert table.row_count == 2
            # Verify it was removed from the file too
            remaining = json.loads(cs_file.read_text())
            assert len(remaining) == 2
            assert all(c["id"] != "abc123" for c in remaining)

    @pytest.mark.asyncio
    async def test_shift_d_clears_all(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("D")
            await pilot.pause()
            table = screen.query_one("#changeset-table", DataTable)
            assert table.row_count == 0
            remaining = json.loads(cs_file.read_text())
            assert remaining == []


class TestChangesetApply:
    """a applies the selected change, A applies all."""

    @pytest.mark.asyncio
    async def test_a_applies_selected(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        applied = []

        def fake_apply(change):
            applied.append(change)
            return True

        app = ChangesetApp(cs_file, apply_fn=fake_apply)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("a")
            await pilot.pause()
            # First change should have been applied
            assert len(applied) == 1
            assert applied[0]["id"] == "abc123"
            # Should be removed from table and file
            table = screen.query_one("#changeset-table", DataTable)
            assert table.row_count == 2

    @pytest.mark.asyncio
    async def test_shift_a_applies_all(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        applied = []

        def fake_apply(change):
            applied.append(change)
            return True

        app = ChangesetApp(cs_file, apply_fn=fake_apply)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("A")
            await pilot.pause()
            assert len(applied) == 3
            table = screen.query_one("#changeset-table", DataTable)
            assert table.row_count == 0

    @pytest.mark.asyncio
    async def test_failed_apply_keeps_change(self, tmp_path):
        cs_file = write_changeset(tmp_path)

        def failing_apply(change):
            return False

        app = ChangesetApp(cs_file, apply_fn=failing_apply)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("a")
            await pilot.pause()
            # Change should NOT be removed
            table = screen.query_one("#changeset-table", DataTable)
            assert table.row_count == 3


class TestChangesetNavigation:
    """Vim-style navigation should work."""

    @pytest.mark.asyncio
    async def test_j_k_navigation(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            table = screen.query_one("#changeset-table", DataTable)
            assert table.cursor_row == 0
            await pilot.press("j")
            await pilot.pause()
            assert table.cursor_row == 1
            await pilot.press("k")
            await pilot.pause()
            assert table.cursor_row == 0
