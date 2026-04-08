"""Generic detail screen for a single resource."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from vanta_cli.tui.service import AsyncVantaService


def _extract_doc_urls(item: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract document entries from a policy's latestApprovedVersion."""
    version = item.get("latestApprovedVersion", {})
    if not version:
        return []
    return version.get("documents", [])


def _policy_filename(policy_name: str, index: int) -> str:
    slug = re.sub(r"[^\w\s-]", "", policy_name).strip().lower()
    slug = re.sub(r"[\s]+", "_", slug)
    suffix = f"_{index}" if index > 0 else ""
    return f"{slug}{suffix}.pdf"


class DetailScreen(Screen):
    """Displays key-value details for a single resource."""

    BINDINGS = [
        Binding("h", "go_back", "Back"),
        Binding("escape", "go_back", "Back", show=False),
        Binding("q", "go_back", "Back", show=False),
    ]

    def __init__(
        self,
        item: dict[str, Any],
        title: str = "Detail",
        service: AsyncVantaService | None = None,
        resource_type: str | None = None,
    ) -> None:
        super().__init__()
        self.item = item
        self.title_text = title
        self.service = service
        self.resource_type = resource_type

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(self.title_text, classes="screen-title")
        yield Static(self._format_item(), id="detail-content")
        yield Footer()

    def on_mount(self) -> None:
        # Add download binding dynamically if this item has documents
        if self._has_downloads():
            self._bindings.bind("D", "download", "Download PDFs", key_display="shift+d")

    def _has_downloads(self) -> bool:
        return self.resource_type == "policies" and bool(_extract_doc_urls(self.item))

    def _format_item(self) -> str:
        lines = []
        for key, val in self.item.items():
            if isinstance(val, (dict, list)):
                val = json.dumps(val, indent=2)
            lines.append(f"[bold]{key}[/bold]: {val}")
        if self._has_downloads():
            docs = _extract_doc_urls(self.item)
            lines.append("")
            lines.append(f"[bold green]{len(docs)} document(s) available — press Shift+D to download[/bold green]")
        return "\n".join(lines)

    def action_go_back(self) -> None:
        self.app.pop_screen()

    def action_download(self) -> None:
        if not self.service:
            self.notify("Download not available", severity="error")
            return
        self._do_download()

    @work
    async def _do_download(self) -> None:
        docs = _extract_doc_urls(self.item)
        if not docs:
            self.notify("No documents to download", severity="warning")
            return

        dest_dir = Path.cwd()
        policy_name = self.item.get("name", "")
        count = 0
        for i, doc in enumerate(docs):
            url = doc.get("url", "")
            if not url:
                continue
            filename = _policy_filename(policy_name, i) if policy_name else f"policy_document_{i}.pdf"
            dest = dest_dir / filename
            self.notify(f"Downloading {filename}...")
            await self.service.download_url(url, dest)
            count += 1

        self.notify(f"Downloaded {count} file(s) to {dest_dir}", severity="information")
