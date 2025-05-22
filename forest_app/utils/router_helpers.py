"""
Router Helpers Module

This module provides centralized helper functions for FastAPI router implementations
to reduce code duplication and ensure consistent error handling patterns.
"""

import logging
from typing import Any, Callable, TypeVar, Awaitable, cast
import functools

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

# Type variable for return values
T = TypeVar("T")

logger = logging.getLogger(__name__)


def handle_router_exceptions(
    user_id: Any,
    operation_name: str,
    validation_detail: str = "Invalid input data",
    db_detail: str = "Database service unavailable",
) -> Callable:
    """
    A decorator for router endpoints to handle common exceptions in a standardized way.
    This follows the Triad of Quality mandate by ensuring consistent error handling
    across all router endpoints.

    Args:
        user_id: User identifier for logging purposes
        operation_name: A description of the operation being performed (for logs)
        validation_detail: Detail message for validation errors
        db_detail: Detail message for database errors

    Returns:
        A decorator function to wrap router endpoint functions
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except HTTPException:
                # Pass through HTTP exceptions directly
                raise
            except (ValueError, TypeError, AttributeError, ValidationError) as data_err:
                logger.exception(
                    "Data/Validation error in %s for user %s: %s",
                    operation_name,
                    user_id,
                    data_err,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"{validation_detail}: {data_err}",
                ) from data_err
            except SQLAlchemyError as db_err:
                logger.exception(
                    "Database error in %s for user %s: %s",
                    operation_name,
                    user_id,
                    db_err,
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=db_detail,
                ) from db_err
            except Exception as e:  # noqa: W0718
                # Broad catch is intentional to ensure FastAPI endpoint robustness
                logger.exception(
                    "Unexpected error in %s for user %s: %s",
                    operation_name,
                    user_id,
                    e,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Internal error: {e}",
                ) from e

        return wrapper

    return decorator


def commit_and_refresh_db(
    db: Any, model_to_refresh: Any, user_id: Any, action_description: str
) -> Any:
    """
    Commit changes to the database and refresh the model data.
    Provides standardized error handling for database commit operations.

    Args:
        db: Database session
        model_to_refresh: Model instance to refresh after commit
        user_id: User identifier for logging purposes
        action_description: Description of the action being committed (for logs)

    Returns:
        The refreshed model

    Raises:
        HTTPException: If there's an error during commit or refresh
    """
    try:
        db.commit()
        db.refresh(model_to_refresh)
        logger.info(
            "Successfully committed %s for user %s", action_description, user_id
        )
        return model_to_refresh
    except SQLAlchemyError as db_err:
        db.rollback()
        logger.exception(
            "Database error committing %s for user %s: %s",
            action_description,
            user_id,
            db_err,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error during {action_description}",
        ) from db_err


# --- Async router helper decorator ---
def async_router_helper(fn: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[return]
    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:  # type: ignore[return]
        try:
            return await fn(*args, **kwargs)
        except Exception as e:
            logger = logging.getLogger(fn.__module__)
            logger.error(f"Async error in router helper {fn.__name__}: {e}")
            raise
    return wrapper
