"""Vanta TUI application built with Textual."""

from __future__ import annotations

from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Static

from vanta_cli.config import load_user_config
from vanta_cli.changeset import CHANGESET_FILE
from vanta_cli.tui.screens.changeset import ChangesetScreen
from vanta_cli.tui.screens.detail import DetailScreen
from vanta_cli.tui.screens.resource_list import ResourceListScreen
from vanta_cli.tui.screens.tests import TestEntityScreen
from vanta_cli.tui.service import AsyncVantaService
from vanta_cli.tui.widgets.breadcrumb import Breadcrumb
from vanta_cli.tui.widgets.dashboard import Dashboard
from vanta_cli.tui.widgets.sidebar import ResourceGroup, RESOURCE_GROUPS, Sidebar


def _find_group(key: str) -> ResourceGroup | None:
    for g in RESOURCE_GROUPS:
        if g.key == key:
            return g
    return None


class VantaTUI(App):
    """Interactive TUI for browsing Vanta compliance data."""

    TITLE = "Vanta"

    CSS = """
    #sidebar {
        width: 28;
        dock: left;
        height: 100%;
        border-right: tall $accent;
    }
    #main-area {
        width: 1fr;
        height: 100%;
    }
    .screen-title {
        dock: top;
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    #filter-bar {
        dock: top;
        height: 3;
        padding: 0 1;
    }
    #filter-label {
        width: 9;
        height: 3;
    }
    #status-filter {
        height: 3;
        layout: horizontal;
    }
    #status-filter RadioButton {
        height: 1;
        width: auto;
        margin-right: 2;
    }
    #status-bar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    #detail-content {
        padding: 1 2;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("1", "my_tests", "My Tests"),
        Binding("2", "code_changes", "Code Changes"),
        Binding("3", "critical_vulns", "Vulns"),
        Binding("4", "risk_review", "Risk Review"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.service = AsyncVantaService()
        self.breadcrumb = Breadcrumb()
        user_config = load_user_config()
        self.user_id = user_config.user_id

    def compose(self) -> ComposeResult:
        yield Header()
        yield self.breadcrumb
        with Horizontal():
            yield Sidebar()
            with Static(id="main-area"):
                yield Dashboard(self.service, user_id=self.user_id)
        yield Footer()

    # --- Quick action shortcuts ---

    def action_my_tests(self) -> None:
        group = _find_group("tests")
        if not group:
            return
        params: dict[str, str] = {"statusFilter": "NEEDS_ATTENTION"}
        if self.user_id:
            params["ownerFilter"] = self.user_id
        screen = ResourceListScreen(group, self.service, params=params)
        self.push_screen(screen)
        self.breadcrumb.push("My Failing Tests" if self.user_id else "Tests Needing Attention")

    def action_code_changes(self) -> None:
        test_id = "github-code-change-automated-checks-enabled"
        screen = TestEntityScreen(test_id, "Code Changes", self.service)
        self.push_screen(screen)
        self.breadcrumb.push("Code Changes")

    def action_critical_vulns(self) -> None:
        group = _find_group("vulnerabilities")
        if not group:
            return
        screen = ResourceListScreen(
            group, self.service,
            params={"severity": "CRITICAL", "isDeactivated": "false"},
        )
        self.push_screen(screen)
        self.breadcrumb.push("Critical Vulnerabilities")

    def action_risk_review(self) -> None:
        group = _find_group("risk-scenarios")
        if not group:
            return
        screen = ResourceListScreen(group, self.service)
        self.push_screen(screen)
        self.breadcrumb.push("Risk Scenarios")

    # --- Navigation ---

    def on_sidebar_selected(self, message: Sidebar.Selected) -> None:
        """Navigate to a resource group list."""
        group = message.group
        if group.key == "changeset":
            self._open_changeset()
        elif group.key == "tests":
            screen = ResourceListScreen(group, self.service)
            self.push_screen(screen)
            self.breadcrumb.push(group.label)
        elif group.columns:
            screen = ResourceListScreen(group, self.service)
            self.push_screen(screen)
            self.breadcrumb.push(group.label)
        else:
            self.notify(f"{group.label} not yet browsable in TUI", severity="warning")

    def _open_changeset(self) -> None:
        """Open the changeset review screen."""
        from vanta_cli.client import VantaClient
        from vanta_cli.config import Settings

        def apply_change(change: dict) -> bool:
            """Apply a single change using the default profile."""
            try:
                settings = Settings.load(profile="default")
                client = VantaClient(settings=settings)
                method = change["method"]
                path = change["path"]
                body = change.get("body")
                if method == "POST":
                    client.post(path, json=body)
                elif method == "PATCH":
                    client.patch(path, json=body)
                elif method == "DELETE":
                    client.delete(path)
                elif method == "PUT":
                    client.put(path, json=body)
                return True
            except Exception:
                return False

        screen = ChangesetScreen(
            changeset_file=CHANGESET_FILE,
            apply_fn=apply_change,
        )
        self.push_screen(screen)
        self.breadcrumb.push("Staged Changes")

    def on_resource_list_screen_row_selected(
        self, message: ResourceListScreen.RowSelected
    ) -> None:
        """Handle row selection — for tests, show entities; otherwise show detail."""
        group = message.group
        item = message.item
        if group.key == "tests":
            test_id = item.get("id", "")
            test_name = item.get("name", test_id)
            screen = TestEntityScreen(test_id, test_name, self.service)
            self.push_screen(screen)
            self.breadcrumb.push(test_name)
        else:
            item_id = item.get("id") or item.get("riskId") or item.get("integrationId") or "detail"
            self.breadcrumb.push(str(item_id))
            self._open_detail(group, item_id)

    @work
    async def _open_detail(self, group: ResourceGroup, item_id: str) -> None:
        """Fetch full resource detail and open the detail screen."""
        full_item = await self.service.get(f"{group.api_path}/{item_id}")
        screen = DetailScreen(
            full_item,
            title=f"{group.label}: {item_id}",
            service=self.service,
            resource_type=group.key,
        )
        self.push_screen(screen)

    def on_screen_resume(self) -> None:
        """Pop breadcrumb when returning from a screen."""
        self.breadcrumb.pop()
