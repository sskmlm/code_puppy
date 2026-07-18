"""Async persistence operations for chat messages and compaction records."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from code_puppy.api.db.connection import get_db

logger = logging.getLogger(__name__)


async def get_next_seq(session_id: str) -> int:
    """Return the next available one-based message sequence."""
    cursor = await get_db().execute(
        "SELECT COALESCE(MAX(seq), 0) FROM messages WHERE session_id = ?",
        (session_id,),
    )
    row = await cursor.fetchone()
    return (row[0] or 0) + 1


async def _insert_immediate_message_and_sync_session(
    *,
    session_id: str,
    role: str,
    content: str,
    type: str,
    timestamp: str,
    agent_name: str = "",
    model_name: str = "",
    thinking: Optional[str] = None,
    attachments_json: Optional[str] = None,
    clean_content: Optional[str] = None,
    system_message_type: Optional[str] = None,
    system_message_path: Optional[str] = None,
    token_count: int = 0,
    increment_message_count: bool = True,
) -> int:
    """Atomically insert an immediate message and synchronize session totals."""
    db = get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT 1 FROM sessions WHERE session_id = ?", (session_id,)
        )
        if await cursor.fetchone() is None:
            await db.execute(
                """
                INSERT INTO sessions
                    (session_id, title, agent_name, model_name, working_directory,
                     pinned, created_at, updated_at, message_count, total_tokens,
                     deleted_at)
                VALUES (?, '', ?, ?, '', 0, ?, ?, 0, 0, NULL)
                """,
                (
                    session_id,
                    agent_name or "code-puppy",
                    model_name,
                    timestamp,
                    timestamp,
                ),
            )

        cursor = await db.execute(
            """
            SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq
            FROM messages WHERE session_id = ?
            """,
            (session_id,),
        )
        row = await cursor.fetchone()
        seq = int(row["next_seq"] if row is not None else 1)
        await db.execute(
            """
            INSERT INTO messages
                (session_id, seq, role, content, type, agent_name, model_name,
                 timestamp, thinking, attachments_json, clean_content,
                 system_message_type, system_message_path, token_count,
                 compacted, pydantic_json, compaction_log_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, NULL)
            """,
            (
                session_id,
                seq,
                role,
                content,
                type,
                agent_name,
                model_name,
                timestamp,
                thinking,
                attachments_json,
                clean_content,
                system_message_type,
                system_message_path,
                token_count,
            ),
        )
        await db.execute(
            """
            UPDATE sessions
            SET message_count = COALESCE(message_count, 0) + ?,
                total_tokens = COALESCE(total_tokens, 0) + ?,
                updated_at = ?
            WHERE session_id = ?
            """,
            (int(increment_message_count), token_count, timestamp, session_id),
        )
        await db.commit()
        return seq
    except Exception:
        await db.rollback()
        raise


async def write_system_message_to_sqlite(
    *,
    session_id: str,
    system_message_type: str,
    content: str,
    system_message_path: str = "",
    agent_name: str = "",
    model_name: str = "",
    timestamp: Optional[str] = None,
) -> None:
    """Persist a system event immediately, deduplicating directory banners."""
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    if system_message_type == "directory" and system_message_path:
        try:
            cursor = await get_db().execute(
                """
                SELECT 1 FROM messages
                WHERE session_id = ? AND system_message_type = 'directory'
                  AND system_message_path = ? LIMIT 1
                """,
                (session_id, system_message_path),
            )
            if await cursor.fetchone():
                return
        except Exception as exc:
            logger.warning("Directory dedup check failed: %s", exc)

    try:
        await _insert_immediate_message_and_sync_session(
            session_id=session_id,
            role="system",
            content=content,
            type="system",
            agent_name=agent_name,
            model_name=model_name,
            timestamp=timestamp,
            system_message_type=system_message_type,
            system_message_path=system_message_path,
            increment_message_count=False,
        )
    except Exception as exc:
        logger.warning(
            "write_system_message_to_sqlite failed (session=%s type=%s): %s",
            session_id,
            system_message_type,
            exc,
            exc_info=True,
        )


async def write_error_message_to_sqlite(
    *,
    session_id: str,
    error: str,
    error_type: str = "unknown",
    technical_details: str = "",
    action_required: Optional[str] = None,
    agent_name: str = "",
    model_name: str = "",
    timestamp: Optional[str] = None,
) -> None:
    """Persist a structured error as an immediate message."""
    timestamp = timestamp or datetime.now(timezone.utc).isoformat()
    payload = {
        "error": error,
        "error_type": error_type,
        "technical_details": technical_details,
        "action_required": action_required,
        "session_id": session_id,
    }
    try:
        await _insert_immediate_message_and_sync_session(
            session_id=session_id,
            role="system",
            content=error,
            type="error",
            agent_name=agent_name,
            model_name=model_name,
            timestamp=timestamp,
            clean_content=error,
            attachments_json=json.dumps(payload),
        )
    except Exception as exc:
        logger.warning(
            "write_error_message_to_sqlite failed (session=%s type=%s): %s",
            session_id,
            error_type,
            exc,
            exc_info=True,
        )


def _has_payload(row: dict[str, Any]) -> bool:
    return not (
        row.get("role") in {"user", "assistant"}
        and not row.get("content", "").strip()
        and not row.get("attachments_json")
        and not row.get("pydantic_json")
    )


async def insert_message(
    *,
    session_id: str,
    seq: int,
    role: str,
    timestamp: str,
    content: str = "",
    type: str = "",
    agent_name: str = "",
    model_name: str = "",
    thinking: Optional[str] = None,
    attachments_json: Optional[str] = None,
    clean_content: Optional[str] = None,
    system_message_type: Optional[str] = None,
    system_message_path: Optional[str] = None,
    token_count: int = 0,
    compacted: int = 0,
    pydantic_json: Optional[str] = None,
    compaction_log_id: Optional[int] = None,
) -> None:
    """Insert one message unless its visible and structured payload are empty."""
    row = locals()
    if not _has_payload(row):
        return
    db = get_db()
    await db.execute(
        """
        INSERT OR IGNORE INTO messages
            (session_id, seq, role, content, type, agent_name, model_name,
             timestamp, thinking, attachments_json, clean_content,
             system_message_type, system_message_path, token_count, compacted,
             pydantic_json, compaction_log_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        _message_params(row),
    )
    await db.commit()


