"""Tests for browser-specific rich UI extension helpers."""

from pydantic import TypeAdapter

from code_puppy.api.ws.schemas import (
    ClientAskUserQuestionResponse as LegacyClientAskUserQuestionResponse,
    ClientMessage,
    ServerMessage,
    ServerUserInputRequest as LegacyServerUserInputRequest,
)
from code_puppy.api.ws.ui_extension_schemas import (
    ClientAskUserQuestionResponse,
    ServerUserInputRequest,
)
from code_puppy.api.ws.ui_extensions import (
    build_browser_ui_extension_message,
    is_browser_ui_extension_response,
)
from code_puppy.messaging.messages import (
    AskUserQuestionRequest,
    ConfirmationRequest,
    SelectionRequest,
    UserInputRequest,
)


def test_browser_extension_schemas_are_reexported_and_stay_in_protocol_unions():
    assert LegacyClientAskUserQuestionResponse is ClientAskUserQuestionResponse
    assert LegacyServerUserInputRequest is ServerUserInputRequest

    client_message = TypeAdapter(ClientMessage).validate_python(
        {
            "type": "ask_user_question_response",
            "prompt_id": "prompt-1",
            "answers": [],
            "cancelled": False,
        }
    )
    server_message = TypeAdapter(ServerMessage).validate_python(
        {
            "type": "user_input_request",
            "prompt_id": "prompt-1",
            "prompt_text": "Name?",
            "session_id": "session-1",
        }
    )

    assert isinstance(client_message, ClientAskUserQuestionResponse)
    assert isinstance(server_message, ServerUserInputRequest)


def test_is_browser_ui_extension_response_recognizes_only_extension_frames():
    assert is_browser_ui_extension_response({"type": "ask_user_question_response"})
    assert not is_browser_ui_extension_response({"type": "message"})
    assert not is_browser_ui_extension_response({})


def test_build_browser_ui_extension_message_for_user_input_request():
    message = build_browser_ui_extension_message(
        UserInputRequest(
            prompt_id="prompt-1",
            prompt_text="Name?",
            default_value="Gamja",
            input_type="text",
        ),
        session_id="session-1",
    )

    assert message is not None
    assert message.type == "user_input_request"
    assert message.prompt_id == "prompt-1"
    assert message.prompt_text == "Name?"
    assert message.default_value == "Gamja"
    assert message.input_type == "text"
    assert message.session_id == "session-1"


def test_build_browser_ui_extension_message_for_confirmation_request():
    message = build_browser_ui_extension_message(
        ConfirmationRequest(
            prompt_id="prompt-2",
            title="Proceed?",
            description="Ship it?",
            options=["yes", "no"],
            allow_feedback=True,
        ),
        session_id="session-2",
    )

    assert message is not None
    assert message.type == "confirmation_request"
    assert message.prompt_id == "prompt-2"
    assert message.title == "Proceed?"
    assert message.description == "Ship it?"
    assert message.options == ["yes", "no"]
    assert message.allow_feedback is True
    assert message.session_id == "session-2"


def test_build_browser_ui_extension_message_for_selection_request():
    message = build_browser_ui_extension_message(
        SelectionRequest(
            prompt_id="prompt-3",
            prompt_text="Pick one",
            options=["A", "B"],
            allow_cancel=False,
        ),
        session_id="session-3",
    )

    assert message is not None
    assert message.type == "selection_request"
    assert message.prompt_id == "prompt-3"
    assert message.prompt_text == "Pick one"
    assert message.options == ["A", "B"]
    assert message.allow_cancel is False
    assert message.session_id == "session-3"


def test_build_browser_ui_extension_message_for_ask_user_question_request():
    message = build_browser_ui_extension_message(
        AskUserQuestionRequest(
            prompt_id="prompt-4",
            questions=[
                {
                    "header": "Color",
                    "question": "Favorite color?",
                    "options": [{"label": "Blue"}],
                }
            ],
            timeout_seconds=123,
        ),
        session_id="session-4",
    )

    assert message is not None
    assert message.type == "ask_user_question_request"
    assert message.prompt_id == "prompt-4"
    assert message.questions == [
        {
            "header": "Color",
            "question": "Favorite color?",
            "options": [{"label": "Blue"}],
        }
    ]
    assert message.timeout_seconds == 123
    assert message.session_id == "session-4"


def test_build_browser_ui_extension_message_returns_none_for_unknown_request():
    assert build_browser_ui_extension_message(object(), session_id="session-5") is None
