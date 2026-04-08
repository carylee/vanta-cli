import re
from pathlib import Path
from typing import Optional

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


def _policy_filename(policy_name: str, index: int) -> str:
    """Build a filename from the policy name, e.g. 'Third-Party Management Policy' -> 'third-party_management_policy.pdf'."""
    slug = re.sub(r"[^\w\s-]", "", policy_name).strip().lower()
    slug = re.sub(r"[\s]+", "_", slug)
    suffix = f"_{index}" if index > 0 else ""
    return f"{slug}{suffix}.pdf"


@app.command("download")
def download_policy(
    policy_id: str = typer.Argument(help="Policy ID to download documents for."),
    output_dir: Path = typer.Option(
        Path("."), "--dir", "-d", help="Directory to save files to."
    ),
) -> None:
    """Download PDF documents for a single policy."""
    client = VantaClient()
    data = client.get(f"/policies/{policy_id}")
    policy = data.get("results", data)

    policy_name = policy.get("name", "")
    docs = _extract_doc_urls(policy)
    if not docs:
        print_error(f"No documents found for policy {policy_id}")
        raise typer.Exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    for i, doc in enumerate(docs):
        url = doc.get("url", "")
        if not url:
            continue
        filename = _policy_filename(policy_name, i) if policy_name else f"policy_document_{i}.pdf"
        dest = output_dir / filename
        client.download_url(url, dest)
        print_success(f"Downloaded {dest}")


@app.command("download-all")
def download_all_policies(
    output_dir: Path = typer.Option(
        Path("vanta-export/policies"), "--dir", "-d", help="Directory to save files to."
    ),
) -> None:
    """Download PDF documents for all policies."""
    client = VantaClient()
    policies = list(client.paginate("/policies"))

    output_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for i, policy_summary in enumerate(policies):
        policy_id = policy_summary.get("id", "")
        policy_name = policy_summary.get("name", "")
        print(f"[{i + 1}/{len(policies)}] {policy_name}...")

        data = client.get(f"/policies/{policy_id}")
        policy = data.get("results", data)
        docs = _extract_doc_urls(policy)

        for j, doc in enumerate(docs):
            url = doc.get("url", "")
            if not url:
                continue
            filename = _policy_filename(policy_name, j) if policy_name else f"policy_document_{policy_id}_{j}.pdf"
            dest = output_dir / filename
            client.download_url(url, dest)
            print_success(f"  Downloaded {dest}")
            total += 1

    print_success(f"\nDownloaded {total} document(s) to {output_dir}")
