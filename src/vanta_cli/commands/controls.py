from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)
documents_app = typer.Typer(no_args_is_help=True, help="Manage documents linked to a control.")
tests_app = typer.Typer(no_args_is_help=True, help="Manage tests linked to a control.")
library_app = typer.Typer(no_args_is_help=True, help="Browse and add controls from the Vanta library.")
app.add_typer(documents_app, name="documents")
app.add_typer(tests_app, name="tests")
app.add_typer(library_app, name="library")

CONTROL_COLUMNS = [
    ("id", "ID"),
    ("externalId", "External ID"),
    ("name", "Name"),
    ("source", "Source"),
    ("domains", "Domains"),
    ("owner.emailAddress", "Owner"),
]

DOCUMENT_COLUMNS = [
    ("id", "ID"),
    ("category", "Category"),
    ("description", "Description"),
]

TEST_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("category", "Category"),
]


@app.command("list")
def list_controls(
    framework: Optional[str] = typer.Option(None, "--framework", help="Filter by framework ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List all controls."""
    client = VantaClient()
    params: dict = {}
    if framework:
        params["frameworkMatchesAny"] = framework
    items = list(client.paginate("/controls", params=params, limit=limit))
    print_list(items, CONTROL_COLUMNS, title="Controls")


@app.command("get")
def get_control(
    control_id: str = typer.Argument(help="Control ID."),
) -> None:
    """Get details for a specific control."""
    client = VantaClient()
    data = client.get(f"/controls/{control_id}")
    print_detail(data.get("results", data), title=f"Control: {control_id}")


@app.command("create")
def create_control(
    name: str = typer.Option(..., "--name", help="Control name."),
    external_id: str = typer.Option(..., "--external-id", help="External ID for the control."),
    description: str = typer.Option(..., "--description", help="Control description."),
    effective_date: str = typer.Option(..., "--effective-date", help="Effective date (ISO format)."),
    domain: str = typer.Option(..., "--domain", help="Control domain/category."),
) -> None:
    """Create a custom control."""
    client = VantaClient()
    body = {
        "name": name,
        "externalId": external_id,
        "description": description,
        "effectiveDate": effective_date,
        "domain": domain,
    }
    data = client.post("/controls", json=body)
    print_detail(data.get("results", data), title="Created Control")


@app.command("update")
def update_control(
    control_id: str = typer.Argument(help="Control ID to update."),
    name: Optional[str] = typer.Option(None, "--name", help="New name."),
    external_id: Optional[str] = typer.Option(None, "--external-id", help="New external ID."),
    description: Optional[str] = typer.Option(None, "--description", help="New description."),
    domain: Optional[str] = typer.Option(None, "--domain", help="New domain."),
    note: Optional[str] = typer.Option(None, "--note", help="New note."),
) -> None:
    """Update a control's metadata."""
    client = VantaClient()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if external_id is not None:
        body["externalId"] = external_id
    if description is not None:
        body["description"] = description
    if domain is not None:
        body["domain"] = domain
    if note is not None:
        body["note"] = note
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/controls/{control_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated Control: {control_id}")


@app.command("delete")
def delete_control(
    control_id: str = typer.Argument(help="Control ID to deactivate."),
) -> None:
    """Deactivate a control."""
    client = VantaClient()
    client.delete(f"/controls/{control_id}")
    print_success(f"Deactivated control {control_id}")


@app.command("set-owner")
def set_owner(
    control_id: str = typer.Argument(help="Control ID."),
    user_id: str = typer.Option(..., "--user-id", help="User ID of the new owner."),
) -> None:
    """Set the owner of a control."""
    client = VantaClient()
    data = client.post(f"/controls/{control_id}/set-owner", json={"userId": user_id})
    print_detail(data.get("results", data), title=f"Control: {control_id}")


@app.command("add-document")
def add_document(
    control_id: str = typer.Argument(help="Control ID."),
    document_id: str = typer.Option(..., "--document-id", help="Document ID to link."),
) -> None:
    """Link a document to a control."""
    client = VantaClient()
    client.post(f"/controls/{control_id}/add-document-to-control", json={"documentId": document_id})
    print_success(f"Linked document {document_id} to control {control_id}")


@app.command("add-test")
def add_test(
    control_id: str = typer.Argument(help="Control ID."),
    test_id: str = typer.Option(..., "--test-id", help="Test ID to link."),
) -> None:
    """Link a test to a control."""
    client = VantaClient()
    client.post(f"/controls/{control_id}/add-test-to-control", json={"testId": test_id})
    print_success(f"Linked test {test_id} to control {control_id}")


# --- Nested: documents ---


@documents_app.command("list")
def list_documents(
    control_id: str = typer.Argument(help="Control ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List documents linked to a control."""
    client = VantaClient()
    items = list(client.paginate(f"/controls/{control_id}/documents", limit=limit))
    print_list(items, DOCUMENT_COLUMNS, title=f"Documents for {control_id}")


@documents_app.command("remove")
def remove_document(
    control_id: str = typer.Argument(help="Control ID."),
    document_id: str = typer.Argument(help="Document ID to unlink."),
) -> None:
    """Remove a document from a control."""
    client = VantaClient()
    client.delete(f"/controls/{control_id}/documents/{document_id}")
    print_success(f"Removed document {document_id} from control {control_id}")


# --- Nested: tests ---


@tests_app.command("list")
def list_tests(
    control_id: str = typer.Argument(help="Control ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List tests linked to a control."""
    client = VantaClient()
    items = list(client.paginate(f"/controls/{control_id}/tests", limit=limit))
    print_list(items, TEST_COLUMNS, title=f"Tests for {control_id}")


@tests_app.command("remove")
def remove_test(
    control_id: str = typer.Argument(help="Control ID."),
    test_id: str = typer.Argument(help="Test ID to unlink."),
) -> None:
    """Remove a test from a control."""
    client = VantaClient()
    client.delete(f"/controls/{control_id}/tests/{test_id}")
    print_success(f"Removed test {test_id} from control {control_id}")


# --- Nested: library ---


@library_app.command("list")
def list_library(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """Browse the Vanta controls library."""
    client = VantaClient()
    items = list(client.paginate("/controls/controls-library", limit=limit))
    print_list(items, CONTROL_COLUMNS, title="Controls Library")


@library_app.command("add")
def add_from_library(
    control_id: str = typer.Argument(help="Library control ID to add."),
) -> None:
    """Add a control from the Vanta library to your organization."""
    client = VantaClient()
    data = client.post("/controls/add-from-library", json={"controlId": control_id})
    print_detail(data.get("results", data), title="Added Control")
