from pathlib import Path
from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)
accounts_app = typer.Typer(no_args_is_help=True, help="Manage customer trust accounts.")
questionnaires_app = typer.Typer(no_args_is_help=True, help="Manage questionnaires.")
exports_app = typer.Typer(no_args_is_help=True, help="Manage questionnaire exports.")
tags_app = typer.Typer(no_args_is_help=True, help="Browse tag categories.")
app.add_typer(accounts_app, name="accounts")
app.add_typer(questionnaires_app, name="questionnaires")
app.add_typer(exports_app, name="exports")
app.add_typer(tags_app, name="tag-categories")

ACCOUNT_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("emailDomain", "Domain"),
]

QUESTIONNAIRE_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("createdAt", "Created"),
]


# --- Accounts ---


@accounts_app.command("list")
def list_accounts(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List customer trust accounts."""
    client = VantaClient()
    items = list(client.paginate("/customer-trust/accounts", limit=limit))
    print_list(items, ACCOUNT_COLUMNS, title="Customer Trust Accounts")


@accounts_app.command("get")
def get_account(
    account_id: str = typer.Argument(help="Account ID."),
) -> None:
    """Get a customer trust account."""
    client = VantaClient()
    data = client.get(f"/customer-trust/accounts/{account_id}")
    print_detail(data.get("results", data), title=f"Account: {account_id}")


@accounts_app.command("create")
def create_account(
    name: str = typer.Option(..., "--name", help="Account name."),
    email_domain: str = typer.Option(..., "--email-domain", help="Email domain."),
) -> None:
    """Create a customer trust account."""
    client = VantaClient()
    body = {"name": name, "emailDomain": email_domain}
    data = client.post("/customer-trust/accounts", json=body)
    print_detail(data.get("results", data), title="Created Account")


@accounts_app.command("update")
def update_account(
    account_id: str = typer.Argument(help="Account ID."),
    name: Optional[str] = typer.Option(None, "--name", help="New name."),
    email_domain: Optional[str] = typer.Option(None, "--email-domain", help="New email domain."),
) -> None:
    """Update a customer trust account."""
    client = VantaClient()
    body: dict = {}
    if name is not None:
        body["name"] = name
    if email_domain is not None:
        body["emailDomain"] = email_domain
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/customer-trust/accounts/{account_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated Account: {account_id}")


@accounts_app.command("delete")
def delete_account(
    account_id: str = typer.Argument(help="Account ID to delete."),
) -> None:
    """Delete a customer trust account."""
    client = VantaClient()
    client.delete(f"/customer-trust/accounts/{account_id}")
    print_success(f"Deleted account {account_id}")


# --- Questionnaires ---


@questionnaires_app.command("list")
def list_questionnaires(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List questionnaires."""
    client = VantaClient()
    items = list(client.paginate("/customer-trust/questionnaires", limit=limit))
    print_list(items, QUESTIONNAIRE_COLUMNS, title="Questionnaires")


@questionnaires_app.command("get")
def get_questionnaire(
    questionnaire_id: str = typer.Argument(help="Questionnaire ID."),
) -> None:
    """Get a questionnaire."""
    client = VantaClient()
    data = client.get(f"/customer-trust/questionnaires/{questionnaire_id}")
    print_detail(data.get("results", data), title=f"Questionnaire: {questionnaire_id}")


@questionnaires_app.command("update")
def update_questionnaire(
    questionnaire_id: str = typer.Argument(help="Questionnaire ID."),
    status: Optional[str] = typer.Option(
        None, "--status",
        help="New status: IN_PROGRESS, IN_REVIEW, READY_FOR_REVIEW, WAITING_ON_ANSWERS, ON_HOLD, NO_LONGER_NEEDED.",
    ),
) -> None:
    """Update a questionnaire."""
    client = VantaClient()
    body: dict = {}
    if status is not None:
        body["status"] = status
    if not body:
        raise typer.BadParameter("Provide at least one field to update.")
    data = client.patch(f"/customer-trust/questionnaires/{questionnaire_id}", json=body)
    print_detail(data.get("results", data), title=f"Updated Questionnaire: {questionnaire_id}")


@questionnaires_app.command("delete")
def delete_questionnaire(
    questionnaire_id: str = typer.Argument(help="Questionnaire ID to delete."),
) -> None:
    """Delete a questionnaire."""
    client = VantaClient()
    client.delete(f"/customer-trust/questionnaires/{questionnaire_id}")
    print_success(f"Deleted questionnaire {questionnaire_id}")


@questionnaires_app.command("approve")
def approve_questionnaire(
    questionnaire_id: str = typer.Argument(help="Questionnaire ID."),
) -> None:
    """Approve a questionnaire."""
    client = VantaClient()
    client.post(f"/customer-trust/questionnaires/{questionnaire_id}/approve")
    print_success(f"Approved questionnaire {questionnaire_id}")


@questionnaires_app.command("complete")
def complete_questionnaire(
    questionnaire_id: str = typer.Argument(help="Questionnaire ID."),
) -> None:
    """Mark a questionnaire as complete."""
    client = VantaClient()
    client.post(f"/customer-trust/questionnaires/{questionnaire_id}/complete")
    print_success(f"Completed questionnaire {questionnaire_id}")


@questionnaires_app.command("from-file")
def create_from_file(
    file: Path = typer.Option(..., "--file", "-f", help="Questionnaire file to upload.", exists=True),
) -> None:
    """Create a questionnaire from a file upload."""
    client = VantaClient()
    data = client.upload("/customer-trust/questionnaires/file", file)
    print_detail(data.get("results", data) if data else {"status": "created"}, title="Created Questionnaire")


@questionnaires_app.command("from-website")
def create_from_website(
    url: str = typer.Option(..., "--url", help="Website URL to create questionnaire from."),
) -> None:
    """Create a questionnaire from a website URL."""
    client = VantaClient()
    data = client.post("/customer-trust/questionnaires/website", json={"url": url})
    print_detail(data.get("results", data), title="Created Questionnaire")


@questionnaires_app.command("assignable-users")
def list_assignable_users(
) -> None:
    """List users assignable to questionnaires."""
    client = VantaClient()
    data = client.get("/customer-trust/questionnaires/assignable-users")
    items = data.get("results", data)
    if isinstance(items, dict):
        items = items.get("data", [items])
    print_list(items, [("id", "ID"), ("displayName", "Name"), ("emailAddress", "Email")], title="Assignable Users")


# --- Exports ---


@exports_app.command("create")
def create_export(
    questionnaire_id: str = typer.Option(..., "--questionnaire-id", help="Questionnaire ID to export."),
) -> None:
    """Create a questionnaire export (async)."""
    client = VantaClient()
    data = client.post("/customer-trust/questionnaires/exports", json={"questionnaireId": questionnaire_id})
    print_detail(data.get("results", data), title="Export Created")


@exports_app.command("get")
def get_export(
    export_id: str = typer.Argument(help="Export ID to check status."),
) -> None:
    """Get export status."""
    client = VantaClient()
    data = client.get(f"/customer-trust/questionnaires/exports/{export_id}")
    print_detail(data.get("results", data), title=f"Export: {export_id}")


# --- Tag Categories ---


@tags_app.command("list")
def list_tag_categories(
) -> None:
    """List tag categories."""
    client = VantaClient()
    data = client.get("/customer-trust/tag-categories")
    items = data.get("results", data)
    if isinstance(items, dict):
        items = items.get("data", [items])
    print_list(items, [("id", "ID"), ("name", "Name")], title="Tag Categories")


@tags_app.command("get")
def get_tag_category(
    category_id: str = typer.Argument(help="Tag category ID."),
) -> None:
    """Get a tag category."""
    client = VantaClient()
    data = client.get(f"/customer-trust/tag-categories/{category_id}")
    print_detail(data.get("results", data), title=f"Tag Category: {category_id}")
