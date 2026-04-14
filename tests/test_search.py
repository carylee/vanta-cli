"""Tests for client-side text search on ResourceListScreen."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Input, Static

from vanta_cli.tui.screens.resource_list import ResourceListScreen
from vanta_cli.tui.service import AsyncVantaService, Page
from vanta_cli.tui.widgets.sidebar import ResourceGroup

# -- Fixtures / helpers -------------------------------------------------------

TEST_GROUP = ResourceGroup(
    label="Tests",
    key="tests",
    api_path="/tests",
    columns=[("id", "ID"), ("name", "Name"), ("status", "Status")],
)

SAMPLE_ITEMS = [
    {"id": "1", "name": "Alpha Test", "status": "OK"},
    {"id": "2", "name": "Beta Check", "status": "FAIL"},
    {"id": "3", "name": "Gamma Test", "status": "OK"},
    {"id": "4", "name": "Delta Check", "status": "FAIL"},
    {"id": "5", "name": "Alpha Review", "status": "OK"},
]


class FakeService(AsyncVantaService):
    """Service that returns canned data without hitting the network."""

    def __init__(self, items: list[dict] | None = None):
        # Skip parent __init__ to avoid creating a real VantaClient
        self._items = items or SAMPLE_ITEMS

    async def list_page(self, path, params=None, cursor=None, page_size=100):
        return Page(items=self._items, next_cursor=None, has_more=False)

    async def get(self, path):
        return {}

    async def download_url(self, url, dest):
        return dest


async def type_text(pilot, text: str) -> None:
    """Type text character by character since Pilot has no .type() method."""
    for char in text:
        await pilot.press(char)


def get_screen(app: App) -> ResourceListScreen:
    """Get the active ResourceListScreen from the app's screen stack."""
    # The pushed screen is the top of the stack
    screen = app.screen
    if isinstance(screen, ResourceListScreen):
        return screen
    # Walk the stack
    for s in reversed(app.screen_stack):
        if isinstance(s, ResourceListScreen):
            return s
    raise AssertionError(f"No ResourceListScreen found. Screen stack: {app.screen_stack}")


def get_status_text(screen: ResourceListScreen) -> str:
    """Get the text content of the status bar."""
    status = screen.query_one("#status-bar", Static)
    return str(status.render())


class ListApp(App):
    """Minimal app wrapping a ResourceListScreen for testing."""

    def __init__(self, group=None, service=None):
        super().__init__()
        self._group = group or TEST_GROUP
        self._service = service or FakeService()

    def on_mount(self) -> None:
        screen = ResourceListScreen(self._group, self._service)
        self.push_screen(screen)


# -- Phase 1 Tests: Client-side search ----------------------------------------


class TestSearchActivation:
    """Pressing `/` should show a search input."""

    @pytest.mark.asyncio
    async def test_slash_opens_search_input(self):
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            # Press `/` to activate search
            await pilot.press("slash")
            await pilot.pause()
            # There should now be a visible Input widget for searching
            search_input = screen.query("Input.search-input")
            assert len(search_input) == 1, "Expected a search Input to appear"

    @pytest.mark.asyncio
    async def test_escape_closes_search_input(self):
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("slash")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            search_input = screen.query("Input.search-input")
            # Input should be hidden or removed
            assert len(search_input) == 0 or not search_input.first().display, \
                "Search input should be hidden after Escape"


class TestSearchMatching:
    """Search should find and navigate to matching rows."""

    @pytest.mark.asyncio
    async def test_search_computes_matches(self):
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            # Searching for "alpha" should match items at index 0 and 4
            await pilot.press("slash")
            await pilot.pause()
            await type_text(pilot, "alpha")
            await pilot.press("enter")
            await pilot.pause()
            assert hasattr(screen, "_match_indices"), "Screen should track match indices"
            assert screen._match_indices == [0, 4], f"Expected [0, 4], got {screen._match_indices}"

    @pytest.mark.asyncio
    async def test_search_jumps_to_first_match(self):
        """After confirming a search, cursor should be on the first match."""
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            # Move cursor down a couple rows first
            await pilot.press("j")
            await pilot.press("j")
            await pilot.pause()
            # Search for "delta" (index 3)
            await pilot.press("slash")
            await pilot.pause()
            await type_text(pilot, "delta")
            await pilot.press("enter")
            await pilot.pause()
            table = screen.query_one("#resource-table")
            assert table.cursor_row == 3

    @pytest.mark.asyncio
    async def test_search_is_case_insensitive(self):
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("slash")
            await pilot.pause()
            await type_text(pilot, "BETA")
            await pilot.press("enter")
            await pilot.pause()
            assert screen._match_indices == [1]

    @pytest.mark.asyncio
    async def test_search_matches_any_column(self):
        """Search should match across all visible columns, not just name."""
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("slash")
            await pilot.pause()
            await type_text(pilot, "FAIL")
            await pilot.press("enter")
            await pilot.pause()
            assert screen._match_indices == [1, 3], \
                f"Expected [1, 3] for 'FAIL' status matches, got {screen._match_indices}"


class TestSearchNavigation:
    """n/N should cycle through matches."""

    @pytest.mark.asyncio
    async def test_n_goes_to_next_match(self):
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("slash")
            await pilot.pause()
            await type_text(pilot, "alpha")
            await pilot.press("enter")
            await pilot.pause()
            table = screen.query_one("#resource-table")
            # Should be on first match (index 0)
            assert table.cursor_row == 0
            # Press n to go to next match (index 4)
            await pilot.press("n")
            await pilot.pause()
            assert table.cursor_row == 4

    @pytest.mark.asyncio
    async def test_n_wraps_around(self):
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("slash")
            await pilot.pause()
            await type_text(pilot, "alpha")
            await pilot.press("enter")
            await pilot.pause()
            table = screen.query_one("#resource-table")
            # First match at 0, press n to go to 4, press n again to wrap to 0
            await pilot.press("n")
            await pilot.pause()
            assert table.cursor_row == 4
            await pilot.press("n")
            await pilot.pause()
            assert table.cursor_row == 0

    @pytest.mark.asyncio
    async def test_shift_n_goes_to_previous_match(self):
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("slash")
            await pilot.pause()
            await type_text(pilot, "alpha")
            await pilot.press("enter")
            await pilot.pause()
            table = screen.query_one("#resource-table")
            # At first match (0), shift+N should wrap to last match (4)
            await pilot.press("N")
            await pilot.pause()
            assert table.cursor_row == 4


class TestSearchStatusBar:
    """Status bar should reflect search state."""

    @pytest.mark.asyncio
    async def test_status_bar_shows_match_count(self):
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("slash")
            await pilot.pause()
            await type_text(pilot, "alpha")
            await pilot.press("enter")
            await pilot.pause()
            status_text = get_status_text(screen)
            assert "1 of 2" in status_text, f"Expected match count in status bar, got: {status_text}"

    @pytest.mark.asyncio
    async def test_no_matches_shows_message(self):
        app = ListApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("slash")
            await pilot.pause()
            await type_text(pilot, "zzzznotfound")
            await pilot.press("enter")
            await pilot.pause()
            status_text = get_status_text(screen)
            assert "no matches" in status_text.lower(), \
                f"Expected 'no matches' in status, got: {status_text}"
