from pathlib import Path
from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)
findings_app = typer.Typer(no_args_is_help=True, help="Manage vendor findings.")
documents_app = typer.Typer(no_args_is_help=True, help="Manage vendor documents.")
reviews_app = typer.Typer(no_args_is_help=True, help="View vendor security reviews.")
app.add_typer(findings_app, name="findings")
app.add_typer(documents_app, name="documents")
app.add_typer(reviews_app, name="security-reviews")

VENDOR_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("category.displayName", "Category"),
    ("inherentRiskLevel", "Risk"),
]

FINDING_COLUMNS = [
    ("id", "ID"),
    ("title", "Title"),
    ("riskStatus", "Risk Status"),
    ("severity", "Severity"),
]

REVIEW_COLUMNS = [
    ("id", "ID"),
    ("decision", "Decision"),
    ("createdAt", "Created"),
]


@app.command("list")
def list_vendors(
    name: Optional[str] = typer.Option(None, "--name", "-q", help="Filter by name (partial, case-insensitive)."),
    status: Optional[str] = typer.Option(
        None, "--status", "-s", help="Filter by status: MANAGED, ARCHIVED, IN_PROCUREMENT."
    ),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List all vendors."""
    client = VantaClient()
    params: dict = {}
    if name:
        params["name"] = name
    if status:
        params["statusMatchesAny"] = status
    items = list(client.paginate("/vendors", params=params, limit=limit))
    print_list(items, VENDOR_COLUMNS, title="Vendors")


@app.command("get")
def get_vendor(
    vendor_id: str = typer.Argument(help="Vendor ID."),
) -> None:
    """Get details for a specific vendor."""
    client = VantaClient()
    data = client.get(f"/vendors/{vendor_id}")
    print_detail(data.get("results", data), title=f"Vendor: {vendor_id}")


@app.command("create")
def create_vendor(
    name: str = typer.Option(..., "--name", help="Vendor display name."),
    website: Optional[str] = typer.Option(None, "--website", help="Vendor website URL."),
    category: Optional[str] = typer.Option(None, "--category", help="Vendor category."),
    status: Optional[str] = typer.Option(None, "--status", help="Status: MANAGED, ARCHIVED, IN_PROCUREMENT."),
    services: Optional[str] = typer.Option(None, "--services", help="Services provided."),
    risk: Optional[str] = typer.Option(None, "--inherent-risk", help="Risk level: CRITICAL, HIGH, MEDIUM, LOW, UNSCORED."),
    notes: Optional[str] = typer.Option(None, "--notes", help="Additional notes."),
) -> None:
    """Create a new vendor."""
    client = VantaClient()
    body: dict = {"name": name}
    if website:
        body["websiteUrl"] = website
    if category:
        body["category"] = category
    if status:
        body["status"] = status
    if services:
        body["servicesProvided"] = services
    if risk:
        body["inherentRiskLevel"] = risk
    if notes:
        body["additionalNotes"] = notes
    data = client.post("/vendors", json=body)
    print_detail(data.get("results", data), title="Created Vendor")


@app.command("update")
def update_vendor(
    vendor_id: str = typer.Argument(help="Vendor ID."),
    name: Optional[str] = typer.Option(None, "--name", help="New name."),
    website: Optional[str] = typer.Option(None, "--website", help="New website URL."),
    category: Optional[str] = typer.Option(None, "--category", help="New category."),
    status: Optional[str] = typer.Option(None, "--status", help="New status."),
    services: Optional[str] = typer.Option(None, "--services", help="New services description."),
    risk: Optional[str] = typer.Option(None, "--inherent-risk", help="New risk level."),
    notes: Optional[str] = typer.Option(None, "--notes", help="New notes."),
) -> None:
    """Update a vendor's metadata."""
    client = VantaClient()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if website is not None:
        body["websiteUrl"] = website
    if category is not None:
        body["category"] = category
    if status is not None:
        body["status"] = status
    if services is not None:
        body["servicesProvided"] = services
    if risk is not None:
        body["inherentRiskLevel"] = risk
    if notes is not None:
        body["additionalNotes"] = notes
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/vendors/{vendor_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated Vendor: {vendor_id}")


@app.command("delete")
def delete_vendor(
    vendor_id: str = typer.Argument(help="Vendor ID to delete."),
) -> None:
    """Delete a vendor."""
    client = VantaClient()
    client.delete(f"/vendors/{vendor_id}")
    print_success(f"Deleted vendor {vendor_id}")


@app.command("set-status")
def set_status(
    vendor_id: str = typer.Argument(help="Vendor ID."),
    status: str = typer.Option(..., "--status", "-s", help="New status: MANAGED, ARCHIVED, IN_PROCUREMENT."),
) -> None:
    """Set a vendor's status."""
    client = VantaClient()
    # This endpoint uses multipart/form-data with just a status field
    resp = client._http.post(
        f"/vendors/{vendor_id}/set-status",
        headers=client._headers(),
        data={"status": status},
    )
    client._handle_response(resp)
    print_success(f"Set vendor {vendor_id} status to {status}")


# --- Findings ---


@findings_app.command("list")
def list_findings(
    vendor_id: str = typer.Argument(help="Vendor ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List findings for a vendor."""
    client = VantaClient()
    items = list(client.paginate(f"/vendors/{vendor_id}/findings", limit=limit))
    print_list(items, FINDING_COLUMNS, title=f"Findings for {vendor_id}")


@findings_app.command("create")
def create_finding(
    vendor_id: str = typer.Argument(help="Vendor ID."),
    title: str = typer.Option(..., "--title", help="Finding title."),
    description: Optional[str] = typer.Option(None, "--description", help="Finding description."),
    severity: Optional[str] = typer.Option(None, "--severity", help="Severity: CRITICAL, HIGH, MEDIUM, LOW."),
    risk_status: Optional[str] = typer.Option(None, "--risk-status", help="Risk status: ACCEPT, REMEDIATE, NONE."),
) -> None:
    """Create a finding for a vendor."""
    client = VantaClient()
    body: dict = {"title": title}
    if description:
        body["description"] = description
    if severity:
        body["severity"] = severity
    if risk_status:
        body["riskStatus"] = risk_status
    data = client.post(f"/vendors/{vendor_id}/findings", json=body)
    print_detail(data.get("results", data), title="Created Finding")


@findings_app.command("update")
def update_finding(
    vendor_id: str = typer.Argument(help="Vendor ID."),
    finding_id: str = typer.Argument(help="Finding ID."),
    title: Optional[str] = typer.Option(None, "--title", help="New title."),
    description: Optional[str] = typer.Option(None, "--description", help="New description."),
    risk_status: Optional[str] = typer.Option(None, "--risk-status", help="New risk status."),
) -> None:
    """Update a vendor finding."""
    client = VantaClient()
    body: dict = {}
    if title is not None:
        body["title"] = title
    if description is not None:
        body["description"] = description
    if risk_status is not None:
        body["riskStatus"] = risk_status
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/vendors/{vendor_id}/findings/{finding_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated Finding: {finding_id}")


@findings_app.command("delete")
def delete_finding(
    vendor_id: str = typer.Argument(help="Vendor ID."),
    finding_id: str = typer.Argument(help="Finding ID to delete."),
) -> None:
    """Delete a vendor finding."""
    client = VantaClient()
    client.delete(f"/vendors/{vendor_id}/findings/{finding_id}")
    print_success(f"Deleted finding {finding_id}")


# --- Documents ---


@documents_app.command("list")
def list_vendor_documents(
    vendor_id: str = typer.Argument(help="Vendor ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List documents for a vendor."""
    client = VantaClient()
    items = list(client.paginate(f"/vendors/{vendor_id}/documents", limit=limit))
    print_list(
        items,
        [("id", "ID"), ("title", "Title"), ("type", "Type"), ("description", "Description")],
        title=f"Documents for vendor {vendor_id}",
    )


@documents_app.command("upload")
def upload_vendor_document(
    vendor_id: str = typer.Argument(help="Vendor ID."),
    file: Path = typer.Option(..., "--file", "-f", help="File to upload.", exists=True),
    doc_type: str = typer.Option(..., "--type", "-t", help="Document type."),
    title: Optional[str] = typer.Option(None, "--title", help="Document title."),
    description: Optional[str] = typer.Option(None, "--description", help="Document description."),
) -> None:
    """Upload a document for a vendor."""
    client = VantaClient()
    fields: dict[str, str] = {"type": doc_type}
    if title:
        fields["title"] = title
    if description:
        fields["description"] = description
    data = client.upload(f"/vendors/{vendor_id}/documents", file, fields=fields)
    print_detail(data.get("results", data) if data else {"status": "uploaded"}, title="Uploaded Document")


# --- Security Reviews ---


@reviews_app.command("list")
def list_reviews(
    vendor_id: str = typer.Argument(help="Vendor ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List security reviews for a vendor."""
    client = VantaClient()
    items = list(client.paginate(f"/vendors/{vendor_id}/security-reviews", limit=limit))
    print_list(items, REVIEW_COLUMNS, title=f"Security Reviews for {vendor_id}")


@reviews_app.command("get")
def get_review(
    vendor_id: str = typer.Argument(help="Vendor ID."),
    review_id: str = typer.Argument(help="Security review ID."),
) -> None:
    """Get a specific security review."""
    client = VantaClient()
    data = client.get(f"/vendors/{vendor_id}/security-reviews/{review_id}")
    print_detail(data.get("results", data), title=f"Security Review: {review_id}")
