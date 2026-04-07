"""Vanta TUI application built with Textual."""

from __future__ import annotations

from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Static

from vanta_cli.tui.screens.detail import DetailScreen
from vanta_cli.tui.screens.resource_list import ResourceListScreen
from vanta_cli.tui.screens.tests import TestEntityScreen
from vanta_cli.tui.service import AsyncVantaService
from vanta_cli.tui.widgets.breadcrumb import Breadcrumb
from vanta_cli.tui.widgets.sidebar import ResourceGroup, Sidebar


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
    #welcome {
        padding: 2 4;
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
    ]

    def __init__(self) -> None:
        super().__init__()
        self.service = AsyncVantaService()
        self.breadcrumb = Breadcrumb()

    def compose(self) -> ComposeResult:
        yield Header()
        yield self.breadcrumb
        with Horizontal():
            yield Sidebar()
            with Static(id="main-area"):
                yield Static(
                    "Select a resource group from the sidebar to browse.\n\n"
                    "Vim-style navigation:\n"
                    "  [bold]j/k[/bold]      Move down/up\n"
                    "  [bold]h[/bold]        Go back\n"
                    "  [bold]l[/bold]/[bold]Enter[/bold]  Drill in / view details\n"
                    "  [bold]g/G[/bold]      Jump to top/bottom\n"
                    "  [bold]Space[/bold]    Load more results\n"
                    "  [bold]/[/bold]        Focus filter\n"
                    "  [bold]q[/bold]        Quit\n\n"
                    "Test entities:\n"
                    "  [bold]d[/bold]        Deactivate selected entity\n"
                    "  [bold]r[/bold]        Reactivate selected entity\n"
                    "  [bold]1/2/0[/bold]    Filter: Failing / Deactivated / All",
                    id="welcome",
                )
        yield Footer()

    def on_sidebar_selected(self, message: Sidebar.Selected) -> None:
        """Navigate to a resource group list."""
        group = message.group
        if group.key == "tests":
            # Tests get special handling — drill into entities
            screen = ResourceListScreen(group, self.service)
            self.push_screen(screen)
            self.breadcrumb.push(group.label)
        elif group.columns:
            screen = ResourceListScreen(group, self.service)
            self.push_screen(screen)
            self.breadcrumb.push(group.label)
        else:
            self.notify(f"{group.label} not yet browsable in TUI", severity="warning")

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
            screen = DetailScreen(item, title=f"{group.label}: {item_id}")
            self.push_screen(screen)
            self.breadcrumb.push(str(item_id))

    def on_screen_resume(self) -> None:
        """Pop breadcrumb when returning from a screen."""
        self.breadcrumb.pop()
