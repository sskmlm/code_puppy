"""SQLite persistence layer for the Code Puppy WS API.

Stores session history in ~/.puppy_desk/chat_messages.db — the same
database that the Desk Puppy Electron FE reads from.

All database operations are async coroutines backed by aiosqlite.
"""

from code_puppy.api.db.connection import close_db, get_db, init_db
from code_puppy.api.db.message_repository import (
    get_active_messages,
    get_next_seq,
    insert_compaction_log,
    insert_message,
    mark_messages_compacted,
    write_system_message_to_sqlite,
)
from code_puppy.api.db.session_repository import (
    get_session_metadata,
    get_session_row,
    session_exists,
    soft_delete_session,
    update_session_stats,
    update_session_working_directory,
    upsert_session,
)
from code_puppy.api.db.tool_call_repository import insert_tool_call
from code_puppy.api.db.turn_writer import write_turn_to_sqlite

__all__ = [
    "init_db",
    "close_db",
    "get_db",
    "get_session_row",
    "get_session_metadata",
    "session_exists",
    "upsert_session",
    "soft_delete_session",
    "update_session_stats",
    "update_session_working_directory",
    "write_system_message_to_sqlite",
    "get_next_seq",
    "insert_message",
    "insert_tool_call",
    "get_active_messages",
    "mark_messages_compacted",
    "insert_compaction_log",
    "write_turn_to_sqlite",
]
