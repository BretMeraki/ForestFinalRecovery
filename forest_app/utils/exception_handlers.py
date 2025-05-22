"""
Exception Handling Utilities

This module provides centralized handling for common exception patterns
to reduce code duplication across the application.

Note: For database-specific error handling, use forest_app.utils.db_helpers instead,
which provides more granular control and standardized database operation patterns.
"""

import logging
from functools import wraps
from typing import Any, Callable, Dict, Type, TypeVar, Union, cast, Awaitable

from fastapi import HTTPException, Request, status
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from forest_app.utils.import_fallbacks import import_with_fallback

logger = logging.getLogger(__name__)

KEY_DETAIL = import_with_fallback(
    lambda: __import__('forest_app.config.app_constants', fromlist=['KEY_DETAIL']).KEY_DETAIL,
    lambda: "detail",
    logger,
    "KEY_DETAIL"
)
KEY_ERROR = import_with_fallback(
    lambda: __import__('forest_app.config.app_constants', fromlist=['KEY_ERROR']).KEY_ERROR,
    lambda: "error",
    logger,
    "KEY_ERROR"
)
KEY_STATUS_CODE = import_with_fallback(
    lambda: __import__('forest_app.config.app_constants', fromlist=['KEY_STATUS_CODE']).KEY_STATUS_CODE,
    lambda: "status_code",
    logger,
    "KEY_STATUS_CODE"
)

# Type variable for return values
T = TypeVar("T")


def handle_db_exceptions(func: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[return]
    """
    Decorator that handles database exceptions and converts them to appropriate
    HTTP exceptions with proper status codes.

    Note: For more granular database error handling, consider using
    forest_app.utils.db_helpers.safe_db_operation instead.

    Args:
        func: The function to decorate

    Returns:
        Wrapped function that handles SQLAlchemy and validation errors
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:  # type: ignore[return]
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception("Unexpected error: %s", str(e))
            raise
    return wrapper


def handle_db_errors(db_val_err: Exception) -> None:
    """
    Handles database and validation errors by raising appropriate HTTP exceptions.
    This function can be used in try/except blocks when the decorator pattern
    isn't suitable.

    Note: For more advanced error handling, consider using functions from
    forest_app.utils.db_helpers which provide more detailed error categorization.

    Args:
        db_val_err: The caught exception

    Raises:
        HTTPException: With appropriate status code and detail message
    """
    if isinstance(db_val_err, NoResultFound):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found"
        ) from db_val_err
    elif isinstance(db_val_err, IntegrityError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Data integrity constraint violation",
        ) from db_val_err
    elif isinstance(db_val_err, SQLAlchemyError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        ) from db_val_err
    elif isinstance(db_val_err, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid data: {db_val_err}",
        ) from db_val_err
    elif isinstance(db_val_err, PydanticValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Validation error", "errors": db_val_err.errors()},
        ) from db_val_err
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred",
        ) from db_val_err


def create_standard_exception_handlers() -> Dict[Type[Exception], Callable]:
    """
    Creates a dictionary of exception handlers that can be registered with FastAPI
    for global exception handling. Produces standardized error responses.

    Usage:
        app = FastAPI()
        exception_handlers = create_standard_exception_handlers()
        for exc_type, handler in exception_handlers.items():
            app.add_exception_handler(exc_type, handler)

    Returns:
        Dictionary mapping exception types to handler functions
    """

    async def handle_sqlalchemy_error(
        _request: Request, exc: SQLAlchemyError
    ) -> Dict[str, Any]:
        logger.error("SQLAlchemy error: %s", str(exc))
        return {
            KEY_STATUS_CODE: status.HTTP_503_SERVICE_UNAVAILABLE,
            KEY_ERROR: "database_error",
            KEY_DETAIL: "Database service unavailable. Please try again later.",
        }

    async def handle_validation_error(
        _request: Request, exc: Union[ValueError, PydanticValidationError]
    ) -> Dict[str, Any]:
        logger.warning("Validation error: %s", str(exc))
        detail = exc.errors() if isinstance(exc, PydanticValidationError) else str(exc)
        return {
            KEY_STATUS_CODE: (
                status.HTTP_422_UNPROCESSABLE_ENTITY
                if isinstance(exc, PydanticValidationError)
                else status.HTTP_400_BAD_REQUEST
            ),
            KEY_ERROR: "validation_error",
            KEY_DETAIL: detail,
        }

    async def handle_general_exception(
        _request: Request, exc: Exception
    ) -> Dict[str, Any]:
        logger.exception("Unexpected error: %s", str(exc))
        return {
            KEY_STATUS_CODE: status.HTTP_500_INTERNAL_SERVER_ERROR,
            KEY_ERROR: "internal_server_error",
            KEY_DETAIL: "An unexpected error occurred. Please try again later.",
        }

    return {
        SQLAlchemyError: handle_sqlalchemy_error,
        ValueError: handle_validation_error,
        PydanticValidationError: handle_validation_error,
        Exception: handle_general_exception,
    }


# --- Async error handler decorator ---
def handle_async_errors(fn: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    @wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> T:
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(fn.__module__)
            logger.error(f"Async error in {fn.__name__}: {e}")
            raise
    return cast(Callable[..., Awaitable[T]], wrapper)
