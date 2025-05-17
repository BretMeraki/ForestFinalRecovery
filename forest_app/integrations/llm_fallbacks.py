"""
LLM Fallback Classes

This module provides centralized fallback implementations for LLM-related components
when the actual LLM implementation fails to import or is not available.

Usage:
    try:
        from forest_app.core.llm.client import LLMClient, LLMError  # Real implementation
    except ImportError:
        from forest_app.integrations.llm_fallbacks import LLMClient, LLMError  # Fallbacks
"""

import logging

logger = logging.getLogger(__name__)


# --- LLM Base Exception Classes ---
class LLMError(Exception):
    """Base exception for all LLM-related errors."""

    pass


class LLMValidationError(LLMError):
    """Exception raised for LLM response validation failures."""

    pass


class LLMConfigurationError(LLMError):
    """Exception raised for LLM configuration issues."""

    pass


class LLMConnectionError(LLMError):
    """Exception raised for LLM connection problems."""

    pass


# --- LLM Client Fallback Implementation ---
class LLMClient:
    """Fallback LLM client implementation when actual client is unavailable."""

    def __init__(self, *_args, **_kwargs):
        logger.warning(
            "Using fallback LLM client. LLM functionality will not be available."
        )

    def __call__(self, *_args, **_kwargs):
        logger.warning(
            "Called fallback LLM client with args=%s, kwargs=%s", _args, _kwargs
        )
        return None


def get_llm_fallbacks():
    """
    Returns all LLM fallback classes as a tuple.

    Returns:
        tuple: (LLMClient, LLMError, LLMValidationError, LLMConfigurationError, LLMConnectionError)
    """
    return (
        LLMClient,
        LLMError,
        LLMValidationError,
        LLMConfigurationError,
        LLMConnectionError,
    )
