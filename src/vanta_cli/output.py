from __future__ import annotations

import json
from enum import Enum
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
error_console = Console(stderr=True)


class OutputFormat(str, Enum):
    table = "table"
    json = "json"
    jsonl = "jsonl"


# Module-level state set by main app callback
_format: OutputFormat = OutputFormat.table


def set_format(fmt: OutputFormat) -> None:
    global _format
    _format = fmt


def get_format() -> OutputFormat:
    return _format


def print_list(
    items: list[dict[str, Any]],
    columns: list[tuple[str, str]],
    title: str = "",
) -> None:
    """Print a list of items.

    columns: list of (key, display_header) tuples.
    """
    if _format == OutputFormat.json:
        console.print_json(json.dumps(items))
        return
    if _format == OutputFormat.jsonl:
        for item in items:
            console.print_json(json.dumps(item))
        return

    table = Table(title=title or None)
    for _, header in columns:
        table.add_column(header)

    for item in items:
        row = []
        for key, _ in columns:
            val = _resolve_key(item, key)
            row.append(str(val) if val is not None else "")
        table.add_row(*row)

    console.print(table)


def print_detail(item: dict[str, Any], title: str = "") -> None:
    """Print a single item's details."""
    if _format in (OutputFormat.json, OutputFormat.jsonl):
        console.print_json(json.dumps(item))
        return

    lines = []
    for key, val in item.items():
        if isinstance(val, (dict, list)):
            val = json.dumps(val, indent=2)
        lines.append(f"[bold]{key}[/bold]: {val}")

    console.print(Panel("\n".join(lines), title=title or None))


def print_success(message: str) -> None:
    console.print(f"[green]{message}[/green]")


def print_error(message: str) -> None:
    error_console.print(f"[red]{message}[/red]")


def _resolve_key(item: dict[str, Any], key: str) -> Any:
    """Resolve a dotted key like 'owner.emailAddress' from a nested dict."""
    parts = key.split(".")
    val: Any = item
    for part in parts:
        if isinstance(val, dict):
            val = val.get(part)
        else:
            return None
    return val
