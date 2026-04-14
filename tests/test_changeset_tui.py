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

ENTITY_CHANGES = [
    {
        "id": "ent001",
        "timestamp": "2026-04-08T12:00:00+00:00",
        "method": "POST",
        "path": "/tests/github-code-change-automated-checks-enabled/entities/GithubPullRequest-6977f9e156a2c8fbe5b90efa/deactivate",
        "body": {
            "deactivateReason": "Configuration-only change in a data-only repository."
        },
        "description": "",
    },
    {
        "id": "ent002",
        "timestamp": "2026-04-08T12:01:00+00:00",
        "method": "POST",
        "path": "/tests/github-code-change-automated-checks-enabled/entities/GithubPullRequest-6977f9e156a2c8fbe5b90efd/deactivate",
        "body": {
            "deactivateReason": "Static asset upload to a content-only repository."
        },
        "description": "",
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


def get_detail_text(screen) -> str:
    detail = screen.query_one("#detail-pane", Static)
    return str(detail.render())


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
            return None  # None = success

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
            return None  # None = success

        app = ChangesetApp(cs_file, apply_fn=fake_apply)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("A")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert len(applied) == 3
            table = screen.query_one("#changeset-table", DataTable)
            assert table.row_count == 0

    @pytest.mark.asyncio
    async def test_failed_apply_keeps_change(self, tmp_path):
        cs_file = write_changeset(tmp_path)

        def failing_apply(change):
            return "Unauthorized (401)"  # non-None = error message

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


class TestDetailPane:
    """Detail pane should show body of the highlighted change."""

    @pytest.mark.asyncio
    async def test_detail_shows_on_mount(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            detail = get_detail_text(screen)
            assert "abc123" in detail
            assert "Acme Corp" in detail

    @pytest.mark.asyncio
    async def test_detail_updates_on_cursor_move(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("j")
            await pilot.pause()
            detail = get_detail_text(screen)
            assert "def456" in detail
            assert "Updated" in detail

    @pytest.mark.asyncio
    async def test_detail_empty_when_no_changes(self, tmp_path):
        cs_file = write_changeset(tmp_path, [])
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            detail = get_detail_text(screen)
            assert detail.strip() == ""

    @pytest.mark.asyncio
    async def test_detail_shows_full_path(self, tmp_path):
        cs_file = write_changeset(tmp_path, ENTITY_CHANGES)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            detail = get_detail_text(screen)
            # Full path is shown in the detail pane even though table shows parsed columns
            assert "github-code-change-automated-checks-enabled" in detail


class TestPathParsing:
    """Path should be parsed into name, entity, action columns."""

    @pytest.mark.asyncio
    async def test_entity_path_parsed(self, tmp_path):
        cs_file = write_changeset(tmp_path, ENTITY_CHANGES)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            table = screen.query_one("#changeset-table", DataTable)
            assert table.row_count == 2


class TestAutoSummary:
    """Empty description should be filled from body."""

    @pytest.mark.asyncio
    async def test_summary_from_body(self, tmp_path):
        cs_file = write_changeset(tmp_path, ENTITY_CHANGES)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            table = screen.query_one("#changeset-table", DataTable)
            # The summary column should contain text from deactivateReason
            row_key = table.get_row("ent001")
            # row_key is a tuple of column values - summary is the last column
            summary = row_key[-1]
            assert "Configuration-only" in str(summary)

    @pytest.mark.asyncio
    async def test_description_preferred_over_body(self, tmp_path):
        cs_file = write_changeset(tmp_path)  # SAMPLE_CHANGES have descriptions
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            table = screen.query_one("#changeset-table", DataTable)
            row = table.get_row("abc123")
            summary = row[-1]
            assert "Create vendor" in str(summary)


class TestBatchSelect:
    """Space toggles selection, s selects all, a/d operate on selection."""

    @pytest.mark.asyncio
    async def test_space_toggles_selection(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            assert len(screen._selected) == 0
            await pilot.press("space")
            await pilot.pause()
            assert "abc123" in screen._selected
            # Cursor should advance to next row
            table = screen.query_one("#changeset-table", DataTable)
            assert table.cursor_row == 1
            # Toggle off: move back and press space again
            await pilot.press("k")
            await pilot.pause()
            await pilot.press("space")
            await pilot.pause()
            assert "abc123" not in screen._selected

    @pytest.mark.asyncio
    async def test_s_selects_all(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("s")
            await pilot.pause()
            assert len(screen._selected) == 3
            # Press again to deselect all
            await pilot.press("s")
            await pilot.pause()
            assert len(screen._selected) == 0

    @pytest.mark.asyncio
    async def test_apply_selected_batch(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        applied = []

        def fake_apply(change):
            applied.append(change["id"])
            return None  # None = success

        app = ChangesetApp(cs_file, apply_fn=fake_apply)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            # Select first two
            await pilot.press("space")  # selects abc123, moves to row 1
            await pilot.pause()
            await pilot.press("space")  # selects def456, moves to row 2
            await pilot.pause()
            assert len(screen._selected) == 2
            await pilot.press("a")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert set(applied) == {"abc123", "def456"}
            table = screen.query_one("#changeset-table", DataTable)
            assert table.row_count == 1

    @pytest.mark.asyncio
    async def test_drop_selected_batch(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            # Select first two
            await pilot.press("space")
            await pilot.pause()
            await pilot.press("space")
            await pilot.pause()
            await pilot.press("d")
            await pilot.pause()
            table = screen.query_one("#changeset-table", DataTable)
            assert table.row_count == 1
            remaining = json.loads(cs_file.read_text())
            assert len(remaining) == 1
            assert remaining[0]["id"] == "ghi789"

    @pytest.mark.asyncio
    async def test_status_shows_selected_count(self, tmp_path):
        cs_file = write_changeset(tmp_path)
        app = ChangesetApp(cs_file)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("space")
            await pilot.pause()
            status = get_status_text(screen)
            assert "1 selected" in status
