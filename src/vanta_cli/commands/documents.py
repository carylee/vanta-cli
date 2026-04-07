from pathlib import Path
from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)
uploads_app = typer.Typer(no_args_is_help=True, help="Manage file uploads for a document.")
links_app = typer.Typer(no_args_is_help=True, help="Manage links for a document.")
app.add_typer(uploads_app, name="uploads")
app.add_typer(links_app, name="links")

DOCUMENT_COLUMNS = [
    ("id", "ID"),
    ("category", "Category"),
    ("description", "Description"),
    ("ownerId", "Owner ID"),
]

UPLOAD_COLUMNS = [
    ("id", "ID"),
    ("fileName", "Filename"),
    ("description", "Description"),
    ("effectiveAtDate", "Effective"),
]

LINK_COLUMNS = [
    ("id", "ID"),
    ("title", "Title"),
    ("url", "URL"),
]


@app.command("list")
def list_documents(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List all documents."""
    client = VantaClient()
    items = list(client.paginate("/documents", limit=limit))
    print_list(items, DOCUMENT_COLUMNS, title="Documents")


@app.command("get")
def get_document(
    document_id: str = typer.Argument(help="Document ID."),
) -> None:
    """Get details for a specific document."""
    client = VantaClient()
    data = client.get(f"/documents/{document_id}")
    print_detail(data.get("results", data), title=f"Document: {document_id}")


@app.command("create")
def create_document(
    title: str = typer.Option(..., "--title", help="Document title."),
    description: str = typer.Option(..., "--description", help="Document description."),
    time_sensitivity: str = typer.Option(
        ..., "--time-sensitivity",
        help="When to upload: MOST_RECENT or DURING_AUDIT_WINDOW.",
    ),
    cadence: str = typer.Option(
        ..., "--cadence",
        help="Renewal cadence: P0D (never), P1D, P1W, P1M, P3M, P6M, P1Y.",
    ),
    reminder_window: str = typer.Option(
        ..., "--reminder-window",
        help="Reminder before renewal: P0D, P1D, P1W, P1M, P3M.",
    ),
    is_sensitive: bool = typer.Option(
        False, "--sensitive/--not-sensitive",
        help="Whether the document is sensitive (restricts access).",
    ),
) -> None:
    """Create a custom document."""
    client = VantaClient()
    body = {
        "title": title,
        "description": description,
        "timeSensitivity": time_sensitivity,
        "cadence": cadence,
        "reminderWindow": reminder_window,
        "isSensitive": is_sensitive,
    }
    data = client.post("/documents", json=body)
    print_detail(data.get("results", data), title="Created Document")


@app.command("delete")
def delete_document(
    document_id: str = typer.Argument(help="Document ID to delete."),
) -> None:
    """Delete a document."""
    client = VantaClient()
    client.delete(f"/documents/{document_id}")
    print_success(f"Deleted document {document_id}")


@app.command("submit")
def submit_document(
    document_id: str = typer.Argument(help="Document ID to submit."),
) -> None:
    """Submit a document for collection."""
    client = VantaClient()
    client.post(f"/documents/{document_id}/submit")
    print_success(f"Submitted document {document_id}")


@app.command("set-owner")
def set_owner(
    document_id: str = typer.Argument(help="Document ID."),
    user_id: str = typer.Option(..., "--user-id", help="User ID of the new owner."),
) -> None:
    """Set the owner of a document."""
    client = VantaClient()
    data = client.post(f"/documents/{document_id}/set-owner", json={"userId": user_id})
    print_success(f"Set owner of document {document_id} to {user_id}")


@app.command("controls")
def list_controls(
    document_id: str = typer.Argument(help="Document ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List controls linked to a document."""
    client = VantaClient()
    items = list(client.paginate(f"/documents/{document_id}/controls", limit=limit))
    print_list(
        items,
        [("id", "ID"), ("name", "Name"), ("source", "Source")],
        title=f"Controls for document {document_id}",
    )


# --- Uploads ---


@uploads_app.command("list")
def list_uploads(
    document_id: str = typer.Argument(help="Document ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List uploaded files for a document."""
    client = VantaClient()
    items = list(client.paginate(f"/documents/{document_id}/uploads", limit=limit))
    print_list(items, UPLOAD_COLUMNS, title=f"Uploads for {document_id}")


@uploads_app.command("add")
def upload_file(
    document_id: str = typer.Argument(help="Document ID."),
    file: Path = typer.Option(..., "--file", "-f", help="File to upload.", exists=True),
    effective_date: Optional[str] = typer.Option(None, "--effective-date", help="Effective date (ISO)."),
    description: Optional[str] = typer.Option(None, "--description", help="File description."),
) -> None:
    """Upload a file to a document."""
    client = VantaClient()
    fields: dict[str, str] = {}
    if effective_date:
        fields["effectiveAtDate"] = effective_date
    if description:
        fields["description"] = description
    data = client.upload(f"/documents/{document_id}/uploads", file, fields=fields)
    print_detail(data.get("results", data) if data else {"status": "uploaded"}, title="Uploaded File")


@uploads_app.command("delete")
def delete_upload(
    document_id: str = typer.Argument(help="Document ID."),
    upload_id: str = typer.Argument(help="Upload ID to delete."),
) -> None:
    """Delete an uploaded file from a document."""
    client = VantaClient()
    client.delete(f"/documents/{document_id}/uploads/{upload_id}")
    print_success(f"Deleted upload {upload_id}")


@uploads_app.command("download")
def download_upload(
    document_id: str = typer.Argument(help="Document ID."),
    upload_id: str = typer.Argument(help="Upload ID to download."),
    output: Path = typer.Option(..., "--output", "-o", help="Destination file path."),
) -> None:
    """Download an uploaded file."""
    client = VantaClient()
    dest = client.download(f"/documents/{document_id}/uploads/{upload_id}/media", output)
    print_success(f"Downloaded to {dest}")


# --- Links ---


@links_app.command("list")
def list_links(
    document_id: str = typer.Argument(help="Document ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List links for a document."""
    client = VantaClient()
    items = list(client.paginate(f"/documents/{document_id}/links", limit=limit))
    print_list(items, LINK_COLUMNS, title=f"Links for {document_id}")


@links_app.command("add")
def create_link(
    document_id: str = typer.Argument(help="Document ID."),
    url: str = typer.Option(..., "--url", help="Link URL."),
    title: str = typer.Option(..., "--title", help="Link title."),
    description: Optional[str] = typer.Option(None, "--description", help="Link description."),
    effective_date: Optional[str] = typer.Option(None, "--effective-date", help="Effective date (ISO)."),
) -> None:
    """Add a link to a document."""
    client = VantaClient()
    body: dict = {"url": url, "title": title}
    if description:
        body["description"] = description
    if effective_date:
        body["effectiveDate"] = effective_date
    data = client.post(f"/documents/{document_id}/links", json=body)
    print_detail(data.get("results", data), title="Created Link")


@links_app.command("delete")
def delete_link(
    document_id: str = typer.Argument(help="Document ID."),
    link_id: str = typer.Argument(help="Link ID to delete."),
) -> None:
    """Delete a link from a document."""
    client = VantaClient()
    client.delete(f"/documents/{document_id}/links/{link_id}")
    print_success(f"Deleted link {link_id}")
