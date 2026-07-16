"""Browser command routing is kept on the custom WebSocket protocol."""

from pathlib import Path


CHAT_TEMPLATE = Path(__file__).parents[1] / "templates" / "chat.html"


def test_chat_template_routes_slash_input_as_command_frames():
    template = CHAT_TEMPLATE.read_text()

    assert "content.startsWith('/')" in template
    assert "{ type: 'command', command: content }" in template
    assert "case 'commands_available':" in template
    assert "case 'command_result':" in template
