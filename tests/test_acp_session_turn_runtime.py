"""ACP adapter coverage for the shared agent-turn runtime."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from code_puppy.plugins.acp.session import ACPSession, STOP_END_TURN


class _Result:
    output = "done"

    def all_messages(self):
        return ["user", "assistant"]

    def usage(self):
        return None


class _Agent:
    def __init__(self):
        self.history = None

    async def run_with_mcp(self, text, **kwargs):
        return _Result()

    def set_message_history(self, history):
        self.history = history


@pytest.mark.asyncio
async def test_acp_prompt_uses_shared_turn_runtime_and_syncs_history(monkeypatch):
    agent = _Agent()
    session = ACPSession("acp-session", agent)
    monkeypatch.setattr(
        "code_puppy.plugins.acp.content.parse_prompt",
        lambda blocks: SimpleNamespace(
            text="hello", attachments=[], link_attachments=[]
        ),
    )
    monkeypatch.setattr(
        "code_puppy.plugins.acp.state.begin_run", lambda session_id: None
    )
    monkeypatch.setattr("code_puppy.plugins.acp.state.end_run", lambda: None)
    monkeypatch.setattr("code_puppy.plugins.acp.state.streamed_text", lambda: True)
    monkeypatch.setattr("code_puppy.plugins.acp.persistence.save", lambda *args: None)

    outcome = await session.prompt([])

    assert outcome.stop_reason == STOP_END_TURN
    assert agent.history == ["user", "assistant"]
