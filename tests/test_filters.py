"""Tests for server-side structured filters on ResourceListScreen."""

from __future__ import annotations

import pytest
from textual.app import App
from textual.widgets import RadioSet, Static

from vanta_cli.tui.screens.resource_list import ResourceListScreen
from vanta_cli.tui.service import AsyncVantaService, Page
from vanta_cli.tui.widgets.sidebar import FilterDef, ResourceGroup

# -- Fixtures / helpers -------------------------------------------------------

TESTS_GROUP = ResourceGroup(
    label="Tests",
    key="tests",
    api_path="/tests",
    columns=[("id", "ID"), ("name", "Name"), ("status", "Status")],
    filters=[
        FilterDef("Status", "statusFilter", [
            (None, "All"),
            ("NEEDS_ATTENTION", "Failing"),
            ("OK", "Passing"),
        ]),
        FilterDef("Category", "categoryFilter", [
            (None, "All"),
            ("Logging", "Logging"),
            ("Access Control", "Access Control"),
        ]),
    ],
)

NO_FILTER_GROUP = ResourceGroup(
    label="Groups",
    key="groups",
    api_path="/groups",
    columns=[("id", "ID"), ("name", "Name")],
    # No filters defined
)

ALL_ITEMS = [
    {"id": "1", "name": "Test A", "status": "OK"},
    {"id": "2", "name": "Test B", "status": "FAIL"},
    {"id": "3", "name": "Test C", "status": "OK"},
]

FILTERED_ITEMS = [
    {"id": "2", "name": "Test B", "status": "FAIL"},
]


class TrackingService(AsyncVantaService):
    """Service that tracks API calls and returns different results based on params."""

    def __init__(self):
        self.calls: list[dict] = []

    async def list_page(self, path, params=None, cursor=None, page_size=100):
        self.calls.append({"path": path, "params": params or {}})
        # Return filtered results if statusFilter is set
        if params and params.get("statusFilter") == "NEEDS_ATTENTION":
            return Page(items=FILTERED_ITEMS, next_cursor=None, has_more=False)
        return Page(items=ALL_ITEMS, next_cursor=None, has_more=False)

    async def get(self, path):
        return {}

    async def download_url(self, url, dest):
        return dest


def get_screen(app: App) -> ResourceListScreen:
    screen = app.screen
    if isinstance(screen, ResourceListScreen):
        return screen
    for s in reversed(app.screen_stack):
        if isinstance(s, ResourceListScreen):
            return s
    raise AssertionError("No ResourceListScreen found")


def get_status_text(screen: ResourceListScreen) -> str:
    status = screen.query_one("#status-bar", Static)
    return str(status.render())


class FilterApp(App):
    def __init__(self, group=None, service=None):
        super().__init__()
        self._group = group or TESTS_GROUP
        self._service = service or TrackingService()

    def on_mount(self) -> None:
        self.push_screen(ResourceListScreen(self._group, self._service))


# -- Phase 2 Tests: Server-side filters ---------------------------------------


class TestFilterDef:
    """FilterDef should be importable and work on ResourceGroup."""

    def test_resource_group_has_filters_field(self):
        assert hasattr(TESTS_GROUP, "filters")
        assert len(TESTS_GROUP.filters) == 2

    def test_resource_group_defaults_to_no_filters(self):
        assert hasattr(NO_FILTER_GROUP, "filters")
        assert len(NO_FILTER_GROUP.filters) == 0

    def test_filter_def_attributes(self):
        f = TESTS_GROUP.filters[0]
        assert f.label == "Status"
        assert f.param == "statusFilter"
        assert len(f.options) == 3


