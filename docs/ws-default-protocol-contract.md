# WebSocket Default Protocol Contract

This document is the UI handoff contract for Code Puppy's default streaming protocol on `GET /ws/chat`.

## Source of truth

- Typed wire schema: `code_puppy/api/ws/schemas.py`
- Shareable JSON schema endpoint: `GET /api/protocol/schema`
- Runtime emitters: `code_puppy/api/ws/chat_handler.py`, `code_puppy/api/ws/ws_session_bootstrap.py`, `code_puppy/api/ws/session_persistence.py`, `code_puppy/api/ws/response_frames.py`

## Transport

- **WebSocket URL:** `/ws/chat`
- **Optional query param:** `session_id=<existing session id>` to resume an existing thread
- **Encoding:** JSON objects
- **Serialization rule:** optional `null` fields are omitted from the wire payload

## Connection bootstrap

When a client connects, expect this startup sequence:

1. `system` — connection acknowledgement with `session_id`, active `agent_name`, active `model_name`, and `protocol_version`
2. `session_meta` — authoritative session snapshot for header/sidebar state
3. `session_restored` — only when reconnecting to an existing session
4. zero or more replayed `system` messages for restored sessions

### Example bootstrap

```json
{
  "type": "system",
  "content": "Connected! Session: WS_session_20260901_154600_deadbeef",
  "session_id": "WS_session_20260901_154600_deadbeef",
  "agent_name": "code-puppy",
  "model_name": "gpt-5.4",
  "resumed": false,
  "protocol_version": "1.0.0"
}
```

```json
{
  "type": "session_meta",
  "session_id": "WS_session_20260901_154600_deadbeef",
  "session_name": "WS_session_20260901_154600_deadbeef",
  "total_tokens": 0,
  "message_count": 0,
  "title": "",
  "working_directory": "/Users/example/project",
  "agent_name": "code-puppy",
  "model_name": "gpt-5.4"
}
```

## Client → server messages

Core messages the UI should support:

- `message` — send a user turn; supports optional `model`, `model_settings`, and `attachments`
- `switch_agent`
- `switch_model`
- `switch_session`
- `set_working_directory`
- `update_session_meta`
- `get_config` / `set_config`
- `command`
- `cancel`
- `permission_response`
- browser-only prompt responses: `user_input_response`, `confirmation_response`, `selection_response`, `ask_user_question_response`

### Example user turn

```json
{
  "type": "message",
  "content": "Summarize the websocket contract changes.",
  "attachments": ["docs/notes.txt"]
}
```

## Server → client streaming frames

### Core streaming sequence

A normal assistant turn usually looks like:

1. `user_message`
2. `assistant_message_start`
3. one or more `assistant_message_delta`
4. `assistant_message_end`
5. zero or more `tool_call` / `tool_result` frames interleaved as tools run
6. `stream_end`
7. refreshed `session_meta`

### Important frame types

#### `assistant_message_start`
- Opens a renderable assistant part
- `part_type` is usually `text` or `thinking`
- `message_id` + `part_index` let the UI correlate deltas and end frames

#### `assistant_message_delta`
- Incremental text chunk for the active message part
- Append by `message_id`

#### `assistant_message_end`
- Closes the part and includes `full_content`

#### `tool_call`
- Announces a tool invocation
- Correlate with later `tool_result` using `tool_id`
- `tool_group_id` groups concurrent tool work

#### `tool_result`
- Final tool result payload
- `success` and `duration_ms` are safe to surface in tool UIs

#### `stream_end`
- Marks logical completion of the assistant stream
- `success=false` means the stream terminated because of an error
- token usage may be attached in `tokens`

#### `session_meta`
- Sent right after connect, after a session switch, and after a persisted turn
- Use it to refresh thread title, token count, message count, cwd, active agent, and active model

#### `error`
- Structured failure frame with `error_type`, `technical_details`, and `action_required` when available

#### `permission_request`
- Frontend must present approve/deny UX and answer with `permission_response`

## Reducer guidance

- Treat `session_id` as the primary thread key
- Build assistant parts by `message_id` and `part_index`
- Expect omitted optional fields instead of explicit `null`
- `session_meta` is a snapshot, not a patch; replace existing header/session state with the latest frame
- `response` still exists in schema for backward compatibility, but the default protocol here is streaming-first

## Recommended frontend test cases

1. New session connect bootstrap
2. Reconnect with `session_restored`
3. Text-only streaming turn
4. Turn with tool calls and grouped tool results
5. Permission request / response loop
6. Error after partial stream where `stream_end.success=false` precedes `error`

## Machine-readable contract

Use `GET /api/protocol/schema` for generated JSON Schema plus examples. This markdown is the human-readable companion for the same contract.
