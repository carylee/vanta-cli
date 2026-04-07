from typing import Optional

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list

app = typer.Typer(no_args_is_help=True)

ASSET_COLUMNS = [
    ("id", "ID"),
    ("name", "Name"),
    ("assetType", "Type"),
    ("integrationId", "Integration"),
]


@app.command("list")
def list_assets(
    query: Optional[str] = typer.Option(None, "--query", "-q", help="Search query."),
    asset_type: Optional[str] = typer.Option(
        None, "--type", "-t",
        help="Asset type: CODE_REPOSITORY, CONTAINER_REPOSITORY, CONTAINER_REPOSITORY_IMAGE, "
             "MANIFEST_FILE, SERVER, SERVERLESS_FUNCTION, WORKSTATION.",
    ),
    integration: Optional[str] = typer.Option(None, "--integration", help="Filter by scanner integration ID."),
    limit: Optional[int] = typer.Option(None, "--limit", "-n", help="Max number of results."),
) -> None:
    """List vulnerable assets."""
    client = VantaClient()
    params: dict = {}
    if query:
        params["q"] = query
    if asset_type:
        params["assetType"] = asset_type
    if integration:
        params["integrationId"] = integration
    items = list(client.paginate("/vulnerable-assets", params=params, limit=limit))
    print_list(items, ASSET_COLUMNS, title="Vulnerable Assets")


@app.command("get")
def get_asset(
    asset_id: str = typer.Argument(help="Vulnerable asset ID."),
) -> None:
    """Get details for a specific vulnerable asset."""
    client = VantaClient()
    data = client.get(f"/vulnerable-assets/{asset_id}")
    print_detail(data.get("results", data), title=f"Vulnerable Asset: {asset_id}")
