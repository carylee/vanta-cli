from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list

app = typer.Typer(no_args_is_help=True)

POLICY_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("status", "Status"),
    ("approvedAtDate", "Approved"),
]


@app.command("list")
def list_policies(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List all policies."""
    client = VantaClient()
    items = list(client.paginate("/policies", limit=limit))
    print_list(items, POLICY_COLUMNS, title="Policies")


@app.command("get")
def get_policy(
    policy_id: str = typer.Argument(help="Policy ID (visible in Vanta URL after /policies/)."),
) -> None:
    """Get details for a specific policy."""
    client = VantaClient()
    data = client.get(f"/policies/{policy_id}")
    print_detail(data.get("results", data), title=f"Policy: {policy_id}")
