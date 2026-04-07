"""Test-specific screens with entity management and deactivation workflows."""

from __future__ import annotations

from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    RadioButton,
    RadioSet,
    Static,
)

from vanta_cli.tui.screens.resource_list import resolve_key
from vanta_cli.tui.service import AsyncVantaService

ENTITY_COLUMNS = [
    ("id", "ID"),
    ("displayName", "Name"),
    ("entityStatus", "Status"),
    ("responseType", "Type"),
    ("lastUpdatedDate", "Updated"),
]


class DeactivateModal(ModalScreen[dict[str, str] | None]):
    """Modal dialog to collect deactivation reason."""

    DEFAULT_CSS = """
    DeactivateModal {
        align: center middle;
    }
    #deactivate-dialog {
        width: 60;
        height: auto;
        max-height: 20;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #deactivate-dialog Label {
        margin-bottom: 1;
    }
    #reason-input {
        margin-bottom: 1;
    }
    #until-input {
        margin-bottom: 1;
    }
    .button-row {
        height: 3;
        align: right middle;
    }
    .button-row Button {
        margin-left: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
    ]

    def __init__(self, entity_name: str) -> None:
        super().__init__()
        self.entity_name = entity_name

    def compose(self) -> ComposeResult:
        with Vertical(id="deactivate-dialog"):
            yield Label(f"Deactivate: {self.entity_name}")
            yield Label("Reason (required):")
            yield Input(placeholder="Justification for deactivation...", id="reason-input")
            yield Label("Reactivate after (optional, ISO date):")
            yield Input(placeholder="e.g. 2025-12-31T00:00:00Z", id="until-input")
            with Horizontal(classes="button-row"):
                yield Button("Cancel", variant="default", id="cancel-btn")
                yield Button("Deactivate", variant="error", id="deactivate-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "deactivate-btn":
            reason = self.query_one("#reason-input", Input).value.strip()
            if not reason:
                self.notify("Reason is required", severity="error")
                return
            result: dict[str, str] = {"reason": reason}
            until = self.query_one("#until-input", Input).value.strip()
            if until:
                result["until"] = until
            self.dismiss(result)
        else:
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class TestEntityScreen(Screen):
    """Browse entities for a specific test, with deactivate/reactivate actions."""

    BINDINGS = [
        Binding("h", "go_back", "Back"),
        Binding("escape", "go_back", "Back", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("space", "load_more", "More"),
        Binding("g", "scroll_top", "Top", show=False),
        Binding("G", "scroll_bottom", "Bottom", show=False),
        Binding("d", "deactivate", "Deactivate"),
        Binding("r", "reactivate", "Reactivate"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("1", "filter_failing", "Failing", show=False),
        Binding("2", "filter_deactivated", "Deactivated", show=False),
        Binding("0", "filter_all", "All", show=False),
    ]

    def __init__(self, test_id: str, test_name: str, service: AsyncVantaService) -> None:
        super().__init__()
        self.test_id = test_id
        self.test_name = test_name
        self.service = service
        self._items: list[dict[str, Any]] = []
        self._cursor: str | None = None
        self._has_more = False
        self._status_filter: str | None = "FAILING"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Entities: {self.test_name}", classes="screen-title")
        with Horizontal(id="filter-bar"):
            yield Static("Filter: ", id="filter-label")
            with RadioSet(id="status-filter"):
                yield RadioButton("Failing", value=True, id="filter-failing")
                yield RadioButton("Deactivated", id="filter-deactivated")
                yield RadioButton("All", id="filter-all")
        yield DataTable(id="entity-table")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#entity-table", DataTable)
        table.cursor_type = "row"
        for key, header in ENTITY_COLUMNS:
            table.add_column(header, key=key)
        self._load_page()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        button_id = event.pressed.id
        if button_id == "filter-failing":
            self._status_filter = "FAILING"
        elif button_id == "filter-deactivated":
            self._status_filter = "DEACTIVATED"
        else:
            self._status_filter = None
        self._reset_and_load()

    def _reset_and_load(self) -> None:
        self._items.clear()
        self._cursor = None
        self._has_more = False
        table = self.query_one("#entity-table", DataTable)
        table.clear()
        self._load_page()

    @work
    async def _load_page(self) -> None:
        status = self.query_one("#status-bar", Static)
        status.update("Loading...")
        params: dict[str, Any] = {}
        if self._status_filter:
            params["entityStatus"] = self._status_filter

        page = await self.service.list_page(
            f"/tests/{self.test_id}/entities",
            params=params,
            cursor=self._cursor,
        )
        self._cursor = page.next_cursor
        self._has_more = page.has_more

        table = self.query_one("#entity-table", DataTable)
        for item in page.items:
            row_key = item.get("id", str(len(self._items)))
            values = []
            for key, _ in ENTITY_COLUMNS:
                val = resolve_key(item, key)
                # Color-code status
                if key == "entityStatus":
                    if val == "FAILING":
                        val = f"[red]{val}[/red]"
                    elif val == "DEACTIVATED":
                        val = f"[dim]{val}[/dim]"
                    elif val == "PASSING":
                        val = f"[green]{val}[/green]"
                values.append(val)
            table.add_row(*values, key=row_key)
            self._items.append(item)

        count_msg = f"{len(self._items)} entities"
        if self._has_more:
            count_msg += " (space for more)"
        status.update(count_msg)

    def action_load_more(self) -> None:
        if self._has_more:
            self._load_page()

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_cursor_down(self) -> None:
        table = self.query_one("#entity-table", DataTable)
        table.action_cursor_down()

    def action_cursor_up(self) -> None:
        table = self.query_one("#entity-table", DataTable)
        table.action_cursor_up()

    def action_scroll_top(self) -> None:
        table = self.query_one("#entity-table", DataTable)
        table.action_scroll_home()

    def action_scroll_bottom(self) -> None:
        table = self.query_one("#entity-table", DataTable)
        table.action_scroll_end()

    def action_focus_filter(self) -> None:
        self.query_one("#status-filter", RadioSet).focus()

    def action_filter_failing(self) -> None:
        self.query_one("#filter-failing", RadioButton).value = True

    def action_filter_deactivated(self) -> None:
        self.query_one("#filter-deactivated", RadioButton).value = True

    def action_filter_all(self) -> None:
        self.query_one("#filter-all", RadioButton).value = True

    def _get_selected_item(self) -> dict[str, Any] | None:
        table = self.query_one("#entity-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self._items):
            return self._items[table.cursor_row]
        return None

    def action_deactivate(self) -> None:
        item = self._get_selected_item()
        if not item:
            self.notify("No entity selected", severity="warning")
            return
        name = item.get("displayName", item.get("id", "unknown"))
        self.app.push_screen(DeactivateModal(name), callback=self._on_deactivate_result)
        self._pending_entity_id = item.get("id")

    def _on_deactivate_result(self, result: dict[str, str] | None) -> None:
        if result is None:
            return
        entity_id = self._pending_entity_id
        self._do_deactivate(entity_id, result["reason"], result.get("until"))

    @work
    async def _do_deactivate(self, entity_id: str, reason: str, until: str | None) -> None:
        body: dict[str, str] = {"deactivateReason": reason}
        if until:
            body["deactivateUntilDate"] = until
        await self.service.post(
            f"/tests/{self.test_id}/entities/{entity_id}/deactivate",
            json=body,
        )
        self.notify(f"Deactivated {entity_id}", severity="information")
        self._reset_and_load()

    def action_reactivate(self) -> None:
        item = self._get_selected_item()
        if not item:
            self.notify("No entity selected", severity="warning")
            return
        entity_id = item.get("id")
        self._do_reactivate(entity_id)

    @work
    async def _do_reactivate(self, entity_id: str) -> None:
        await self.service.post(
            f"/tests/{self.test_id}/entities/{entity_id}/reactivate"
        )
        self.notify(f"Reactivated {entity_id}", severity="information")
        self._reset_and_load()
