"""Async persistence operations for tool calls."""

from __future__ import annotations

from typing import Any, Optional

from code_puppy.api.db.connection import get_db

_INSERT_SQL = """
INSERT OR IGNORE INTO tool_calls
    (id, session_id, parent_message_seq, seq, tool_name, args_json,
     result_json, status, duration_ms, error_text, agent_name, model_name,
     timestamp)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _params(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["id"],
        row["session_id"],
        row.get("parent_message_seq"),
        row["seq"],
        row["tool_name"],
        row.get("args_json"),
        row.get("result_json"),
        row.get("status", "success"),
        row.get("duration_ms"),
        row.get("error_text"),
        row.get("agent_name", ""),
        row.get("model_name", ""),
        row["timestamp"],
    )


async def insert_tool_call(
    *,
    id: str,
    session_id: str,
    parent_message_seq: Optional[int],
    seq: int,
    tool_name: str,
    timestamp: float,
    args_json: Optional[str] = None,
    result_json: Optional[str] = None,
    status: str = "success",
    duration_ms: Optional[int] = None,
    error_text: Optional[str] = None,
    agent_name: str = "",
    model_name: str = "",
) -> None:
    """Insert one tool call, ignoring a duplicate identifier."""
    db = get_db()
    await db.execute(_INSERT_SQL, _params(locals()))
    await db.commit()


async def insert_tool_calls_batch(rows: list[dict[str, Any]]) -> None:
    """Insert tool calls in one transaction."""
    if not rows:
        return
    db = get_db()
    try:
        await db.executemany(_INSERT_SQL, [_params(row) for row in rows])
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def get_session_tool_calls(session_id: str) -> list[dict[str, Any]]:
    """Return all tool calls for a session in sequence order."""
    cursor = await get_db().execute(
        """
        SELECT id, session_id, parent_message_seq, seq, tool_name,
               args_json, result_json, status, duration_ms, error_text,
               agent_name, model_name, timestamp
        FROM tool_calls
        WHERE session_id = ?
        ORDER BY seq
        """,
        (session_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]
