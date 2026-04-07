"""Breadcrumb navigation bar."""

from __future__ import annotations

from textual.widgets import Static


class Breadcrumb(Static):
    """Shows the current navigation path."""

    DEFAULT_CSS = """
    Breadcrumb {
        dock: top;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self) -> None:
        super().__init__("Vanta", id="breadcrumb")
        self._path: list[str] = []

    def push(self, label: str) -> None:
        self._path.append(label)
        self._refresh_text()

    def pop(self) -> None:
        if self._path:
            self._path.pop()
        self._refresh_text()

    def clear(self) -> None:
        self._path.clear()
        self._refresh_text()

    def _refresh_text(self) -> None:
        parts = ["Vanta"] + self._path
        self.update(" > ".join(parts))
