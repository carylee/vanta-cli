"""Generic resource list screen with pagination."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Input, RadioButton, RadioSet, Static

from vanta_cli.tui.service import AsyncVantaService
from vanta_cli.tui.widgets.sidebar import ResourceGroup


def resolve_key(item: dict[str, Any], key: str) -> str:
    """Resolve a dotted key from a nested dict, return string."""
    parts = key.split(".")
    val: Any = item
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return ""
    return str(val) if val is not None else ""


def _policy_filename(policy_name: str, index: int) -> str:
    slug = re.sub(r"[^\w\s-]", "", policy_name).strip().lower()
    slug = re.sub(r"[\s]+", "_", slug)
    suffix = f"_{index}" if index > 0 else ""
    return f"{slug}{suffix}.pdf"


class ResourceListScreen(Screen):
    """Displays a paginated list of resources."""

    BINDINGS = [
        Binding("h", "go_back", "Back"),
        Binding("escape", "go_back", "Back", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("l", "select_row", "Open"),
        Binding("space", "load_more", "More"),
        Binding("g", "scroll_top", "Top"),
        Binding("G", "scroll_bottom", "Bottom", key_display="shift+g"),
        Binding("slash", "search", "Search"),
        Binding("n", "next_match", "Next", show=False),
        Binding("N", "prev_match", "Prev", key_display="shift+n", show=False),
        Binding("f", "toggle_filters", "Filter"),
    ]

    class RowSelected(Message):
        """Emitted when a row is selected for detail view."""

        def __init__(self, item: dict[str, Any], group: ResourceGroup) -> None:
            super().__init__()
            self.item = item
            self.group = group

    def __init__(
        self,
        group: ResourceGroup,
        service: AsyncVantaService,
        params: dict[str, Any] | None = None,
    ) -> None:
        super().__init__()
        self.group = group
        self.service = service
        self.params = params
        self._items: list[dict[str, Any]] = []
        self._cursor: str | None = None
        self._has_more = False
        # Search state
        self._search_term: str = ""
        self._match_indices: list[int] = []
        self._match_pos: int = 0
        # Filter state: maps param name -> (selected value, display label)
        self._active_filters: dict[str, tuple[str | None, str]] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self.group.label, classes="screen-title")
        if self.group.filters:
            with Horizontal(id="filter-bar") as bar:
                bar.display = False
                for fdef in self.group.filters:
                    with RadioSet(id=f"filter-{fdef.param}"):
                        for value, label in fdef.options:
                            yield RadioButton(label)
        yield DataTable(id="resource-table")
        search = Input(placeholder="Search...", classes="search-input")
        search.display = False
        yield search
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#resource-table", DataTable)
        table.cursor_type = "row"
        for key, header in self.group.columns:
            table.add_column(header, key=key)
        if self.group.key == "policies":
            self._bindings.bind("D", "download_all", "Download All", key_display="shift+d")
        self._load_page()

    @work(group="loader", exclusive=True)
    async def _load_page(self) -> None:
        status = self.query_one("#status-bar", Static)
        status.update("Loading...")
        page = await self.service.list_page(
            self.group.api_path,
            params=self.params,
            cursor=self._cursor,
        )
        self._cursor = page.next_cursor
        self._has_more = page.has_more

        table = self.query_one("#resource-table", DataTable)
        for item in page.items:
            row_key = item.get("id") or item.get("riskId") or item.get("integrationId") or str(len(self._items))
            values = [resolve_key(item, key) for key, _ in self.group.columns]
            table.add_row(*values, key=row_key)
            self._items.append(item)

        self._update_status()

    def action_load_more(self) -> None:
        if self._has_more:
            self._load_page()

    def action_cursor_down(self) -> None:
        table = self.query_one("#resource-table", DataTable)
        table.action_cursor_down()

    def action_cursor_up(self) -> None:
        table = self.query_one("#resource-table", DataTable)
        table.action_cursor_up()

    def action_scroll_top(self) -> None:
        table = self.query_one("#resource-table", DataTable)
        table.action_scroll_home()

    def action_scroll_bottom(self) -> None:
        table = self.query_one("#resource-table", DataTable)
        table.action_scroll_end()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle Enter key on the DataTable."""
        self.action_select_row()

    def action_select_row(self) -> None:
        table = self.query_one("#resource-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self._items):
            item = self._items[table.cursor_row]
            self.post_message(self.RowSelected(item, self.group))

    # -- Search actions ----------------------------------------------------------

    def action_search(self) -> None:
        """Show the search input and focus it."""
        search = self.query_one("Input.search-input", Input)
        search.display = True
        search.value = ""
        search.focus()

    @on(Input.Submitted, ".search-input")
    def _on_search_submitted(self, event: Input.Submitted) -> None:
        """Confirm search: compute matches and jump to the first one."""
        search = self.query_one("Input.search-input", Input)
        term = search.value.strip()
        search.display = False

        self._search_term = term
        self._compute_matches()

        if self._match_indices:
            self._match_pos = 0
            self._jump_to_match()
        else:
            self._update_status()

        # Return focus to the table
        self.query_one("#resource-table", DataTable).focus()

    def _on_search_input_key(self, event) -> None:
        """Handle Escape inside the search input."""
        # This is handled by the screen-level escape binding,
        # but we override go_back when search is open.
        pass

    def action_go_back(self) -> None:
        search = self.query_one("Input.search-input", Input)
        if search.display:
            # Close search instead of navigating back
            search.display = False
            self._search_term = ""
            self._match_indices = []
            self._match_pos = 0
            self._update_status()
            self.query_one("#resource-table", DataTable).focus()
        elif self.group.filters:
            bar = self.query_one("#filter-bar")
            if bar.display:
                bar.display = False
                self.query_one("#resource-table", DataTable).focus()
                return
            self.app.pop_screen()
        else:
            self.app.pop_screen()

    def _compute_matches(self) -> None:
        """Find indices of items matching the current search term."""
        if not self._search_term:
            self._match_indices = []
            return
        term = self._search_term.lower()
        matches = []
        for i, item in enumerate(self._items):
            values = [resolve_key(item, key).lower() for key, _ in self.group.columns]
            if any(term in v for v in values):
                matches.append(i)
        self._match_indices = matches

    def _jump_to_match(self) -> None:
        """Move the table cursor to the current match and update status."""
        if not self._match_indices:
            return
        row = self._match_indices[self._match_pos]
        table = self.query_one("#resource-table", DataTable)
        table.move_cursor(row=row)
        self._update_status()

    def _update_status(self) -> None:
        """Update the status bar with match info or default item count."""
        status = self.query_one("#status-bar", Static)
        # Build filter suffix
        filter_parts = [f"{label}" for _param, (_val, label) in self._active_filters.items()]
        filter_str = f" \\[{', '.join(filter_parts)}]" if filter_parts else ""

        if self._search_term and self._match_indices:
            msg = f"match {self._match_pos + 1} of {len(self._match_indices)}{filter_str}"
            status.update(msg)
        elif self._search_term and not self._match_indices:
            status.update(f"no matches{filter_str}")
        else:
            count_msg = f"{len(self._items)} items{filter_str}"
            if self._has_more:
                count_msg += " (space for more)"
            status.update(count_msg)

    def action_next_match(self) -> None:
        """Jump to the next search match (wraps around)."""
        if not self._match_indices:
            return
        self._match_pos = (self._match_pos + 1) % len(self._match_indices)
        self._jump_to_match()

    def action_prev_match(self) -> None:
        """Jump to the previous search match (wraps around)."""
        if not self._match_indices:
            return
        self._match_pos = (self._match_pos - 1) % len(self._match_indices)
        self._jump_to_match()

    # -- Filter actions ----------------------------------------------------------

    def action_toggle_filters(self) -> None:
        """Toggle the filter bar visibility."""
        if not self.group.filters:
            return
        bar = self.query_one("#filter-bar")
        bar.display = not bar.display
        if bar.display:
            # Focus the first RadioSet
            radio_sets = self.query("#filter-bar RadioSet")
            if radio_sets:
                radio_sets.first().focus()
        else:
            self.query_one("#resource-table", DataTable).focus()

    @on(RadioSet.Changed)
    def _on_filter_changed(self, event: RadioSet.Changed) -> None:
        """When a filter RadioSet changes, rebuild params and reload."""
        if not self.group.filters:
            return
        # Map each RadioSet back to its FilterDef
        self._active_filters.clear()
        for fdef in self.group.filters:
            radio_set = self.query_one(f"#filter-{fdef.param}", RadioSet)
            idx = radio_set.pressed_index
            if idx >= 0 and idx < len(fdef.options):
                value, label = fdef.options[idx]
                if value is not None:
                    self._active_filters[fdef.param] = (value, label)
        self._reset_and_reload()

    def _reset_and_reload(self) -> None:
        """Clear table and items, rebuild params from filters, and re-fetch."""
        table = self.query_one("#resource-table", DataTable)
        table.clear()
        self._items.clear()
        self._cursor = None
        self._has_more = False
        self._search_term = ""
        self._match_indices = []
        self._match_pos = 0
        # Merge base params with filter params
        self.params = dict(self.params or {})
        # Remove old filter params
        for fdef in self.group.filters:
            self.params.pop(fdef.param, None)
        # Add active filter params
        for param, (value, _label) in self._active_filters.items():
            self.params[param] = value
        self._load_page()

    def action_download_all(self) -> None:
        if self.group.key != "policies":
            return
        self._do_download_all()

    @work
    async def _do_download_all(self) -> None:
        """Fetch all policies (paginating fully) and download all their documents."""
        status = self.query_one("#status-bar", Static)
        dest_dir = Path.cwd() / "vanta-export" / "policies"
        dest_dir.mkdir(parents=True, exist_ok=True)

        # Paginate through all policies first.
        status.update("Fetching all policies...")
        all_policies: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            page = await self.service.list_page(self.group.api_path, cursor=cursor)
            all_policies.extend(page.items)
            if not page.has_more:
                break
            cursor = page.next_cursor

        total = 0
        for i, item in enumerate(all_policies):
            policy_id = item.get("id", "")
            policy_name = item.get("name", "")
            status.update(f"Downloading policy {i + 1}/{len(all_policies)}: {policy_name}...")

            full = await self.service.get(f"/policies/{policy_id}")
            docs = (full.get("latestApprovedVersion") or {}).get("documents", [])

            for j, doc in enumerate(docs):
                url = doc.get("url", "")
                if not url:
                    continue
                filename = _policy_filename(policy_name, j) if policy_name else f"policy_document_{policy_id}_{j}.pdf"
                dest = dest_dir / filename
                await self.service.download_url(url, dest)
                total += 1

        status.update(f"Downloaded {total} document(s) to {dest_dir}")
        self.notify(f"Downloaded {total} document(s) to {dest_dir}", severity="information")
