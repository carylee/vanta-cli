"""Sidebar tree navigation widget."""

from __future__ import annotations

from dataclasses import dataclass

from textual.message import Message
from textual.widgets import Tree


@dataclass
class ResourceGroup:
    """Definition of a navigable resource group."""

    label: str
    key: str
    api_path: str
    columns: list[tuple[str, str]]


RESOURCE_GROUPS: list[ResourceGroup] = [
    ResourceGroup("Tests", "tests", "/tests", [
        ("id", "ID"), ("name", "Name"), ("status", "Status"), ("category", "Category"),
    ]),
    ResourceGroup("Controls", "controls", "/controls", [
        ("id", "ID"), ("name", "Name"), ("status", "Status"),
    ]),
    ResourceGroup("Frameworks", "frameworks", "/frameworks", [
        ("id", "ID"), ("name", "Name"),
    ]),
    ResourceGroup("People", "people", "/people", [
        ("id", "ID"), ("name.display", "Name"), ("email", "Email"), ("employment.status", "Status"),
    ]),
    ResourceGroup("Policies", "policies", "/policies", [
        ("id", "ID"), ("name", "Name"),
    ]),
    ResourceGroup("Vendors", "vendors", "/vendors", [
        ("id", "ID"), ("name", "Name"), ("category.displayName", "Category"), ("riskLevel", "Risk"),
    ]),
    ResourceGroup("Documents", "documents", "/documents", [
        ("id", "ID"), ("name", "Name"),
    ]),
    ResourceGroup("Groups", "groups", "/groups", [
        ("id", "ID"), ("name", "Name"),
    ]),
    ResourceGroup("Vulnerabilities", "vulnerabilities", "/vulnerabilities", [
        ("id", "ID"), ("title", "Title"), ("severity", "Severity"), ("status", "Status"),
    ]),
    ResourceGroup("Vulnerable Assets", "vulnerable-assets", "/vulnerable-assets", [
        ("id", "ID"), ("displayName", "Name"),
    ]),
    ResourceGroup("Vuln Remediations", "vuln-remediations", "/vulnerability-remediations", [
        ("id", "ID"), ("title", "Title"),
    ]),
    ResourceGroup("Trust Centers", "trust-centers", "/trust-center", []),
    ResourceGroup("Customer Trust", "customer-trust", "/customer-trust/accounts", [
        ("id", "ID"), ("name", "Name"),
    ]),
    ResourceGroup("Integrations", "integrations", "/integrations", [
        ("integrationId", "ID"), ("displayName", "Name"),
    ]),
    ResourceGroup("Risk Scenarios", "risk-scenarios", "/risk-scenarios", [
        ("riskId", "ID"), ("description", "Description"), ("treatment", "Treatment"),
    ]),
    ResourceGroup("Discovered Vendors", "discovered-vendors", "/discovered-vendors", [
        ("id", "ID"), ("name", "Name"),
    ]),
    ResourceGroup("Monitored Computers", "monitored-computers", "/monitored-computers", [
        ("id", "ID"), ("serialNumber", "Serial"), ("operatingSystem.type", "OS"),
    ]),
    ResourceGroup("Users", "users", "/users", [
        ("id", "ID"), ("displayName", "Name"), ("email", "Email"),
    ]),
    ResourceGroup("Vendor Risk Attributes", "vendor-risk-attrs", "/vendor-risk-attributes", [
        ("id", "ID"), ("name", "Name"),
    ]),
]


class Sidebar(Tree[ResourceGroup]):
    """Tree navigation for Vanta resource groups."""

    class Selected(Message):
        """Emitted when a resource group is selected."""

        def __init__(self, group: ResourceGroup) -> None:
            super().__init__()
            self.group = group

    def __init__(self) -> None:
        super().__init__("Vanta", id="sidebar")
        self.guide_depth = 3

    def on_mount(self) -> None:
        for group in RESOURCE_GROUPS:
            self.root.add_leaf(group.label, data=group)
        self.root.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data is not None:
            self.post_message(self.Selected(event.node.data))
