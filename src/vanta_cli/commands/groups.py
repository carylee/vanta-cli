from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_success

app = typer.Typer(no_args_is_help=True)
members_app = typer.Typer(no_args_is_help=True, help="Manage group members.")
app.add_typer(members_app, name="members")

GROUP_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("description", "Description"),
]

MEMBER_COLUMNS = [
    ("id", "ID"),
    ("emailAddress", "Email"),
    ("name.display", "Name"),
    ("employment.status", "Status"),
]


@app.command("list")
def list_groups(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List all groups."""
    client = VantaClient()
    items = list(client.paginate("/groups", limit=limit))
    print_list(items, GROUP_COLUMNS, title="Groups")


@app.command("get")
def get_group(
    group_id: str = typer.Argument(help="Group ID."),
) -> None:
    """Get details for a specific group."""
    client = VantaClient()
    data = client.get(f"/groups/{group_id}")
    print_detail(data.get("results", data), title=f"Group: {group_id}")


# --- Members ---


@members_app.command("list")
def list_members(
    group_id: str = typer.Argument(help="Group ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List people in a group."""
    client = VantaClient()
    items = list(client.paginate(f"/groups/{group_id}/people", limit=limit))
    print_list(items, MEMBER_COLUMNS, title=f"Members of {group_id}")


@members_app.command("add")
def add_member(
    group_id: str = typer.Argument(help="Group ID."),
    person_id: str = typer.Argument(help="Person ID to add."),
) -> None:
    """Add a person to a group."""
    client = VantaClient()
    client.post(f"/groups/{group_id}/people", json={"personId": person_id})
    print_success(f"Added {person_id} to group {group_id}")


@members_app.command("remove")
def remove_member(
    group_id: str = typer.Argument(help="Group ID."),
    person_id: str = typer.Argument(help="Person ID to remove."),
) -> None:
    """Remove a person from a group."""
    client = VantaClient()
    client.delete(f"/groups/{group_id}/people/{person_id}")
    print_success(f"Removed {person_id} from group {group_id}")


@members_app.command("bulk-add")
def bulk_add(
    group_id: str = typer.Argument(help="Group ID."),
    person_ids: list[str] = typer.Argument(help="Person IDs to add."),
) -> None:
    """Add multiple people to a group."""
    client = VantaClient()
    client.post(f"/groups/{group_id}/add-people", json={"updates": person_ids})
    print_success(f"Added {len(person_ids)} people to group {group_id}")


@members_app.command("bulk-remove")
def bulk_remove(
    group_id: str = typer.Argument(help="Group ID."),
    person_ids: list[str] = typer.Argument(help="Person IDs to remove."),
) -> None:
    """Remove multiple people from a group."""
    client = VantaClient()
    client.post(f"/groups/{group_id}/remove-people", json={"updates": person_ids})
    print_success(f"Removed {len(person_ids)} people from group {group_id}")
