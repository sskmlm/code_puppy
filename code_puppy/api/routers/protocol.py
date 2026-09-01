"""Protocol schema endpoint – exposes JSON Schema for the WebSocket protocol."""

from fastapi import APIRouter
from pydantic import TypeAdapter

from code_puppy.api.ws.schemas import (
    PROTOCOL_VERSION,
    ClientMessage,
    ServerMessage,
)

router = APIRouter()

# Cache the schemas since they don't change at runtime
_client_schema = TypeAdapter(ClientMessage).json_schema()
_server_schema = TypeAdapter(ServerMessage).json_schema()

_WS_CHAT_EXAMPLES = {
    "connect": {
        "request": "GET /ws/chat?session_id=<optional-existing-session-id>",
        "server_frames": [
            {
                "type": "system",
                "content": "Connected! Session: WS_session_20260901_154600_deadbeef",
                "session_id": "WS_session_20260901_154600_deadbeef",
                "agent_name": "code-puppy",
                "model_name": "gpt-5.4",
                "resumed": False,
                "protocol_version": PROTOCOL_VERSION,
            },
            {
                "type": "session_meta",
                "session_id": "WS_session_20260901_154600_deadbeef",
                "session_name": "WS_session_20260901_154600_deadbeef",
                "total_tokens": 0,
                "message_count": 0,
                "title": "",
                "working_directory": "/Users/example/project",
                "agent_name": "code-puppy",
                "model_name": "gpt-5.4",
            },
        ],
    },
    "chat_turn": {
        "client_message": {
            "type": "message",
            "content": "Summarize the websocket contract changes.",
            "attachments": ["docs/notes.txt"],
        },
        "server_frames": [
            {
                "type": "user_message",
                "content": "Summarize the websocket contract changes.",
                "session_id": "WS_session_20260901_154600_deadbeef",
            },
            {
                "type": "assistant_message_start",
                "message_id": "msg-1725205560-0",
                "part_type": "text",
                "part_index": 0,
                "timestamp": 1725205560.123,
                "session_id": "WS_session_20260901_154600_deadbeef",
                "agent_name": "code-puppy",
                "model_name": "gpt-5.4",
            },
            {
                "type": "assistant_message_delta",
                "message_id": "msg-1725205560-0",
                "content": "Here is the summary...",
                "part_index": 0,
                "session_id": "WS_session_20260901_154600_deadbeef",
                "agent_name": "code-puppy",
                "model_name": "gpt-5.4",
            },
            {
                "type": "assistant_message_end",
                "message_id": "msg-1725205560-0",
                "part_type": "text",
                "part_index": 0,
                "full_content": "Here is the summary...",
                "timestamp": 1725205560.456,
                "session_id": "WS_session_20260901_154600_deadbeef",
                "agent_name": "code-puppy",
                "model_name": "gpt-5.4",
            },
            {
                "type": "stream_end",
                "success": True,
                "total_length": 22,
                "session_id": "WS_session_20260901_154600_deadbeef",
                "agent_name": "code-puppy",
                "model_name": "gpt-5.4",
                "tokens": {"total_tokens": 42},
            },
            {
                "type": "session_meta",
                "session_id": "WS_session_20260901_154600_deadbeef",
                "session_name": "WS_session_20260901_154600_deadbeef",
                "total_tokens": 42,
                "message_count": 2,
                "title": "summarize-the-websocket-contract-changes",
                "working_directory": "/Users/example/project",
                "agent_name": "code-puppy",
                "model_name": "gpt-5.4",
            },
        ],
    },
}


@router.get("/schema")
async def get_protocol_schema():
    """Return the WebSocket protocol JSON Schema for client consumption."""
    return {
        "protocol_version": PROTOCOL_VERSION,
        "transport": {
            "websocket_path": "/ws/chat",
            "query_parameters": {
                "session_id": {
                    "required": False,
                    "description": "Existing websocket session ID to resume; omit to create a new session.",
                }
            },
            "message_encoding": "json",
            "serialization": "model_dump(exclude_none=True)",
        },
        "client_messages": _client_schema,
        "server_messages": _server_schema,
        "examples": _WS_CHAT_EXAMPLES,
        "notes": [
            "This contract covers the default /ws/chat protocol only.",
            "The server sends an initial system frame followed by session_meta after connect.",
            "Successful streaming turns normally end with stream_end and then a refreshed session_meta snapshot.",
        ],
    }
