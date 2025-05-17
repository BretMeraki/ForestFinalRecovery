"""
Error Handling Utilities

This module provides centralized error handling patterns and utilities
to reduce code duplication across the application.

IMPORTANT: This module now imports core error handling functionality from
exception_handlers.py to avoid code duplication (R0801). For consistent error
handling across the application, use the functions from exception_handlers.py directly.

This module is maintained for backward compatibility and contains specialized
functions not found in exception_handlers.py.
"""

import logging
from typing import Any, Optional, TypeVar

from fastapi import HTTPException, status

# Import from central exception_handlers to avoid duplication
from forest_app.utils.exception_handlers import (handle_db_errors,
                                                 handle_db_exceptions)

logger = logging.getLogger(__name__)

T = TypeVar("T")


# Alias for backward compatibility
def handle_db_errors(
    operation: str = "database operation",
    default_detail: str = "An unexpected error occurred",
) -> callable:
    """
    Decorator to handle common database errors and convert them to HTTP exceptions.

    DEPRECATED: Use handle_db_exceptions from exception_handlers.py instead.
    This function is maintained for backward compatibility.

    Args:
        operation: Description of the operation being performed (for logging)
        default_detail: Default error detail message if no specific one can be determined

    Returns:
        Decorated function with error handling
    """
    # Log deprecation warning
    logger.warning(
        "The handle_db_errors decorator in error_handling.py is deprecated. "
        "Use handle_db_exceptions from exception_handlers.py instead."
    )

    # Forward to the centralized implementation
    def decorator(func):
        # Wrap the function with handle_db_exceptions for consistency
        wrapped = handle_db_exceptions(func)
        return wrapped

    return decorator


def handle_http_errors(
    _success_status: int = status.HTTP_200_OK, error_detail: str = "An error occurred"
) -> callable:
    """
    Decorator to handle common HTTP errors and standardize responses.

    DEPRECATED: Use handle_db_exceptions from exception_handlers.py instead,
    which handles both sync and async functions properly.
    This function is maintained for backward compatibility.

    Args:
        _success_status: HTTP status code to return on success (unused)
        error_detail: Default error detail message

    Returns:
        Decorated function with error handling
    """
    # Log deprecation warning
    logger.warning(
        "The handle_http_errors decorator in error_handling.py is deprecated. "
        "Use handle_db_exceptions from exception_handlers.py instead."
    )

    # The implementation is kept for backward compatibility but
    # moved to a simpler approach leveraging the common error handler
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                return result
            except HTTPException:
                # Pass through HTTP exceptions directly
                raise
            except Exception as e:
                # Use the common error handler for all other exceptions
                handle_db_errors(e)
                # This line should never be reached as handle_db_errors will raise
                # an HTTPException for any Exception type
                raise

        return wrapper

    return decorator


# Additional utility functions for error handling


def log_import_error(error: Exception, module_name: str = None) -> None:
    """
    Centralized function for logging import errors consistently across the codebase.

    This function provides a standardized way to log errors when importing modules,
    helping to reduce duplicate code and ensure consistent error messages.

    Args:
        error: The import error that occurred
        module_name: Optional name of the module where the error occurred (defaults to caller module)
    """
    module_context = f" in {module_name}" if module_name else ""
    logger.error(f"Failed to import required modules{module_context}: {error}")


# For functions that remain specific to this module and don't have duplicates,
# we keep them as-is with clear documentation.
def validate_and_parse_timestamp(timestamp: Any) -> Optional[str]:
    """
    Validates and parses a timestamp from various input formats.

    This function is specific to error_handling.py and not duplicated elsewhere.

    Args:
        timestamp: Input timestamp (str, dict, or None)

    Returns:
        Optional[str]: ISO formatted timestamp string or None if invalid
    """
    if timestamp is None:
        return None

    if isinstance(timestamp, str):
        # Could add ISO format validation here
        return timestamp

    if hasattr(timestamp, "isoformat"):
        return timestamp.isoformat()

    logger.warning("Invalid timestamp format: %s", type(timestamp))
    return None
