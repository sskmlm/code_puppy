"""Transport-neutral lifecycle for one cancellable agent turn.

Browser WebSocket and ACP own their respective wires, but both run the same
agent turn: create a task, allow cancellation, collect a normal/cancelled/
failed outcome, and synchronize successful history back onto the session agent.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class AgentTurnOutcome:
    """The completed state of one agent invocation."""

    result: Any | None = None
    error: BaseException | None = None
    cancelled: bool = False


class AgentTurn:
    """A transport-neutral handle for one ``agent.run_with_mcp`` invocation."""

    def __init__(
        self, agent: Any, message: str, run_kwargs: dict[str, Any] | None = None
    ) -> None:
        self.agent = agent
        self.task: asyncio.Task[Any] = asyncio.create_task(
            agent.run_with_mcp(message, **(run_kwargs or {}))
        )

    def cancel(self) -> None:
        """Request cancellation if the turn has not finished."""
        if not self.task.done():
            self.task.cancel()

    async def wait(self) -> AgentTurnOutcome:
        """Wait for the task and normalize its terminal state."""
        try:
            # Shielding preserves caller cancellation (connection teardown)
            # while still translating cancellation requested through ``cancel``.
            return AgentTurnOutcome(result=await asyncio.shield(self.task))
        except asyncio.CancelledError:
            if self.task.cancelled():
                return AgentTurnOutcome(cancelled=True)
            raise
        except Exception as error:  # noqa: BLE001 - transport reports the failure.
            return AgentTurnOutcome(error=error)


def sync_agent_history(agent: Any, result: Any) -> list[Any]:
    """Persist a completed result's full conversation onto its session agent.

    ``run_with_mcp`` deliberately leaves history ownership to its caller. This
    is shared session semantics, independent from whether the caller is ACP or
    the browser WebSocket transport.
    """
    if result is None:
        return []
    try:
        messages = list(result.all_messages())
    except Exception:  # noqa: BLE001 - result shapes vary across pydantic-ai versions.
        return []
    if messages:
        agent.set_message_history(messages)
    return messages
