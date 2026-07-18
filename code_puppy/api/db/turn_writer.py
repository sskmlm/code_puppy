"""Orchestration for persisting a completed agent turn."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any

from code_puppy.api.db.message_repository import (
    get_next_seq,
    insert_messages_batch,
)
from code_puppy.api.db.message_serialization import (
    extract_content,
    extract_thinking,
    extract_tool_calls,
    extract_tool_returns,
    get_message_timestamp,
    get_role,
    pydantic_json_for_message,
)
from code_puppy.api.db.session_repository import (
    update_session_stats,
    upsert_session,
)
from code_puppy.api.db.tool_call_repository import insert_tool_calls_batch

logger = logging.getLogger(__name__)


def _json_value(value: Any) -> str:
    """Serialize a persisted tool value with safe fallbacks."""
    try:
        if hasattr(value, "model_dump"):
            value = value.model_dump()
        elif hasattr(value, "dict"):
            value = value.dict()
        elif hasattr(value, "__dict__"):
            value = vars(value)
        return json.dumps(value)
    except Exception:
        return json.dumps(str(value))


def _timestamp(value: Any) -> float:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:
        return time.time()


def _token_count(ctx: Any, message: Any, content: str) -> int:
    try:
        if ctx:
            return ctx.agent.estimate_tokens_for_message(message)
    except Exception:
        pass
    return max(1, len(content) // 4)


def _unwrap(item: Any) -> tuple[Any, dict[str, Any]]:
    if isinstance(item, dict) and "msg" in item:
        return item["msg"], item
    return item, {}


async def write_turn_to_sqlite(
    *,
    session_id: str,
    enhanced_history: list[Any],
    updated_at: str,
    created_at: str,
    ctx: Any,
    title: str = "",
    working_directory: str = "",
    pinned: bool = False,
    project_id: str = "",
    agent_name: str = "code-puppy",
    model_name: str = "",
    total_tokens: int = 0,
) -> None:
    """Persist assistant messages and matched tool calls for a completed turn."""
    try:
        await upsert_session(
            session_id=session_id,
            title=title,
            agent_name=agent_name,
            model_name=model_name,
            working_directory=working_directory,
            pinned=pinned,
            project_id=project_id,
            created_at=created_at,
            updated_at=updated_at,
            message_count=len(enhanced_history),
            total_tokens=total_tokens,
            deleted_at=None,
        )
    except Exception as exc:
        logger.warning("write_turn_to_sqlite: upsert_session failed: %s", exc)
        return

    message_rows: list[dict[str, Any]] = []
    pending_calls: dict[str, dict[str, Any]] = {}
    matched_calls: list[dict[str, Any]] = []
    current_max_seq = await get_next_seq(session_id) - 1

    for item in enhanced_history:
        message, wrapper = _unwrap(item)
        if not hasattr(message, "parts"):
            continue

        role = get_role(message)
        timestamp = wrapper.get("ts") or get_message_timestamp(message) or updated_at
        content = extract_content(message)

        if role == "user":
            for tool_return in extract_tool_returns(message):
                call = pending_calls.pop(tool_return["id"], None)
                if call is None:
                    continue
                matched_calls.append(
                    {
                        "id": tool_return["id"],
                        "session_id": session_id,
                        "parent_message_seq": call["parent_seq"],
                        "tool_name": call["name"],
                        "args_json": _json_value(call["args"]),
                        "result_json": _json_value(tool_return["result"]),
                        "status": "success",
                        "agent_name": call["agent"],
                        "model_name": call["model"],
                        "timestamp": _timestamp(call["timestamp"]),
                    }
                )
            # User rows are persisted before streaming and must not be duplicated.
            continue

        current_max_seq += 1
        seq = current_max_seq
        message_agent = wrapper.get("agent") or agent_name or "code-puppy"
        message_model = wrapper.get("model") or model_name or "unknown"
        tool_calls = extract_tool_calls(message) if role == "assistant" else []
        attachments = wrapper.get("attachments")
        attachments_json = json.dumps(attachments) if attachments else None
        if tool_calls and not attachments_json:
            attachments_json = json.dumps({"tool_calls": tool_calls})

        if role == "assistant" and not content.strip() and not tool_calls:
            continue

        message_rows.append(
            {
                "session_id": session_id,
                "seq": seq,
                "role": role,
                "content": content,
                "type": type(message).__name__,
                "agent_name": message_agent,
                "model_name": message_model,
                "timestamp": timestamp,
                "thinking": extract_thinking(message),
                "attachments_json": attachments_json,
                "clean_content": wrapper.get("clean_content") or None,
                "token_count": _token_count(ctx, message, content),
                "pydantic_json": pydantic_json_for_message(message),
            }
        )

        for tool_call in tool_calls:
            pending_calls[tool_call["id"]] = {
                "name": tool_call["name"],
                "args": tool_call["args"],
                "parent_seq": seq,
                "agent": message_agent,
                "model": message_model,
                "timestamp": timestamp,
            }

    for index, call in enumerate(matched_calls, start=1):
        call["seq"] = current_max_seq + index

    try:
        await insert_messages_batch(message_rows)
    except Exception as exc:
        logger.warning("write_turn_to_sqlite: message batch failed: %s", exc)

    try:
        await insert_tool_calls_batch(matched_calls)
    except Exception as exc:
        logger.warning("write_turn_to_sqlite: tool-call batch failed: %s", exc)

    computed_tokens = sum(row.get("token_count", 0) for row in message_rows)
    try:
        await update_session_stats(
            session_id,
            message_count=len(message_rows),
            total_tokens=total_tokens if total_tokens > 0 else computed_tokens,
            updated_at=updated_at,
        )
    except Exception as exc:
        logger.warning("write_turn_to_sqlite: session stats failed: %s", exc)

    if pending_calls:
        logger.warning(
            "write_turn_to_sqlite: %d unmatched tool calls for session=%s: %s",
            len(pending_calls),
            session_id,
            list(pending_calls),
        )
