import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from starlette.routing import Router


class _HTTPException(Exception):
    def __init__(self, status_code, detail):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _APIRouter:
    def get(self, *args, **kwargs):
        return lambda fn: fn

    def delete(self, *args, **kwargs):
        return lambda fn: fn

    def patch(self, *args, **kwargs):
        return lambda fn: fn


def _query(*args, **kwargs):
    return kwargs.get("default")


_fastapi_stub = types.ModuleType("fastapi")
_fastapi_stub.APIRouter = _APIRouter
_fastapi_stub.HTTPException = _HTTPException
_fastapi_stub.Query = _query
sys.modules.setdefault("fastapi", _fastapi_stub)


async def _unused_async(*args, **kwargs):
    raise AssertionError("test stub should be monkeypatched before use")


_history_stub = types.ModuleType("code_puppy.api.db.history_repository")
_history_stub.get_session_history_parity = _unused_async
sys.modules.setdefault("code_puppy.api.db.history_repository", _history_stub)

_message_stub = types.ModuleType("code_puppy.api.db.message_repository")
_message_stub.get_active_messages = _unused_async
sys.modules.setdefault("code_puppy.api.db.message_repository", _message_stub)

_session_stub = types.ModuleType("code_puppy.api.db.session_repository")
_session_stub.get_session_metadata = _unused_async
_session_stub.soft_delete_session = _unused_async
_session_stub.update_session_meta_fields = _unused_async
sys.modules.setdefault("code_puppy.api.db.session_repository", _session_stub)

_tool_call_stub = types.ModuleType("code_puppy.api.db.tool_call_repository")
_tool_call_stub.get_session_tool_calls = _unused_async
sys.modules.setdefault("code_puppy.api.db.tool_call_repository", _tool_call_stub)


_original_router_init = Router.__init__


def _compat_router_init(self, *args, **kwargs):
    kwargs.pop("on_startup", None)
    kwargs.pop("on_shutdown", None)
    kwargs.pop("lifespan", None)
    return _original_router_init(self, *args, **kwargs)


Router.__init__ = _compat_router_init
try:
    module_path = (
        Path(__file__).resolve().parents[2]
        / "code_puppy"
        / "api"
        / "routers"
        / "ws_sessions.py"
    )
    spec = importlib.util.spec_from_file_location(
        "test_ws_sessions_module", module_path
    )
    assert spec is not None and spec.loader is not None
    ws_sessions = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ws_sessions)
finally:
    Router.__init__ = _original_router_init


@pytest.mark.asyncio
async def test_get_ws_session_messages_keeps_plain_legacy_rows(monkeypatch):
    monkeypatch.setattr(
        ws_sessions,
        "_validate_session_name",
        lambda session_name: session_name,
    )
    monkeypatch.setattr(
        ws_sessions,
        "get_active_messages",
        AsyncMock(
            return_value=[
                {
                    "role": "assistant",
                    "content": "plain legacy row",
                    "type": "message",
                    "agent_name": "code-puppy",
                    "model_name": "gpt-5",
                    "timestamp": "2026-01-01T00:00:00Z",
                    "thinking": None,
                    "clean_content": "plain legacy row",
                    "seq": 7,
                    "pydantic_json": None,
                }
            ]
        ),
    )
    monkeypatch.setattr(
        ws_sessions,
        "get_session_metadata",
        AsyncMock(return_value=None),
    )

    result = await ws_sessions.get_ws_session_messages(
        "session-1",
        include_tool_calls=False,
    )

    assert result == [
        {
            "role": "assistant",
            "content": "plain legacy row",
            "type": "message",
            "agent_name": "code-puppy",
            "model_name": "gpt-5",
            "timestamp": "2026-01-01T00:00:00Z",
            "thinking": None,
            "clean_content": "plain legacy row",
            "seq": 7,
        }
    ]


@pytest.mark.asyncio
async def test_update_ws_session_supports_project_id(monkeypatch):
    monkeypatch.setattr(
        ws_sessions,
        "_validate_session_name",
        lambda session_name: session_name,
    )
    monkeypatch.setattr(
        ws_sessions,
        "get_session_metadata",
        AsyncMock(
            return_value={
                "session_id": "session-1",
                "title": "Original",
                "project_id": "old-project",
                "pinned": 0,
            }
        ),
    )
    update_mock = AsyncMock()
    monkeypatch.setattr(ws_sessions, "update_session_meta_fields", update_mock)

    result = await ws_sessions.update_ws_session(
        "session-1",
        {
            "title": "  Renamed  ",
            "project_id": "  project-alpha  ",
            "pinned": True,
        },
    )

    update_mock.assert_awaited_once()
    _, kwargs = update_mock.await_args
    assert kwargs["title"] == "Renamed"
    assert kwargs["project_id"] == "project-alpha"
    assert kwargs["pinned"] is True

    assert result["session_id"] == "session-1"
    assert result["title"] == "Renamed"
    assert result["project_id"] == "project-alpha"
    assert result["pinned"] is True


@pytest.mark.parametrize("session_name", ["", "../secret", "a/b", "a\\b"])
def test_validate_session_name_rejects_path_like_identifiers(session_name):
    with pytest.raises(_HTTPException) as exc_info:
        ws_sessions._validate_session_name(session_name)

    assert exc_info.value.status_code == 400
