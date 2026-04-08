"""Sidebar tree navigation widget."""

from __future__ import annotations

from dataclasses import dataclass, field

from textual.binding import Binding
from textual.message import Message
from textual.widgets import Tree


@dataclass
class FilterDef:
    """Definition of a server-side filter for an API endpoint."""

    label: str  # Display label, e.g. "Status"
    param: str  # API query param, e.g. "statusFilter"
    options: list[tuple[str | None, str]]  # (value, display_label) pairs; None means no filter


@dataclass
class ResourceGroup:
    """Definition of a navigable resource group."""

    label: str
    key: str
    api_path: str
    columns: list[tuple[str, str]]
    filters: list[FilterDef] = field(default_factory=list)


RESOURCE_GROUPS: list[ResourceGroup] = [
    ResourceGroup("Tests", "tests", "/tests", [
        ("id", "ID"), ("name", "Name"), ("status", "Status"), ("category", "Category"),
    ], filters=[
        FilterDef("Status", "statusFilter", [
            (None, "All"),
            ("NEEDS_ATTENTION", "Failing"),
            ("OK", "Passing"),
            ("DEACTIVATED", "Deactivated"),
        ]),
    ]),
    ResourceGroup("Controls", "controls", "/controls", [
        ("externalId", "ID"), ("name", "Name"), ("owner.displayName", "Owner"),
    ]),
    ResourceGroup("Frameworks", "frameworks", "/frameworks", [
        ("id", "ID"), ("name", "Name"),
        ("numControlsCompleted", "Controls OK"), ("numControlsTotal", "Controls Total"),
        ("numTestsPassing", "Tests OK"), ("numTestsTotal", "Tests Total"),
    ]),
    ResourceGroup("People", "people", "/people", [
        ("id", "ID"), ("name.display", "Name"), ("email", "Email"), ("employment.status", "Status"),
    ], filters=[
        FilterDef("Status", "employmentStatus", [
            (None, "All"),
            ("CURRENT", "Current"),
            ("FORMER", "Former"),
            ("INACTIVE", "Inactive"),
        ]),
    ]),
    ResourceGroup("Policies", "policies", "/policies", [
        ("id", "ID"), ("name", "Name"), ("status", "Status"),
    ]),
    ResourceGroup("Vendors", "vendors", "/vendors", [
        ("id", "ID"), ("name", "Name"), ("category.displayName", "Category"),
        ("inherentRiskLevel", "Risk"), ("status", "Status"),
    ], filters=[
        FilterDef("Status", "statusMatchesAny", [
            (None, "All"),
            ("MANAGED", "Managed"),
            ("ARCHIVED", "Archived"),
            ("IN_PROCUREMENT", "In Procurement"),
        ]),
    ]),
    ResourceGroup("Documents", "documents", "/documents", [
        ("id", "ID"), ("title", "Title"), ("category", "Category"), ("uploadStatus", "Status"),
    ]),
    ResourceGroup("Groups", "groups", "/groups", [
        ("id", "ID"), ("name", "Name"),
    ]),
    ResourceGroup("Vulnerabilities", "vulnerabilities", "/vulnerabilities", [
        ("id", "ID"), ("title", "Title"), ("severity", "Severity"), ("status", "Status"),
    ], filters=[
        FilterDef("Severity", "severity", [
            (None, "All"),
            ("CRITICAL", "Critical"),
            ("HIGH", "High"),
            ("MEDIUM", "Medium"),
            ("LOW", "Low"),
        ]),
        FilterDef("Active", "isDeactivated", [
            ("false", "Active"),
            ("true", "Deactivated"),
            (None, "All"),
        ]),
    ]),
    ResourceGroup("Vulnerable Assets", "vulnerable-assets", "/vulnerable-assets", [
        ("id", "ID"), ("name", "Name"), ("assetType", "Type"),
    ]),
    ResourceGroup("Vuln Remediations", "vuln-remediations", "/vulnerability-remediations", [
        ("id", "ID"), ("severity", "Severity"), ("slaDeadlineDate", "SLA Deadline"),
        ("remediationDate", "Remediated"),
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
        ("id", "ID"), ("name", "Name"), ("source", "Source"), ("numberOfAccounts", "Accounts"),
    ]),
    ResourceGroup("Monitored Computers", "monitored-computers", "/monitored-computers", [
        ("id", "ID"), ("serialNumber", "Serial"), ("operatingSystem.type", "OS"),
        ("owner.displayName", "Owner"),
    ]),
    ResourceGroup("Users", "users", "/users", [
        ("id", "ID"), ("displayName", "Name"), ("email", "Email"), ("isActive", "Active"),
    ]),
    ResourceGroup("Vendor Risk Attributes", "vendor-risk-attrs", "/vendor-risk-attributes", [
        ("id", "ID"), ("name", "Name"), ("riskLevel", "Risk"), ("enabled", "Enabled"),
    ]),
]


class Sidebar(Tree[ResourceGroup]):
    """Tree navigation for Vanta resource groups."""

    BINDINGS = [
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
        Binding("l", "select_cursor", "Open", show=False),
    ]

    class Selected(Message):
        """Emitted when a resource group is selected."""

        def __init__(self, group: ResourceGroup) -> None:
            super().__init__()
            self.group = group

    def __init__(self) -> None:
        super().__init__("Vanta", id="sidebar")
        self.guide_depth = 3

    def on_mount(self) -> None:
        # Add changeset entry at the top
        changeset_group = ResourceGroup("Staged Changes", "changeset", "", [])
        self.root.add_leaf(changeset_group.label, data=changeset_group)
        for group in RESOURCE_GROUPS:
            self.root.add_leaf(group.label, data=group)
        self.root.expand()

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data is not None:
            self.post_message(self.Selected(event.node.data))
