"""Browser-only rich UI extension schemas.

These frames intentionally remain custom to the browser WebSocket client. ACP
uses its own protocol and can provide a plain-text fallback until structured
elicitation is standardized, so these models must not be mistaken for core
agent/session transport messages.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class _BrowserUIExtensionMessage(BaseModel):
    """Shared permissive config for browser extension frames."""

    model_config = {"extra": "allow"}


class ClientUserInputResponse(_BrowserUIExtensionMessage):
    """Response to a free-form input prompt emitted by the runtime."""

    type: Literal["user_input_response"] = "user_input_response"
    prompt_id: str
    value: str


class ClientConfirmationResponse(_BrowserUIExtensionMessage):
    """Response to a confirmation prompt emitted by the runtime."""

    type: Literal["confirmation_response"] = "confirmation_response"
    prompt_id: str
    confirmed: bool
    feedback: Optional[str] = None


class ClientSelectionResponse(_BrowserUIExtensionMessage):
    """Response to an option-selection prompt emitted by the runtime."""

    type: Literal["selection_response"] = "selection_response"
    prompt_id: str
    selected_index: int
    selected_value: str


class ClientAskUserQuestionResponse(_BrowserUIExtensionMessage):
    """Response to a structured ask_user_question prompt emitted by the runtime."""

    type: Literal["ask_user_question_response"] = "ask_user_question_response"
    prompt_id: str
    answers: List[Dict[str, Any]] = Field(default_factory=list)
    cancelled: bool = False


class ServerUserInputRequest(_BrowserUIExtensionMessage):
    """Ask the browser UI to collect free-form text from the user."""

    type: Literal["user_input_request"] = "user_input_request"
    prompt_id: str
    prompt_text: str
    session_id: str
    default_value: Optional[str] = None
    input_type: Literal["text", "password"] = "text"


class ServerConfirmationRequest(_BrowserUIExtensionMessage):
    """Ask the browser UI to collect a yes/no-style confirmation."""

    type: Literal["confirmation_request"] = "confirmation_request"
    prompt_id: str
    title: str
    description: str
    session_id: str
    options: List[str] = []
    allow_feedback: bool = False


class ServerSelectionRequest(_BrowserUIExtensionMessage):
    """Ask the browser UI to collect one selected option from a list."""

    type: Literal["selection_request"] = "selection_request"
    prompt_id: str
    prompt_text: str
    options: List[str]
    session_id: str
    allow_cancel: bool = True


class ServerAskUserQuestionRequest(_BrowserUIExtensionMessage):
    """Ask the browser UI to collect structured ask_user_question answers."""

    type: Literal["ask_user_question_request"] = "ask_user_question_request"
    prompt_id: str
    questions: List[Dict[str, Any]]
    session_id: str
    timeout_seconds: int = 300
