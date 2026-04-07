from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list

app = typer.Typer(no_args_is_help=True)

FRAMEWORK_COLUMNS = [
    ("id", "ID"),
    ("displayName", "Name"),
    ("numControlsCompleted", "Controls Done"),
    ("numControlsTotal", "Controls Total"),
    ("numTestsPassing", "Tests Passing"),
    ("numTestsTotal", "Tests Total"),
]

CONTROL_COLUMNS = [
    ("id", "ID"),
    ("externalId", "External ID"),
    ("name", "Name"),
    ("source", "Source"),
    ("domains", "Domains"),
]


@app.command("list")
def list_frameworks(
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List available compliance frameworks."""
    client = VantaClient()
    items = list(client.paginate("/frameworks", limit=limit))
    print_list(items, FRAMEWORK_COLUMNS, title="Frameworks")


@app.command("get")
def get_framework(
    framework_id: str = typer.Argument(help="Framework ID (e.g. 'soc2')."),
) -> None:
    """Get details for a specific framework."""
    client = VantaClient()
    data = client.get(f"/frameworks/{framework_id}")
    print_detail(data.get("results", data), title=f"Framework: {framework_id}")


@app.command("controls")
def list_framework_controls(
    framework_id: str = typer.Argument(help="Framework ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List controls for a framework."""
    client = VantaClient()
    items = list(client.paginate(f"/frameworks/{framework_id}/controls", limit=limit))
    print_list(items, CONTROL_COLUMNS, title=f"Controls for {framework_id}")