def _message_params(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row["session_id"],
        row["seq"],
        row["role"],
        row.get("content", ""),
        row.get("type", ""),
        row.get("agent_name", ""),
        row.get("model_name", ""),
        row["timestamp"],
        row.get("thinking"),
        row.get("attachments_json"),
        row.get("clean_content"),
        row.get("system_message_type"),
        row.get("system_message_path"),
        row.get("token_count", 0),
        row.get("compacted", 0),
        row.get("pydantic_json"),
        row.get("compaction_log_id"),
    )


async def insert_messages_batch(rows: list[dict[str, Any]]) -> None:
    """Insert non-empty message rows in one transaction."""
    rows = [row for row in rows if _has_payload(row)]
    if not rows:
        return
    db = get_db()
    try:
        await db.executemany(
            """
            INSERT OR IGNORE INTO messages
                (session_id, seq, role, content, type, agent_name, model_name,
                 timestamp, thinking, attachments_json, clean_content,
                 system_message_type, system_message_path, token_count,
                 compacted, pydantic_json, compaction_log_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [_message_params(row) for row in rows],
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def get_active_messages(session_id: str) -> list[dict[str, Any]]:
    """Return active messages in sequence order."""
    cursor = await get_db().execute(
        """
        SELECT session_id, seq, role, content, type, agent_name, model_name,
               timestamp, thinking, attachments_json, clean_content,
               system_message_type, system_message_path, token_count, compacted,
               pydantic_json, compaction_log_id
        FROM messages
        WHERE session_id = ? AND compacted = 0
        ORDER BY seq
        """,
        (session_id,),
    )
    return [dict(row) for row in await cursor.fetchall()]


async def mark_messages_compacted(
    session_id: str, start_seq: int, end_seq: int
) -> None:
    """Mark an inclusive message sequence range as compacted."""
    db = get_db()
    await db.execute(
        """
        UPDATE messages SET compacted = 1
        WHERE session_id = ? AND seq BETWEEN ? AND ? AND compacted = 0
        """,
        (session_id, start_seq, end_seq),
    )
    await db.commit()


async def insert_compaction_log(
    *,
    session_id: str,
    summary_text: str,
    source_start: int,
    source_end: int,
    source_count: int,
    source_tokens: int,
    summary_tokens: int,
    created_at: str,
    strategy: str = "summarization",
) -> int:
    """Insert a compaction record and return its generated identifier."""
    db = get_db()
    cursor = await db.execute(
        """
        INSERT INTO compaction_log
            (session_id, summary_text, source_start, source_end, source_count,
             source_tokens, summary_tokens, strategy, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id,
            summary_text,
            source_start,
            source_end,
            source_count,
            source_tokens,
            summary_tokens,
            strategy,
            created_at,
        ),
    )
    await db.commit()
    return int(cursor.lastrowid)
