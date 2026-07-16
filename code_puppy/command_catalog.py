"""Transport-neutral discovery of Code Puppy's slash-command catalogue."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CommandCatalogEntry:
    """Public command metadata safe to advertise to any client transport."""

    name: str
    description: str
    usage: str
    aliases: tuple[str, ...]


def get_command_catalog() -> list[CommandCatalogEntry]:
    """Return unique registered commands, including plugin-provided commands."""
    from code_puppy.command_line.command_registry import get_unique_commands

    catalog = {
        command.name: CommandCatalogEntry(
            name=command.name,
            description=command.description,
            usage=command.usage,
            aliases=tuple(command.aliases),
        )
        for command in get_unique_commands()
    }

    from code_puppy import callbacks

    for result in callbacks.on_custom_command_help():
        for name, description in _custom_help_entries(result):
            catalog.setdefault(
                name,
                CommandCatalogEntry(
                    name=name,
                    description=description,
                    usage=f"/{name}",
                    aliases=(),
                ),
            )
    return sorted(catalog.values(), key=lambda command: command.name.casefold())


def _custom_help_entries(result: object) -> list[tuple[str, str]]:
    """Normalize supported ``custom_command_help`` callback result shapes."""
    if isinstance(result, tuple) and len(result) == 2:
        return [(str(result[0]).lstrip("/"), str(result[1]))]
    if not isinstance(result, list):
        return []
    return [
        (str(item[0]).lstrip("/"), str(item[1]))
        for item in result
        if isinstance(item, tuple) and len(item) == 2
    ]
