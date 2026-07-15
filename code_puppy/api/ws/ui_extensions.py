"""Browser UI extension helpers for rich user interactions.

ACP can own the core session/prompt/tool protocol later, but these richer
browser-specific interactions still need a stable home today. This module
keeps that transport glue in one place so the WebSocket handler and active-turn
runner do not each grow their own little pile of schema trivia.
"""

from __future__ import annotations

from typing import Any

from code_puppy.api.ws.ui_extension_schemas import (
    ServerAskUserQuestionRequest,
    ServerConfirmationRequest,
    ServerSelectionRequest,
    ServerUserInputRequest,
)
from code_puppy.messaging.bus import get_message_bus
from code_puppy.messaging.commands import (
    AskUserQuestionResponse,
    ConfirmationResponse,
    SelectionResponse,
    UserInputResponse,
)
from code_puppy.messaging.messages import (
    AskUserQuestionRequest,
    ConfirmationRequest,
    SelectionRequest,
    UserInputRequest,
)

_BROWSER_UI_RESPONSE_TYPES = frozenset(
    {
        "user_input_response",
        "confirmation_response",
        "selection_response",
        "ask_user_question_response",
    }
)


def is_browser_ui_extension_response(message: dict[str, Any]) -> bool:
    """Return whether a client frame belongs to the browser UI extension."""
    return message.get("type") in _BROWSER_UI_RESPONSE_TYPES


def build_browser_ui_extension_message(
    request: Any, *, session_id: str
) -> (
    ServerUserInputRequest
    | ServerConfirmationRequest
    | ServerSelectionRequest
    | ServerAskUserQuestionRequest
    | None
):
    """Translate a MessageBus UI request into the browser-specific WS schema."""
    if isinstance(request, UserInputRequest):
        return ServerUserInputRequest(
            prompt_id=request.prompt_id,
            prompt_text=request.prompt_text,
            default_value=request.default_value,
            input_type=request.input_type,
            session_id=session_id,
        )
    if isinstance(request, ConfirmationRequest):
        return ServerConfirmationRequest(
            prompt_id=request.prompt_id,
            title=request.title,
            description=request.description,
            options=request.options,
            allow_feedback=request.allow_feedback,
            session_id=session_id,
        )
    if isinstance(request, SelectionRequest):
        return ServerSelectionRequest(
            prompt_id=request.prompt_id,
            prompt_text=request.prompt_text,
            options=request.options,
            allow_cancel=request.allow_cancel,
            session_id=session_id,
        )
    if isinstance(request, AskUserQuestionRequest):
        return ServerAskUserQuestionRequest(
            prompt_id=request.prompt_id,
            questions=request.questions,
            timeout_seconds=request.timeout_seconds,
            session_id=session_id,
        )
    return None


def handle_browser_ui_extension_response(message: dict[str, Any]) -> bool:
    """Resolve a browser-specific rich UI response back onto the MessageBus."""
    if not is_browser_ui_extension_response(message):
        return False
    msg_type = message["type"]

    bus = get_message_bus()
    if msg_type == "user_input_response":
        bus.provide_response(
            UserInputResponse(
                prompt_id=message.get("prompt_id", ""),
                value=message.get("value", ""),
            )
        )
    elif msg_type == "confirmation_response":
        bus.provide_response(
            ConfirmationResponse(
                prompt_id=message.get("prompt_id", ""),
                confirmed=bool(message.get("confirmed", False)),
                feedback=message.get("feedback"),
            )
        )
    elif msg_type == "selection_response":
        bus.provide_response(
            SelectionResponse(
                prompt_id=message.get("prompt_id", ""),
                selected_index=int(message.get("selected_index", -1)),
                selected_value=message.get("selected_value", ""),
            )
        )
    else:
        bus.provide_response(
            AskUserQuestionResponse(
                prompt_id=message.get("prompt_id", ""),
                answers=message.get("answers") or [],
                cancelled=bool(message.get("cancelled", False)),
            )
        )
    return True
