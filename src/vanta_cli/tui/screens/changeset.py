"""TUI screen for reviewing and applying staged changesets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static


class ChangesetScreen(Screen):
    """Displays staged changes and allows applying or dropping them."""

    BINDINGS = [
        Binding("h", "go_back", "Back"),
        Binding("escape", "go_back", "Back", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("a", "apply_selected", "Apply"),
        Binding("A", "apply_all", "Apply All", key_display="shift+a"),
        Binding("d", "drop_selected", "Drop"),
        Binding("D", "clear_all", "Clear All", key_display="shift+d"),
    ]

    def __init__(
        self,
        changeset_file: Path,
        apply_fn: Callable[[dict[str, Any]], bool] | None = None,
    ) -> None:
        super().__init__()
        self._changeset_file = changeset_file
        self._apply_fn = apply_fn
        self._changes: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Staged Changes", classes="screen-title")
        yield DataTable(id="changeset-table")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#changeset-table", DataTable)
        table.cursor_type = "row"
        table.add_column("ID", key="id")
        table.add_column("Method", key="method")
        table.add_column("Path", key="path")
        table.add_column("Description", key="description")
        self._load_changes()

    def _load_changes(self) -> None:
        """Load changes from the file and populate the table."""
        self._changes = self._read_file()
        table = self.query_one("#changeset-table", DataTable)
        table.clear()
        for change in self._changes:
            table.add_row(
                change.get("id", ""),
                change.get("method", ""),
                change.get("path", ""),
                change.get("description", ""),
                key=change["id"],
            )
        self._update_status()

    def _read_file(self) -> list[dict[str, Any]]:
        if not self._changeset_file.exists():
            return []
        try:
            return json.loads(self._changeset_file.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _write_file(self) -> None:
        self._changeset_file.parent.mkdir(parents=True, exist_ok=True)
        self._changeset_file.write_text(json.dumps(self._changes, indent=2))

    def _update_status(self) -> None:
        status = self.query_one("#status-bar", Static)
        if self._changes:
            status.update(f"{len(self._changes)} staged change(s)")
        else:
            status.update("No staged changes")

    def _selected_index(self) -> int | None:
        table = self.query_one("#changeset-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self._changes):
            return table.cursor_row
        return None

    def _remove_change(self, index: int) -> None:
        """Remove a change by index from state, table, and file."""
        change = self._changes.pop(index)
        table = self.query_one("#changeset-table", DataTable)
        table.remove_row(change["id"])
        self._write_file()
        self._update_status()

    # -- Actions ---------------------------------------------------------------

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_cursor_down(self) -> None:
        self.query_one("#changeset-table", DataTable).action_cursor_down()

    def action_cursor_up(self) -> None:
        self.query_one("#changeset-table", DataTable).action_cursor_up()

    def action_apply_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        change = self._changes[idx]
        if self._apply_fn and self._apply_fn(change):
            self._remove_change(idx)
            self.notify(f"Applied: {change['method']} {change['path']}")
        elif self._apply_fn:
            self.notify(f"Failed to apply {change['id']}", severity="error")
        else:
            self.notify("No apply function configured", severity="warning")

    def action_apply_all(self) -> None:
        applied = []
        for i, change in enumerate(list(self._changes)):
            if self._apply_fn and self._apply_fn(change):
                applied.append(change["id"])
            elif self._apply_fn:
                self.notify(f"Failed: {change['id']}", severity="error")
        # Remove applied in reverse to preserve indices
        self._changes = [c for c in self._changes if c["id"] not in applied]
        table = self.query_one("#changeset-table", DataTable)
        for cid in applied:
            table.remove_row(cid)
        self._write_file()
        self._update_status()
        if applied:
            self.notify(f"Applied {len(applied)} change(s)")

    def action_drop_selected(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        change = self._changes[idx]
        self._remove_change(idx)
        self.notify(f"Dropped: {change['id']}")

    def action_clear_all(self) -> None:
        table = self.query_one("#changeset-table", DataTable)
        table.clear()
        self._changes.clear()
        self._write_file()
        self._update_status()
        self.notify("Cleared all staged changes")
