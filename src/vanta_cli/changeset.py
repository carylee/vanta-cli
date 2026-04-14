"""Changeset staging for agent profile write operations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CHANGESET_FILE = Path("vanta-export/changeset.json")


def load_changeset() -> list[dict[str, Any]]:
    """Load the current changeset from disk."""
    if not CHANGESET_FILE.exists():
        return []
    try:
        return json.loads(CHANGESET_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def save_changeset(changes: list[dict[str, Any]]) -> None:
    """Write the changeset to disk."""
    CHANGESET_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHANGESET_FILE.write_text(json.dumps(changes, indent=2))


def stage_change(
    method: str,
    path: str,
    body: dict[str, Any] | None,
    description: str = "",
) -> dict[str, Any]:
    """Append a staged change and return the entry."""
    entry = {
        "id": uuid.uuid4().hex[:8],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "method": method,
        "path": path,
        "body": body,
        "description": description,
    }
    changes = load_changeset()
    changes.append(entry)
    save_changeset(changes)
    return entry


def drop_change(change_id: str) -> bool:
    """Remove a single change by ID. Returns True if found and removed."""
    changes = load_changeset()
    new = [c for c in changes if c["id"] != change_id]
    if len(new) == len(changes):
        return False
    save_changeset(new)
    return True


def clear_changeset() -> None:
    """Remove all staged changes."""
    save_changeset([])
