import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import TypeAdapter, ValidationError

from code_puppy.api.routers import protocol as protocol_router
from code_puppy.api.ws.schemas import ClientMessage, ServerMessage, ServerSessionMeta


def _get_protocol_payload():
    app = FastAPI()
    app.include_router(protocol_router.router, prefix="/api/protocol")

    with TestClient(app) as client:
        resp = client.get("/api/protocol/schema")

    assert resp.status_code == 200
    return resp.json()


def test_protocol_schema_endpoint_exposes_ws_chat_contract_and_examples():
    payload = _get_protocol_payload()

    assert payload["protocol_version"] == "1.0.0"
    assert payload["transport"]["websocket_path"] == "/ws/chat"
    assert payload["transport"]["message_encoding"] == "json"
    assert payload["examples"]["connect"]["server_frames"][1]["type"] == "session_meta"
    assert (
        payload["examples"]["chat_turn"]["server_frames"][-1]["type"] == "session_meta"
    )


def test_protocol_schema_examples_validate_against_wire_unions():
    payload = _get_protocol_payload()
    client_adapter = TypeAdapter(ClientMessage)
    server_adapter = TypeAdapter(ServerMessage)

    client_adapter.validate_python(payload["examples"]["chat_turn"]["client_message"])
    for frame in payload["examples"]["connect"]["server_frames"]:
        server_adapter.validate_python(frame)
    for frame in payload["examples"]["chat_turn"]["server_frames"]:
        server_adapter.validate_python(frame)


def test_protocol_schema_includes_session_meta_in_server_message_union():
    payload = _get_protocol_payload()
    one_of = payload["server_messages"].get("oneOf", [])
    session_meta_entries = [
        entry for entry in one_of if entry.get("$ref", "").endswith("ServerSessionMeta")
    ]

    assert session_meta_entries
    defs = payload["server_messages"].get("$defs", {})
    session_meta_schema = defs["ServerSessionMeta"]
    assert session_meta_schema["properties"]["type"]["const"] == "session_meta"
    assert "session_id" in session_meta_schema["required"]
    assert "message_count" in session_meta_schema["required"]


def test_server_session_meta_requires_message_count():
    with pytest.raises(ValidationError):
        ServerSessionMeta(
            session_id="session-1",
            session_name="session-1",
            total_tokens=0,
            title="",
            working_directory="/tmp",
            agent_name="code-puppy",
            model_name="gpt-5",
        )
