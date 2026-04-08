from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import typer

from vanta_cli.client import VantaClient
from vanta_cli.output import print_detail, print_list, print_error, print_success

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


def _extract_doc_urls(policy: dict) -> list[dict]:
    """Extract document entries from a policy response."""
    version = policy.get("latestApprovedVersion", {})
    if not version:
        return []
    return version.get("documents", [])


def _filename_from_url(url: str, index: int) -> str:
    """Derive a filename from a URL, falling back to a numbered name."""
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    name = path.rsplit("/", 1)[-1] if path else ""
    if not name or "." not in name:
        name = f"policy_document_{index}.pdf"
    return name


@app.command("download")
def download_policy(
    policy_id: str = typer.Argument(help="Policy ID to download documents for."),
    output_dir: Path = typer.Option(
        Path("."), "--dir", "-d", help="Directory to save files to."
    ),
) -> None:
    """Download PDF documents for a policy."""
    client = VantaClient()
    data = client.get(f"/policies/{policy_id}")
    policy = data.get("results", data)

    docs = _extract_doc_urls(policy)
    if not docs:
        print_error(f"No documents found for policy {policy_id}")
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    for i, doc in enumerate(docs):
        url = doc.get("url", "")
        if not url:
            continue
        filename = _filename_from_url(url, i)
        dest = output_dir / filename
        client.download_url(url, dest)
        print_success(f"Downloaded {dest}")
