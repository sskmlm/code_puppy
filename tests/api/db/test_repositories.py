from __future__ import annotations

from dataclasses import dataclass

import pytest
import pytest_asyncio

from code_puppy.api.db.connection import close_db, init_db
from code_puppy.api.db.history_repository import get_session_history_parity
from code_puppy.api.db.message_repository import (
    insert_message,
    mark_messages_compacted,
)
from code_puppy.api.db.session_repository import (
    get_session_metadata,
    upsert_session,
)
from code_puppy.api.db.tool_call_repository import (
    get_session_tool_calls,
    insert_tool_call,
)
from code_puppy.api.db.turn_writer import write_turn_to_sqlite

NOW = "2026-01-01T00:00:00+00:00"


@pytest_asyncio.fixture
async def database(tmp_path, monkeypatch):
    monkeypatch.setenv("PUPPY_DESK_DB", str(tmp_path / "chat_messages.db"))
    await init_db()
    yield
    await close_db()


async def _create_session(session_id: str = "session-1") -> None:
    await upsert_session(
        session_id=session_id,
        created_at=NOW,
        updated_at=NOW,
        title="Original",
        project_id="project-a",
    )


@pytest.mark.asyncio
async def test_session_repository_round_trip(database):
    await _create_session()

    metadata = await get_session_metadata("session-1")

    assert metadata is not None
    assert metadata["title"] == "Original"
    assert metadata["project_id"] == "project-a"


@pytest.mark.asyncio
async def test_history_interleaves_rows_and_filters_compacted_messages(database):
    await _create_session()
    await insert_message(
        session_id="session-1",
        seq=1,
        role="assistant",
        content="visible",
        timestamp=NOW,
    )
    await insert_tool_call(
        id="call-1",
        session_id="session-1",
        parent_message_seq=1,
        seq=2,
        tool_name="lookup",
        timestamp=1.0,
    )
    await insert_message(
        session_id="session-1",
        seq=3,
        role="assistant",
        content="old",
        timestamp=NOW,
    )
    await mark_messages_compacted("session-1", 3, 3)

    active = await get_session_history_parity("session-1", include_compacted=False)
    complete = await get_session_history_parity("session-1", include_compacted=True)

    assert [(row["row_type"], row["seq"]) for row in active] == [
        ("message", 1),
        ("tool_call", 2),
    ]
    assert [row["seq"] for row in complete] == [1, 2, 3]


@dataclass
class TextPart:
    content: str


@dataclass
class ToolCallPart:
    tool_call_id: str
    tool_name: str
    args: dict


@dataclass
class ToolReturnPart:
    tool_call_id: str
    tool_name: str
    content: dict


@dataclass
class FakeMessage:
    kind: str
    parts: list


@pytest.mark.asyncio
async def test_turn_writer_persists_assistant_and_matched_tool_call(database):
    await _create_session()
    await insert_message(
        session_id="session-1",
        seq=1,
        role="user",
        content="run lookup",
        timestamp=NOW,
    )
    assistant = FakeMessage(
        kind="response",
        parts=[
            TextPart("working"),
            ToolCallPart("call-1", "lookup", {"query": "puppy"}),
        ],
    )
    tool_return = FakeMessage(
        kind="request",
        parts=[ToolReturnPart("call-1", "lookup", {"answer": 42})],
    )

    await write_turn_to_sqlite(
        session_id="session-1",
        enhanced_history=[{"msg": assistant, "ts": NOW}, {"msg": tool_return}],
        updated_at=NOW,
        created_at=NOW,
        ctx=None,
    )

    history = await get_session_history_parity("session-1")
    calls = await get_session_tool_calls("session-1")
    assert [(row["row_type"], row["seq"]) for row in history] == [
        ("message", 1),
        ("message", 2),
        ("tool_call", 3),
    ]
    assert calls[0]["tool_name"] == "lookup"
    assert '"answer": 42' in calls[0]["result_json"]