class TestFilterBarVisibility:
    """f should toggle the filter bar; it shouldn't appear for non-filterable resources."""

    @pytest.mark.asyncio
    async def test_f_shows_filter_bar(self):
        app = FilterApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            # Filter bar should be hidden initially
            filter_bar = screen.query("#filter-bar")
            assert len(filter_bar) == 1, "Filter bar widget should exist"
            assert not filter_bar.first().display, "Filter bar should be hidden initially"
            # Press f to show it
            await pilot.press("f")
            await pilot.pause()
            assert filter_bar.first().display, "Filter bar should be visible after pressing f"

    @pytest.mark.asyncio
    async def test_f_toggles_filter_bar_off(self):
        app = FilterApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("f")
            await pilot.pause()
            await pilot.press("f")
            await pilot.pause()
            filter_bar = screen.query_one("#filter-bar")
            assert not filter_bar.display, "Filter bar should hide on second f press"

    @pytest.mark.asyncio
    async def test_no_filter_bar_for_non_filterable_resource(self):
        app = FilterApp(group=NO_FILTER_GROUP)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            filter_bar = screen.query("#filter-bar")
            assert len(filter_bar) == 0, "No filter bar for resources without filters"

    @pytest.mark.asyncio
    async def test_escape_closes_filter_bar(self):
        app = FilterApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("f")
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()
            filter_bar = screen.query_one("#filter-bar")
            assert not filter_bar.display


class TestFilterBarContents:
    """Filter bar should contain RadioSets matching the FilterDefs."""

    @pytest.mark.asyncio
    async def test_filter_bar_has_radio_sets(self):
        app = FilterApp()
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("f")
            await pilot.pause()
            radio_sets = screen.query("#filter-bar RadioSet")
            assert len(radio_sets) == 2, f"Expected 2 RadioSets, got {len(radio_sets)}"


class TestFilterTriggersReload:
    """Changing a filter should clear items and re-fetch from the API with filter params."""

    @pytest.mark.asyncio
    async def test_selecting_filter_reloads_with_params(self):
        service = TrackingService()
        app = FilterApp(service=service)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            # Initial load happened
            initial_call_count = len(service.calls)
            assert initial_call_count >= 1

            # Open filter bar and select "Failing"
            await pilot.press("f")
            await pilot.pause()
            # Click on the "Failing" radio button (second option in first RadioSet)
            radio_sets = screen.query("#filter-bar RadioSet")
            radio_set = radio_sets.first()
            # Change the value by pressing right arrow (moves from "All" to "Failing")
            radio_set.focus()
            await pilot.pause()
            await pilot.press("right")
            await pilot.pause()
            await pilot.pause()  # extra pause for async reload

            # Should have made a new API call with the filter param
            new_calls = service.calls[initial_call_count:]
            assert len(new_calls) >= 1, "Expected a new API call after filter change"
            last_call = new_calls[-1]
            assert last_call["params"].get("statusFilter") == "NEEDS_ATTENTION", \
                f"Expected statusFilter=NEEDS_ATTENTION, got {last_call['params']}"

    @pytest.mark.asyncio
    async def test_filter_clears_table_before_reload(self):
        """After filter change, the table should show only the filtered results."""
        service = TrackingService()
        app = FilterApp(service=service)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            # Initially 3 items
            assert len(screen._items) == 3

            await pilot.press("f")
            await pilot.pause()
            radio_sets = screen.query("#filter-bar RadioSet")
            radio_set = radio_sets.first()
            radio_set.focus()
            await pilot.pause()
            await pilot.press("right")
            await pilot.pause()
            await pilot.pause()

            # After filtering, should have only 1 item (FILTERED_ITEMS)
            assert len(screen._items) == 1, \
                f"Expected 1 filtered item, got {len(screen._items)}"


class TestFilterStatusBar:
    """Status bar should show active filters."""

    @pytest.mark.asyncio
    async def test_status_shows_active_filter(self):
        service = TrackingService()
        app = FilterApp(service=service)
        async with app.run_test(size=(120, 30)) as pilot:
            await pilot.pause()
            screen = get_screen(app)
            await pilot.press("f")
            await pilot.pause()
            radio_sets = screen.query("#filter-bar RadioSet")
            radio_set = radio_sets.first()
            radio_set.focus()
            await pilot.pause()
            await pilot.press("right")
            await pilot.pause()
            await pilot.pause()

            status_text = get_status_text(screen)
            assert "Failing" in status_text or "Status" in status_text, \
                f"Expected active filter in status bar, got: {status_text}"
