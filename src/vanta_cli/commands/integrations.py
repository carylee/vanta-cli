from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_error, print_list, print_success

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
    # This endpoint returns a bare list; other endpoints wrap data in a dict.
    if isinstance(data, list):
        items = data
    else:
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
    print_list(items, [("id", "ID"), ("displayName", "Name"), ("owner", "Owner"), ("inScope", "In scope")], title=f"Resources ({resource_kind})")


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


def _resolve_owner_id(client: VantaClient, owner: str) -> str:
    """Resolve an owner given as either a Vanta user ID or an email address."""
    if "@" not in owner:
        return owner
    email = owner.lower()
    for user in client.paginate("/users"):
        if (user.get("email") or "").lower() == email:
            if not user.get("isActive", True):
                raise typer.BadParameter(
                    f"User {owner} is not active; Vanta rejects former users as owners."
                )
            return user["id"]
    raise typer.BadParameter(f"No Vanta user found with email {owner}.")


@resource_kinds_app.command("set-owner")
def set_owner(
    integration_id: str = typer.Argument(help="Integration ID."),
    resource_kind: str = typer.Argument(help="Resource kind name (e.g. GithubRepo)."),
    resource_ids: list[str] = typer.Argument(help="Resource IDs to update."),
    owner: str = typer.Option(..., "--owner", help="Owner as a Vanta user ID or email address."),
    description: Optional[str] = typer.Option(None, "--description", help="Optional description to set."),
    in_scope: Optional[bool] = typer.Option(
        None,
        "--in-scope/--out-of-scope",
        help="Also mark the resources in or out of monitoring scope.",
    ),
) -> None:
    """Set the owner (and optionally description/scope) of integration resources."""
    client = VantaClient()
    owner_id = _resolve_owner_id(client, owner)
    updates = []
    for rid in resource_ids:
        entry: dict = {"id": rid, "ownerId": owner_id}
        if description is not None:
            entry["description"] = description
        if in_scope is not None:
            entry["inScope"] = in_scope
        updates.append(entry)

    # The API accepts up to 50 resources per call.
    results = []
    path = f"/integrations/{integration_id}/resource-kinds/{resource_kind}/resources"
    for start in range(0, len(updates), 50):
        data = client.patch(path, json={"updates": updates[start : start + 50]})
        results.extend((data or {}).get("results", []))

    failures = [r for r in results if r.get("status") != "SUCCESS"]
    if failures:
        for r in failures:
            print_error(f"Failed to update {r.get('id')}: {r.get('status')}")
        raise typer.Exit(1)
    print_success(f"Set owner to {owner_id} on {len(resource_ids)} resource(s)")
