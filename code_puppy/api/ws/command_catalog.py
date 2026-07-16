"""Browser-native adapter for the shared slash-command catalogue."""

from __future__ import annotations
from typing import Any

from code_puppy.command_catalog import get_command_catalog


def browser_command_catalog() -> list[dict[str, Any]]:
    """Serialize public command metadata for the browser WebSocket protocol."""
    return [
        {
            "name": command.name,
            "description": command.description,
            "usage": command.usage,
            "aliases": list(command.aliases),
        }
        for command in get_command_catalog()
    ]
