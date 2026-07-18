"""Async persistence operations for WebSocket session metadata."""

from __future__ import annotations

from typing import Optional

from code_puppy.api.db.connection import get_db


async def session_exists(session_id: str) -> bool:
    """Return whether a session row exists, including soft-deleted rows."""
    cursor = await get_db().execute(
        "SELECT 1 FROM sessions WHERE session_id = ? LIMIT 1", (session_id,)
    )
    return await cursor.fetchone() is not None


async def get_session_row(session_id: str) -> Optional[dict]:
    """Return a complete session row, or ``None`` when unavailable."""
    try:
        cursor = await get_db().execute(
            "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row is not None else None
    except Exception:
        return None


async def get_session_metadata(session_id: str) -> Optional[dict]:
    """Return session fields required by API handlers, or ``None``."""
    try:
        cursor = await get_db().execute(
            """
            SELECT session_id, title, project_id, agent_name, model_name,
                   working_directory, pinned, created_at
            FROM sessions
            WHERE session_id = ?
            """,
            (session_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row is not None else None
    except Exception:
        return None


async def upsert_session(
    *,
    session_id: str,
    title: str = "",
    agent_name: str = "code-puppy",
    model_name: str = "",
    working_directory: str = "",
    project_id: str = "",
    pinned: bool = False,
    created_at: str,
    updated_at: str,
    message_count: int = 0,
    total_tokens: int = 0,
    deleted_at: Optional[str] = None,
) -> None:
    """Create a session or update its mutable metadata."""
    db = get_db()
    try:
        await db.execute(
            """
            INSERT INTO sessions
                (session_id, title, project_id, agent_name, model_name,
                 working_directory, pinned, created_at, updated_at,
                 message_count, total_tokens, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                title = excluded.title,
                project_id = excluded.project_id,
                agent_name = excluded.agent_name,
                model_name = excluded.model_name,
                working_directory = excluded.working_directory,
                pinned = excluded.pinned,
                updated_at = excluded.updated_at,
                message_count = excluded.message_count,
                total_tokens = excluded.total_tokens,
                deleted_at = COALESCE(sessions.deleted_at, excluded.deleted_at)
            """,
            (
                session_id,
                title,
                project_id,
                agent_name,
                model_name,
                working_directory,
                int(pinned),
                created_at,
                updated_at,
                message_count,
                total_tokens,
                deleted_at,
            ),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def update_session_stats(
    session_id: str,
    *,
    message_count: int,
    total_tokens: int,
    updated_at: str,
) -> None:
    """Replace persisted message and token totals for a session."""
    db = get_db()
    try:
        await db.execute(
            """
            UPDATE sessions
            SET message_count = ?, total_tokens = ?, updated_at = ?
            WHERE session_id = ?
            """,
            (message_count, total_tokens, updated_at, session_id),
        )
        await db.commit()
    except Exception:
        await db.rollback()
        raise


async def update_session_working_directory(
    session_id: str, working_directory: str, updated_at: str
) -> None:
    """Update only the working directory and modification time."""
    db = get_db()
    await db.execute(
        "UPDATE sessions SET working_directory = ?, updated_at = ? WHERE session_id = ?",
        (working_directory, updated_at, session_id),
    )
    await db.commit()


async def update_session_meta_fields(
    session_id: str,
    *,
    title: str,
    project_id: str,
    pinned: bool,
    updated_at: str,
) -> None:
    """Update user-editable session metadata without touching runtime fields."""
    db = get_db()
    await db.execute(
        """
        UPDATE sessions
        SET title = ?, project_id = ?, pinned = ?, updated_at = ?
        WHERE session_id = ?
        """,
        (title, project_id, int(pinned), updated_at, session_id),
    )
    await db.commit()


async def soft_delete_session(session_id: str, deleted_at: str) -> None:
    """Mark a session deleted while preserving its data."""
    db = get_db()
    await db.execute(
        "UPDATE sessions SET deleted_at = ? WHERE session_id = ?",
        (deleted_at, session_id),
    )
    await db.commit()
