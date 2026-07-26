"""Compatibility shim for API branches that still import ``code_puppy.api.db.queries``.

These transport/runtime branches are prepared directly against ``main`` rather
than stacked on the DB cleanup PR, so they keep a thin import surface matching
older call sites while delegating to the split repository modules.
"""

from code_puppy.api.db.history_repository import get_session_history_parity
from code_puppy.api.db.message_repository import (
    get_active_messages,
    get_next_seq,
    insert_compaction_log,
    insert_message,
    insert_messages_batch,
    mark_messages_compacted,
    write_error_message_to_sqlite,
    write_system_message_to_sqlite,
)
from code_puppy.api.db.session_repository import (
    get_session_metadata,
    get_session_row,
    session_exists,
    soft_delete_session,
    update_session_meta_fields,
    update_session_stats,
    update_session_working_directory,
    upsert_session,
)
from code_puppy.api.db.tool_call_repository import (
    get_session_tool_calls,
    insert_tool_call,
    insert_tool_calls_batch,
)
from code_puppy.api.db.turn_writer import write_turn_to_sqlite

__all__ = [
    "get_active_messages",
    "get_next_seq",
    "get_session_history_parity",
    "get_session_metadata",
    "get_session_row",
    "get_session_tool_calls",
    "insert_compaction_log",
    "insert_message",
    "insert_messages_batch",
    "insert_tool_call",
    "insert_tool_calls_batch",
    "mark_messages_compacted",
    "session_exists",
    "soft_delete_session",
    "update_session_meta_fields",
    "update_session_stats",
    "update_session_working_directory",
    "upsert_session",
    "write_error_message_to_sqlite",
    "write_system_message_to_sqlite",
    "write_turn_to_sqlite",
]
