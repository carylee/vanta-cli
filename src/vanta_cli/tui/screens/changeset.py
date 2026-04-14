"""TUI screen for reviewing and applying staged changesets."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import DataTable, Footer, Header, Static
from textual import work

# Regex to parse API paths like /tests/{test}/entities/{entity}/{action}
_PATH_RE = re.compile(
    r"^/(?P<resource>[^/]+)/(?P<name>[^/]+)"
    r"(?:/entities/(?P<entity>[^/]+))?(?:/(?P<action>[^/]+))?$"
)

# apply_fn returns None on success, or an error message string on failure.
ApplyFn = Callable[[dict[str, Any]], str | None]


def _parse_path(path: str) -> tuple[str, str, str]:
    """Parse an API path into (resource/name, entity, action) display columns."""
    m = _PATH_RE.match(path)
    if not m:
        return path, "", ""
    name = m.group("name") or ""
    entity = m.group("entity") or ""
    action = m.group("action") or ""
    # Truncate long entity IDs
    if len(entity) > 16:
        entity = entity[:7] + "…" + entity[-7:]
    return name, entity, action


def _summarise_body(body: Any, max_len: int = 80) -> str:
    """Generate a short summary string from the request body."""
    if not body or not isinstance(body, dict):
        return ""
    first_val = next(iter(body.values()), None)
    if not isinstance(first_val, str):
        return ""
    return first_val[:max_len] + ("…" if len(first_val) > max_len else "")


class ChangesetScreen(Screen):
    """Displays staged changes and allows applying or dropping them."""

    DEFAULT_CSS = """
    #changeset-table {
        height: 1fr;
    }
    #detail-pane {
        height: auto;
        max-height: 40%;
        border-top: solid $accent;
        padding: 0 1;
        overflow-y: auto;
    }
    """

    BINDINGS = [
        Binding("h", "go_back", "Back"),
        Binding("escape", "go_back", "Back", show=False),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("a", "apply_selected", "Apply"),
        Binding("A", "apply_all", "Apply All", key_display="shift+a"),
        Binding("d", "drop_selected", "Drop"),
        Binding("D", "clear_all", "Clear All", key_display="shift+d"),
        Binding("space", "toggle_select", "Select", show=False),
        Binding("s", "select_all", "Sel All"),
    ]

    def __init__(
        self,
        changeset_file: Path,
        apply_fn: ApplyFn | None = None,
    ) -> None:
        super().__init__()
        self._changeset_file = changeset_file
        self._apply_fn = apply_fn
        self._changes: list[dict[str, Any]] = []
        self._selected: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Staged Changes", classes="screen-title")
        yield DataTable(id="changeset-table")
        yield Static("", id="detail-pane")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        table = self.query_one("#changeset-table", DataTable)
        table.cursor_type = "row"
        table.add_column("", key="sel", width=3)
        table.add_column("ID", key="id")
        table.add_column("Method", key="method")
        table.add_column("Path", key="path")
        table.add_column("Entity", key="entity")
        table.add_column("Action", key="action")
        table.add_column("Summary", key="summary")
        self._load_changes()

    def _load_changes(self) -> None:
        """Load changes from the file and populate the table."""
        self._changes = self._read_file()
        self._selected.clear()
        table = self.query_one("#changeset-table", DataTable)
        table.clear()
        for change in self._changes:
            self._add_table_row(table, change)
        self._update_status()
        self._update_detail()

    def _add_table_row(self, table: DataTable, change: dict[str, Any]) -> None:
        path_name, entity, action = _parse_path(change.get("path", ""))
        summary = change.get("description", "") or _summarise_body(
            change.get("body")
        )
        sel = "✓" if change["id"] in self._selected else " "
        table.add_row(
            sel,
            change.get("id", ""),
            change.get("method", ""),
            path_name,
            entity,
            action,
            summary,
            key=change["id"],
        )

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

    def _update_status(self, message: str | None = None) -> None:
        status = self.query_one("#status-bar", Static)
        if message:
            status.update(message)
            return
        parts = []
        if self._changes:
            parts.append(f"{len(self._changes)} staged change(s)")
        else:
            parts.append("No staged changes")
        if self._selected:
            parts.append(f"{len(self._selected)} selected")
        status.update(" | ".join(parts))

    def _update_detail(self) -> None:
        """Update the detail pane with the currently highlighted change."""
        detail = self.query_one("#detail-pane", Static)
        idx = self._selected_index()
        if idx is None:
            detail.update("")
            return
        change = self._changes[idx]
        lines = [
            f"[bold]ID:[/bold] {change.get('id', '')}",
            f"[bold]Method:[/bold] {change.get('method', '')}",
            f"[bold]Path:[/bold] {change.get('path', '')}",
            f"[bold]Timestamp:[/bold] {change.get('timestamp', '')}",
        ]
        if change.get("description"):
            lines.append(f"[bold]Description:[/bold] {change['description']}")
        body = change.get("body")
        if body:
            lines.append("[bold]Body:[/bold]")
            lines.append(json.dumps(body, indent=2))
        detail.update("\n".join(lines))

    def _selected_index(self) -> int | None:
        table = self.query_one("#changeset-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self._changes):
            return table.cursor_row
        return None

    def _refresh_sel_column(self) -> None:
        """Refresh the selection marker column for all rows."""
        table = self.query_one("#changeset-table", DataTable)
        for i, change in enumerate(self._changes):
            marker = "✓" if change["id"] in self._selected else " "
            table.update_cell(change["id"], "sel", marker)

    def _remove_change(self, index: int) -> None:
        """Remove a change by index from state, table, and file."""
        change = self._changes.pop(index)
        self._selected.discard(change["id"])
        table = self.query_one("#changeset-table", DataTable)
        table.remove_row(change["id"])
        self._write_file()
        self._update_status()
        self._update_detail()

    def _remove_changes(self, ids: set[str]) -> None:
        """Remove multiple changes by ID."""
        self._changes = [c for c in self._changes if c["id"] not in ids]
        self._selected -= ids
        table = self.query_one("#changeset-table", DataTable)
        for cid in ids:
            table.remove_row(cid)
        self._write_file()
        self._update_status()
        self._update_detail()

    def _try_apply(self, change: dict[str, Any]) -> str | None:
        """Call the apply function. Returns None on success, error string on failure."""
        if not self._apply_fn:
            return "No apply function configured"
        return self._apply_fn(change)

    # -- Events ----------------------------------------------------------------

    def on_data_table_cursor_moved(self, event: DataTable.CursorMoved) -> None:
        self._update_detail()

    # -- Actions ---------------------------------------------------------------

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_cursor_down(self) -> None:
        self.query_one("#changeset-table", DataTable).action_cursor_down()
        self._update_detail()

    def action_cursor_up(self) -> None:
        self.query_one("#changeset-table", DataTable).action_cursor_up()
        self._update_detail()

    def action_toggle_select(self) -> None:
        idx = self._selected_index()
        if idx is None:
            return
        cid = self._changes[idx]["id"]
        if cid in self._selected:
            self._selected.discard(cid)
        else:
            self._selected.add(cid)
        self._refresh_sel_column()
        self._update_status()
        # Advance cursor after toggling
        self.query_one("#changeset-table", DataTable).action_cursor_down()

    def action_select_all(self) -> None:
        if self._selected == {c["id"] for c in self._changes}:
            self._selected.clear()
        else:
            self._selected = {c["id"] for c in self._changes}
        self._refresh_sel_column()
        self._update_status()

    def action_apply_selected(self) -> None:
        if self._selected:
            self._apply_batch(self._selected.copy())
            return
        idx = self._selected_index()
        if idx is None:
            return
        change = self._changes[idx]
        error = self._try_apply(change)
        if error is None:
            self._remove_change(idx)
            self.notify(f"Applied: {change['method']} {change['path']}")
        else:
            self.notify(
                f"Failed ({change['id']}): {error}", severity="error", timeout=8
            )

    @work(group="apply", exclusive=True, thread=True)
    def _apply_batch(self, ids: set[str]) -> None:
        """Apply a batch of changes with progress updates."""
        import time

        total = len(ids)
        applied: set[str] = set()
        failed = 0
        for change in list(self._changes):
            if change["id"] not in ids:
                continue
            n = len(applied) + failed + 1
            self.app.call_from_thread(
                self._update_status, f"Applying {n}/{total}..."
            )
            error = self._try_apply(change)
            if error is None:
                applied.add(change["id"])
            else:
                failed += 1
                self.app.call_from_thread(
                    self.notify,
                    f"Failed ({change['id']}): {error}",
                    severity="error",
                    timeout=8,
                )
            # Rate-limit: 200ms between requests to avoid 429s
            if n < total:
                time.sleep(0.2)
        if applied:
            self.app.call_from_thread(self._remove_changes, applied)
        if applied or failed:
            self.app.call_from_thread(
                self.notify, f"Applied {len(applied)}, failed {failed}"
            )
        self.app.call_from_thread(self._update_status)

    def action_apply_all(self) -> None:
        if not self._changes:
            return
        self._apply_batch({c["id"] for c in self._changes})

    def action_drop_selected(self) -> None:
        if self._selected:
            count = len(self._selected)
            self._remove_changes(self._selected.copy())
            self.notify(f"Dropped {count} change(s)")
            return
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
        self._selected.clear()
        self._write_file()
        self._update_status()
        self._update_detail()
        self.notify("Cleared all staged changes")
