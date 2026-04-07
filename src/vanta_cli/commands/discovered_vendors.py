from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)

VENDOR_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("source", "Source"),
    ("numberOfAccounts", "Accounts"),
    ("discoveredDate", "Discovered"),
]


@app.command("list")
def list_discovered_vendors(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List discovered vendors."""
    client = VantaClient()
    items = list(client.paginate("/discovered-vendors", limit=limit))
    print_list(items, VENDOR_COLUMNS, title="Discovered Vendors")


@app.command("accounts")
def list_accounts(
    vendor_id: str = typer.Argument(help="Discovered vendor ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List accounts for a discovered vendor."""
    client = VantaClient()
    items = list(client.paginate(f"/discovered-vendors/{vendor_id}/accounts", limit=limit))
    print_list(items, [("id", "ID"), ("email", "Email"), ("displayName", "Name")], title=f"Accounts for {vendor_id}")


@app.command("add-to-managed")
def add_to_managed(
    vendor_id: str = typer.Argument(help="Discovered vendor ID to promote to managed."),
) -> None:
    """Promote a discovered vendor to a managed vendor."""
    client = VantaClient()
    data = client.post(f"/discovered-vendors/{vendor_id}/add-to-managed")
    print_success(f"Added discovered vendor {vendor_id} to managed vendors")
