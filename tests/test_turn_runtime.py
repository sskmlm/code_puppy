"""Shared turn lifecycle tests used by browser WebSocket and ACP adapters."""

from __future__ import annotations

import asyncio

import pytest

from code_puppy.api.turn_runtime import AgentTurn, sync_agent_history


class _Agent:
    def __init__(self, result=None):
        self.result = result
        self.history = None

    async def run_with_mcp(self, message, **kwargs):
        return self.result

    def set_message_history(self, history):
        self.history = history


class _Result:
    def all_messages(self):
        return ["user", "assistant"]


@pytest.mark.asyncio
async def test_completed_turn_returns_result_and_syncs_session_history():
    result = _Result()
    agent = _Agent(result)

    outcome = await AgentTurn(agent, "hello").wait()
    sync_agent_history(agent, outcome.result)

    assert outcome.result is result
    assert outcome.error is None
    assert not outcome.cancelled
    assert agent.history == ["user", "assistant"]


@pytest.mark.asyncio
async def test_cancelled_turn_has_a_normalized_cancelled_outcome():
    started = asyncio.Event()

    class BlockingAgent(_Agent):
        async def run_with_mcp(self, message, **kwargs):
            started.set()
            await asyncio.Future()

    turn = AgentTurn(BlockingAgent(), "hello")
    await started.wait()
    turn.cancel()

    assert (await turn.wait()).cancelled
