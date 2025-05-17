"""
LLM Utilities Module

This module provides import and error handling utilities for LLM-related components
to reduce code duplication across the application.

The actual fallback implementations are now centralized in forest_app.integrations.llm_fallbacks.
"""

import logging

# Import centralized fallbacks
from forest_app.integrations.llm_fallbacks import get_llm_fallbacks

logger = logging.getLogger(__name__)


def create_llm_dummy_classes():
    """
    Returns dummy LLM classes when the actual LLM implementation fails to import.

    This is kept for backward compatibility. New code should use get_llm_fallbacks
    from forest_app.integrations.llm_fallbacks directly.

    Returns:
        tuple: (LLMClient, LLMError, LLMValidationError, LLMConfigurationError, LLMConnectionError)
    """
    return get_llm_fallbacks()


def handle_llm_import_error(error: Exception) -> tuple:
    """
    Handles LLM import errors by logging the error and returning dummy classes.

    Args:
        error: The import error that occurred

    Returns:
        tuple: (False, LLMClient, LLMError, LLMValidationError, LLMConfigurationError, LLMConnectionError)
    """
    logger.error(
        "Failed to import LLM integration components: %s. Check llm.py.", error
    )
    return (False,) + get_llm_fallbacks()
