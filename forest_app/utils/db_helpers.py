"""
Database Helper Utilities

This module provides centralized patterns for common database operations
to reduce code duplication and standardize error handling across the application.
"""

import logging
from typing import Any, Callable, Dict, Optional, Type, TypeVar, cast

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import DeclarativeMeta

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Any)  # Consider binding to Base if available


def safe_db_operation(
    operation_name: str,
    session: Session,
    not_found_message: Optional[str] = None,
    integrity_message: Optional[str] = None,
    default_error_message: str = "Database operation failed",
    log_result: bool = False,
) -> Callable[..., Any]:  # type: ignore[return]
    """
    Decorator for database operations with standardized error handling.

    Args:
        operation_name: Name of the operation for logging purposes
        session: SQLAlchemy database session
        not_found_message: Custom message for NoResultFound errors
        integrity_message: Custom message for IntegrityError errors
        default_error_message: Default error message for other exceptions
        log_result: Whether to log the operation result (may be verbose)

    Returns:
        Decorator function that wraps database operations with error handling
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:  # type: ignore[return]
        def wrapper(*args, **kwargs) -> Any:
            try:
                result = func(*args, **kwargs)
                if log_result:
                    logger.debug(
                        "DB operation '%s' succeeded: %s", operation_name, result
                    )
                return result
            except NoResultFound as e:
                message = not_found_message or "Resource not found"
                logger.warning(
                    "DB operation '%s' - not found: %s", operation_name, str(e)
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail=message
                ) from e
            except IntegrityError as e:
                message = integrity_message or "Data integrity constraint violated"
                logger.warning(
                    "DB operation '%s' - integrity error: %s", operation_name, str(e)
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT, detail=message
                ) from e
            except SQLAlchemyError as e:
                logger.error(
                    "DB operation '%s' - database error: %s", operation_name, str(e)
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Database service unavailable. Please try again later.",
                ) from e
            except ValueError as e:
                logger.warning(
                    "DB operation '%s' - validation error: %s", operation_name, str(e)
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
                ) from e
            except Exception as e:
                logger.exception("DB operation '%s' - unexpected error", operation_name)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=default_error_message,
                ) from e
            finally:
                # No session commit/rollback here as it should be managed by the caller
                pass

        return wrapper

    return decorator


def commit_with_rollback(
    session: Session, error_message: str = "Failed to commit changes to database"
) -> None:
    """
    Safely commit changes to the database with automatic rollback on error.

    Args:
        session: SQLAlchemy database session
        error_message: Error message to include in the raised HTTPException

    Raises:
        HTTPException: If the commit fails
    """
    try:
        session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        logger.error("Failed to commit to database: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=error_message,
        ) from e
    except Exception as e:
        session.rollback()
        logger.exception("Unexpected error during database commit")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_message,
        ) from e


def get_or_404(
    session: Session,
    model_class: Type[T],
    filter_criteria: Dict[str, Any],
    error_message: Optional[str] = None,
) -> T:
    """
    Get a database object or raise a 404 exception if not found.

    Args:
        session: SQLAlchemy database session
        model_class: SQLAlchemy model class to query
        filter_criteria: Dictionary of filter criteria
        error_message: Custom error message for 404 response

    Returns:
        Found database object

    Raises:
        HTTPException: With 404 status code if object not found
    """
    try:
        instance = session.query(model_class).filter_by(**filter_criteria).one()
        return instance
    except NoResultFound:
        model_name = getattr(model_class, "__name__", "Resource")
        criteria_str = ", ".join(f"{k}={v}" for k, v in filter_criteria.items())
        message = error_message or f"{model_name} with {criteria_str} not found"
        logger.warning("Resource not found: %s with %s", model_name, criteria_str)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    except SQLAlchemyError as e:
        logger.error("Database error in get_or_404: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable. Please try again later.",
        ) from e


def get_by_id(session: Session, model: Type[T], id_: Any) -> T | None:
    # Explicitly return None if not found
    result = session.query(model).get(id_)
    if result is not None:
        return result
    return None


def get_all(session: Session, model: Type[T]) -> list[T]:
    # Explicitly return an empty list if nothing found
    results = session.query(model).all()
    return results


def get_first(session: Session, model: Type[T], **filters) -> T | None:
    # Explicitly return None if not found
    result = session.query(model).filter_by(**filters).first()
    if result is not None:
        return result
    return None


def run_query(session: Session, model: Type[T], query_fn: Callable[[Any], Any]) -> Any:
    # Use type: ignore if type checker complains about model type
    query = session.query(model)  # type: ignore[arg-type]  # Model is a mapped class
    return query_fn(query)


def get_with_custom_filter(session: Session, model: Type[T], filter_fn: Callable[[Any], Any]) -> list[T]:
    query = session.query(model)  # type: ignore[arg-type]  # Model is a mapped class
    results = filter_fn(query)
    if results is None:
        return []
    return results
