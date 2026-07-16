"""Slash-command handling for the chat WebSocket."""

from __future__ import annotations

import asyncio
import logging
from io import StringIO
from typing import Any

from rich.console import Console

from code_puppy.api.ws.schemas import ServerCommandResult

logger = logging.getLogger(__name__)


async def handle_command_message(
    *,
    msg: dict[str, Any],
    session_id: str,
    send_typed: Any,
) -> bool:
    """Handle a websocket ``type=command`` payload."""
    if msg.get("type") != "command":
        return False

    command_str = msg.get("command", "")
    logger.debug("Command requested: %s", command_str)

    try:
        from code_puppy.command_line.command_handler import (
            get_commands_help,
            handle_command,
        )

        from code_puppy.messaging.message_queue import get_global_queue

        output = None
        captured_messages = []
        captured_message_ids: set[int] = set()
        queue = get_global_queue()

        def capture(message: Any) -> None:
            if id(message) not in captured_message_ids:
                captured_message_ids.add(id(message))
                capture(message)

        queue.add_listener(capture)
        cmd_name = (
            command_str.strip().lstrip("/").split()[0] if command_str.strip() else ""
        )
        try:
            if cmd_name in ("help", "h"):
                help_text = get_commands_help()
                output_buffer = StringIO()
                console = Console(
                    file=output_buffer,
                    force_terminal=False,
                    width=100,
                    no_color=True,
                )
                console.print(help_text)
                output = output_buffer.getvalue().strip()
                result = True
            else:
                result = handle_command(command_str)
                if isinstance(result, str):
                    output = result
                    result = True
            # Legacy command output is delivered from the queue's worker
            # thread; yield briefly so its listener can capture plugin feedback.
            await asyncio.sleep(0.05)
        finally:
            while True:
                message = queue.get_nowait()
                if message is None:
                    break
                captured_messages.append(message)
            queue.remove_listener(capture)

        message_text = "\n".join(
            str(getattr(message, "content", ""))
            for message in captured_messages
            if getattr(message, "content", None) is not None
        ).strip()
        output = output or message_text

        await send_typed(
            ServerCommandResult(
                command=command_str,
                success=result is True,
                output=output or None,
                messages=[
                    str(getattr(message, "content", message))
                    for message in captured_messages
                ],
                result=str(result) if result and result is not True else None,
                session_id=session_id,
            )
        )
        logger.debug(
            "Command executed: %s -> success=%s, output_len=%s",
            command_str,
            result is True,
            len(output) if output else 0,
        )
    except Exception as cmd_error:
        import traceback

        error_details = traceback.format_exc()
        logger.error("Command error: %s", cmd_error)
        logger.error("Traceback: %s", error_details)
        await send_typed(
            ServerCommandResult(
                command=command_str,
                success=False,
                error=str(cmd_error),
                session_id=session_id,
            )
        )

    return True


__all__ = ["handle_command_message"]
