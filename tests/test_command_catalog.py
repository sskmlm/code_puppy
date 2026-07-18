"""Tests for transport-neutral slash-command discovery."""

from types import SimpleNamespace

from code_puppy.command_catalog import get_command_catalog


def test_command_catalog_exposes_unique_plugin_commands(monkeypatch):
    commands = [
        SimpleNamespace(
            name="spinner",
            description="Pick a spinner",
            usage="/spinner [name]",
            aliases=["spin"],
        ),
        SimpleNamespace(
            name="help",
            description="Show help",
            usage="/help",
            aliases=[],
        ),
    ]
    monkeypatch.setattr(
        "code_puppy.command_line.command_registry.get_unique_commands",
        lambda: commands,
    )
    monkeypatch.setattr(
        "code_puppy.callbacks.on_custom_command_help",
        lambda: [[("plugin-command", "Plugin command")]],
    )

    catalog = get_command_catalog()

    assert [command.name for command in catalog] == [
        "help",
        "plugin-command",
        "spinner",
    ]
    assert catalog[2].aliases == ("spin",)
