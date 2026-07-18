"""SQLite connection singleton for the pre-release WS session database.

This feature has not shipped to users yet, so we intentionally keep the schema
policy boring: one canonical schema, one user_version, zero migration archaeology.
If a developer has an older pre-release database, they should delete it and let
Code Puppy recreate it from scratch.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import aiosqlite

from code_puppy.api.db.schema import SCHEMA_SQL, SCHEMA_VERSION

logger = logging.getLogger(__name__)

_PUPPY_DESK_DB_ENV = "PUPPY_DESK_DB"

_aconn: Optional[aiosqlite.Connection] = None


def get_db_path() -> Path:
    """Return path to the shared SQLite database.

    Override with PUPPY_DESK_DB env var for testing.
    """
    env = os.environ.get(_PUPPY_DESK_DB_ENV)
    if env:
        return Path(env)
    return Path.home() / ".puppy_desk" / "chat_messages.db"


async def init_db() -> None:
    """Open the database and ensure the canonical pre-release schema exists."""
    global _aconn

    if _aconn is not None:
        return

    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Opening aiosqlite DB at %s", db_path)
    _aconn = await aiosqlite.connect(str(db_path))
    _aconn.row_factory = aiosqlite.Row

    await _aconn.execute("PRAGMA journal_mode = WAL")
    await _aconn.execute("PRAGMA foreign_keys = ON")
    await _aconn.execute("PRAGMA busy_timeout = 5000")

    cursor = await _aconn.execute("PRAGMA user_version")
    row = await cursor.fetchone()
    current_version = int(row[0]) if row else 0

    if current_version not in {0, SCHEMA_VERSION}:
        raise RuntimeError(
            "Unsupported pre-release WS session DB schema "
            f"v{current_version} at {db_path}. Delete the database and restart "
            "to recreate it with the current schema."
        )

    await _aconn.executescript(SCHEMA_SQL)
    if current_version != SCHEMA_VERSION:
        await _aconn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    await _aconn.commit()

    logger.info(" aiosqlite DB ready (schema v%d)", SCHEMA_VERSION)


def get_db() -> aiosqlite.Connection:
    """Return the open aiosqlite connection.

    Raises RuntimeError if init_db() has not been awaited.
    """
    if _aconn is None:
        raise RuntimeError(
            "aiosqlite DB not initialised — call `await init_db()` first"
        )
    return _aconn


async def close_db() -> None:
    """Close the database connection. Called during app shutdown."""
    global _aconn
    if _aconn is not None:
        await _aconn.close()
        _aconn = None
        logger.info("aiosqlite DB closed")
