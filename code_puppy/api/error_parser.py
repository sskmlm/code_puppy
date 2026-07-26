"""Error parsing utilities for API errors.

Provides human-readable error messages and actionable guidance for common API errors.
"""

import logging
import re
from typing import Any, Dict

logger = logging.getLogger(__name__)


def parse_api_error(error: Exception) -> Dict[str, Any]:
    """Parse API errors into user-friendly messages with actionable guidance."""
    error_str = str(error)
    error_type_name = type(error).__name__

    logger.debug(
        "parse_api_error: incoming type=%s msg=%r",
        error_type_name,
        error_str[:400],
    )

    if _is_quota_exceeded_error(error_str):
        return {
            "error_type": "quota_exceeded",
            "user_message": "Your API quota has been exceeded for the current model. Please switch to a different model and click continue to retry your request.",
            "technical_details": _extract_quota_details(error_str),
            "action_required": "switch_model",
            "original_error": error_str,
        }
    if _is_rate_limit_error(error_str):
        return {
            "error_type": "rate_limit",
            "user_message": "You're making requests too quickly. Please wait a moment and try again, or switch to a different model.",
            "technical_details": error_str,
            "action_required": "wait_or_switch_model",
            "original_error": error_str,
        }
    if _is_auth_error(error_str):
        return {
            "error_type": "auth_error",
            "user_message": "Authentication failed. Please check your credentials or API key configuration.",
            "technical_details": error_str,
            "action_required": "check_credentials",
            "original_error": error_str,
        }
    if _is_network_error(error_str, error_type_name):
        return {
            "error_type": "network_error",
            "user_message": "Network connection failed. Please check your internet connection and try again.",
            "technical_details": error_str,
            "action_required": "retry",
            "original_error": error_str,
        }
    if _is_model_not_found_error(error_str):
        return {
            "error_type": "model_not_found",
            "user_message": "The requested model is not available. Please switch to a different model.",
            "technical_details": error_str,
            "action_required": "switch_model",
            "original_error": error_str,
        }
    if _is_claude_temperature_thinking_error(error_str):
        return {
            "error_type": "claude_temperature_error",
            "user_message": "Claude's extended thinking mode requires temperature to be set to 1.0. Please adjust your model settings or disable extended thinking.",
            "technical_details": error_str,
            "action_required": "adjust_temperature",
            "original_error": error_str,
        }

    return {
        "error_type": "unknown",
        "user_message": f"An unexpected error occurred: {error_str}",
        "technical_details": error_str,
        "action_required": None,
        "original_error": error_str,
    }


def _is_quota_exceeded_error(error_str: str) -> bool:
    quota_patterns = [
        r"quota\s+exceeded",
        r"insufficient\s+quota",
        r"billing\s+quota",
        r"exceeded\s+your\s+current\s+quota",
        r"429.*quota",
    ]
    return any(
        re.search(pattern, error_str, re.IGNORECASE) for pattern in quota_patterns
    )


def _extract_quota_details(error_str: str) -> str:
    if len(error_str) > 500:
        return error_str[:500] + "..."
    return error_str


def _is_rate_limit_error(error_str: str) -> bool:
    rate_limit_patterns = [
        r"rate\s+limit",
        r"too\s+many\s+requests",
        r"429(?!.*quota)",
        r"requests\s+too\s+quickly",
    ]
    return any(
        re.search(pattern, error_str, re.IGNORECASE) for pattern in rate_limit_patterns
    )


def _is_auth_error(error_str: str) -> bool:
    auth_patterns = [
        r"authentication",
        r"unauthorized",
        r"invalid\s+api\s+key",
        r"forbidden",
        r"permission\s+denied",
        r"401",
        r"403",
    ]
    return any(
        re.search(pattern, error_str, re.IGNORECASE) for pattern in auth_patterns
    )


def _is_network_error(error_str: str, error_type_name: str) -> bool:
    network_patterns = [r"timeout", r"connection", r"network", r"dns", r"socket"]
    type_patterns = ["TimeoutError", "ConnectionError", "NetworkError"]
    return (
        any(
            re.search(pattern, error_str, re.IGNORECASE) for pattern in network_patterns
        )
        or error_type_name in type_patterns
    )


def _is_model_not_found_error(error_str: str) -> bool:
    model_patterns = [r"model.*not.*found", r"unknown\s+model", r"invalid\s+model"]
    return any(
        re.search(pattern, error_str, re.IGNORECASE) for pattern in model_patterns
    )


def _is_claude_temperature_thinking_error(error_str: str) -> bool:
    patterns = [
        r"temperature.*1\.0",
        r"thinking.*temperature",
        r"extended thinking.*temperature",
    ]
    return any(re.search(pattern, error_str, re.IGNORECASE) for pattern in patterns)
