from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list

app = typer.Typer(no_args_is_help=True)
resource_kinds_app = typer.Typer(no_args_is_help=True, help="Browse and manage integration resource kinds.")
app.add_typer(resource_kinds_app, name="resource-kinds")

INTEGRATION_COLUMNS = [
    ("integrationId", "ID"),
    ("displayName", "Name"),
]


@app.command("list")
def list_integrations(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List all integrations."""
    client = VantaClient()
    items = list(client.paginate("/integrations", limit=limit))
    print_list(items, INTEGRATION_COLUMNS, title="Integrations")


@app.command("get")
def get_integration(
    integration_id: str = typer.Argument(help="Integration ID."),
) -> None:
    """Get integration details."""
    client = VantaClient()
    data = client.get(f"/integrations/{integration_id}")
    print_detail(data.get("results", data), title=f"Integration: {integration_id}")


# --- Resource Kinds ---


@resource_kinds_app.command("list")
def list_resource_kinds(
    integration_id: str = typer.Argument(help="Integration ID."),
) -> None:
    """List resource kinds for an integration."""
    client = VantaClient()
    data = client.get(f"/integrations/{integration_id}/resource-kinds")
    items = data.get("results", data)
    if isinstance(items, dict):
        items = items.get("data", [items])
    print_list(items, [("resourceKind", "Kind"), ("displayName", "Name"), ("count", "Count")], title=f"Resource Kinds for {integration_id}")


@resource_kinds_app.command("get")
def get_resource_kind(
    integration_id: str = typer.Argument(help="Integration ID."),
    resource_kind: str = typer.Argument(help="Resource kind name."),
) -> None:
    """Get details for a resource kind."""
    client = VantaClient()
    data = client.get(f"/integrations/{integration_id}/resource-kinds/{resource_kind}")
    print_detail(data.get("results", data), title=f"Resource Kind: {resource_kind}")


@resource_kinds_app.command("resources")
def list_resources(
    integration_id: str = typer.Argument(help="Integration ID."),
    resource_kind: str = typer.Argument(help="Resource kind name."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max results."),
) -> None:
    """List resources of a specific kind."""
    client = VantaClient()
    items = list(client.paginate(
        f"/integrations/{integration_id}/resource-kinds/{resource_kind}/resources", limit=limit
    ))
    print_list(items, [("id", "ID"), ("displayName", "Name"), ("status", "Status")], title=f"Resources ({resource_kind})")


@resource_kinds_app.command("get-resource")
def get_resource(
    integration_id: str = typer.Argument(help="Integration ID."),
    resource_kind: str = typer.Argument(help="Resource kind name."),
    resource_id: str = typer.Argument(help="Resource ID."),
) -> None:
    """Get a specific resource."""
    client = VantaClient()
    data = client.get(f"/integrations/{integration_id}/resource-kinds/{resource_kind}/resources/{resource_id}")
    print_detail(data.get("results", data), title=f"Resource: {resource_id}")


@resource_kinds_app.command("update-resources")
def update_resources(
    integration_id: str = typer.Argument(help="Integration ID."),
    resource_kind: str = typer.Argument(help="Resource kind name."),
) -> None:
    """Trigger resource update for a kind (PATCH)."""
    client = VantaClient()
    data = client.patch(f"/integrations/{integration_id}/resource-kinds/{resource_kind}/resources")
    print_detail(data.get("results", data) if data else {"status": "updated"}, title="Updated Resources")
