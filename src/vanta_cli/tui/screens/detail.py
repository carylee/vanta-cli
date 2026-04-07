"""Generic detail screen for a single resource."""

from __future__ import annotations

import json
from typing import Any

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static


class DetailScreen(Screen):
    """Displays key-value details for a single resource."""

    BINDINGS = [
        Binding("h", "go_back", "Back"),
        Binding("escape", "go_back", "Back", show=False),
        Binding("q", "go_back", "Back", show=False),
    ]

    def __init__(self, item: dict[str, Any], title: str = "Detail") -> None:
        super().__init__()
        self.item = item
        self.title_text = title

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self.title_text, classes="screen-title")
        yield Static(self._format_item(), id="detail-content")
        yield Footer()

    def _format_item(self) -> str:
        lines = []
        for key, val in self.item.items():
            if isinstance(val, (dict, list)):
                val = json.dumps(val, indent=2)
            lines.append(f"[bold]{key}[/bold]: {val}")
        return "\n".join(lines)

    def action_go_back(self) -> None:
        self.app.pop_screen()
