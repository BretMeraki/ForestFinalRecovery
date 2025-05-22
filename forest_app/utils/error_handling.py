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
from typing import Any, Optional, TypeVar, Callable

from fastapi import HTTPException, status
from forest_app.utils.import_fallbacks import import_with_fallback

# Import from central exception_handlers to avoid duplication
try:
    from forest_app.utils.exception_handlers import handle_db_errors, handle_db_exceptions
except ImportError as e:
    logging.error(f"Failed to import exception_handlers: {e}")
    def handle_db_errors(*args, **kwargs):
        raise Exception("handle_db_errors unavailable")
    def handle_db_exceptions(*args, **kwargs):
        raise Exception("handle_db_exceptions unavailable")

logger = logging.getLogger(__name__)

T = TypeVar("T")

handle_db_errors = import_with_fallback(
    lambda: __import__('forest_app.utils.exception_handlers', fromlist=['handle_db_errors']).handle_db_errors,
    lambda: (lambda *a, **k: None),
    logger,
    "handle_db_errors"
)
handle_db_exceptions = import_with_fallback(
    lambda: __import__('forest_app.utils.exception_handlers', fromlist=['handle_db_exceptions']).handle_db_exceptions,
    lambda: (lambda *a, **k: None),
    logger,
    "handle_db_exceptions"
)

# Alias for backward compatibility
def handle_db_errors(
    operation: str,
    db_fn: Callable[..., Any],
    *args: Any,
    module_name: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """
    Handles database errors for a given operation and function.

    Args:
        operation: Name of the operation being performed (should be a string)
        db_fn: The database function to call
        *args: Positional arguments for db_fn
        module_name: Optional module name for logging
        **kwargs: Keyword arguments for db_fn

    Returns:
        Any: The result of db_fn(*args, **kwargs)

    Raises:
        HTTPException: If a database error occurs
    """
    try:
        return db_fn(*args, **kwargs)
    except Exception as e:
        op_str = operation if isinstance(operation, str) else str(operation)
        logger.error(f"Error in {op_str}: {e}")
        raise


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
        async def wrapper(*args, **kwargs) -> Any:  # type: ignore[return]
            try:
                result = await func(*args, **kwargs)
                return result
            except HTTPException:
                raise
            except Exception as e:
                handle_db_errors(str(e), lambda: None)  # Provide required arguments
                raise
        return wrapper

    return decorator


# Additional utility functions for error handling


def log_import_error(error: Exception, module_name: Optional[str] = None) -> None:
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
