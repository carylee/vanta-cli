"""Generic resource list screen with pagination."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static

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

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self.group.label, classes="screen-title")
        yield DataTable(id="resource-table")
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

    @work
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

        count_msg = f"{len(self._items)} items"
        if self._has_more:
            count_msg += " (space for more)"
        status.update(count_msg)

    def action_load_more(self) -> None:
        if self._has_more:
            self._load_page()

    def action_go_back(self) -> None:
        self.app.pop_screen()

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
