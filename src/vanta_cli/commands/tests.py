from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)
entities_app = typer.Typer(no_args_is_help=True, help="Manage test entities (individual tested items).")
app.add_typer(entities_app, name="entities")

TEST_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("category", "Category"),
]

ENTITY_COLUMNS = [
    ("id", "ID"),
    ("displayName", "Name"),
    ("entityStatus", "Status"),
    ("responseType", "Type"),
    ("lastUpdatedDate", "Updated"),
]


@app.command("list")
def list_tests(
    status: Optional[str] = typer.Option(
        None,
        "--status", "-s",
        help="Filter by status: OK, NEEDS_ATTENTION, DEACTIVATED, IN_PROGRESS, INVALID, NOT_APPLICABLE",
    ),
    framework: Optional[str] = typer.Option(None, "--framework", help="Filter by framework ID."),
    integration: Optional[str] = typer.Option(None, "--integration", help="Filter by integration ID."),
    category: Optional[str] = typer.Option(None, "--category", help="Filter by category."),
    control: Optional[str] = typer.Option(None, "--control", help="Filter by control ID."),
    owner: Optional[str] = typer.Option(None, "--owner", help="Filter by owner ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List all compliance tests."""
    client = VantaClient()
    params: dict = {}
    if status:
        params["statusFilter"] = status
    if framework:
        params["frameworkFilter"] = framework
    if integration:
        params["integrationFilter"] = integration
    if category:
        params["categoryFilter"] = category
    if control:
        params["controlFilter"] = control
    if owner:
        params["ownerFilter"] = owner

    items = list(client.paginate("/tests", params=params, limit=limit))
    print_list(items, TEST_COLUMNS, title="Tests")


@app.command("get")
def get_test(
    test_id: str = typer.Argument(help="Test ID (visible in Vanta URL after /tests/)."),
) -> None:
    """Get details for a specific test."""
    client = VantaClient()
    data = client.get(f"/tests/{test_id}")
    print_detail(data.get("results", data), title=f"Test: {test_id}")


@entities_app.command("list")
def list_entities(
    test_id: str = typer.Argument(help="Test ID to list entities for."),
    status: Optional[str] = typer.Option(
        "FAILING",
        "--status", "-s",
        help="Entity status: FAILING (default) or DEACTIVATED.",
    ),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List tested items (entities) for a test. Defaults to FAILING entities."""
    client = VantaClient()
    params: dict = {}
    if status:
        params["entityStatus"] = status

    items = list(client.paginate(f"/tests/{test_id}/entities", params=params, limit=limit))
    print_list(items, ENTITY_COLUMNS, title=f"Entities for {test_id}")


@entities_app.command("deactivate")
def deactivate_entity(
    test_id: str = typer.Argument(help="Test ID."),
    entity_id: str = typer.Argument(help="Entity ID to deactivate."),
    reason: str = typer.Option(
        ..., "--reason", "-r", help="Justification for deactivating this entity."
    ),
    until: Optional[str] = typer.Option(
        None, "--until", help="ISO date to auto-reactivate (e.g. 2025-12-31T00:00:00Z)."
    ),
) -> None:
    """Deactivate a test entity with a justification reason."""
    client = VantaClient()
    body: dict = {"deactivateReason": reason}
    if until:
        body["deactivateUntilDate"] = until

    client.post(f"/tests/{test_id}/entities/{entity_id}/deactivate", json=body)
    print_success(f"Deactivated entity {entity_id} on test {test_id}")


@entities_app.command("reactivate")
def reactivate_entity(
    test_id: str = typer.Argument(help="Test ID."),
    entity_id: str = typer.Argument(help="Entity ID to reactivate."),
) -> None:
    """Reactivate a previously deactivated test entity."""
    client = VantaClient()
    client.post(f"/tests/{test_id}/entities/{entity_id}/reactivate")
    print_success(f"Reactivated entity {entity_id} on test {test_id}")
