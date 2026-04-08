"""Dashboard widget showing compliance summary and quick actions."""

from __future__ import annotations

import asyncio
from typing import Any

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Static

from vanta_cli.tui.service import AsyncVantaService


class DashPanel(Static):
    """A single dashboard summary panel."""

    def __init__(self, label: str, panel_id: str, style_class: str = "") -> None:
        super().__init__(f"[dim]{label}: loading...[/dim]", id=panel_id)
        if style_class:
            self.add_class(style_class)
        self.add_class("dash-panel")

    def set_count(self, label: str, count: int, has_more: bool = False) -> None:
        suffix = "+" if has_more else ""
        if count == 0:
            self.update(f"[green]{label}: {count}[/green]")
            self.remove_class("critical")
            self.remove_class("warning")
            self.add_class("ok")
        else:
            self.update(f"[bold]{label}: {count}{suffix}[/bold]")

    def set_error(self, label: str) -> None:
        self.update(f"[dim]{label}: --[/dim]")


class Dashboard(Widget):
    """Compliance dashboard with live summary counts."""

    DEFAULT_CSS = """
    Dashboard {
        height: 100%;
        padding: 1 2;
    }
    .dash-row {
        height: 5;
        margin-bottom: 1;
    }
    .dash-panel {
        width: 1fr;
        height: 5;
        margin: 0 1;
        border: round $accent;
        padding: 1 2;
        content-align: center middle;
    }
    .dash-panel.critical {
        border: round red;
    }
    .dash-panel.warning {
        border: round $warning;
    }
    .dash-panel.ok {
        border: round green;
    }
    #dash-shortcuts {
        height: auto;
        margin-top: 1;
        padding: 0 2;
        color: $text-muted;
    }
    #dash-title {
        height: 1;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, service: AsyncVantaService, user_id: str | None = None) -> None:
        super().__init__(id="dashboard")
        self.service = service
        self.user_id = user_id

    def compose(self) -> ComposeResult:
        yield Static("Dashboard", id="dash-title")
        with Horizontal(classes="dash-row"):
            yield DashPanel("Tests Needing Attention", "panel-tests-all", "warning")
            yield DashPanel("My Failing Tests", "panel-tests-mine", "warning")
        with Horizontal(classes="dash-row"):
            yield DashPanel("Critical Vulnerabilities", "panel-vulns-crit", "critical")
            yield DashPanel("High Vulnerabilities", "panel-vulns-high", "warning")
        with Horizontal(classes="dash-row"):
            yield DashPanel("Risk Scenarios Pending Review", "panel-risk", "warning")
            yield DashPanel("", "panel-spacer")
        shortcuts = (
            "[bold]Quick Actions:[/bold]  "
            "[bold]1[/bold] My failing tests  "
            "[bold]2[/bold] Code changes  "
            "[bold]3[/bold] Critical/high vulns  "
            "[bold]4[/bold] Risk scenarios"
        )
        yield Static(shortcuts, id="dash-shortcuts")

    def on_mount(self) -> None:
        self._load_data()
        # Hide "my tests" panel if user not configured
        if not self.user_id:
            panel = self.query_one("#panel-tests-mine", DashPanel)
            panel.update("[dim]My Failing Tests: run 'vanta configure' to set up[/dim]")
        # Hide spacer label
        self.query_one("#panel-spacer", DashPanel).update("")

    @work
    async def _load_data(self) -> None:
        tasks: list = [
            self._fetch_count("panel-tests-all", "Tests Needing Attention",
                              "/tests", {"statusFilter": "NEEDS_ATTENTION"}),
            self._fetch_count("panel-vulns-crit", "Critical Vulnerabilities",
                              "/vulnerabilities", {"severity": "CRITICAL", "isDeactivated": "false"}),
            self._fetch_count("panel-vulns-high", "High Vulnerabilities",
                              "/vulnerabilities", {"severity": "HIGH", "isDeactivated": "false"}),
            self._fetch_count("panel-risk", "Risk Scenarios Pending Review",
                              "/risk-scenarios", {}),
        ]
        if self.user_id:
            tasks.append(
                self._fetch_count("panel-tests-mine", "My Failing Tests",
                                  "/tests", {"statusFilter": "NEEDS_ATTENTION",
                                             "ownerFilter": self.user_id})
            )
        await asyncio.gather(*tasks)

    async def _fetch_count(
        self, panel_id: str, label: str, path: str, params: dict[str, Any]
    ) -> None:
        try:
            page = await self.service.list_page(path, params=params, page_size=100)
            count = len(page.items)
            panel = self.query_one(f"#{panel_id}", DashPanel)
            panel.set_count(label, count, page.has_more)
        except Exception:
            panel = self.query_one(f"#{panel_id}", DashPanel)
            panel.set_error(label)
