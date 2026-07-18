"""Canonical schema for the pre-release WebSocket session database.

The feature has not shipped, so schema changes intentionally require deleting
an incompatible developer database instead of maintaining migrations.
"""

SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id         TEXT PRIMARY KEY,
    title              TEXT DEFAULT '',
    project_id         TEXT DEFAULT '',
    agent_name         TEXT DEFAULT 'code-puppy',
    model_name         TEXT DEFAULT '',
    working_directory  TEXT DEFAULT '',
    pinned             INTEGER DEFAULT 0,
    created_at         TEXT NOT NULL,
    updated_at         TEXT NOT NULL,
    message_count      INTEGER DEFAULT 0,
    total_tokens       INTEGER DEFAULT 0,
    deleted_at         TEXT
);
CREATE INDEX IF NOT EXISTS idx_sessions_updated ON sessions(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_deleted ON sessions(deleted_at);
CREATE INDEX IF NOT EXISTS idx_sessions_project_id ON sessions(project_id);

CREATE TABLE IF NOT EXISTS compaction_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id     TEXT NOT NULL,
    summary_text   TEXT NOT NULL,
    source_start   INTEGER NOT NULL,
    source_end     INTEGER NOT NULL,
    source_count   INTEGER NOT NULL,
    source_tokens  INTEGER NOT NULL,
    summary_tokens INTEGER NOT NULL,
    strategy       TEXT DEFAULT 'summarization',
    created_at     TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_compaction_session ON compaction_log(session_id);

CREATE TABLE IF NOT EXISTS messages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id          TEXT NOT NULL,
    seq                 INTEGER NOT NULL,
    role                TEXT NOT NULL,
    content             TEXT DEFAULT '',
    type                TEXT DEFAULT '',
    agent_name          TEXT DEFAULT '',
    model_name          TEXT DEFAULT '',
    timestamp           TEXT NOT NULL,
    thinking            TEXT,
    attachments_json    TEXT,
    clean_content       TEXT,
    system_message_type TEXT,
    system_message_path TEXT,
    token_count         INTEGER DEFAULT 0,
    compacted           INTEGER DEFAULT 0,
    pydantic_json       TEXT,
    compaction_log_id   INTEGER REFERENCES compaction_log(id) ON DELETE SET NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE,
    UNIQUE(session_id, seq)
);
CREATE INDEX IF NOT EXISTS idx_messages_session_seq ON messages(session_id, seq);
CREATE INDEX IF NOT EXISTS idx_messages_active ON messages(session_id, compacted);

CREATE TABLE IF NOT EXISTS tool_calls (
    id                 TEXT PRIMARY KEY,
    session_id         TEXT NOT NULL,
    parent_message_seq INTEGER,
    seq                INTEGER NOT NULL,
    tool_name          TEXT NOT NULL,
    args_json          TEXT,
    result_json        TEXT,
    status             TEXT DEFAULT 'running',
    duration_ms        INTEGER,
    error_text         TEXT,
    agent_name         TEXT DEFAULT '',
    model_name         TEXT DEFAULT '',
    timestamp          REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_tool_calls_session_seq ON tool_calls(session_id, seq);
CREATE INDEX IF NOT EXISTS idx_tool_calls_parent ON tool_calls(parent_message_seq);
"""
